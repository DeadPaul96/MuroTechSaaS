"""Servicio de gestión de productos e inventario."""
import uuid
import logging

from sqlalchemy import or_

from app.extensions import db
from app.models import Producto, InventarioMovimiento
from app.utils.validators import ValidationError, validar_cabys

logger = logging.getLogger(__name__)


class ProductoService:
    @staticmethod
    def get_products(empresa_id, q=None, limit=50):
        query = Producto.query.filter_by(empresa_id=empresa_id)
        if q:
            query = query.filter(
                or_(
                    Producto.descripcion.ilike(f'%{q}%'),
                    Producto.nombre_servicio.ilike(f'%{q}%'),
                    Producto.marca.ilike(f'%{q}%'),
                    Producto.modelo.ilike(f'%{q}%'),
                    Producto.caracteristicas.ilike(f'%{q}%'),
                    Producto.cabys.ilike(f'%{q}%'),
                    Producto.codigo.ilike(f'%{q}%'),
                )
            )
        return query.limit(limit).all()

    @staticmethod
    def get_product(empresa_id, producto_id):
        return Producto.query.filter_by(id=producto_id, empresa_id=empresa_id).first()

    @staticmethod
    def create_product(empresa_id, data):
        if not data.get('codigo') or not data.get('descripcion'):
            raise ValidationError('Código y descripción son requeridos.')

        if data.get('cabys'):
            try:
                validar_cabys(data.get('cabys'))
            except ValidationError:
                raise

        if Producto.query.filter_by(
            empresa_id=empresa_id,
            codigo=data.get('codigo'),
        ).first():
            raise ValidationError('Ya existe un producto con ese código.')

        producto = Producto(
            id=str(uuid.uuid4()),
            empresa_id=empresa_id,
            cabys=data.get('cabys'),
            codigo=data.get('codigo'),
            unidad_medida=data.get('unidadMedida', 'Unid'),
            descripcion=data.get('descripcion'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            caracteristicas=data.get('caracteristicas'),
            nombre_servicio=data.get('nombreServicio'),
            detalle_servicio=data.get('detalleServicio'),
            costo=float(data.get('precio', 0)),
            margen=float(data.get('margen', 0)),
            precio_venta=float(data.get('precioVenta', 0)),
            impuesto=float(data.get('impuesto', 13)),
            tipo_impuesto=data.get('tipoImpuesto', '01'),
            stock=int(data.get('stock', 0)),
            descuento_max=float(data.get('descuentoMax', 0)),
        )
        db.session.add(producto)
        db.session.commit()
        return producto

    @staticmethod
    def update_product(empresa_id, producto_id, data):
        producto = ProductoService.get_product(empresa_id, producto_id)
        if not producto:
            raise ValidationError('Producto no encontrado.')

        for field, key in [
            ('descripcion', 'descripcion'),
            ('marca', 'marca'),
            ('modelo', 'modelo'),
            ('caracteristicas', 'caracteristicas'),
            ('nombre_servicio', 'nombreServicio'),
            ('detalle_servicio', 'detalleServicio'),
            ('tipo_impuesto', 'tipoImpuesto'),
            ('cabys', 'cabys'),
        ]:
            if key in data:
                setattr(producto, field, data[key])

        if 'cabys' in data and data['cabys']:
            validar_cabys(data['cabys'])

        for field, key, converter in [
            ('costo', 'precio', float),
            ('margen', 'margen', float),
            ('precio_venta', 'precioVenta', float),
            ('impuesto', 'impuesto', float),
            ('stock', 'stock', int),
            ('descuento_max', 'descuentoMax', float),
            ('unidad_medida', 'unidadMedida', str),
        ]:
            if key in data:
                setattr(producto, field, converter(data[key]))

        db.session.commit()
        return producto

    @staticmethod
    def delete_product(empresa_id, producto_id):
        producto = ProductoService.get_product(empresa_id, producto_id)
        if not producto:
            raise ValidationError('Producto no encontrado.')

        if producto.factura_detalles:
            raise ValidationError('No se puede eliminar un producto con facturas asociadas.')

        db.session.delete(producto)
        db.session.commit()
        return True

    @staticmethod
    def adjust_stock(empresa_id, producto_id, cantidad_ajuste, sucursal_id, usuario_id, referencia='', tipo_movimiento='Ajuste'):
        producto = ProductoService.get_product(empresa_id, producto_id)
        if not producto:
            raise ValidationError('Producto no encontrado.')

        anterior = producto.stock or 0
        nuevo = anterior + cantidad_ajuste

        movimiento = InventarioMovimiento(
            id=str(uuid.uuid4()),
            producto_id=producto_id,
            sucursal_id=sucursal_id,
            usuario_id=usuario_id,
            tipo_movimiento=tipo_movimiento,
            cantidad_anterior=anterior,
            cantidad_ajuste=cantidad_ajuste,
            cantidad_nueva=nuevo,
            referencia=referencia,
        )
        db.session.add(movimiento)
        producto.stock = nuevo
        db.session.commit()
        logger.info('Stock ajustado: %s (%d -> %d)', producto.codigo, anterior, nuevo)
        return producto
