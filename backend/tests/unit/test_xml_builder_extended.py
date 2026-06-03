"""Tests para fiscal/xml_builder.py — generación XML v4.4 con todos los tipos."""
import os
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from lxml import etree

from fiscal.xml_builder import build_comprobante_xml
from fiscal.constants import DOC_ROOT, DOC_XMLNS


class MockDetalle:
    def __init__(self, descripcion='Test Item', cantidad=1, precio_unitario=1000,
                 porcentaje_descuento=0, porcentaje_impuesto=13, tipo_impuesto='01',
                 total_linea=1130, producto_id=None):
        self.descripcion = descripcion
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.porcentaje_descuento = porcentaje_descuento
        self.porcentaje_impuesto = porcentaje_impuesto
        self.tipo_impuesto = tipo_impuesto
        self.total_linea = total_linea
        self.producto_id = producto_id
        self.producto_rel = None


class MockCliente:
    def __init__(self, nombre='Cliente Test', tipo_id='01', identificacion='111111111',
                 email='test@test.com', provincia='1', canton='01'):
        self.nombre = nombre
        self.tipo_id = tipo_id
        self.identificacion = identificacion
        self.email = email
        self.provincia = provincia
        self.canton = canton


class MockSucursal:
    def __init__(self):
        self.numero_sucursal = '001'
        self.terminal = '00001'
        self.provincia = '1'
        self.canton = '01'
        self.distrito = '01'
        self.barrio = '01'
        self.direccion = 'San José'
        self.otras_senas = '100m sur del parque'
        self.empresa = None


class MockEmpresa:
    def __init__(self):
        self.razon_social = 'MUROTECH SOLUTIONS S.A.'
        self.nombre_comercial = 'MUROTECH'
        self.tipo_identificacion = '02'
        self.cedula_juridica = '3101123456'
        self.actividad_economica = '620100'


def _make_factura(tipo_doc='01', cliente=None, referencia_id=None):
    """Factory para crear factura mock."""
    suc = MockSucursal()
    emp = MockEmpresa()
    suc.empresa = emp

    class Factura:
        pass

    f = Factura()
    f.sucursal = suc
    f.cliente = cliente
    f.tipo_documento = tipo_doc
    f.clave = '506020626310112345600100010000010000119999999999999'
    f.numero_consecutivo = '00100001010000000001'
    f.fecha_emision = datetime(2026, 6, 2, 10, 0, 0, tzinfo=timezone(timedelta(hours=-6)))
    f.condicion_venta = '01'
    f.medio_pago = '01'
    f.moneda = 'CRC'
    f.referencia_id = referencia_id
    f.referencia_codigo = '01' if referencia_id else None
    f.referencia_razon = 'Ajuste' if referencia_id else None
    f.detalles = [MockDetalle()]
    return f


class TestXMLFacturaElectronica:
    """Tests para Factura Electrónica (01)."""

    def test_genera_xml_valido(self):
        factura = _make_factura('01')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        assert root.tag.endswith('FacturaElectronica')

    def test_namespace_correcto(self):
        factura = _make_factura('01')
        xml_bytes = build_comprobante_xml(factura)
        assert b'facturaElectronica' in xml_bytes

    def test_tiene_receptor(self):
        factura = _make_factura('01', cliente=MockCliente())
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        xmlns = DOC_XMLNS['01']
        receptor = root.find(f'{{{xmlns}}}Receptor')
        assert receptor is not None


class TestXMLTiqueteElectronico:
    """Tests para Tiquete Electrónico (04)."""

    def test_genera_xml_valido(self):
        factura = _make_factura('04')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        assert root.tag.endswith('TiqueteElectronico')

    def test_namespace_tiquete(self):
        factura = _make_factura('04')
        xml_bytes = build_comprobante_xml(factura)
        assert b'tiqueteElectronico' in xml_bytes

    def test_resumen_tiquete(self):
        """Tiquete usa ResumenTiquete en lugar de ResumenFactura."""
        factura = _make_factura('04')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        xmlns = DOC_XMLNS['04']
        resumen = root.find(f'{{{xmlns}}}ResumenTiquete')
        assert resumen is not None

    def test_sin_receptor_es_valido(self):
        """Tiquete no requiere receptor."""
        factura = _make_factura('04', cliente=None)
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        xmlns = DOC_XMLNS['04']
        receptor = root.find(f'{{{xmlns}}}Receptor')
        assert receptor is None


class TestXMLNotaCredito:
    """Tests para Nota de Crédito (03) con referencia."""

    def test_genera_xml_valido(self):
        factura = _make_factura('03', referencia_id='506020626310112345600100010000010000119999999999999')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        assert root.tag.endswith('NotaCreditoElectronica')

    def test_tiene_informacion_referencia(self):
        factura = _make_factura('03', referencia_id='506020626310112345600100010000010000119999999999999')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        xmlns = DOC_XMLNS['03']
        ref = root.find(f'{{{xmlns}}}InformacionReferencia')
        assert ref is not None


class TestXMLNotaDebito:
    """Tests para Nota de Débito (02) con referencia."""

    def test_genera_xml_valido(self):
        factura = _make_factura('02', referencia_id='506020626310112345600100010000010000119999999999999')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        assert root.tag.endswith('NotaDebitoElectronica')


class TestXMLContingencia:
    """Tests para comprobantes de contingencia (09, 10)."""

    def test_contingencia_factura_09(self):
        """Tipo 09 usa namespace de factura con situación=2."""
        factura = _make_factura('09')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        assert root.tag.endswith('FacturaElectronica')

    def test_contingencia_tiquete_10(self):
        """Tipo 10 usa namespace de tiquete con situación=2."""
        factura = _make_factura('10')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        assert root.tag.endswith('TiqueteElectronico')

    def test_resumen_contingencia_10(self):
        """Tipo 10 debe usar ResumenTiquete."""
        factura = _make_factura('10')
        xml_bytes = build_comprobante_xml(factura)
        root = etree.fromstring(xml_bytes)
        xmlns = DOC_XMLNS['10']
        resumen = root.find(f'{{{xmlns}}}ResumenTiquete')
        assert resumen is not None
