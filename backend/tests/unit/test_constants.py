"""Tests para fiscal/constants.py — tipos de documento y constantes."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest

from fiscal.constants import (
    DOC_ROOT, DOC_XMLNS, DOC_FACTURA, DOC_NOTA_DEBITO, DOC_NOTA_CREDITO,
    DOC_TIQUETE, DOC_FACTURA_EXPORTACION, DOC_FACTURA_COMPRA,
    DOC_CONT_FACTURA, DOC_CONT_TIQUETE,
    TARIFA_IVA, SITUACION_NORMAL, SITUACION_CONTINGENCIA,
    XSI_NS, PROVEEDOR_SISTEMAS,
)


class TestConstants:
    """Tests para constantes fiscales."""

    def test_doc_factura(self):
        assert DOC_FACTURA == '01'

    def test_doc_nota_debito(self):
        assert DOC_NOTA_DEBITO == '02'

    def test_doc_nota_credito(self):
        assert DOC_NOTA_CREDITO == '03'

    def test_doc_tiquete(self):
        assert DOC_TIQUETE == '04'

    def test_doc_exportacion(self):
        assert DOC_FACTURA_EXPORTACION == '05'

    def test_doc_contingencia_factura(self):
        assert DOC_CONT_FACTURA == '09'

    def test_doc_contingencia_tiquete(self):
        assert DOC_CONT_TIQUETE == '10'

    def test_doc_root_tiene_todos_los_tipos(self):
        for tipo in ['01', '02', '03', '04', '05', '08', '09', '10']:
            assert tipo in DOC_ROOT, f"Tipo {tipo} debe estar en DOC_ROOT"

    def test_doc_xmlns_tiene_todos_los_tipos(self):
        for tipo in ['01', '02', '03', '04', '05', '08', '09', '10']:
            assert tipo in DOC_XMLNS, f"Tipo {tipo} debe estar en DOC_XMLNS"

    def test_doc_root_factura_exportacion(self):
        assert DOC_ROOT['05'] == 'FacturaElectronicaExportacion'

    def test_doc_xmlns_exportacion_url(self):
        assert 'facturaElectronicaExportacion' in DOC_XMLNS['05']

    def test_contingencia_usa_namespace_factura(self):
        assert DOC_ROOT['09'] == DOC_ROOT['01']
        assert DOC_XMLNS['09'] == DOC_XMLNS['01']

    def test_contingencia_usa_namespace_tiquete(self):
        assert DOC_ROOT['10'] == DOC_ROOT['04']
        assert DOC_XMLNS['10'] == DOC_XMLNS['04']

    def test_tarifa_iva_tiene_13(self):
        assert TARIFA_IVA[13] == '08'

    def test_tarifa_iva_tiene_0(self):
        assert TARIFA_IVA[0] == '01'

    def test_situaciones(self):
        assert SITUACION_NORMAL == '1'
        assert SITUACION_CONTINGENCIA == '2'

    def test_proveedor_sistemas(self):
        assert PROVEEDOR_SISTEMAS == 'MUROTECH'

    def test_xsi_ns(self):
        assert XSI_NS == 'http://www.w3.org/2001/XMLSchema-instance'
