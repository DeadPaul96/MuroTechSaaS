"""Servicio de facturación electrónica — lógica de negocio central."""
import logging
import uuid
from decimal import Decimal

from app.extensions import db
from app.models import Factura, FacturaDetalle, Sucursal
from app.utils.money import _parse_decimal, quantize_money
from app.utils.validators import ValidationError

logger = logging.getLogger(__name__)


class FacturaService:
    @staticmethod
    def create_invoice(data):
        """Crea una factura con sus detalles a partir de los datos proporcionados."""
        detalles = data.get('detalles', [])
        if not detalles:
            raise ValidationError('Debe enviar al menos un detalle de factura.')

        sucursal_id = data.get('sucursal_id')
        sucursal = Sucursal.query.get(sucursal_id)
        if not sucursal:
            raise ValidationError('Sucursal no encontrada.')

        tipo_doc = data.get('tipoDoc', '01')
        moneda = data.get('moneda', 'CRC')

        subtotal_total = Decimal('0.00')
        descuentos_total = Decimal('0.00')
        impuestos_total = Decimal('0.00')
        total_final = Decimal('0.00')

        nueva_factura = Factura(
            sucursal_id=sucursal.id,
            cliente_id=data.get('cliente_id'),
            numero_consecutivo=data.get('consecutivo', ''),
            clave=data.get('clave', ''),
            tipo_documento=tipo_doc,
            condicion_venta=data.get('condicionVenta', '01'),
            medio_pago=data.get('medioPago', '01'),
            moneda=moneda,
            tipo_cambio=data.get('tipo_cambio', 1.0),
            estado=data.get('estado', 'Pendiente'),
            is_draft=data.get('is_draft', False),
            usuario_id=data.get('usuario_id'),
            referencia_id=data.get('referencia_id'),
            referencia_codigo=data.get('referencia_codigo'),
            referencia_razon=data.get('referencia_razon'),
        )
        db.session.add(nueva_factura)
        db.session.flush()

        for idx, item in enumerate(detalles, start=1):
            cantidad = _parse_decimal(item.get('cantidad', 1))
            precio_unitario = _parse_decimal(item.get('precio', 0))
            porcentaje_descuento = _parse_decimal(item.get('descuento', 0))
            porcentaje_impuesto = _parse_decimal(item.get('impuesto', 13))

            monto_base = quantize_money(cantidad * precio_unitario)
            descuento_monto = quantize_money(monto_base * porcentaje_descuento / Decimal('100'))
            base_neta = quantize_money(monto_base - descuento_monto)
            impuesto_monto = quantize_money(base_neta * porcentaje_impuesto / Decimal('100'))
            total_linea = quantize_money(base_neta + impuesto_monto)

            subtotal_total += base_neta
            descuentos_total += descuento_monto
            impuestos_total += impuesto_monto
            total_final += total_linea

            detalle = FacturaDetalle(
                factura_id=nueva_factura.id,
                producto_id=item.get('producto_id'),
                descripcion=item.get('descripcion', item.get('nombre', 'Producto')),
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                porcentaje_descuento=porcentaje_descuento,
                porcentaje_impuesto=porcentaje_impuesto,
                tipo_impuesto=item.get('tipo_impuesto', '01'),
                total_linea=total_linea,
            )
            db.session.add(detalle)

        nueva_factura.subtotal = quantize_money(subtotal_total)
        nueva_factura.descuentos = quantize_money(descuentos_total)
        nueva_factura.impuestos = quantize_money(impuestos_total)
        nueva_factura.total = quantize_money(total_final)

        db.session.commit()
        return nueva_factura

    @staticmethod
    def get_facturas(sucursal_id, is_draft=False):
        return Factura.query.filter_by(
            sucursal_id=sucursal_id, is_draft=is_draft,
        ).all()

    @staticmethod
    def get_factura(factura_id):
        return Factura.query.get(factura_id)

    @staticmethod
    def delete_drafts(sucursal_id):
        deleted = Factura.query.filter_by(
            sucursal_id=sucursal_id, is_draft=True,
        ).delete()
        db.session.commit()
        return deleted
