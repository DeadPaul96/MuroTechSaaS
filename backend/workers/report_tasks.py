"""Tareas asíncronas para generación de reportes."""
import io
import csv
import logging
from datetime import datetime

from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)
logger = logging.getLogger(__name__)


@celery.task(name='workers.report_tasks.generate_report')
def generate_report(filters):
    """Genera un reporte de facturación según filtros y retorna los datos."""
    from app.services.reporte_service import ReporteService

    empresa_id = filters.get('empresa_id')
    if not empresa_id:
        return {'status': 'error', 'message': 'empresa_id es requerido'}

    try:
        data = ReporteService.get_reportes_data(
            empresa_id,
            desde=filters.get('desde'),
            hasta=filters.get('hasta'),
            cliente_id=filters.get('cliente_id'),
        )
        logger.info('Reporte generado para empresa %s', empresa_id)
        return {'status': 'completed', 'data': data}

    except Exception as err:
        logger.error('Error generando reporte para empresa %s: %s', empresa_id, err)
        return {'status': 'error', 'message': str(err)}


@celery.task(name='workers.report_tasks.generate_csv_report')
def generate_csv_report(empresa_id, periodo='mes', start_date=None, end_date=None):
    """Genera un reporte CSV para descarga."""
    from app.models import Factura, Sucursal
    from app.extensions import db

    query = Factura.query.join(Sucursal).filter(
        Factura.is_draft == False,
        Sucursal.empresa_id == empresa_id,
    )

    if start_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Factura.fecha_emision >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Factura.fecha_emision <= ed)
        except ValueError:
            pass

    facturas = query.all()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Consecutivo', 'Fecha', 'Cliente', 'Moneda', 'Subtotal', 'Impuestos', 'Descuentos', 'Total', 'Estado'])

    for f in facturas:
        writer.writerow([
            f.numero_consecutivo,
            f.fecha_emision.strftime('%Y-%m-%d %H:%M') if f.fecha_emision else '',
            f.cliente.nombre if f.cliente else 'Consumidor Final',
            f.moneda,
            f"{float(f.subtotal or 0):.2f}",
            f"{float(f.impuestos or 0):.2f}",
            f"{float(f.descuentos or 0):.2f}",
            f"{float(f.total or 0):.2f}",
            f.estado,
        ])

    logger.info('Reporte CSV generado para empresa %s (%d filas)', empresa_id, len(facturas))
    return {'status': 'completed', 'csv_content': output.getvalue(), 'rows': len(facturas)}
