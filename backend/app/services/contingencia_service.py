"""Modo Contingencia — comprobantes offline para MH Costa Rica v4.4.

Cuando MH no está disponible, el sistema puede generar comprobantes en modo
contingencia (tipos 09/10) con situación=2. Estos se almacenan localmente
y se sincronizan cuando el servicio de MH vuelve a estar disponible.
"""
import json
import logging
import os
import zlib
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models import Factura

logger = logging.getLogger(__name__)

CR_TZ = timezone(timedelta(hours=-6))


def is_contingencia_tipo(tipo_doc: str) -> bool:
    return tipo_doc in ('09', '10')


def map_to_contingencia(tipo_doc: str) -> str:
    """Convierte tipo normal a tipo contingencia: 01→09, 04→10."""
    mapping = {'01': '09', '04': '10', '02': '09', '03': '09'}
    return mapping.get(tipo_doc, '09')


def crear_comprobante_contingencia(factura_id: str) -> dict:
    """Marca una factura como contingencia para envío posterior.

    Si el tipo original es 01, cambia a 09 (contingencia factura).
    Si el tipo original es 04, cambia a 10 (contingencia tiquete).
    Actualiza la situación en la clave a '2' (contingencia).
    """
    factura = Factura.query.get(factura_id)
    if not factura:
        return {'error': 'Factura no encontrada'}

    if factura.estado in ('Aceptada MH', 'Rechazada MH'):
        return {'error': f'Factura ya procesada por MH (estado: {factura.estado})'}

    tipo_original = factura.tipo_documento
    if is_contingencia_tipo(tipo_original):
        return {'message': 'Ya es comprobante de contingencia', 'factura_id': factura.id}

    tipo_contingencia = map_to_contingencia(tipo_original)
    factura.tipo_documento = tipo_contingencia

    # Actualizar la situación en la clave (posición 43 de la clave = '2')
    clave = str(factura.clave)
    if len(clave) == 50:
        factura.clave = clave[:42] + '2' + clave[43:]

    factura.estado = 'Contingencia'
    db.session.commit()

    logger.info('Factura %s convertida a contingencia (tipo %s)', factura_id, tipo_contingencia)
    return {
        'message': 'Comprobante marcado como contingencia. Se enviará cuando MH esté disponible.',
        'factura_id': factura.id,
        'tipo_documento': tipo_contingencia,
        'estado': factura.estado,
    }


def obtener_pendientes_sincronizacion(empresa_id: str = None) -> list:
    """Obtiene facturas en estado Contingencia pendientes de envío a MH."""
    query = Factura.query.filter_by(estado='Contingencia', is_draft=False)
    if empresa_id:
        from app.models import Sucursal
        query = query.join(Sucursal).filter(Sucursal.empresa_id == empresa_id)
    return query.order_by(Factura.fecha_emision.asc()).all()


def sincronizar_contingencia(empresa_id: str = None, max_lote: int = 50) -> dict:
    """Intenta enviar todos los comprobantes de contingencia pendientes a MH.

    Returns:
        dict con resumen de envíos exitosos y fallidos.
    """
    from fiscal.horario import validar_horario_envio
    from fiscal.hacienda_client import HaciendaError

    permitido, motivo = validar_horario_envio()
    if not permitido:
        return {'message': f'No se puede sincronizar: {motivo}', 'enviados': 0, 'fallidos': 0}

    pendientes = obtener_pendientes_sincronizacion(empresa_id)
    if not pendientes:
        return {'message': 'No hay comprobantes de contingencia pendientes.', 'enviados': 0, 'fallidos': 0}

    enviados = 0
    fallidos = 0
    errores = []

    for factura in pendientes[:max_lote]:
        try:
            empresa = factura.sucursal.empresa

            if not factura.xml_comprobante:
                fallidos += 1
                errores.append({'id': factura.id, 'error': 'Sin XML almacenado'})
                continue

            xml_bytes = zlib.decompress(factura.xml_comprobante)

            # Obtener credenciales MH (requiere helper del blueprint companies)
            from app.api.blueprints.companies import _mh_credenciales, _empresa_ambiente, _read_empresa_secret, _p12_encryption_key
            from app.config import Config
            from fiscal.hacienda_client import HaciendaClient, mapear_estado_mh

            creds = _mh_credenciales(empresa)
            cliente_mh = HaciendaClient(ambiente=_empresa_ambiente(empresa))
            cliente = factura.cliente

            resultado = cliente_mh.enviar_comprobante(
                clave=factura.clave,
                xml_bytes=xml_bytes,
                emisor_tipo=empresa.tipo_identificacion,
                emisor_numero=empresa.cedula_juridica,
                receptor_tipo=getattr(cliente, 'tipo_id', None) if cliente else None,
                receptor_numero=getattr(cliente, 'identificacion', None) if cliente else None,
                fecha_emision=factura.fecha_emision,
                username=creds['username'],
                password=creds['password'],
            )

            body = resultado.get('body') or {}
            factura.respuesta_hacienda = zlib.compress(
                json.dumps(body, ensure_ascii=False).encode('utf-8')
            )
            factura.estado = mapear_estado_mh(body) if body else 'Enviada'
            db.session.commit()
            enviados += 1
            logger.info('Contingencia sincronizada: %s → %s', factura.id, factura.estado)

        except HaciendaError as err:
            fallidos += 1
            errores.append({'id': factura.id, 'error': str(err)})
            logger.warning('Error sincronizando contingencia %s: %s', factura.id, err)
        except Exception as err:
            fallidos += 1
            errores.append({'id': factura.id, 'error': str(err)})
            logger.error('Error inesperado en contingencia %s: %s', factura.id, err)

    return {
        'message': f'Sincronización completada: {enviados} enviados, {fallidos} fallidos.',
        'enviados': enviados,
        'fallidos': fallidos,
        'errores': errores if errores else None,
    }
