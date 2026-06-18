import logging

import os
from datetime import datetime, timedelta
import zlib
import base64
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from decimal import Decimal
import requests
from flask import Blueprint, jsonify, request, current_app
from app.models import (
    db, Factura, FacturaDetalle, Sucursal, Empresa, Cliente, Producto,
    InventarioMovimiento, Notificacion, Cotizacion, CotizacionDetalle, MensajeReceptor
)
from app.api.decorators.auth import token_required
from app.api.decorators.rbac import require_role
from app.api.decorators.audit import audit_log
from app.api.blueprints.companies import (
    _read_empresa_secret, _store_empresa_secret, _empresa_ambiente, _mh_credenciales,
    validate_sucursal, create_notification
)
from app.utils.validators import ValidationError, validar_consecutivo, validar_clave, validar_cabys
from app.utils.money import _parse_decimal, _parse_float, quantize_money
from app.utils.date_utils import _parse_date
from fiscal.xml_builder import build_comprobante_xml, build_mensaje_receptor_xml
from fiscal.clave import generar_clave, generar_consecutivo, calcular_digito_verificador
from fiscal.signer import firmar_xml
from fiscal.hacienda_client import HaciendaClient, HaciendaError, mapear_estado_mh
from fiscal.horario import validar_horario_envio, enviar_con_reintentos
from fiscal.xsd_validator import validate_comprobante_xml, XmlSchemaError, validation_status
from app.services.contingencia_service import crear_comprobante_contingencia, sincronizar_contingencia

bp = Blueprint('invoices', __name__, url_prefix='/api')

logger = logging.getLogger(__name__)

# Cache para tipo de cambio
_tipo_cambio_cache = {
    'timestamp': None,
    'rates': None
}

def get_tipo_cambio():
    """Obtiene el tipo de cambio real desde la API de Hacienda con cache de una hora."""
    ahora = datetime.utcnow()
    if _tipo_cambio_cache['rates'] and _tipo_cambio_cache['timestamp']:
        if (ahora - _tipo_cambio_cache['timestamp']).total_seconds() < 3600:
            return _tipo_cambio_cache['rates']

    try:
        res = requests.get("https://api.hacienda.go.cr/indicadores/tc", timeout=5)
        if res.ok:
            data = res.json()
            rates = {
                'venta': float(data['dolar']['venta']['valor']),
                'compra': float(data['dolar']['compra']['valor']),
                'euro_colones': float(data['euro']['colones']),
                'euro_dolares': float(data['euro']['dolares'])
            }
            _tipo_cambio_cache['rates'] = rates
            _tipo_cambio_cache['timestamp'] = ahora
            return rates
    except Exception as e:
        logger.warning("Error consultando API Hacienda tipo cambio: %s", e)

    # Fallback local
    fallback = {'venta': 525.50, 'compra': 515.20, 'euro_colones': 542.11, 'euro_dolares': 1.1772}
    if _tipo_cambio_cache['rates']:
        return _tipo_cambio_cache['rates']
    return fallback

def _p12_encryption_key():
    return current_app.config.get('ENCRYPTION_KEY')

def build_hacienda_factura_xml(factura):
    return build_comprobante_xml(factura).decode('utf-8')

def _guardar_respuesta_mh(factura, payload: dict):
    import json
    factura.respuesta_hacienda = zlib.compress(
        json.dumps(payload, ensure_ascii=False).encode('utf-8')
    )

def _leer_respuesta_mh(factura):
    import json
    raw = getattr(factura, 'respuesta_hacienda', None)
    if not raw:
        return None
    try:
        data = zlib.decompress(raw)
        return json.loads(data.decode('utf-8'))
    except Exception:
        return None

def _get_plan_period_start(periodo):
    ahora = datetime.utcnow()
    mes = ahora.month
    periodo = (periodo or 'mensual').lower()
    meses_periodo = {
        'mensual': 1, 'bimestral': 2, 'trimestral': 3,
        'cuatrimestral': 4, 'semestral': 6, 'anual': 12
    }.get(periodo, 1)
    inicio_mes = mes - ((mes - 1) % meses_periodo)
    return ahora.replace(month=inicio_mes, day=1, hour=0, minute=0, second=0, microsecond=0)

def verificar_cupo_facturas(empresa):
    if not getattr(empresa, 'plan_cuota', 0):
        return True, 0
    inicio_periodo = _get_plan_period_start(empresa.plan_tipo)
    facturas_emitidas = Factura.query.join(Sucursal).filter(
        Sucursal.empresa_id == empresa.id,
        Factura.fecha_emision >= inicio_periodo,
        Factura.is_draft == False
    ).count()
    return facturas_emitidas < empresa.plan_cuota, facturas_emitidas

