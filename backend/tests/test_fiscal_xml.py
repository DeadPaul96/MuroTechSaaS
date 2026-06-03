"""XML fiscal v4.4 y clave MH."""
from datetime import datetime
from types import SimpleNamespace

from fiscal.clave import generar_clave, generar_consecutivo
from fiscal.xml_builder import build_comprobante_xml
from core.validators import validar_clave, validar_consecutivo


def _empresa():
    return SimpleNamespace(
        cedula_juridica='3101234567',
        razon_social='MUROTECH TEST SA',
        nombre_comercial='MUROTECH',
        tipo_identificacion='02',
        actividad_economica='620100',
    )


def _sucursal(empresa):
    return SimpleNamespace(
        empresa=empresa,
        numero_sucursal=1,
        terminal=1,
        provincia='1',
        canton='01',
        distrito='01',
        barrio='01',
        otras_senas='San Jose',
        direccion='San Jose',
    )


def _cliente():
    return SimpleNamespace(nombre='Cliente Test', tipo_id='01', identificacion='123456789')


def _detalle(producto=None):
    return SimpleNamespace(
        cantidad=1,
        precio_unitario=1000,
        porcentaje_descuento=0,
        porcentaje_impuesto=13,
        descripcion='Servicio test',
        tipo_impuesto='01',
        producto_rel=producto,
    )


def test_generar_clave_y_consecutivo():
    emp = _empresa()
    suc = _sucursal(emp)
    consecutivo = generar_consecutivo(suc, '01', 1)
    validar_consecutivo(consecutivo)
    clave = generar_clave(emp, consecutivo)
    assert len(clave) == 50
    validar_clave(clave)


def test_build_comprobante_xml_fe():
    emp = _empresa()
    suc = _sucursal(emp)
    consecutivo = generar_consecutivo(suc, '01', 1)
    prod = SimpleNamespace(cabys='8517120000000')
    factura = SimpleNamespace(
        sucursal=suc,
        cliente=_cliente(),
        clave=generar_clave(emp, consecutivo),
        numero_consecutivo=consecutivo,
        fecha_emision=datetime.utcnow(),
        tipo_documento='01',
        condicion_venta='01',
        medio_pago='01',
        moneda='CRC',
        tipo_cambio=1,
        subtotal=1000,
        descuentos=0,
        impuestos=130,
        total=1130,
        detalles=[_detalle(prod)],
        referencia_id=None,
    )
    xml = build_comprobante_xml(factura)
    assert xml.startswith(b'<?xml')
    assert b'FacturaElectronica' in xml or b'factura' in xml.lower()
