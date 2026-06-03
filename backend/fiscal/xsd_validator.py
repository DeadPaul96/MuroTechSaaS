"""Validación XSD v4.4 — esquemas oficiales MH (carpeta fiscal/schemas/)."""
import logging
import os
from pathlib import Path

import requests
from lxml import etree

from .constants import DOC_XMLNS

logger = logging.getLogger('murotech.fiscal.xsd')

SCHEMA_DIR = Path(__file__).resolve().parent / 'schemas'
CDN_BASE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4'

# carpeta CDN / nombre archivo principal
SCHEMA_PATHS = {
    '01': ('facturaElectronica', 'facturaElectronica.xsd'),
    '02': ('notaDebitoElectronica', 'notaDebitoElectronica.xsd'),
    '03': ('notaCreditoElectronica', 'notaCreditoElectronica.xsd'),
    '04': ('tiqueteElectronico', 'tiqueteElectronico.xsd'),
    '08': ('facturaElectronicaCompra', 'facturaElectronicaCompra.xsd'),
}


class XmlSchemaError(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or []


def _schema_file(tipo_documento: str) -> Path | None:
    folder, filename = SCHEMA_PATHS.get(str(tipo_documento or '01').zfill(2)[-2:], SCHEMA_PATHS['01'])
    path = SCHEMA_DIR / folder / filename
    return path if path.is_file() else None


def ensure_schema_downloaded(tipo_documento: str, timeout: int = 30) -> Path:
    """Descarga el XSD principal si no existe localmente."""
    tipo = str(tipo_documento or '01').zfill(2)[-2:]
    folder, filename = SCHEMA_PATHS.get(tipo, SCHEMA_PATHS['01'])
    target = SCHEMA_DIR / folder / filename
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f'{CDN_BASE}/{folder}/{filename}'
    res = requests.get(url, timeout=timeout)
    if not res.ok:
        raise XmlSchemaError(f'No se pudo descargar XSD: {url} ({res.status_code})')
    target.write_bytes(res.content)
    logger.info('XSD descargado: %s', target)
    return target


def _load_schema(tipo_documento: str, auto_download: bool) -> etree.XMLSchema:
    path = _schema_file(tipo_documento)
    if not path and auto_download:
        path = ensure_schema_downloaded(tipo_documento)
    if not path:
        raise XmlSchemaError(
            f'Esquema XSD no encontrado para tipo {tipo_documento}. '
            f'Ejecute: python scripts/download_xsd_schemas.py'
        )
    parser = etree.XMLParser(resolve_entities=False, no_network=not auto_download)
    doc = etree.parse(str(path), parser)
    return etree.XMLSchema(doc)


def validate_comprobante_xml(xml_bytes: bytes, tipo_documento: str, *, auto_download: bool = None) -> None:
    """
    Valida XML contra XSD MH v4.4.
    Si HACIENDA_XSD_VALIDATE=false, no hace nada.
    """
    enabled = os.environ.get('HACIENDA_XSD_VALIDATE', 'true').lower() not in ('0', 'false', 'no')
    if not enabled:
        return
    if auto_download is None:
        auto_download = os.environ.get('HACIENDA_XSD_AUTO_DOWNLOAD', 'true').lower() in ('1', 'true', 'yes')
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as err:
        raise XmlSchemaError(f'XML mal formado: {err}') from err
    expected_ns = DOC_XMLNS.get(str(tipo_documento or '01').zfill(2)[-2:])
    if expected_ns and root.nsmap.get(None) != expected_ns:
        logger.warning('Namespace XML=%s esperado=%s', root.nsmap.get(None), expected_ns)
    schema = _load_schema(tipo_documento, auto_download)
    if not schema.validate(root):
        errors = [str(e) for e in schema.error_log]
        raise XmlSchemaError('El XML no cumple el XSD de Hacienda v4.4', errors=errors[:20])


def validation_status(tipo_documento: str = '01') -> dict:
    path = _schema_file(tipo_documento)
    return {
        'tipo_documento': tipo_documento,
        'xsd_presente': bool(path),
        'ruta': str(path) if path else None,
        'cdn': f'{CDN_BASE}/{SCHEMA_PATHS.get(str(tipo_documento).zfill(2)[-2:], SCHEMA_PATHS["01"])[0]}/',
    }