def enviar_comprobante_email(destinatario, factura_data, xml_bin, pdf_bin):
    """Envía el comprobante electrónico (XML y PDF) al receptor."""
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_user or not smtp_pass:
        current_app.logger.warning('SMTP no configurado. No se envió correo a %s', destinatario)
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"MUROTECH Facturación <{smtp_user}>"
        msg['To'] = destinatario
        msg['Subject'] = f"Comprobante Electrónico: {factura_data['consecutivo']}"

        html = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                <div style="background: #1e40af; padding: 40px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 24px; letter-spacing: -1px;">MUROTECH</h1>
                    <p style="opacity: 0.8; margin-top: 5px;">Sistema de Facturación Electrónica</p>
                </div>
                <div style="padding: 40px;">
                    <h2 style="color: #0f172a; font-size: 20px;">¡Hola! Has recibido un comprobante electrónico.</h2>
                    <p>Le informamos que se ha generado un nuevo documento electrónico a su nombre con los siguientes detalles:</p>
                    <div style="background: #f8fafc; padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #1e40af;">
                        <p style="margin: 5px 0;"><strong>Consecutivo:</strong> {factura_data['consecutivo']}</p>
                        <p style="margin: 5px 0;"><strong>Fecha:</strong> {factura_data['fecha']}</p>
                        <p style="margin: 5px 0;"><strong>Monto Total:</strong> {factura_data['moneda']} {factura_data['monto']}</p>
                    </div>
                    <p style="font-size: 14px; color: #64748b;">Encuentre adjunto el archivo XML (Validez Legal) y el PDF (Representación Gráfica).</p>
                </div>
                <div style="background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                    Este es un correo automático generado por MUROTECH SaaS. Por favor no responda a este mensaje.
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        part_xml = MIMEBase('application', 'xml')
        part_xml.set_payload(xml_bin)
        encoders.encode_base64(part_xml)
        part_xml.add_header('Content-Disposition', f'attachment; filename="{factura_data["consecutivo"]}.xml"')
        msg.attach(part_xml)

        part_pdf = MIMEBase('application', 'pdf')
        part_pdf.set_payload(pdf_bin)
        encoders.encode_base64(part_pdf)
        part_pdf.add_header('Content-Disposition', f'attachment; filename="{factura_data["consecutivo"]}.pdf"')
        msg.attach(part_pdf)
        
        print(f"Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        logger.error("Error enviando correo a %s: %s", destinatario, e)
        return False

@bp.route('/facturas', methods=['GET', 'POST'])
@token_required
@require_role(['Administrador', 'Emisor'])
@audit_log('factura')
def facturas_endpoint(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    if request.method == 'GET':
        facturas = Factura.query.filter_by(sucursal_id=sucursal.id, is_draft=False).all()
        return jsonify([{
            'id': f.id,
            'numero_consecutivo': f.numero_consecutivo,
            'cliente_nombre': f.cliente.nombre if f.cliente else 'Consumidor Final',
            'fecha_emision': f.fecha_emision.isoformat(),
            'moneda': f.moneda,
            'total': float(f.total),
            'estado': f.estado,
            'tipo_documento': f.tipo_documento
        } for f in facturas])

    if request.method == 'POST':
        data = request.get_json() or {}
        detalles = data.get('detalles', [])
        if not detalles:
            return jsonify({'message': 'Debe enviar al menos un detalle de factura.'}), 400

        tipo_doc = data.get('tipoDoc', '01')

        # Validar referencia obligatoria para NC/ND
        if tipo_doc in ('02', '03') and not data.get('referencia_id'):
            return jsonify({'message': 'Para Notas de Crédito/Débito es obligatorio indicar la clave del documento original (referencia_id).'}), 400

        try:
            
            sucursal = db.session.query(Sucursal).with_for_update().filter_by(id=sucursal_id, empresa_id=current_user.empresa_id).first()
            if not sucursal:
                return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

            empresa = sucursal.empresa
            puede_emitir, emitidas = verificar_cupo_facturas(empresa)
            if not puede_emitir:
                return jsonify({
                    'message': 'Límite de facturas del plan alcanzado.',
                    'facturas_emitidas': emitidas,
                    'plan_cuota': empresa.plan_cuota,
                    'plan_tipo': empresa.plan_tipo
                }), 403

            tipo_doc = data.get('tipoDoc', '01')
            if tipo_doc == '01':
                sucursal.c_factura = (sucursal.c_factura or 0) + 1
                cont = sucursal.c_factura
            elif tipo_doc == '04':
                sucursal.c_tiquete = (sucursal.c_tiquete or 0) + 1
                cont = sucursal.c_tiquete
            elif tipo_doc == '03':
                sucursal.c_nota_credito = (sucursal.c_nota_credito or 0) + 1
                cont = sucursal.c_nota_credito
            else:
                sucursal.c_nota_debito = (sucursal.c_nota_debito or 0) + 1
                cont = sucursal.c_nota_debito

            consecutivo = generar_consecutivo(sucursal, tipo_doc, cont)
            clave = generar_clave(current_user.empresa, consecutivo)
            try:
                validar_consecutivo(consecutivo)
                validar_clave(clave)
            except ValidationError as verr:
                return jsonify({'message': str(verr)}), 400

            moneda = data.get('moneda', 'CRC')
            tc = Decimal('1.00')
            if moneda != 'CRC':
                rates = get_tipo_cambio()
                tc = Decimal(str(rates['venta']))

            subtotal_total = Decimal('0.00')
            descuentos_total = Decimal('0.00')
            impuestos_total = Decimal('0.00')
            total_final = Decimal('0.00')

            nueva_factura = Factura(
                sucursal_id=sucursal.id,
                cliente_id=data.get('cliente_id'),
                numero_consecutivo=consecutivo,
                clave=clave,
                tipo_documento=tipo_doc,
                condicion_venta=data.get('condicionVenta', '01'),
                medio_pago=data.get('medioPago', '01'),
                moneda=moneda,
                tipo_cambio=tc,
                estado='Pendiente',
                is_draft=False,
                usuario_id=current_user.id,
                referencia_id=data.get('referencia_id'),
                referencia_codigo=data.get('referencia_codigo'),
                referencia_razon=data.get('referencia_razon'),
            )
            db.session.add(nueva_factura)
            db.session.flush()

            for idx, item in enumerate(detalles, start=1):
                cantidad = _parse_decimal(item.get('cantidad', 1))
                precio_unitario = _parse_decimal(item.get('precio', 0))
                porcentaje_descuento = _parse_decimal(item.get('descuento', 0))
                porcentaje_impuesto = _parse_decimal(item.get('impuesto', 13))

                monto_base = quantize_money(cantidad * precio_unitario)
                descuento_monto = quantize_money(monto_base * porcentaje_descuento / Decimal('100'))
                base_neta = quantize_money(monto_base - descuento_monto)
                impuesto_monto = quantize_money(base_neta * porcentaje_impuesto / Decimal('100'))
                total_linea = quantize_money(base_neta + impuesto_monto)

                subtotal_total += base_neta
                descuentos_total += descuento_monto
                impuestos_total += impuesto_monto
                total_final += total_linea

                detalle_factura = FacturaDetalle(
                    factura_id=nueva_factura.id,
                    producto_id=item.get('producto_id'),
                    descripcion=item.get('descripcion', item.get('nombre', 'Producto')),
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    porcentaje_descuento=porcentaje_descuento,
                    porcentaje_impuesto=porcentaje_impuesto,
                    tipo_impuesto=item.get('tipo_impuesto', '01'),
                    total_linea=total_linea
                )
                db.session.add(detalle_factura)

                prod_id = item.get('producto_id')
                if prod_id:
                    producto = Producto.query.get(prod_id)
                    if producto and producto.cabys:
                        try:
                            validar_cabys(producto.cabys)
                        except ValidationError as verr:
                            return jsonify({'message': f'Línea {idx}: {verr}'}), 400
                    if producto:
                        cant_int = int(cantidad)
                        anterior = producto.stock or 0
                        nuevo_stock = anterior - cant_int
                        
                        movimiento = InventarioMovimiento(
                            producto_id=producto.id,
                            sucursal_id=nueva_factura.sucursal_id,
                            usuario_id=current_user.id,
                            tipo_movimiento='Venta',
                            cantidad_anterior=anterior,
                            cantidad_ajuste=-cant_int,
                            cantidad_nueva=nuevo_stock,
                            referencia=f"Factura: {consecutivo}"
                        )
                        db.session.add(movimiento)
                        
                        producto.stock = nuevo_stock
                        logger.info("Inventario Actualizado: %s (%d -> %d)", producto.codigo, anterior, nuevo_stock)

                        if nuevo_stock < 5:
                            notificacion = Notificacion(
                                empresa_id=current_user.empresa_id,
                                sucursal_id=nueva_factura.sucursal_id,
                                tipo='inventario',
                                icono='fas fa-exclamation-triangle',
                                titulo='Stock Bajo Detectado',
                                descripcion=f"El producto '{producto.descripcion}' ({producto.codigo}) ha bajado de 5 unidades. Stock actual: {nuevo_stock}",
                                link='/frontend/html/inventario.html'
                            )
                            db.session.add(notificacion)
                            logger.info("Alerta: Stock bajo para %s", producto.codigo)

            nueva_factura.subtotal = quantize_money(subtotal_total)
            nueva_factura.descuentos = quantize_money(descuentos_total)
            nueva_factura.impuestos = quantize_money(impuestos_total)
            nueva_factura.total = quantize_money(total_final)

            xml_content = build_hacienda_factura_xml(nueva_factura)
            xml_bytes_para_mh = xml_content.encode('utf-8')
            try:
                validate_comprobante_xml(xml_bytes_para_mh, tipo_doc)
            except XmlSchemaError as xsd_err:
                db.session.rollback()
                return jsonify({
                    'message': str(xsd_err),
                    'xsd_errors': getattr(xsd_err, 'errors', []),
                }), 422

            try:
                pin_p12 = _read_empresa_secret(empresa, 'api_pin_p12')
                if empresa.api_p12_bin and pin_p12:
                    xml_firmado = firmar_xml(
                        xml_content, empresa.api_p12_bin, pin_p12, _p12_encryption_key()
                    )
                    xml_bytes_para_mh = xml_firmado
                    nueva_factura.xml_comprobante = zlib.compress(xml_firmado)
                    nueva_factura.estado = 'Firmada'
                else:
                    nueva_factura.xml_comprobante = zlib.compress(xml_bytes_para_mh)
            except Exception as sign_err:
                logger.warning("Error en firma XML: %s", sign_err)
                nueva_factura.xml_comprobante = zlib.compress(xml_bytes_para_mh)

            mh_envio = None
            if os.environ.get('HACIENDA_SEND_ENABLED', '').lower() in ('1', 'true', 'yes') and nueva_factura.estado == 'Firmada':
                try:
                    permitido, motivo = validar_horario_envio()
                    if not permitido:
                        nueva_factura.estado = 'Pendiente Horario'
                        logger.info("[MH] %s Se enviará en próximo horario hábil.", motivo)
                    else:
                        creds = _mh_credenciales(empresa)
                        cliente_mh = HaciendaClient(ambiente=_empresa_ambiente(empresa))
                        cliente = nueva_factura.cliente

                        def _enviar():
                            return cliente_mh.enviar_comprobante(
                                clave=clave,
                                xml_bytes=xml_bytes_para_mh,
                                emisor_tipo=empresa.tipo_identificacion,
                                emisor_numero=empresa.cedula_juridica,
                                receptor_tipo=getattr(cliente, 'tipo_id', None) if cliente else None,
                                receptor_numero=getattr(cliente, 'identificacion', None) if cliente else None,
                                fecha_emision=nueva_factura.fecha_emision,
                                username=creds['username'],
                                password=creds['password'],
                            )

                        mh_envio = enviar_con_reintentos(_enviar, max_reintentos=3)
                        body_mh = mh_envio.get('body') or {}
                        _guardar_respuesta_mh(nueva_factura, body_mh)
                        nueva_factura.estado = mapear_estado_mh(body_mh) if body_mh else 'Enviada'
                except HaciendaError as mh_err:
                    logger.warning("MH recepción: %s payload=%s", mh_err, getattr(mh_err, 'payload', None))
                except Exception as mh_err:
                    logger.error("MH recepción error: %s", mh_err)

            pdf_base64 = data.get('pdf_base64')
            if pdf_base64:
                try:
                    if "," in pdf_base64:
                        pdf_base64 = pdf_base64.split(",")[1]
                    pdf_bin = base64.b64decode(pdf_base64)
                    nueva_factura.pdf_comprobante = zlib.compress(pdf_bin)
                except Exception as pdf_err:
                    logger.warning("Error procesando PDF base64: %s", pdf_err)
                    nueva_factura.pdf_comprobante = zlib.compress(b"ERROR_GENERACION_PDF")
            else:
                nueva_factura.pdf_comprobante = zlib.compress(b"SIN_PDF_ADJUNTO")

            db.session.commit()

            try:
                Factura.query.filter_by(sucursal_id=sucursal.id, is_draft=True).delete()
                db.session.commit()
            except Exception:
                db.session.rollback()

            resp = {
                'id': str(nueva_factura.id),
                'message': 'Documento emitido y almacenado correctamente.',
                'consecutivo': consecutivo,
                'clave': clave,
            }
            if mh_envio:
                resp['hacienda'] = mh_envio.get('body')
            return jsonify(resp), 201

        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return jsonify({'message': 'Error al procesar emisión', 'error': str(e)}), 500

@bp.route('/facturas/borrador', methods=['GET', 'POST'])
@token_required
def gestionar_borradores(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    if request.method == 'GET':
        borrador = Factura.query.filter_by(sucursal_id=sucursal.id, is_draft=True).first()
        if not borrador:
            return jsonify({'message': 'No hay borradores'}), 404
        return jsonify({
            'cliente_id': borrador.cliente_id,
            'moneda': borrador.moneda,
            'tipoDoc': borrador.tipo_documento,
            'detalles': [{
                'descripcion': d.descripcion,
                'cantidad': d.cantidad,
                'precio': d.precio_unitario,
                'descuento': d.porcentaje_descuento,
                'impuesto': d.porcentaje_impuesto,
                'total_linea': d.total_linea
            } for d in borrador.detalles]
        })

    if request.method == 'POST':
        data = request.get_json() or {}
        detalles = data.get('detalles', [])
        Factura.query.filter_by(sucursal_id=sucursal.id, is_draft=True).delete()

        nuevo_borrador = Factura(
            sucursal_id=sucursal.id,
            cliente_id=data.get('cliente_id'),
            moneda=data.get('moneda', 'CRC'),
            tipo_documento=data.get('tipoDoc', '01'),
            is_draft=True,
            estado='Borrador',
            numero_consecutivo='BORRADOR-' + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            clave='BORRADOR',
            condicion_venta=data.get('condicionVenta', '01'),
            medio_pago=data.get('medioPago', '01')
        )
        db.session.add(nuevo_borrador)
        db.session.flush()

        subtotal_total = 0.0
        descuentos_total = 0.0
        impuestos_total = 0.0
        total_final = 0.0

        for item in detalles:
            cantidad = _parse_float(item.get('cantidad', 1))
            precio_unitario = _parse_float(item.get('precio', 0))
            porcentaje_descuento = _parse_float(item.get('descuento', 0))
            porcentaje_impuesto = _parse_float(item.get('impuesto', 13))

            monto_base = cantidad * precio_unitario
            descuento_monto = monto_base * porcentaje_descuento / 100.0
            base_neta = monto_base - descuento_monto
            impuesto_monto = base_neta * porcentaje_impuesto / 100.0
            total_linea = base_neta + impuesto_monto

            subtotal_total += base_neta
            descuentos_total += descuento_monto
            impuestos_total += impuesto_monto
            total_final += total_linea

            db.session.add(FacturaDetalle(
                factura_id=nuevo_borrador.id,
                producto_id=item.get('producto_id'),
                descripcion=item.get('descripcion', item.get('nombre', 'Linea de factura')),
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                porcentaje_descuento=porcentaje_descuento,
                porcentaje_impuesto=porcentaje_impuesto,
                tipo_impuesto=item.get('tipo_impuesto', '01'),
                total_linea=total_linea
            ))

        nuevo_borrador.subtotal = subtotal_total
        nuevo_borrador.descuentos = descuentos_total
        nuevo_borrador.impuestos = impuestos_total
        nuevo_borrador.total = total_final

        db.session.commit()
        return jsonify({'message': 'Borrador guardado exitosamente.', 'id': nuevo_borrador.id})

@bp.route('/facturas/<string:id>/hacienda/estado', methods=['GET'])
@token_required
@require_role(['Administrador', 'Emisor', 'Auditor'])
def consultar_estado_hacienda(current_user, id):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403
    factura = Factura.query.filter_by(id=id, sucursal_id=sucursal.id).first()
    if not factura:
        return jsonify({'message': 'Factura no encontrada'}), 404
    if not factura.clave:
        return jsonify({'message': 'La factura no tiene clave fiscal.'}), 400
    empresa = sucursal.empresa
    creds = _mh_credenciales(empresa)
    if not creds.get('username') or not creds.get('password'):
        return jsonify({'message': 'Configure credenciales ATV de Hacienda en la empresa.'}), 400
    try:
        cliente_mh = HaciendaClient(ambiente=_empresa_ambiente(empresa))
        resultado = cliente_mh.consultar_estado_recepcion(
            factura.clave, creds['username'], creds['password']
        )
        body = resultado.get('body') or {}
        _guardar_respuesta_mh(factura, body)
        factura.estado = mapear_estado_mh(body)
        db.session.commit()
        return jsonify({
            'clave': factura.clave,
            'estado': factura.estado,
            'hacienda': body,
            'respuesta_guardada': True,
        })
    except HaciendaError as err:
        return jsonify({
            'message': str(err),
            'hacienda': getattr(err, 'payload', None),
        }), err.status_code or 502

@bp.route('/hacienda/xsd-status', methods=['GET'])
@token_required
def hacienda_xsd_status(current_user):
    tipos = request.args.getlist('tipo') or ['01', '04', '03', '02']
    return jsonify({'schemas': [validation_status(t) for t in tipos]})

@bp.route('/facturas/<string:id>', methods=['GET', 'PUT'])
@token_required
@require_role(['Administrador', 'Emisor'])
@audit_log('factura')
def factura_detalle(current_user, id):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    factura = Factura.query.filter_by(id=id, sucursal_id=sucursal.id).first()
    if not factura:
        return jsonify({'message': 'Factura no encontrada'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': factura.id,
            'consecutivo': factura.numero_consecutivo,
            'fecha': factura.fecha_emision.isoformat(),
            'moneda': factura.moneda,
            'condicionVenta': factura.condicion_venta,
            'medioPago': factura.medio_pago,
            'observaciones': factura.observaciones,
            'estado': factura.estado,
            'clave': factura.clave,
            'hacienda_ultima_respuesta': _leer_respuesta_mh(factura),
            'monto': factura.total,
            'clienteNombre': factura.cliente.nombre if factura.cliente else 'N/A',
            'clienteId': factura.cliente_id,
            'receptor': {
                'nombre': factura.cliente.nombre if factura.cliente else '',
                'identificacion': factura.cliente.identificacion if factura.cliente else '',
                'correo': factura.cliente.email if factura.cliente else '',
                'provincia': factura.cliente.provincia if factura.cliente else '',
                'canton': factura.cliente.canton if factura.cliente else ''
            } if factura.cliente else None,
            'detalle': [{
                'descripcion': d.descripcion,
                'cantidad': d.cantidad,
                'precio': d.precio_unitario,
                'subtotal': d.total_linea,
                'impuesto': d.porcentaje_impuesto,
                'descuento': d.porcentaje_descuento,
                'cabys': d.producto_rel.cabys if d.producto_rel else '00000000'
            } for d in factura.detalles]
        })
        
    if request.method == 'PUT':
        data = request.get_json() or {}
        
        def parse_money(val):
            if isinstance(val, (int, float)): return float(val)
            return float(re.sub(r'[^\d.-]', '', str(val))) if val else 0.0
            
        factura.estado = data.get('estado', factura.estado)
        factura.observaciones = data.get('observaciones', factura.observaciones)
        if data.get('fecha'):
            try:
                factura.fecha_emision = datetime.fromisoformat(data.get('fecha').replace('Z', ''))
            except (ValueError, TypeError):
                pass
        factura.condicion_venta = data.get('condicionVenta', factura.condicion_venta)
        factura.medio_pago = data.get('medioPago', factura.medio_pago)
        factura.moneda = data.get('moneda', factura.moneda)

        subtotal_total = 0.0
        descuentos_total = 0.0
        impuestos_total = 0.0
        total_final = 0.0

        for d in factura.detalles:
            db.session.delete(d)
            
        for item in data.get('detalle', []):
            cantidad = parse_money(item.get('cantidad', 1))
            precio_unitario = parse_money(item.get('precio', 0))
            porcentaje_descuento = parse_money(item.get('descuento', 0))
            porcentaje_impuesto = parse_money(item.get('impuesto', 13))

            monto_base = cantidad * precio_unitario
            descuento_monto = monto_base * porcentaje_descuento / 100.0
            base_neta = monto_base - descuento_monto
            impuesto_monto = base_neta * porcentaje_impuesto / 100.0
            total_linea = base_neta + impuesto_monto

            subtotal_total += base_neta
            descuentos_total += descuento_monto
            impuestos_total += impuesto_monto
            total_final += total_linea

            det = FacturaDetalle(
                factura_id=factura.id,
                descripcion=item.get('descripcion'),
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                porcentaje_descuento=porcentaje_descuento,
                porcentaje_impuesto=porcentaje_impuesto,
                tipo_impuesto=item.get('tipo_impuesto', '01'),
                total_linea=total_linea
            )
            db.session.add(det)
            
        factura.subtotal = subtotal_total
        factura.descuentos = descuentos_total
        factura.impuestos = impuestos_total
        factura.total = total_final

        db.session.commit()
        return jsonify({'message': 'Factura actualizada y emitida correctamente'}), 200

@bp.route('/facturas/descargar/<string:id>/<tipo>', methods=['GET'])
@token_required
def descargar_comprobante(current_user, id, tipo):
    factura = Factura.query.get_or_404(id)
    if factura.sucursal.empresa_id != current_user.empresa_id:
        return jsonify({'message': 'No autorizado'}), 403
        
    try:
        if tipo == 'xml':
            data = zlib.decompress(factura.xml_comprobante)
            mimetype = 'application/xml'
            ext = 'xml'
        else:
            data = zlib.decompress(factura.pdf_comprobante)
            mimetype = 'application/pdf'
            ext = 'pdf'
            
        return data, 200, {
            'Content-Type': mimetype,
            'Content-Disposition': f'attachment; filename={factura.numero_consecutivo}.{ext}'
        }
    except Exception:
        return jsonify({'message': 'Archivo no disponible'}), 404

@bp.route('/cotizaciones/proforma', methods=['POST'])
@token_required
def crear_cotizacion_proforma(current_user):
    data = request.get_json() or {}
    
    sucursal = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).first()
    if not sucursal:
        return jsonify({'message': 'No hay sucursales configuradas.'}), 400

    cliente_id = data.get('cliente_id')
    if cliente_id == 'all' or not cliente_id:
        cliente_id = None
        
    nueva_cot = Factura(
        sucursal_id=sucursal.id,
        cliente_id=cliente_id,
        numero_consecutivo=f"COT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        clave=f"PROFORMA-{datetime.now().timestamp()}",
        tipo_documento="Proforma",
        moneda=data.get('moneda', 'CRC'),
        condicion_venta=data.get('condicion_venta', 'Contado'),
        subtotal=data.get('subtotal', 0),
        descuentos=data.get('descuento', 0),
        impuestos=data.get('impuestos', 0),
        total=data.get('total', 0),
        estado="Proforma",
        is_quotation=True,
        observaciones=data.get('notas', ''),
        tipo_cambio=data.get('tipo_cambio', 1.0)
    )
    
    validez = int(data.get('validez_dias', 15))
    nueva_cot.fecha_vencimiento = datetime.now() + timedelta(days=validez)
    
    db.session.add(nueva_cot)
    db.session.flush()

    for item in data.get('detalles', []):
        detalle = FacturaDetalle(
            factura_id=nueva_cot.id,
            producto_id=item.get('id'),
            descripcion=item.get('nombre'),
            cantidad=item.get('cantidad'),
            precio_unitario=item.get('precio'),
            porcentaje_descuento=item.get('descuento_p', 0),
            porcentaje_impuesto=item.get('iva_p', 13.0),
            tipo_impuesto=item.get('tipo_impuesto', '01'),
            total_linea=item.get('subtotal')
        )
        db.session.add(detalle)

    db.session.commit()
    
    create_notification(current_user.empresa_id, 'sistema', 'Nueva Cotización Generada', f'Se ha creado la proforma {nueva_cot.numero_consecutivo} para {data.get("receptor_nombre", "Prospecto")}.')

    return jsonify({
        'message': 'Cotización guardada exitosamente.',
        'id': nueva_cot.id,
        'consecutivo': nueva_cot.numero_consecutivo
    }), 201

@bp.route('/facturas/consecutivo', methods=['GET'])
@token_required
def get_next_consecutivo(current_user):
    tipo_doc = request.args.get('tipo', '01')
    sucursal_id = request.headers.get('X-Sucursal-ID') or request.args.get('sucursal_id')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    if tipo_doc == '01':
        siguiente = (sucursal.c_factura or 0) + 1
    elif tipo_doc == '04':
        siguiente = (sucursal.c_tiquete or 0) + 1
    elif tipo_doc == '03':
        siguiente = (sucursal.c_nota_credito or 0) + 1
    elif tipo_doc == '02':
        siguiente = (sucursal.c_nota_debito or 0) + 1
    else:
        siguiente = (sucursal.c_factura or 0) + 1

    consecutivo = generar_consecutivo(sucursal, tipo_doc, siguiente)
    return jsonify({
        'consecutivo': consecutivo,
        'sucursal': sucursal.numero_sucursal,
        'terminal': sucursal.terminal,
        'correlativo': siguiente,
        'tipo_doc': tipo_doc
    })

@bp.route('/cotizaciones', methods=['GET', 'POST'])
@token_required
@require_role(['Administrador', 'Emisor'])
def cotizaciones_endpoint(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    if request.method == 'GET':
        cotizaciones = Cotizacion.query.filter_by(sucursal_id=sucursal.id).all()
        return jsonify([{
            'id': c.id,
            'cliente_nombre': c.cliente_nombre,
            'cliente_cedula': c.cliente_cedula,
            'fecha_emision': c.fecha_emision.isoformat(),
            'fecha_vencimiento': c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
            'moneda': c.moneda,
            'total': float(c.total),
            'estado': c.estado
        } for c in cotizaciones])

    if request.method == 'POST':
        data = request.get_json() or {}
        detalles = data.get('detalles', [])
        if not detalles:
            return jsonify({'message': 'Debe enviar al menos un detalle de cotización.'}), 400

        try:
            moneda = data.get('moneda', 'CRC')
            tc = Decimal('1.00')
            if moneda != 'CRC':
                rates = get_tipo_cambio()
                tc = Decimal(str(rates['venta']))

            subtotal_total = Decimal('0.00')
            descuentos_total = Decimal('0.00')
            impuestos_total = Decimal('0.00')
            total_final = Decimal('0.00')

            nueva_cotizacion = Cotizacion(
                sucursal_id=sucursal.id,
                cliente_nombre=data.get('cliente_nombre', ''),
                cliente_cedula=data.get('cliente_cedula', ''),
                fecha_vencimiento=datetime.fromisoformat(data.get('fecha_vencimiento')) if data.get('fecha_vencimiento') else None,
                moneda=moneda,
                tipo_cambio=tc,
                estado='Borrador',
                usuario_id=current_user.id
            )
            db.session.add(nueva_cotizacion)
            db.session.flush()

            for idx, item in enumerate(detalles, start=1):
                cantidad = _parse_decimal(item.get('cantidad', 1))
                precio_unitario = _parse_decimal(item.get('precio', 0))
                porcentaje_descuento = _parse_decimal(item.get('descuento', 0))
                porcentaje_impuesto = _parse_decimal(item.get('impuesto', 13))

                monto_base = quantize_money(cantidad * precio_unitario)
                descuento_monto = quantize_money(monto_base * porcentaje_descuento / Decimal('100'))
                base_neta = quantize_money(monto_base - descuento_monto)
                impuesto_monto = quantize_money(base_neta * porcentaje_impuesto / Decimal('100'))
                total_linea = quantize_money(base_neta + impuesto_monto)

                subtotal_total += base_neta
                descuentos_total += descuento_monto
                impuestos_total += impuesto_monto
                total_final += total_linea

                detalle_cotizacion = CotizacionDetalle(
                    cotizacion_id=nueva_cotizacion.id,
                    producto_id=item.get('producto_id'),
                    descripcion=item.get('descripcion', item.get('nombre', 'Producto')),
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    porcentaje_descuento=porcentaje_descuento,
                    porcentaje_impuesto=porcentaje_impuesto,
                    tipo_impuesto=item.get('tipo_impuesto', '01'),
                    total_linea=total_linea
                )
                db.session.add(detalle_cotizacion)

            nueva_cotizacion.subtotal = quantize_money(subtotal_total)
            nueva_cotizacion.descuentos = quantize_money(descuentos_total)
            nueva_cotizacion.impuestos = quantize_money(impuestos_total)
            nueva_cotizacion.total = quantize_money(total_final)

            pdf_base64 = data.get('pdf_base64')
            if pdf_base64:
                try:
                    if "," in pdf_base64:
                        pdf_base64 = pdf_base64.split(",")[1]
                    pdf_bin = base64.b64decode(pdf_base64)
                    nueva_cotizacion.pdf_comprobante = zlib.compress(pdf_bin)
                except Exception as pdf_err:
                    logger.warning("Error procesando PDF base64 cotización: %s", pdf_err)
                    nueva_cotizacion.pdf_comprobante = zlib.compress(b"ERROR_GENERACION_PDF")
            else:
                nueva_cotizacion.pdf_comprobante = zlib.compress(b"SIN_PDF_ADJUNTO")

            db.session.commit()

            return jsonify({
                'id': str(nueva_cotizacion.id),
                'message': 'Cotización creada correctamente.',
                'estado': nueva_cotizacion.estado
            }), 201

        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return jsonify({'message': 'Error al procesar cotización', 'error': str(e)}), 500

@bp.route('/cotizaciones/borrador', methods=['GET', 'POST'])
@token_required
def gestionar_borradores_cotizaciones(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    if request.method == 'GET':
        borradores = Cotizacion.query.filter_by(sucursal_id=sucursal.id, estado='Borrador').all()
        return jsonify([{
            'id': c.id,
            'cliente_nombre': c.cliente_nombre,
            'cliente_cedula': c.cliente_cedula,
            'fecha_emision': c.fecha_emision.isoformat(),
            'total': float(c.total),
            'estado': c.estado
        } for c in borradores])

    if request.method == 'POST':
        data = request.get_json() or {}
        detalles = data.get('detalles', [])

        try:
            db.session.commit()
            
            nuevo_borrador = Cotizacion(
                sucursal_id=sucursal.id,
                cliente_nombre=data.get('cliente_nombre', ''),
                cliente_cedula=data.get('cliente_cedula', ''),
                moneda=data.get('moneda', 'CRC'),
                estado='Borrador',
                usuario_id=current_user.id
            )
            db.session.add(nuevo_borrador)
            db.session.flush()

            for item in detalles:
                cantidad = _parse_decimal(item.get('cantidad', 1))
                precio_unitario = _parse_decimal(item.get('precio', 0))
                porcentaje_descuento = _parse_decimal(item.get('descuento', 0))
                porcentaje_impuesto = _parse_decimal(item.get('impuesto', 13))

                monto_base = quantize_money(cantidad * precio_unitario)
                descuento_monto = quantize_money(monto_base * porcentaje_descuento / Decimal('100'))
                base_neta = quantize_money(monto_base - descuento_monto)
                impuesto_monto = quantize_money(base_neta * porcentaje_impuesto / Decimal('100'))
                total_linea = quantize_money(base_neta + impuesto_monto)

                detalle = CotizacionDetalle(
                    cotizacion_id=nuevo_borrador.id,
                    descripcion=item.get('descripcion', 'Producto'),
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    porcentaje_descuento=porcentaje_descuento,
                    porcentaje_impuesto=porcentaje_impuesto,
                    tipo_impuesto=item.get('tipo_impuesto', '01'),
                    total_linea=total_linea
                )
                db.session.add(detalle)

            db.session.commit()
            return jsonify({'message': 'Borrador guardado exitosamente.', 'id': nuevo_borrador.id})

        except Exception as e:
            db.session.rollback()
            return jsonify({'message': 'Error al guardar borrador', 'error': str(e)}), 500

@bp.route('/cotizaciones/<string:id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
@require_role(['Administrador', 'Emisor'])
def cotizacion_detalle(current_user, id):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    cotizacion = Cotizacion.query.filter_by(id=id, sucursal_id=sucursal.id).first()
    if not cotizacion:
        return jsonify({'message': 'Cotización no encontrada'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': cotizacion.id,
            'cliente_nombre': cotizacion.cliente_nombre,
            'cliente_cedula': cotizacion.cliente_cedula,
            'fecha_emision': cotizacion.fecha_emision.isoformat(),
            'fecha_vencimiento': cotizacion.fecha_vencimiento.isoformat() if cotizacion.fecha_vencimiento else None,
            'moneda': cotizacion.moneda,
            'estado': cotizacion.estado,
            'observaciones': cotizacion.observaciones,
            'subtotal': float(cotizacion.subtotal),
            'descuentos': float(cotizacion.descuentos),
            'impuestos': float(cotizacion.impuestos),
            'total': float(cotizacion.total),
            'detalles': [{
                'descripcion': d.descripcion,
                'cantidad': float(d.cantidad),
                'precio': float(d.precio_unitario),
                'subtotal': float(d.total_linea),
                'impuesto': float(d.porcentaje_impuesto),
                'descuento': float(d.porcentaje_descuento)
            } for d in cotizacion.detalles]
        })

    if request.method == 'PUT':
        data = request.get_json() or {}
        
        cotizacion.estado = data.get('estado', cotizacion.estado)
        cotizacion.observaciones = data.get('observaciones', cotizacion.observaciones)
        if data.get('fecha_vencimiento'):
            try:
                cotizacion.fecha_vencimiento = datetime.fromisoformat(data.get('fecha_vencimiento').replace('Z', ''))
            except (ValueError, TypeError):
                pass

        subtotal_total = Decimal('0.00')
        descuentos_total = Decimal('0.00')
        impuestos_total = Decimal('0.00')
        total_final = Decimal('0.00')

        for d in cotizacion.detalles:
            db.session.delete(d)
            
        for item in data.get('detalles', []):
            cantidad = _parse_decimal(item.get('cantidad', 1))
            precio_unitario = _parse_decimal(item.get('precio', 0))
            porcentaje_descuento = _parse_decimal(item.get('descuento', 0))
            porcentaje_impuesto = _parse_decimal(item.get('impuesto', 13))

            monto_base = quantize_money(cantidad * precio_unitario)
            descuento_monto = quantize_money(monto_base * porcentaje_descuento / Decimal('100'))
            base_neta = quantize_money(monto_base - descuento_monto)
            impuesto_monto = quantize_money(base_neta * porcentaje_impuesto / Decimal('100'))
            total_linea = quantize_money(base_neta + impuesto_monto)

            subtotal_total += base_neta
            descuentos_total += descuento_monto
            impuestos_total += impuesto_monto
            total_final += total_linea

            det = CotizacionDetalle(
                cotizacion_id=cotizacion.id,
                descripcion=item.get('descripcion'),
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                porcentaje_descuento=porcentaje_descuento,
                porcentaje_impuesto=porcentaje_impuesto,
                tipo_impuesto=item.get('tipo_impuesto', '01'),
                total_linea=total_linea
            )
            db.session.add(det)
            
        cotizacion.subtotal = quantize_money(subtotal_total)
        cotizacion.descuentos = quantize_money(descuentos_total)
        cotizacion.impuestos = quantize_money(impuestos_total)
        cotizacion.total = quantize_money(total_final)

        db.session.commit()
        return jsonify({'message': 'Cotización actualizada correctamente'}), 200

    if request.method == 'DELETE':
        db.session.delete(cotizacion)
        db.session.commit()
        return jsonify({'message': 'Cotización eliminada correctamente'}), 200

@bp.route('/cotizaciones/<string:id>/descargar', methods=['GET'])
@token_required
def descargar_cotizacion(current_user, id):
    cotizacion = Cotizacion.query.get_or_404(id)
    if cotizacion.sucursal.empresa_id != current_user.empresa_id:
        return jsonify({'message': 'No autorizado'}), 403
        
    try:
        data = zlib.decompress(cotizacion.pdf_comprobante)
        return data, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename=cotizacion_{cotizacion.id}.pdf'
        }
    except Exception:
        return jsonify({'message': 'Archivo no disponible'}), 404

# ─── MODO CONTINGENCIA ──────────────────────────────────────
@bp.route('/contingencia/<string:id>', methods=['POST'])
@token_required
@require_role(['Administrador', 'Emisor'])
def marcar_contingencia(current_user, id):
    """Marca una factura como comprobante de contingencia para envío posterior."""
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada.'}), 403

    factura = Factura.query.filter_by(id=id, sucursal_id=sucursal.id).first()
    if not factura:
        return jsonify({'message': 'Factura no encontrada'}), 404

    result = crear_comprobante_contingencia(id)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result), 200


@bp.route('/contingencia/sincronizar', methods=['POST'])
@token_required
@require_role(['Administrador'])
def sincronizar_contingencia_endpoint(current_user):
    """Intenta enviar todos los comprobantes de contingencia pendientes a MH."""
    result = sincronizar_contingencia(empresa_id=current_user.empresa_id)
    status = 200 if result.get('fallidos', 0) == 0 else 207
    return jsonify(result), status

@bp.route('/mensajes-receptor', methods=['GET', 'POST'])
@token_required
@require_role(['Administrador', 'Emisor'])
def mensajes_receptor(current_user):
    empresa = Empresa.query.get(current_user.empresa_id)
    if request.method == 'GET':
        rows = MensajeReceptor.query.filter_by(empresa_id=empresa.id).order_by(MensajeReceptor.created_at.desc()).limit(100).all()
        return jsonify([{
            'id': m.id,
            'clave_comprobante': m.clave_comprobante,
            'tipo_mensaje': m.tipo_mensaje,
            'estado': m.estado,
            'detalle_mensaje': m.detalle_mensaje,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        } for m in rows])

    data = request.get_json() or {}
    try:
        clave = validar_clave(data.get('clave_comprobante'))
    except ValidationError as verr:
        return jsonify({'message': str(verr)}), 400

    tipo = str(data.get('tipo_mensaje', '1')).strip().lower()
    if tipo not in ('1', '2', '3', 'aceptar', 'parcial', 'rechazar'):
        return jsonify({'message': 'tipo_mensaje invalido (1, 2 o 3).'}), 400

    fecha_doc = _parse_date(data.get('fecha_emision_doc')) or datetime.utcnow()
    xml_bytes = build_mensaje_receptor_xml(
        clave_comprobante=clave,
        cedula_emisor=data.get('cedula_emisor', empresa.cedula_juridica),
        cedula_receptor=data.get('cedula_receptor', empresa.cedula_juridica),
        fecha_emision_doc=fecha_doc,
        tipo_mensaje=tipo,
        detalle_mensaje=data.get('detalle_mensaje', ''),
        consecutivo_receptor=data.get('consecutivo_receptor'),
        total_factura=_parse_decimal(data.get('total_factura')) if data.get('total_factura') is not None else None,
        total_impuesto=_parse_decimal(data.get('total_impuesto')) if data.get('total_impuesto') is not None else None,
    )

    registro = MensajeReceptor(
        empresa_id=empresa.id,
        clave_comprobante=clave,
        tipo_mensaje={'aceptar': '1', 'parcial': '2', 'rechazar': '3'}.get(tipo, tipo),
        detalle_mensaje=(data.get('detalle_mensaje') or '')[:80],
        consecutivo_receptor=data.get('consecutivo_receptor'),
        estado='generado',
        xml_mensaje=zlib.compress(xml_bytes),
        fecha_emision_doc=fecha_doc,
    )
    db.session.add(registro)
    db.session.commit()
    return jsonify({'message': 'Mensaje receptor generado.', 'id': registro.id}), 201
