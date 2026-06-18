"""Servicio de reportes y dashboards."""
import logging
from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import Factura, FacturaDetalle, Sucursal, Producto, Cliente
from app.utils.date_utils import _parse_date
from app.utils.money import calcular_variacion

logger = logging.getLogger(__name__)


class ReporteService:
    @staticmethod
    def get_reportes_data(empresa_id, desde=None, hasta=None, cliente_id=None):
        sucursales_ids = [
            s.id for s in Sucursal.query.filter_by(empresa_id=empresa_id).all()
        ]
        if not sucursales_ids:
            return {
                'total_ventas': 0, 'total_iva': 0, 'total_neto': 0,
                'ventas_por_fecha': [], 'top_productos': [],
                'por_estado': {}, 'por_moneda': {},
            }

        query = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
        )

        desde_dt = _parse_date(desde)
        hasta_dt = _parse_date(hasta, end_of_day=True)
        if desde_dt:
            query = query.filter(Factura.fecha_emision >= desde_dt)
        if hasta_dt:
            query = query.filter(Factura.fecha_emision <= hasta_dt)
        if cliente_id and cliente_id != 'all':
            query = query.filter(Factura.cliente_id == cliente_id)

        facturas = query.all()

        total_ventas = sum(float(f.total or 0) for f in facturas)
        total_iva = sum(float(f.impuestos or 0) for f in facturas)
        total_neto = total_ventas - total_iva

        ventas_por_fecha = {}
        por_estado = {}
        por_moneda = {}
        productos_vendidos = {}

        for f in facturas:
            fecha_str = f.fecha_emision.strftime('%Y-%m-%d')
            ventas_por_fecha[fecha_str] = ventas_por_fecha.get(fecha_str, 0) + float(f.total or 0)
            por_estado[f.estado] = por_estado.get(f.estado, 0) + 1
            por_moneda[f.moneda] = por_moneda.get(f.moneda, 0) + float(f.total or 0)

            for d in f.detalles:
                key = d.descripcion or 'Sin nombre'
                productos_vendidos[key] = productos_vendidos.get(key, 0) + float(d.total_linea or 0)

        top_productos = sorted(productos_vendidos.items(), key=lambda x: x[1], reverse=True)[:10]

        ventas_list = [{'fecha': k, 'total': v} for k, v in sorted(ventas_por_fecha.items())]

        return {
            'total_ventas': total_ventas,
            'total_iva': total_iva,
            'total_neto': total_neto,
            'ventas_por_fecha': ventas_list,
            'top_productos': [{'nombre': k, 'total': v} for k, v in top_productos],
            'por_estado': por_estado,
            'por_moneda': por_moneda,
            'total_facturas': len(facturas),
        }

    @staticmethod
    def generate_report(filters=None):
        """Genera un reporte genérico según filtros proporcionados."""
        filters = filters or {}
        empresa_id = filters.get('empresa_id')
        if not empresa_id:
            return {'error': 'empresa_id es requerido.'}
        return ReporteService.get_reportes_data(
            empresa_id,
            desde=filters.get('desde'),
            hasta=filters.get('hasta'),
            cliente_id=filters.get('cliente_id'),
        )

    @staticmethod
    def get_dashboard_kpis(empresa_id):
        sucursales_ids = [
            s.id for s in Sucursal.query.filter_by(empresa_id=empresa_id).all()
        ]
        if not sucursales_ids:
            return {
                'facturas_mes': 0, 'ventas_mes': 0,
                'clientes_total': 0, 'productos_total': 0,
                'variacion_ventas': 0,
            }

        hoy = datetime.utcnow()
        inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        facturas_mes = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes,
        ).all()

        ventas_mes = sum(float(f.total or 0) for f in facturas_mes)

        clientes_total = Cliente.query.filter_by(empresa_id=empresa_id).count()
        productos_total = Producto.query.filter_by(empresa_id=empresa_id).count()

        # Variación vs mes anterior
        from datetime import timedelta
        inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        facturas_mes_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision < inicio_mes,
        ).all()
        ventas_mes_anterior = sum(float(f.total or 0) for f in facturas_mes_anterior)
        variacion = calcular_variacion(ventas_mes, ventas_mes_anterior)

        return {
            'facturas_mes': len(facturas_mes),
            'ventas_mes': ventas_mes,
            'clientes_total': clientes_total,
            'productos_total': productos_total,
            'variacion_ventas': variacion,
        }
