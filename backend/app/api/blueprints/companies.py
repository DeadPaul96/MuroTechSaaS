from datetime import datetime
import os
import re
import zlib
import requests
from flask import Blueprint, jsonify, request, current_app
from cryptography.hazmat.primitives.serialization import pkcs12
from app.models import db, Empresa, Sucursal, Usuario, Rol, AccesoSucursal, Notificacion
from app.api.decorators.auth import token_required
from app.api.decorators.audit import audit_log
from app.services.auditoria_service import AuditoriaService
from app.extensions import limiter
from app.utils.validators import ValidationError, validar_identificacion, validar_email
from app.services.auth_service import AuthService
from app.services.empresa_service import EmpresaService
from app.api.blueprints.payments import create_payment_order, activate_empresa
from app.services.billing_plans import get_plan_info, DEFAULT_PLAN_TYPE
from app.utils.money import _parse_int
from app.utils.date_utils import _parse_date
from app.utils.crypto import encrypt_text, decrypt_text

bp = Blueprint('companies', __name__, url_prefix='/api')


# ── Helpers compartidos con invoices ──────────────────────────

def _empresa_ambiente(empresa) -> str:
    amb = (getattr(empresa, 'ambiente_hacienda', None) or os.environ.get('HACIENDA_AMBIENTE', 'stag')).lower()
    return 'prod' if amb in ('prod', 'produccion', 'production') else 'stag'


def _store_empresa_secret(empresa, field_name: str, plain_value: str):
    if not plain_value:
        return
    enc = encrypt_text(plain_value, current_app.config.get('ENCRYPTION_KEY'))
    setattr(empresa, field_name, enc)


def _read_empresa_secret(empresa, field_name: str) -> str:
    raw = getattr(empresa, field_name, None) or ''
    try:
        return decrypt_text(raw, current_app.config.get('ENCRYPTION_KEY'))
    except ValueError:
        return raw


def _mh_credenciales(empresa) -> dict:
    return {
        'username': _read_empresa_secret(empresa, 'api_usuario') or getattr(empresa, 'api_usuario', None),
        'password': _read_empresa_secret(empresa, 'api_password'),
    }


def validate_sucursal(current_user, sucursal_id):
    return EmpresaService.validate_sucursal(current_user, sucursal_id)


def create_notification(empresa_id, tipo, titulo, descripcion, link=None):
    return EmpresaService.create_notification(empresa_id, tipo, titulo, descripcion, link=link)

