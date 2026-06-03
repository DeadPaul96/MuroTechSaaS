"""Validador XSD — comportamiento sin esquema local."""
import os

from fiscal.xsd_validator import XmlSchemaError, validate_comprobante_xml, validation_status


def test_validation_status_sin_xsd():
    st = validation_status('01')
    assert st['xsd_presente'] is False


def test_validate_disabled(monkeypatch):
    monkeypatch.setenv('HACIENDA_XSD_VALIDATE', 'false')
    validate_comprobante_xml(b'<root/>', '01')


def test_validate_falla_xml_invalido(monkeypatch):
    monkeypatch.setenv('HACIENDA_XSD_VALIDATE', 'true')
    monkeypatch.setenv('HACIENDA_XSD_AUTO_DOWNLOAD', 'false')
    try:
        validate_comprobante_xml(b'<not-xml', '01')
        assert False, 'debía fallar'
    except XmlSchemaError as err:
        assert 'mal formado' in str(err).lower() or 'XML' in str(err)
