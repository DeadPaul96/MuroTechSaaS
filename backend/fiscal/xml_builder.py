"""XML comprobantes electrónicos v4.4 — MH Costa Rica."""
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from lxml import etree
from .constants import (
    DOC_ROOT, DOC_XMLNS, XSI_NS, PROVEEDOR_SISTEMAS, TARIFA_IVA,
    DOC_TIQUETE, DOC_NOTA_CREDITO, DOC_NOTA_DEBITO, DOC_FACTURA_EXPORTACION,
    DOC_CONT_TIQUETE,
)

CR_TZ = timezone(timedelta(hours=-6))

def _q(v):
    return Decimal(str(v or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def _fmt(v):
    return f'{_q(v):.2f}'

def _digits(v, n=None):
    d = re.sub(r'\D', '', str(v or ''))
    return d.zfill(n)[-n:] if n else d

def _tipo_doc(t):
    m = {'factura': '01', '01': '01', '02': '02', '03': '03', '04': '04',
         '05': '05', '08': '08', '09': '09', '10': '10',
         'tiquete': '04', 'nota credito': '03', 'nota debito': '02',
         'factura exportacion': '05', 'exportacion': '05',
         'contingencia factura': '09', 'contingencia tiquete': '10'}
    k = str(t or '01').strip().lower()
    return m.get(k, k if k in DOC_ROOT else '01')

def _actividad(raw):
    d = _digits(raw)
    return (d[:6] if len(d) >= 6 else d.zfill(6)) or '000000'

def _fecha(dt):
    if not dt:
        dt = datetime.now(CR_TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CR_TZ)
    return dt.astimezone(CR_TZ).strftime('%Y-%m-%dT%H:%M:%S-06:00')

def _cabys(det):
    p = getattr(det, 'producto_rel', None)
    c = _digits(getattr(p, 'cabys', None) if p else '')
    return c if len(c) == 13 else '0000000000000'

def build_comprobante_xml(factura) -> bytes:
    empresa = factura.sucursal.empresa
    sucursal = factura.sucursal
    cliente = factura.cliente
    td = _tipo_doc(factura.tipo_documento)
    xmlns = DOC_XMLNS[td]
    root_name = DOC_ROOT[td]
    root = etree.Element(f'{{{xmlns}}}{root_name}', nsmap={None: xmlns, 'xsi': XSI_NS})
    root.set(f'{{{XSI_NS}}}schemaLocation', f'{xmlns} {xmlns}.xsd')

    etree.SubElement(root, 'Clave').text = _digits(factura.clave, 50)
    etree.SubElement(root, 'ProveedorSistemas').text = PROVEEDOR_SISTEMAS
    etree.SubElement(root, 'CodigoActividadEmisor').text = _actividad(empresa.actividad_economica)
    etree.SubElement(root, 'NumeroConsecutivo').text = _digits(factura.numero_consecutivo, 20)
    etree.SubElement(root, 'FechaEmision').text = _fecha(factura.fecha_emision)

    em = etree.SubElement(root, 'Emisor')
    etree.SubElement(em, 'Nombre').text = (empresa.razon_social or '')[:100]
    idem = etree.SubElement(em, 'Identificacion')
    etree.SubElement(idem, 'Tipo').text = str(empresa.tipo_identificacion or '02')[-2:]
    etree.SubElement(idem, 'Numero').text = _digits(empresa.cedula_juridica, 12)
    etree.SubElement(em, 'NombreComercial').text = (empresa.nombre_comercial or empresa.razon_social or '')[:80]
    ub = etree.SubElement(em, 'Ubicacion')
    for tag, val, w in [('Provincia', sucursal.provincia, 1), ('Canton', sucursal.canton, 2), ('Distrito', sucursal.distrito, 2), ('Barrio', sucursal.barrio, 2)]:
        etree.SubElement(ub, tag).text = _digits(val, w) if _digits(val) else {'1': '1', '2': '01'}[str(w)]
    etree.SubElement(ub, 'OtrasSenas').text = str(getattr(sucursal, 'otras_senas', None) or sucursal.direccion or 'CR')[:250]

    if cliente or td != DOC_TIQUETE:
        rec = etree.SubElement(root, 'Receptor')
        etree.SubElement(rec, 'Nombre').text = (cliente.nombre if cliente else 'Consumidor final')[:100]
        if cliente:
            ir = etree.SubElement(rec, 'Identificacion')
            etree.SubElement(ir, 'Tipo').text = str(cliente.tipo_id or '01')[-2:]
            etree.SubElement(ir, 'Numero').text = _digits(cliente.identificacion, 12 if cliente.tipo_id == '02' else 9)

    etree.SubElement(root, 'CondicionVenta').text = _digits(factura.condicion_venta, 2) or '01'
    # Múltiples medios de pago (MH v4.4 permite varios)
    medios_raw = str(getattr(factura, 'medio_pago', '01') or '01')
    for medio in medios_raw.split(','):
        medio = medio.strip()
        if medio:
            etree.SubElement(root, 'MedioPago').text = _digits(medio, 2)

    # Notas de Crédito usan montos negativos según normativa MH v4.4
    sign = Decimal(-1) if td == DOC_NOTA_CREDITO else Decimal(1)

    ds = etree.SubElement(root, 'DetalleServicio')
    tg, te, ti, tdsc, tv, tc = [Decimal(0)] * 6
    for i, det in enumerate(factura.detalles, 1):
        cant, pu = _q(det.cantidad), _q(det.precio_unitario)
        desc_p, iva_p = _q(det.porcentaje_descuento), _q(det.porcentaje_impuesto)
        mt = _q(cant * pu * sign)
        dm = _q(mt * desc_p / 100) if sign > 0 else _q(cant * pu * desc_p / 100)
        st = _q(mt - dm) if sign > 0 else _q(cant * pu * sign - dm)
        im = _q(st * iva_p / 100)
        mtl = _q(st + im)
        ln = etree.SubElement(ds, 'LineaDetalle')
        etree.SubElement(ln, 'NumeroLinea').text = str(i)
        etree.SubElement(ln, 'CodigoCABYS').text = _cabys(det)
        etree.SubElement(ln, 'Cantidad').text = f'{cant:.3f}'
        etree.SubElement(ln, 'UnidadMedida').text = 'Unid'
        etree.SubElement(ln, 'Detalle').text = (det.descripcion or 'Item')[:200]
        etree.SubElement(ln, 'PrecioUnitario').text = _fmt(pu)
        etree.SubElement(ln, 'MontoTotal').text = _fmt(mt)
        etree.SubElement(ln, 'SubTotal').text = _fmt(st)
        etree.SubElement(ln, 'BaseImponible').text = _fmt(st)
        if iva_p > 0:
            imp = etree.SubElement(ln, 'Impuesto')
            etree.SubElement(imp, 'Codigo').text = str(det.tipo_impuesto or '01')
            etree.SubElement(imp, 'CodigoTarifaIVA').text = TARIFA_IVA.get(int(iva_p), '08')
            etree.SubElement(imp, 'Tarifa').text = _fmt(iva_p)
            etree.SubElement(imp, 'Monto').text = _fmt(im)
            # Exoneración (si aplica)
            exon_pct = Decimal(str(getattr(det, 'porcentaje_exoneracion', 0) or 0))
            if exon_pct > 0:
                exon = etree.SubElement(imp, 'Exoneracion')
                etree.SubElement(exon, 'TipoDocumento').text = str(getattr(det, 'tipo_doc_exoneracion', '01'))[:2]
                etree.SubElement(exon, 'NumeroDocumento').text = str(getattr(det, 'num_doc_exoneracion', ''))[:20]
                etree.SubElement(exon, 'NombreInstitucion').text = str(getattr(det, 'nombre_institucion', ''))[:100]
                etree.SubElement(exon, 'FechaEmision').text = _fecha(getattr(det, 'fecha_emision_exo', None))
                monto_exon = _q(im * exon_pct / 100)
                etree.SubElement(exon, 'MontoExoneracion').text = _fmt(monto_exon)
                etree.SubElement(exon, 'PorcentajeExoneracion').text = _fmt(exon_pct)
            tg += st
            ti += im
        else:
            te += st
        etree.SubElement(ln, 'MontoTotalLinea').text = _fmt(mtl)
        tdsc += dm
        tv += mt
        tc += mtl

    res_tag = 'ResumenTiquete' if td in (DOC_TIQUETE, DOC_CONT_TIQUETE) else 'ResumenFactura'
    res = etree.SubElement(root, res_tag)
    mon = etree.SubElement(res, 'CodigoTipoMoneda')
    etree.SubElement(mon, 'CodigoMoneda').text = (factura.moneda or 'CRC')[:3]
    etree.SubElement(res, 'TotalServGravados').text = _fmt(tg)
    etree.SubElement(res, 'TotalServExentos').text = _fmt(te)
    etree.SubElement(res, 'TotalMercanciasGravadas').text = _fmt(Decimal(0))
    etree.SubElement(res, 'TotalMercanciasExentas').text = _fmt(Decimal(0))
    etree.SubElement(res, 'TotalGravado').text = _fmt(tg)
    etree.SubElement(res, 'TotalExento').text = _fmt(te)
    etree.SubElement(res, 'TotalVenta').text = _fmt(tv)
    etree.SubElement(res, 'TotalDescuentos').text = _fmt(tdsc)
    etree.SubElement(res, 'TotalVentaNeta').text = _fmt(tv - tdsc)
    etree.SubElement(res, 'TotalImpuesto').text = _fmt(ti)
    etree.SubElement(res, 'TotalComprobante').text = _fmt(tc)

    # Campos adicionales para Factura de Exportación (05)
    if td == DOC_FACTURA_EXPORTACION:
        exp_info = getattr(factura, 'exportacion', None)
        if exp_info:
            exp = etree.SubElement(root, 'InformacionExportacion')
            etree.SubElement(exp, 'Incoterm').text = str(getattr(exp_info, 'incoterm', 'FOB'))[:10]
            etree.SubElement(exp, 'MedioPagoExportacion').text = str(getattr(exp_info, 'medio_pago_exportacion', '01'))[:2]
            ub_exp = etree.SubElement(exp, 'UbicacionDestinoExportacion')
            etree.SubElement(ub_exp, 'CodigoPaisDestino').text = str(getattr(exp_info, 'pais_destino', 'US'))[:2]
            etree.SubElement(ub_exp, 'NombrePaisDestino').text = str(getattr(exp_info, 'nombre_pais', 'Estados Unidos'))[:50]
            if getattr(exp_info, 'divisa', None):
                etree.SubElement(exp, 'Divisa').text = str(exp_info.divisa)[:3]
            if getattr(exp_info, 'tipo_cambio', None):
                etree.SubElement(exp, 'TipoCambio').text = _fmt(exp_info.tipo_cambio)

    # Otros Cargos (si aplica)
    otros_cargos = getattr(factura, 'otros_cargos', None)
    if otros_cargos:
        cargo_list = otros_cargos if isinstance(otros_cargos, list) else [otros_cargos]
        oc_root = etree.SubElement(root, 'OtrosCargos')
        for cargo in cargo_list:
            oc = etree.SubElement(oc_root, 'TipoDocumento')
            oc.text = str(getattr(cargo, 'tipo_documento', '99'))[:2]
            detalle_oc = etree.SubElement(oc_root, 'Detalle')
            detalle_oc.text = str(getattr(cargo, 'detalle', ''))[:160]
            monto_oc = etree.SubElement(oc_root, 'MontoCargo')
            monto_oc.text = _fmt(getattr(cargo, 'monto', 0))

    if td in (DOC_NOTA_CREDITO, DOC_NOTA_DEBITO) and getattr(factura, 'referencia_id', None):
        inf = etree.SubElement(root, 'InformacionReferencia')
        etree.SubElement(inf, 'TipoDoc').text = str(factura.referencia_codigo or '01')
        etree.SubElement(inf, 'Numero').text = str(factura.referencia_id)[:50]
        etree.SubElement(inf, 'FechaEmision').text = _fecha(factura.fecha_emision)
        etree.SubElement(inf, 'Codigo').text = '01'
        etree.SubElement(inf, 'Razon').text = (factura.referencia_razon or 'Ajuste')[:180]
        # Referencias adicionales (si existen)
        referencias_extra = getattr(factura, 'referencias_extra', None)
        if referencias_extra:
            ref_list = referencias_extra if isinstance(referencias_extra, list) else [referencias_extra]
            for ref in ref_list:
                inf2 = etree.SubElement(root, 'InformacionReferencia')
                etree.SubElement(inf2, 'TipoDoc').text = str(getattr(ref, 'tipo_doc', '01'))[:2]
                etree.SubElement(inf2, 'Numero').text = str(getattr(ref, 'numero', ''))[:50]
                etree.SubElement(inf2, 'FechaEmision').text = _fecha(getattr(ref, 'fecha_emision', factura.fecha_emision))
                etree.SubElement(inf2, 'Codigo').text = str(getattr(ref, 'codigo', '01'))[:2]
                etree.SubElement(inf2, 'Razon').text = str(getattr(ref, 'razon', 'Ajuste'))[:180]

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8')

def build_mensaje_receptor_xml(*, clave_comprobante, cedula_emisor, cedula_receptor, fecha_emision_doc, tipo_mensaje, detalle_mensaje='', **kw) -> bytes:
    xmlns = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/mensajeReceptor'
    root = etree.Element(f'{{{xmlns}}}MensajeReceptor', nsmap={None: xmlns, 'xsi': XSI_NS})
    root.set(f'{{{XSI_NS}}}schemaLocation', f'{xmlns} {xmlns}.xsd')
    etree.SubElement(root, 'Clave').text = _digits(clave_comprobante, 50)
    etree.SubElement(root, 'NumeroCedulaEmisor').text = _digits(cedula_emisor, 12)
    etree.SubElement(root, 'FechaEmisionDoc').text = _fecha(fecha_emision_doc)
    m = {'aceptar': '1', 'parcial': '2', 'rechazar': '3'}.get(str(tipo_mensaje).lower(), str(tipo_mensaje))
    etree.SubElement(root, 'Mensaje').text = m
    if detalle_mensaje:
        etree.SubElement(root, 'DetalleMensaje').text = detalle_mensaje[:80]
    etree.SubElement(root, 'NumeroCedulaReceptor').text = _digits(cedula_receptor, 12)
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8')
