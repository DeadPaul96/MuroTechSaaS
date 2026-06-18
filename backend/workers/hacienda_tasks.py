"""Tareas asíncronas para integración con Hacienda."""
import json
import logging
import zlib

from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)
logger = logging.getLogger(__name__)


@celery.task(
    name='workers.hacienda_tasks.enviar_a_hacienda',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def enviar_a_hacienda(self, factura_id):
    """Envía un comprobante electrónico a Hacienda de forma asíncrona."""
    from app.models import Factura, Sucursal
    from app.api.blueprints.companies import _read_empresa_secret, _empresa_ambiente, _mh_credenciales
    from fiscal.hacienda_client import HaciendaClient, HaciendaError
    from fiscal.horario import validar_horario_envio, enviar_con_reintentos

    factura = Factura.query.get(factura_id)
    if not factura:
        logger.error('Factura %s no encontrada para envío MH', factura_id)
        return {'status': 'error', 'message': 'Factura no encontrada'}

    if not factura.xml_comprobante:
        logger.error('Factura %s sin XML para envío MH', factura_id)
        return {'status': 'error', 'message': 'Sin XML almacenado'}

    try:
        sucursal = factura.sucursal
        empresa = sucursal.empresa
        xml_bytes = zlib.decompress(factura.xml_comprobante)
        cliente = factura.cliente

        permitido, motivo = validar_horario_envio()
        if not permitido:
            factura.estado = 'Pendiente Horario'
            from app.extensions import db
            db.session.commit()
            return {'status': 'postponed', 'reason': motivo}

        creds = _mh_credenciales(empresa)
        cliente_mh = HaciendaClient(ambiente=_empresa_ambiente(empresa))

        resultado = enviar_con_reintentos(
            lambda: cliente_mh.enviar_comprobante(
                clave=factura.clave,
                xml_bytes=xml_bytes,
                emisor_tipo=empresa.tipo_identificacion,
                emisor_numero=empresa.cedula_juridica,
                receptor_tipo=getattr(cliente, 'tipo_id', None) if cliente else None,
                receptor_numero=getattr(cliente, 'identificacion', None) if cliente else None,
                fecha_emision=factura.fecha_emision,
                username=creds['username'],
                password=creds['password'],
            ),
            max_reintentos=3,
        )

        from fiscal.hacienda_client import mapear_estado_mh
        body = resultado.get('body') or {}
        factura.respuesta_hacienda = zlib.compress(
            json.dumps(body, ensure_ascii=False).encode('utf-8')
        )
        factura.estado = mapear_estado_mh(body) if body else 'Enviada'
        from app.extensions import db
        db.session.commit()

        logger.info('Factura %s enviada a MH: %s', factura_id, factura.estado)
        return {'status': 'sent', 'estado': factura.estado}

    except HaciendaError as err:
        logger.warning('Error MH enviando factura %s: %s', factura_id, err)
        try:
            self.retry(exc=err)
        except self.MaxRetriesExceededError:
            factura.estado = 'Error MH'
            from app.extensions import db
            db.session.commit()
            return {'status': 'error', 'message': str(err)}

    except Exception as err:
        logger.error('Error inesperado enviando factura %s: %s', factura_id, err)
        try:
            self.retry(exc=err)
        except self.MaxRetriesExceededError:
            return {'status': 'error', 'message': str(err)}


@celery.task(name='workers.hacienda_tasks.consultar_estado_lote')
def consultar_estado_lote(empresa_id):
    """Consulta el estado de todas las facturas pendientes de una empresa."""
    from app.models import Factura, Sucursal
    from app.api.blueprints.companies import _read_empresa_secret, _empresa_ambiente, _mh_credenciales
    from fiscal.hacienda_client import HaciendaClient, HaciendaError, mapear_estado_mh

    pendientes = Factura.query.join(Sucursal).filter(
        Sucursal.empresa_id == empresa_id,
        Factura.estado.in_(['Enviada', 'Pendiente', 'Firmada']),
        Factura.is_draft == False,
    ).limit(50).all()

    if not pendientes:
        return {'status': 'ok', 'consultadas': 0}

    creds = None
    cliente_mh = None
    consultadas = 0

    for factura in pendientes:
        try:
            empresa = factura.sucursal.empresa
            if not creds or not cliente_mh:
                creds = _mh_credenciales(empresa)
                cliente_mh = HaciendaClient(ambiente=_empresa_ambiente(empresa))

            resultado = cliente_mh.consultar_estado_recepcion(
                factura.clave, creds['username'], creds['password'],
            )
            body = resultado.get('body') or {}
            factura.respuesta_hacienda = zlib.compress(
                json.dumps(body, ensure_ascii=False).encode('utf-8')
            )
            factura.estado = mapear_estado_mh(body) if body else factura.estado
            consultadas += 1
        except HaciendaError:
            continue
        except Exception:
            continue

    from app.extensions import db
    db.session.commit()
    return {'status': 'ok', 'consultadas': consultadas}