# Flujo de alta recomendado:
# 1. Registrar empresa
# 2. Seleccionar plan
# 3. Crear orden de pago / completar pago
@bp.route('/contribuyentes', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_REGISTRO', '10 per hour'))
def registrar_empresa():
    data = request.form
    file_p12 = request.files.get('api_p12_file')

    requerido = ['identificacion', 'nombre', 'email', 'password', 'api_usuario', 'api_password', 'api_pin']
    faltantes = [campo for campo in requerido if not data.get(campo)]
    if faltantes:
        return jsonify({'message': 'Campos requeridos faltantes.', 'missing': faltantes}), 400
    
    if Empresa.query.filter_by(cedula_juridica=data.get('identificacion')).first():
        return jsonify({'message': 'La empresa con esta cédula ya existe.'}), 400
        
    if Usuario.query.filter_by(email=data.get('email')).first():
        return jsonify({'message': 'El correo electrónico ya está en uso.'}), 400

    if not file_p12:
        return jsonify({'message': 'El archivo .p12 es requerido para configurar Hacienda.'}), 400

    # Honeypot anti-bot
    if data.get('website') or data.get('_hp') or request.form.get('company_url'):
        return jsonify({'message': 'Solicitud rechazada.'}), 400

    recaptcha_secret = os.environ.get('RECAPTCHA_SECRET_KEY')
    if recaptcha_secret:
        token = data.get('recaptcha_token') or request.form.get('recaptcha_token')
        if not token:
            return jsonify({'message': 'Verificación reCAPTCHA requerida.'}), 400
        verify = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': recaptcha_secret, 'response': token},
            timeout=10,
        )
        if not verify.ok or not verify.json().get('success'):
            return jsonify({'message': 'reCAPTCHA inválido.'}), 400

    try:
        tipo_id = data.get('tipo_id', '02')
        validar_identificacion(tipo_id, data.get('identificacion'))
        validar_email(data.get('email'))
    except ValidationError as verr:
        return jsonify({'message': str(verr)}), 400

    try:
        p12_bin_comprimido = None
        p12_metadata = ""

        if file_p12:
            raw_p12 = file_p12.read()
            pin = data.get('api_pin', '').encode()
            
            try:
                p12_data = pkcs12.load_key_and_certificates(raw_p12, pin)
                cert = p12_data[1]
                if cert:
                    p12_metadata = str(cert.serial_number)
            except Exception as crypto_err:
                return jsonify({'message': 'Error al leer la Llave Criptográfica. Verifique el PIN.', 'error': str(crypto_err)}), 400

            p12_bin_comprimido = EmpresaService.encrypt_p12_data(raw_p12)

        plan_info = get_plan_info(data.get('plan_tipo', DEFAULT_PLAN_TYPE))
        plan_tipo = plan_info['type']
        plan_cuota = plan_info['plan_cuota']

        nueva_empresa = Empresa(
            tipo_identificacion=data.get('tipo_id', '02'),
            cedula_juridica=data.get('identificacion'),
            razon_social=data.get('nombre'),
            nombre_comercial=data.get('nombre'),
            actividad_economica=data.get('actividad'),
            regimen=data.get('regimen'),
            email_contacto=data.get('email'),
            telefono=data.get('telefono'),
            api_usuario=data.get('api_usuario'),
            api_password=data.get('api_password'),
            api_pin_p12=data.get('api_pin'),
            ambiente_hacienda='stag',
            api_p12_bin=p12_bin_comprimido,
            api_p12_text=None,
            api_p12_metadata=p12_metadata,
            plan_tipo=plan_tipo,
            plan_cuota=plan_cuota,
            plan_estado='pendiente',
            is_active=False,
            rep_nombre=data.get('contacto_nombre'),
            rep_apellidos=data.get('contacto_apellidos'),
            rep_telefono=data.get('contacto_telefono'),
            rep_email=data.get('contacto_email')
        )
        EmpresaService.store_secret(nueva_empresa, 'api_password', data.get('api_password'))
        EmpresaService.store_secret(nueva_empresa, 'api_pin_p12', data.get('api_pin'))
        db.session.add(nueva_empresa)
        db.session.flush()
        
        sucursal_principal = Sucursal(
            empresa_id=nueva_empresa.id,
            nombre="Sede Principal",
            numero_sucursal=data.get('api_sucursal', '001'),
            terminal=data.get('api_terminal', '00001'),
            direccion=data.get('direccion_completa'),
            c_factura=_parse_int(data.get('ultimo_consecutivo'), 0)
        )
        db.session.add(sucursal_principal)
        db.session.flush()

        nuevo_usuario = Usuario(
            empresa_id=nueva_empresa.id,
            nombre=data.get('nombre_admin', 'Administrador Principal'),
            email=data.get('email'),
            is_superadmin=False,
            is_active=False
        )
        nuevo_usuario.set_password(data.get('password'))
        db.session.add(nuevo_usuario)
        db.session.flush()

        rol_admin = Rol.query.filter_by(nombre='Administrador').first()
        acceso = AccesoSucursal(
            usuario_id=nuevo_usuario.id,
            sucursal_id=sucursal_principal.id,
            rol_id=rol_admin.id
        )
        db.session.add(acceso)

        payment = create_payment_order(nueva_empresa, usuario=nuevo_usuario, plan_tipo=plan_tipo)
        db.session.commit()

        return jsonify({
            'message': 'Empresa registrada. El plan está pendiente hasta confirmar el pago.',
            'empresa_id': nueva_empresa.id,
            'p12_digits': p12_metadata,
            'payment': {
                'id': payment.id,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'checkout_url': payment.checkout_url,
                'plan_tipo': payment.plan_tipo,
                'plan_cuota': payment.plan_cuota
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error crítico en el registro', 'error': str(e)}), 500

@bp.route('/sucursales', methods=['GET', 'POST'])
@token_required
def gestionar_sucursales(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede gestionar sucursales.'}), 403

    if request.method == 'GET':
        return jsonify(EmpresaService.list_sucursales(current_user))

    try:
        payload = EmpresaService.create_sucursal(current_user, request.get_json() or {})
        return jsonify(payload), 201
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/usuarios', methods=['GET', 'POST'])
@token_required
def gestionar_usuarios(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Solo el Emisor/Administrador puede gestionar usuarios.'}), 403

    if request.method == 'GET':
        return jsonify(EmpresaService.list_users(current_user.empresa_id))

    if request.method == 'POST':
        try:
            payload = EmpresaService.create_user(current_user, request.get_json() or {})
            return jsonify(payload), 201
        except ValidationError as exc:
            return jsonify({'message': str(exc)}), 400

@bp.route('/usuarios/<string:id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_usuario(current_user, id):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Solo el Emisor/Administrador puede gestionar usuarios.'}), 403

    try:
        if request.method == 'PUT':
            result = EmpresaService.update_user(current_user, id, request.get_json() or {})
            return jsonify(result)

        result = EmpresaService.delete_user(current_user, id)
        return jsonify(result)
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/roles', methods=['GET'])
@token_required
def get_roles(current_user):
    roles = Rol.query.all()
    return jsonify([{'id': r.id, 'nombre': r.nombre, 'descripcion': r.descripcion} for r in roles])

@bp.route('/config/empresa', methods=['GET', 'PUT'])
@token_required
@audit_log('empresa', snapshot_fn=AuditoriaService.snapshot_empresa)
def config_empresa(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Acceso denegado. Solo el Emisor/Administrador puede gestionar la configuración de la empresa.'}), 403

    if request.method == 'GET':
        return jsonify(EmpresaService.get_empresa_config(Empresa.query.get(current_user.empresa_id)))

    try:
        payload = EmpresaService.update_empresa_config(current_user, request.get_json() or {})
        return jsonify(payload)
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/config/facturacion', methods=['GET', 'PUT'])
@token_required
def config_facturacion(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Acceso denegado. Solo el Emisor/Administrador puede gestionar la configuración de facturación.'}), 403

    if request.method == 'GET':
        return jsonify(EmpresaService.get_facturacion_config(Empresa.query.get(current_user.empresa_id)))

    try:
        payload = EmpresaService.update_facturacion_config(current_user, request.get_json() or {})
        return jsonify(payload)
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/config/plan', methods=['GET', 'PUT'])
@token_required
def config_plan(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede gestionar el plan.'}), 403

    if request.method == 'GET':
        return jsonify(EmpresaService.get_plan_config(Empresa.query.get(current_user.empresa_id)))

    try:
        payload = EmpresaService.update_plan_config(current_user, request.get_json() or {})
        return jsonify(payload)
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/config/plan/suspender', methods=['POST'])
@token_required
@audit_log('plan')
def suspender_plan(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede suspender el plan.'}), 403

    payload = EmpresaService.suspend_plan(current_user, motivo=request.json.get('motivo', 'Suspensión por administrador'))
    return jsonify(payload), 200

@bp.route('/config/plan/reactivar', methods=['POST'])
@token_required
@audit_log('plan')
def reactivar_plan(current_user):
    if not AuthService.is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede reactivar el plan.'}), 403

    try:
        payload = EmpresaService.reactivate_empresa(current_user, motivo=request.json.get('motivo', 'Reactivación por administrador'))
        return jsonify(payload), 200
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/notificaciones/mark-all-read', methods=['POST'])
@token_required
def mark_all_read_endpoint(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    try:
        payload = EmpresaService.mark_all_notifications_read(current_user, sucursal_id=sucursal_id)
        return jsonify(payload)
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 400

@bp.route('/notificaciones/unread-count', methods=['GET'])
@token_required
def get_unread_count(current_user):
    return jsonify({'count': EmpresaService.get_unread_notifications_count(current_user)})

@bp.route('/notificaciones', methods=['GET'])
@token_required
def get_notificaciones(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    try:
        return jsonify(EmpresaService.get_notifications(current_user, sucursal_id))
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 403

@bp.route('/notificaciones/<string:id>/read', methods=['PUT'])
@token_required
def mark_notificacion_read(current_user, id):
    try:
        return jsonify(EmpresaService.mark_notification_read(current_user, id))
    except ValidationError as exc:
        return jsonify({'message': str(exc)}), 404

@bp.route('/notificaciones/read_all', methods=['PUT'])
@token_required
def mark_all_notificaciones_read(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    payload = EmpresaService.mark_all_notifications_read(current_user, sucursal_id=sucursal_id)
    return jsonify(payload)
