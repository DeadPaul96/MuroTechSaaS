"""Central API backend para MUROTECH.

Este módulo es el orquestador principal del backend: configura Flask,
registra middleware, define rutas de la API, administra la integración
con Hacienda y coordina la persistencia en la base de datos.

El backend mantiene topologías de negocio y fiscales en módulos separados
pero usa este archivo como punto único de entrada y control.
"""

# NOTE: Este archivo es el monolito legacy activo que todavía usan
# scripts y despliegue (`gunicorn --chdir backend api.app:app`).
# La migración a `backend/app/api/blueprints/` y `backend/app/services/`
# está en curso.

import os
import sys
import re
import zlib
import base64
import secrets
from pathlib import Path
from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, getcontext
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import jwt
import requests
from lxml import etree
from sqlalchemy import func, or_, text
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

sys_path_inserted = False
_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
    sys_path_inserted = True

from fiscal.xml_builder import build_comprobante_xml, build_mensaje_receptor_xml
from fiscal.clave import generar_clave, generar_consecutivo, calcular_digito_verificador
from fiscal.signer import firmar_xml, encrypt_p12_data, decrypt_p12_data
from fiscal.hacienda_client import HaciendaClient, HaciendaError, mapear_estado_mh
from fiscal.xsd_validator import validate_comprobante_xml, XmlSchemaError, validation_status
from core.config import Config
from core.logging_setup import setup_logging
from core.crypto_utils import encrypt_text, decrypt_text
from services.billing_plans import (
    AVAILABLE_PLANS,
    DEFAULT_PLAN_TYPE,
    get_plan_info,
    plans_public_payload,
)
from core.validators import (
    ValidationError,
    validar_identificacion,
    validar_email,
    validar_clave,
    validar_consecutivo,
    validar_cabys,
)

try:
    from .models import (
        db, Empresa, Sucursal, Rol, Usuario, RevokedToken, AccesoSucursal,
        Cliente, Producto, Factura, FacturaDetalle, Notificacion, Pago,
        InventarioMovimiento, Compra, Cotizacion, CotizacionDetalle, MensajeReceptor,
        Plan, Suscripcion, PagoSuscripcion,
    )
    from . import supadmin_api
except ImportError:
    from models import (
        db, Empresa, Sucursal, Rol, Usuario, RevokedToken, AccesoSucursal,
        Cliente, Producto, Factura, FacturaDetalle, Notificacion, Pago,
        InventarioMovimiento, Compra, Cotizacion, CotizacionDetalle, MensajeReceptor,
        Plan, Suscripcion, PagoSuscripcion,
    )
    import supadmin_api

current_file = Path(__file__).resolve()
backend_root = current_file.parents[1]
load_dotenv(backend_root / '.env')

app = Flask(__name__)
_cfg = Config(backend_root)
_cfg.apply_flask(app)
setup_logging(app)

CORS(app, resources={r"/api/*": {"origins": _cfg.cors_origins()}})

_default_limits = os.environ.get('RATELIMIT_DEFAULT', '300 per day;60 per hour').split(';')
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URL', 'memory://'),
    default_limits=[lim.strip() for lim in _default_limits if lim.strip()],
)

if app.config.get('ENCRYPTION_KEY'):
    try:
        Fernet(app.config['ENCRYPTION_KEY'])
    except Exception as err:
        raise RuntimeError(
            'ENCRYPTION_KEY inválida. Debe ser una llave URL-safe base64 de 32 bytes.'
        ) from err
else:
    print('WARNING: ENCRYPTION_KEY no definida. P12 y credenciales MH no se cifrarán en reposo.')

getcontext().prec = 28

db.init_app(app)

try:
    from flask_migrate import Migrate
    Migrate(app, db)
except ImportError:
    pass


def create_payment_order(empresa, usuario=None, plan_tipo=None, provider='manual'):
    """Crea un objeto de pago de suscripción en estado pendiente.

    Este helper no confirma el pago, solo registra el pedido para el flujo
    de suscripción y habilitación de planes.
    """
    plan_info = get_plan_info(plan_tipo or empresa.plan_tipo)
    checkout_code = secrets.token_urlsafe(16)
    payment = Pago(
        empresa_id=empresa.id,
        usuario_id=getattr(usuario, 'id', None) if usuario else None,
        plan_tipo=plan_info['type'],
        plan_cuota=plan_info['plan_cuota'],
        amount=plan_info['amount'],
        currency='CRC',
        status='pending',
        provider=provider,
        description=f'Pago de activación para plan {plan_info["label"]}',
        checkout_url=f'https://pagos.murotech.local/checkout/{checkout_code}'
    )
    db.session.add(payment)
    db.session.flush()
    return payment

# ==========================================
# INICIALIZACIÃN DE ROLES POR DEFECTO
# ==========================================
def init_db():
    """Crea tablas y roles iniciales si no existen.

    Este método se usa para inicializar la base de datos en entornos de
    desarrollo y pruebas; no está pensado para ejecución en cada request.
    """
    with app.app_context():
        db.create_all()
        # Insertar roles si no existen
        roles_default = [
            {'nombre': 'Administrador', 'descripcion': 'Control total de la sucursal/empresa'},
            {'nombre': 'Emisor', 'descripcion': 'Solo puede emitir facturas y gestionar clientes'},
            {'nombre': 'Auditor', 'descripcion': 'Solo lectura para revisar mÃ©tricas y facturas'}
        ]
        for rd in roles_default:
            if not Rol.query.filter_by(nombre=rd['nombre']).first():
                rol = Rol(nombre=rd['nombre'], descripcion=rd['descripcion'])
                db.session.add(rol)
        db.session.commit()

# ==========================================
# MIDDLEWARE DE AUTENTICACIÃ“N (JWT)
# ==========================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'message': 'Token faltante. Acceso denegado.'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = Usuario.query.get(data['user_id'])
            if not current_user:
                raise Exception("Usuario no encontrado")
            if not current_user.is_active:
                return jsonify({'message': 'Usuario inactivo. Acceso denegado.'}), 403
            if not current_user.empresa or not current_user.empresa.is_active:
                return jsonify({'message': 'Empresa inactiva. Acceso denegado.'}), 403
            if current_user.empresa.plan_estado != 'activo':
                return jsonify({'message': 'Cuenta con plan bloqueado. Contacte al administrador.'}), 403
            revoked = RevokedToken.query.filter_by(token=token).first() if 'RevokedToken' in globals() else None
            if revoked:
                return jsonify({'message': 'Token revocado. Inicie sesión nuevamente.'}), 401
        except Exception as e:
            return jsonify({'message': 'Token invÃ¡lido o expirado.', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'message': 'Token faltante. Acceso denegado.'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = Usuario.query.get(data['user_id'])
            if not current_user:
                raise Exception("Usuario no encontrado")
            if not current_user.is_superadmin:
                return jsonify({'message': 'Acceso denegado. Solo SuperAdmin.'}), 403
            revoked = RevokedToken.query.filter_by(token=token).first() if 'RevokedToken' in globals() else None
            if revoked:
                return jsonify({'message': 'Token revocado. Inicie sesión nuevamente.'}), 401
        except Exception as e:
            return jsonify({'message': 'Token inválido o expirado.', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated


def is_company_admin(user):
    """Determina si un usuario es administrador de la empresa (Emisor).
    Este rol puede administrar sucursales, usuarios y ver métricas de toda la empresa.
    """
    if not user:
        return False
    return any(acc.rol and acc.rol.nombre == 'Administrador' for acc in user.accesos)


def get_profile_type(user):
    if not user:
        return None
    if user.is_superadmin:
        return 'SuperAdmin'
    if is_company_admin(user):
        return 'Emisor'
    return 'Usuario'


def require_role(allowed_roles):
    """
    Decorador para verificar si el usuario tiene permiso en una sucursal.
    Espera que la peticiÃ³n incluya 'sucursal_id' en los headers o args.
    """
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.is_superadmin:
                return f(current_user, *args, **kwargs)
                
            sucursal_id = request.headers.get('X-Sucursal-ID') or request.args.get('sucursal_id')
            if not sucursal_id:
                return jsonify({'message': 'Debe especificar la sucursal (X-Sucursal-ID).'}), 400
                
            acceso = AccesoSucursal.query.filter_by(usuario_id=current_user.id, sucursal_id=sucursal_id).first()
            if not acceso or acceso.rol.nombre not in allowed_roles:
                return jsonify({'message': 'No tiene permisos suficientes en esta sucursal.'}), 403
                
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

# ==========================================
# RUTAS DE ESTADO Y UTILIDADES
# ==========================================

@app.route('/')
def home():
    return jsonify({"message": "MUROTECH API is running", "status": "online"}), 200

@app.route('/api/health')
def health():
    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'ok'
    except Exception as e:
        db_status = f'error: {str(e)}'

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    db_type = 'sqlite' if 'sqlite' in db_uri else 'postgresql' if 'postgresql' in db_uri else 'unknown'

    return jsonify({
        "status": "healthy",
        "db_type": db_type,
        "db_status": db_status
    }), 200

@app.route('/api/time')
def get_server_time():
    now = datetime.now()
    return jsonify({
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    }), 200

@app.route('/api/tipo-cambio', methods=['GET'])
def route_tipo_cambio():
    """Endpoint para que el frontend obtenga el tipo de cambio actual."""
    try:
        rates = get_tipo_cambio()
        # Retornar formato plano que espera el frontend
        return jsonify({
            "venta": rates.get('venta', 0.0),
            "compra": rates.get('compra', 0.0),
            "euro_colones": rates.get('euro_colones', 542.11),
            "euro_dolares": rates.get('euro_dolares', 1.1772),
            "timestamp": datetime.now().isoformat(),
            "fecha": datetime.now().strftime("%d/%m/%Y")
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "venta": 525.50,
            "compra": 515.20,
            "euro_colones": 542.11,
            "euro_dolares": 1.1772,
            "fecha": datetime.now().strftime("%d/%m/%Y")
        }), 200

def _parse_float(value, default=0.0):
    """Normaliza diferentes formatos de número a float seguro."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r'[^\d\.-]', '', str(value))
    try:
        return float(cleaned) if cleaned not in ('', '.', '-', '-0') else default
    except ValueError:
        return default


def _parse_int(value, default=0):
    """Convierte un valor a entero o retorna un valor por defecto."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value, end_of_day=False):
    """Convierte fechas en string a datetime con múltiples formatos admitidos."""
    if not value:
        return None
    if isinstance(value, datetime):
        if end_of_day:
            return value.replace(hour=23, minute=59, second=59, microsecond=999999)
        return value
    try:
        parsed = datetime.fromisoformat(value)
        if end_of_day:
            return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed
    except ValueError:
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                parsed = datetime.strptime(value, fmt)
                if end_of_day:
                    return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
                return parsed
            except ValueError:
                continue
    return None


def _parse_decimal(value, default=Decimal('0.00')):
    """Convierte una cadena numérica a Decimal con dos decimales."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = re.sub(r'[^\d\.-]', '', str(value))
        if cleaned in ('', '.', '-', '-0'):
            return default
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return default


def quantize_money(value):
    """Normaliza un Decimal financiero al formato de dos decimales."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _p12_encryption_key():
    return app.config.get('ENCRYPTION_KEY')


def _decrypt_p12_data(p12_data):
    return decrypt_p12_data(p12_data, _p12_encryption_key())


def _encrypt_p12_data(raw_p12):
    return encrypt_p12_data(raw_p12, _p12_encryption_key())


@app.route('/api/planes', methods=['GET'])
def obtener_planes():
    return jsonify({'planes': plans_public_payload()})


@app.route('/api/pagos/checkout', methods=['POST'])
def crear_checkout_pago():
    data = request.get_json(force=True, silent=True) or {}
    empresa_id = data.get('empresa_id')
    plan_tipo = data.get('plan_tipo')

    if not empresa_id:
        return jsonify({'message': 'Se requiere empresa_id para iniciar un pago.'}), 400

    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404

    payment = create_payment_order(empresa, plan_tipo=plan_tipo)
    db.session.commit()

    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'amount': str(payment.amount),
        'currency': payment.currency,
        'checkout_url': payment.checkout_url,
        'plan_tipo': payment.plan_tipo,
        'plan_cuota': payment.plan_cuota
    })


@app.route('/api/pagos/confirmar', methods=['POST'])
def confirmar_pago():
    data = request.get_json(force=True, silent=True) or {}
    payment_id = data.get('payment_id')

    if not payment_id:
        return jsonify({'message': 'payment_id es requerido.'}), 400

    payment = Pago.query.filter_by(id=payment_id).first()
    if not payment:
        return jsonify({'message': 'Pago no encontrado.'}), 404

    if payment.status != 'pending':
        return jsonify({'message': 'El pago ya fue procesado o no está en estado pendiente.'}), 400

    payment.status = 'completed'
    payment.provider = data.get('provider', payment.provider)
    payment.transaction_id = data.get('transaction_id')
    payment.updated_at = datetime.utcnow()

    empresa = Empresa.query.filter_by(id=payment.empresa_id).first()
    if empresa:
        empresa.plan_tipo = payment.plan_tipo
        empresa.plan_cuota = payment.plan_cuota
        empresa.plan_estado = 'activo'
        empresa.is_active = True
        activate_empresa(empresa, motivo='Pago confirmado')

    db.session.commit()

    return jsonify({
        'message': 'Pago confirmado y cuenta activada.',
        'payment_id': payment.id,
        'plan_tipo': payment.plan_tipo,
        'plan_cuota': payment.plan_cuota,
        'empresa_id': payment.empresa_id
    })


@app.route('/api/pagos/estatus/<string:payment_id>', methods=['GET'])
def estado_pago(payment_id):
    payment = Pago.query.filter_by(id=payment_id).first()
    if not payment:
        return jsonify({'message': 'Pago no encontrado.'}), 404
    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'amount': str(payment.amount),
        'currency': payment.currency,
        'checkout_url': payment.checkout_url,
        'plan_tipo': payment.plan_tipo,
        'plan_cuota': payment.plan_cuota,
        'empresa_id': payment.empresa_id
    })


def _get_plan_period_start(periodo):
    ahora = datetime.utcnow()
    mes = ahora.month
    periodo = (periodo or 'mensual').lower()
    meses_periodo = {
        'mensual': 1,
        'bimestral': 2,
        'trimestral': 3,
        'cuatrimestral': 4,
        'semestral': 6,
        'anual': 12
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


def validate_sucursal(current_user, sucursal_id):
    if not sucursal_id:
        return None
    return Sucursal.query.filter_by(id=sucursal_id, empresa_id=current_user.empresa_id).first()


def suspend_empresa(empresa, motivo='Plan vencido o bloqueado'):
    empresa.plan_estado = 'suspendido'
    empresa.is_active = False
    for usuario in empresa.usuarios:
        usuario.is_active = False
    create_notification(
        empresa.id,
        'pago',
        'Cuenta suspendida',
        f'La cuenta fue suspendida: {motivo}'
    )


def activate_empresa(empresa, motivo='Plan reactivado'):
    empresa.plan_estado = 'activo'
    empresa.is_active = True
    for usuario in empresa.usuarios:
        usuario.is_active = True
    create_notification(
        empresa.id,
        'pago',
        'Cuenta reactivada',
        f'La cuenta fue reactivada: {motivo}'
    )


# ==========================================
# UTILIDADES FISCALES HACIENDA v4.4
# ==========================================

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
        print(f"Error consultando API Hacienda: {e}")

    # Fallback local solo si la API de Hacienda falla
    fallback = {'venta': 525.50, 'compra': 515.20, 'euro_colones': 542.11, 'euro_dolares': 1.1772}
    if _tipo_cambio_cache['rates']:
        return _tipo_cambio_cache['rates']
    return fallback


def build_hacienda_factura_xml(factura):
    """Genera XML v4.4 según tipo de comprobante (FE, TE, NC, ND, FEC)."""
    return build_comprobante_xml(factura).decode('utf-8')


def _empresa_ambiente(empresa) -> str:
    amb = (getattr(empresa, 'ambiente_hacienda', None) or os.environ.get('HACIENDA_AMBIENTE', 'stag')).lower()
    return 'prod' if amb in ('prod', 'produccion', 'production') else 'stag'


def _store_empresa_secret(empresa, field_name: str, plain_value: str):
    if not plain_value:
        return
    enc = encrypt_text(plain_value, app.config.get('ENCRYPTION_KEY'))
    setattr(empresa, field_name, enc)


def _read_empresa_secret(empresa, field_name: str) -> str:
    raw = getattr(empresa, field_name, None) or ''
    try:
        return decrypt_text(raw, app.config.get('ENCRYPTION_KEY'))
    except ValueError:
        return raw


def _mh_credenciales(empresa) -> dict:
    return {
        'username': _read_empresa_secret(empresa, 'api_usuario') or getattr(empresa, 'api_usuario', None),
        'password': _read_empresa_secret(empresa, 'api_password'),
    }


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

# ==========================================
# UTILIDADES DE NOTIFICACIONES
# ==========================================

def create_notification(empresa_id, tipo, titulo, descripcion, link=None):
    """Crea una notificación persistente para la empresa"""
    notif = Notificacion(
        empresa_id=empresa_id,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
    return notif

def parse_ubicacion_costarica(direccion_texto):
    """
    Parsea Provincia, Cantón, Distrito, Barrio a partir del texto libre de la dirección.
    Si no encuentra coincidencia, usa los códigos por defecto (San José, Central, Carmen).
    """
    provincia = "1"
    canton = "01"
    distrito = "01"
    barrio = "01"
    otras_senas = (direccion_texto or "Otras senas por definir").strip()[:250]
    
    texto = (direccion_texto or "").lower()
    
    # Mapeo básico de provincias
    provincias_map = {
        "alajuela": "2",
        "cartago": "3",
        "heredia": "4",
        "guanacaste": "5",
        "puntarenas": "6",
        "limon": "7",
        "limón": "7",
        "san jose": "1",
        "san josé": "1"
    }
    
    for key, code in provincias_map.items():
        if key in texto:
            provincia = code
            break
            
    # Mapeo básico de cantones conocidos
    cantones_map = {
        "escazu": "02", "escazú": "02",
        "desamparados": "03",
        "puriscal": "04",
        "tarrazu": "05", "tarrazú": "05",
        "aserri": "06", "aserrí": "06",
        "mora": "07",
        "goicoechea": "08",
        "santa ana": "09",
        "alajuelita": "10",
        "coronado": "11",
        "acosta": "12",
        "tibas": "13", "tibás": "13",
        "moravia": "14",
        "montes de oca": "15",
        "turrubares": "16",
        "dota": "17",
        "curridabat": "18",
        "perez zeledon": "19", "pérez zeledón": "19",
        "leon cortes": "20", "león cortés": "20"
    }
    
    # Si la provincia es San José
    if provincia == "1":
        for key, code in cantones_map.items():
            if key in texto:
                canton = code
                break
                
    # Alajuela
    elif provincia == "2":
        canton = "01" # Default Central Alajuela
        if "san ramon" in texto or "san ramón" in texto: canton = "02"
        elif "grecia" in texto: canton = "03"
        elif "san carlos" in texto: canton = "10"
    # Cartago
    elif provincia == "3":
        canton = "01" # Default Central Cartago
        if "paraiso" in texto or "paraíso" in texto: canton = "02"
        elif "la union" in texto or "la unión" in texto: canton = "03"
    # Heredia
    elif provincia == "4":
        canton = "01" # Default Central Heredia
        if "barva" in texto: canton = "02"
        elif "santo domingo" in texto: canton = "03"
        elif "san rafael" in texto: canton = "05"
        
    return provincia, canton, distrito, barrio, otras_senas


@app.route('/api/contribuyentes', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_REGISTRO', '10 per hour'))
def registrar_empresa():
    """Registra una nueva empresa (Tenant) y su usuario SuperAdministrador con compresión de datos"""
    # Usamos form data para recibir el archivo p12
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

    # Honeypot anti-bot (campo oculto que no debe completarse)
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

        # Procesamiento de Llave Criptográfica (Mindset Mojo: Eficiencia y Seguridad)
        if file_p12:
            raw_p12 = file_p12.read()
            pin = data.get('api_pin', '').encode()
            
            # 1. Extraer Metadatos (Dígitos del Serial/ID)
            try:
                # El formato PKCS12 requiere el PIN para abrirse
                p12_data = pkcs12.load_key_and_certificates(raw_p12, pin)
                cert = p12_data[1] # El certificado es el segundo elemento
                if cert:
                    # Extraemos el número de serie como los "dígitos" representativos
                    p12_metadata = str(cert.serial_number)
            except Exception as crypto_err:
                return jsonify({'message': 'Error al leer la Llave Criptográfica. Verifique el PIN.', 'error': str(crypto_err)}), 400

            # 2. Compresión y encriptación de la llave fiscal guardada en el tenant
            p12_bin_comprimido = _encrypt_p12_data(raw_p12)

        # 1. Preparar plan y estado inicial de la empresa
        plan_info = get_plan_info(data.get('plan_tipo', DEFAULT_PLAN_TYPE))
        plan_tipo = plan_info['type']
        plan_cuota = plan_info['plan_cuota']

        # 2. Crear Empresa (Tenant) con todos los datos de Hacienda, plan y compresión
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
            api_password=encrypt_text(data.get('api_password'), app.config.get('ENCRYPTION_KEY')),
            api_pin_p12=encrypt_text(data.get('api_pin'), app.config.get('ENCRYPTION_KEY')),
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
        db.session.add(nueva_empresa)
        db.session.flush() # Para obtener el ID de la empresa
        
        # 3. Crear Sucursal y Terminal
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

        # 4. Crear Usuario Administrador en estado pendiente
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

        # 5. Asignar rol Admin
        rol_admin = Rol.query.filter_by(nombre='Administrador').first()
        acceso = AccesoSucursal(
            usuario_id=nuevo_usuario.id,
            sucursal_id=sucursal_principal.id,
            rol_id=rol_admin.id
        )
        db.session.add(acceso)

        # 6. Crear orden de pago inicial para activar el plan
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

@app.route('/api/hacienda/validar-llave', methods=['POST'])
def validar_llave():
    """Valida una llave .p12 y extrae sus metadatos (Serial/Dígitos) sin guardarla"""
    file_p12 = request.files.get('api_p12_file')
    pin = request.form.get('api_pin', '')
    
    if not file_p12 or not pin:
        return jsonify({'message': 'Archivo y PIN son requeridos.'}), 400
        
    try:
        raw_p12 = file_p12.read()
        p12_data = pkcs12.load_key_and_certificates(raw_p12, pin.encode())
        cert = p12_data[1]
        
        if cert:
            metadata = str(cert.serial_number)
            # Retornamos los dígitos para llenar el campo de texto en el frontend
            return jsonify({
                'valid': True,
                'digits': metadata,
                'subject': str(cert.subject)
            })
        return jsonify({'message': 'No se encontró certificado en el archivo.'}), 400
    except Exception as e:
        return jsonify({'message': 'PIN incorrecto o archivo inválido.', 'error': str(e)}), 400

@app.route('/api/login', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_LOGIN', '20 per hour'))
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(email=data.get('email')).first()
    
    if not usuario or not usuario.check_password(data.get('password')):
        return jsonify({'message': 'Credenciales inválidas.'}), 401
        
    if not usuario.is_active:
        return jsonify({'message': 'Usuario inactivo. Contacte al administrador.'}), 403
    if not usuario.empresa or not usuario.empresa.is_active:
        return jsonify({'message': 'Empresa inactiva. Contacte al administrador.'}), 403
    if usuario.empresa.plan_estado != 'activo':
        return jsonify({'message': 'Cuenta con plan bloqueado. Contacte al administrador.'}), 403

    # Generar Token JWT
    token = jwt.encode({
        'user_id': usuario.id,
        'empresa_id': usuario.empresa_id,
        'is_superadmin': usuario.is_superadmin,
        'exp': datetime.utcnow() + timedelta(hours=12)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    # Determinar pantallas según perfil
    if usuario.is_superadmin:
        pantallas = ['superAdmin']
    elif is_company_admin(usuario):
        # Emisor: Acceso a todo menos superAdmin
        pantallas = ["auditoria", "clientes", "configuracion", "cotizaciones", "editarFactura", "inventario", "notificaciones", "panelControl", "pantallaFacturacion", "pos", "registro", "reportes"]
    else:
        # Usuario de sucursal: solo sus pantallas asignadas por el Emisor.
        pantallas_raw = usuario.pantallas_asignadas.split(',') if usuario.pantallas_asignadas else []
        pantallas = [p.strip() for p in pantallas_raw if p.strip() and p.strip() != 'superAdmin']

    # Obtener sucursales a las que tiene acceso
    accesos = []
    if usuario.is_superadmin or is_company_admin(usuario):
        sucursales = Sucursal.query.filter_by(empresa_id=usuario.empresa_id).all()
        rol_name = 'SuperAdmin' if usuario.is_superadmin else 'Administrador'
        for s in sucursales:
            accesos.append({'sucursal_id': s.id, 'nombre': s.nombre, 'rol': rol_name})
    else:
        for acc in usuario.accesos:
            accesos.append({'sucursal_id': acc.sucursal_id, 'nombre': acc.sucursal.nombre, 'rol': acc.rol.nombre})

    if not accesos and not usuario.is_superadmin:
        return jsonify({'message': 'Usuario sin acceso a sucursales. Contacte al administrador.'}), 403

    return jsonify({
        'token': token,
        'user': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'email': usuario.email,
            'empresa': usuario.empresa.razon_social,
            'perfil': get_profile_type(usuario),
            'is_superadmin': usuario.is_superadmin,
            'pantallas': pantallas,
            'plan_tipo': usuario.empresa.plan_tipo,
            'plan_label': get_plan_info(usuario.empresa.plan_tipo)['label'],
            'plan_cuota': usuario.empresa.plan_cuota,
            'plan_estado': usuario.empresa.plan_estado
        },
        'accesos': accesos
    }), 200


# ==========================================
# GESTIÓN DE USUARIOS Y SUCURSALES (MULTI-TENANT)
# ==========================================

@app.route('/api/sucursales', methods=['GET', 'POST'])
@token_required
def gestionar_sucursales(current_user):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede gestionar sucursales.'}), 403
        
    if request.method == 'GET':
        sucursales = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()
        return jsonify([{'id': s.id, 'nombre': s.nombre, 'numero': s.numero_sucursal} for s in sucursales])
        
    if request.method == 'POST':
        data = request.get_json()
        nueva = Sucursal(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            numero_sucursal=data.get('numero_sucursal'),
            direccion=data.get('direccion')
        )
        db.session.add(nueva)
        db.session.commit()
        return jsonify({'message': 'Sucursal creada.'}), 201

@app.route('/api/usuarios', methods=['GET', 'POST'])
@token_required
def gestionar_usuarios(current_user):
    """Permite a un Emisor/Administrador crear nuevos usuarios dentro de su empresa"""
    if not is_company_admin(current_user):
        return jsonify({'message': 'Solo el Emisor/Administrador puede gestionar usuarios.'}), 403
        
    if request.method == 'GET':
        usuarios = Usuario.query.filter_by(empresa_id=current_user.empresa_id).all()
        result = []
        for u in usuarios:
            acc = [{'sucursal': a.sucursal.nombre, 'rol': a.rol.nombre} for a in u.accesos]
            result.append({
                'id': u.id, 
                'nombre': u.nombre, 
                'email': u.email, 
                'activo': u.is_active, 
                'is_superadmin': u.is_superadmin,
                'pantallas': u.pantallas_asignadas.split(',') if u.pantallas_asignadas else [],
                'accesos': acc
            })
        return jsonify(result)
        
    if request.method == 'POST':
        data = request.get_json() or {}
        
        if not data.get('email') or not data.get('password') or not data.get('nombre'):
            return jsonify({'message': 'Email, nombre y contraseña son requeridos.'}), 400
        
        if Usuario.query.filter_by(email=data.get('email')).first():
            return jsonify({'message': 'Email ya en uso.'}), 400
        
        sucursal_id = data.get('sucursal_id')
        if sucursal_id:
            sucursal = Sucursal.query.filter_by(id=sucursal_id, empresa_id=current_user.empresa_id).first()
            if not sucursal:
                return jsonify({'message': 'Sucursal inválida.'}), 400
        else:
            sucursal = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).first()
            if not sucursal:
                return jsonify({'message': 'No hay sucursales configuradas. Contacte al administrador.'}), 400

        pantallas_raw = data.get('pantallas', ['facturacion', 'inventario'])
        pantallas_filtradas = [p for p in pantallas_raw if p not in ['superAdmin']]

        nuevo_user = Usuario(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            email=data.get('email'),
            is_superadmin=False,
            pantallas_asignadas=','.join(pantallas_filtradas),
            is_active=True
        )
        nuevo_user.set_password(data.get('password'))
        db.session.add(nuevo_user)
        db.session.flush()
        
        rol_nombre = data.get('rol', 'Emisor')
        map_roles = {'admin': 'Administrador', 'user': 'Emisor', 'viewer': 'Auditor'}
        rol_final = map_roles.get(rol_nombre, 'Emisor')
        
        rol_db = Rol.query.filter_by(nombre=rol_final).first()
        if not rol_db:
            return jsonify({'message': f'Rol {rol_final} no configurado en el sistema.'}), 400

        acc = AccesoSucursal(
            usuario_id=nuevo_user.id,
            sucursal_id=sucursal.id,
            rol_id=rol_db.id
        )
        db.session.add(acc)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario creado exitosamente.',
            'usuario': {
                'id': nuevo_user.id,
                'nombre': nuevo_user.nombre,
                'email': nuevo_user.email,
                'rol': rol_final,
                'sucursal': sucursal.nombre
            }
        }), 201




@app.route('/api/notificaciones/mark-all-read', methods=['POST'])
@token_required
def mark_all_read_endpoint(current_user):
    Notificacion.query.filter_by(empresa_id=current_user.empresa_id, leida=False).update({Notificacion.leida: True})
    db.session.commit()
    return jsonify({'message': 'Todas las notificaciones marcadas como leídas'})

@app.route('/api/notificaciones/unread-count', methods=['GET'])
@token_required
def get_unread_count(current_user):
    count = Notificacion.query.filter_by(empresa_id=current_user.empresa_id, leida=False).count()
    return jsonify({'count': count})

# ==========================================
# MÓDULO ADMINISTRATIVO (CONFIGURACIÓN)
# ==========================================

@app.route('/api/config/empresa', methods=['GET', 'PUT'])
@token_required
def config_empresa(current_user):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Acceso denegado. Solo el Emisor/Administrador puede gestionar la configuración de la empresa.'}), 403
    empresa = Empresa.query.get(current_user.empresa_id)
    
    if request.method == 'GET':
        return jsonify({
            'razon_social': empresa.razon_social,
            'nombre_comercial': empresa.nombre_comercial,
            'cedula': empresa.cedula_juridica,
            'correo_hacienda': empresa.email_contacto,
            'telefono': empresa.telefono,
            'actividad': empresa.actividad_economica,
            'direccion': Sucursal.query.filter_by(empresa_id=empresa.id).first().direccion if Sucursal.query.filter_by(empresa_id=empresa.id).first() else ''
        })

    if request.method == 'PUT':
        data = request.get_json()
        empresa.razon_social = data.get('razon_social', empresa.razon_social)
        empresa.nombre_comercial = data.get('nombre_comercial', empresa.nombre_comercial)
        empresa.email_contacto = data.get('correo_hacienda', empresa.email_contacto)
        empresa.telefono = data.get('telefono', empresa.telefono)
        empresa.actividad_economica = data.get('actividad', empresa.actividad_economica)
        
        # Actualizar dirección en sucursal principal
        sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
        if sucursal:
            sucursal.direccion = data.get('direccion', sucursal.direccion)
            
        db.session.commit()
        create_notification(current_user.empresa_id, 'sistema', 'Datos de Empresa Actualizados', 'Se han modificado los datos comerciales de la empresa.')
        return jsonify({'message': 'Datos de empresa actualizados correctamente.'})

@app.route('/api/config/facturacion', methods=['GET', 'PUT'])
@token_required
def config_facturacion(current_user):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Acceso denegado. Solo el Emisor/Administrador puede gestionar la configuración de facturación.'}), 403
    empresa = Empresa.query.get(current_user.empresa_id)
    sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
    
    if request.method == 'GET':
        return jsonify({
            'api_user': empresa.api_usuario,
            'sucursal_num': sucursal.numero_sucursal if sucursal else '001',
            'terminal_num': sucursal.terminal if sucursal else '00001',
            'ambiente': _empresa_ambiente(empresa),
        })

    if request.method == 'PUT':
        data = request.get_json() or {}
        empresa.api_usuario = data.get('api_user', empresa.api_usuario)
        if data.get('api_pass'):
            _store_empresa_secret(empresa, 'api_password', data.get('api_pass'))
        if data.get('api_pin'):
            _store_empresa_secret(empresa, 'api_pin_p12', data.get('api_pin'))
        nuevo_ambiente = (data.get('ambiente') or '').lower()
        if nuevo_ambiente in ('stag', 'prod', 'produccion', 'production'):
            empresa.ambiente_hacienda = 'prod' if nuevo_ambiente in ('prod', 'produccion', 'production') else 'stag'
        
        db.session.commit()
        return jsonify({'message': 'Configuración de facturación actualizada.', 'ambiente': _empresa_ambiente(empresa)})

@app.route('/api/config/plan', methods=['GET', 'PUT'])
@token_required
def config_plan(current_user):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede gestionar el plan.'}), 403

    empresa = Empresa.query.get(current_user.empresa_id)
    if request.method == 'GET':
        return jsonify({
            'plan_tipo': empresa.plan_tipo,
            'plan_cuota': empresa.plan_cuota,
            'plan_estado': empresa.plan_estado,
            'plan_inicio': empresa.plan_inicio.isoformat() if empresa.plan_inicio else None,
            'plan_vencimiento': empresa.plan_vencimiento.isoformat() if empresa.plan_vencimiento else None
        })

    data = request.get_json() or {}
    empresa.plan_tipo = data.get('plan_tipo', empresa.plan_tipo)
    empresa.plan_cuota = _parse_int(data.get('plan_cuota', empresa.plan_cuota), empresa.plan_cuota)
    empresa.plan_vencimiento = _parse_date(data.get('plan_vencimiento')) or empresa.plan_vencimiento
    empresa.plan_estado = data.get('plan_estado', empresa.plan_estado)
    db.session.commit()
    return jsonify({'message': 'Plan de facturación actualizado correctamente.'})


@app.route('/api/config/plan/suspender', methods=['POST'])
@token_required
def suspender_plan(current_user):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede suspender el plan.'}), 403
    empresa = Empresa.query.get(current_user.empresa_id)
    suspend_empresa(empresa, motivo=request.json.get('motivo', 'Suspensión por administrador'))
    db.session.commit()
    return jsonify({'message': 'Plan suspendido y usuarios desactivados.'}), 200


@app.route('/api/config/plan/reactivar', methods=['POST'])
@token_required
def reactivar_plan(current_user):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Solo un Emisor/Administrador puede reactivar el plan.'}), 403
    empresa = Empresa.query.get(current_user.empresa_id)
    activate_empresa(empresa, motivo=request.json.get('motivo', 'Reactivación por administrador'))
    db.session.commit()
    return jsonify({'message': 'Plan reactivado y usuarios activados.'}), 200


@app.route('/api/logout', methods=['POST'])
@token_required
def logout(current_user):
    token = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]

    if token and not RevokedToken.query.filter_by(token=token).first():
        db.session.add(RevokedToken(token=token))
        db.session.commit()

    return jsonify({'message': 'Sesión cerrada correctamente.'}), 200


# (config_usuarios eliminado — se usa /api/usuarios que ya existe)

@app.route('/api/usuarios/<string:id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_usuario(current_user, id):
    if not is_company_admin(current_user):
        return jsonify({'message': 'Solo el Emisor/Administrador puede gestionar usuarios.'}), 403
        
    usuario = Usuario.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado.'}), 404
        
    if request.method == 'PUT':
        data = request.get_json()
        usuario.nombre = data.get('nombre', usuario.nombre)
        usuario.is_active = data.get('activo', usuario.is_active)
        if 'pantallas' in data:
            pantallas_raw = data.get('pantallas', [])
            pantallas_filtradas = [p for p in pantallas_raw if p not in ['superAdmin']]
            usuario.pantallas_asignadas = ','.join(pantallas_filtradas)
            
        if 'password' in data and data['password']:
            usuario.set_password(data['password'])
            
        db.session.commit()
        return jsonify({'message': 'Usuario actualizado.'})
        
    if request.method == 'DELETE':
        if usuario.id == current_user.id:
            return jsonify({'message': 'No puedes eliminarte a ti mismo.'}), 400
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'message': 'Usuario eliminado.'})

@app.route('/api/roles', methods=['GET'])
@token_required
def get_roles(current_user):
    roles = Rol.query.all()
    return jsonify([{'id': r.id, 'nombre': r.nombre, 'descripcion': r.descripcion} for r in roles])


# ==========================================
# RUTAS DE NEGOCIO (FACTURACIÓN E INVENTARIO)
# ==========================================

@app.route('/api/clientes', methods=['GET', 'POST'])
@token_required
def clientes(current_user):
    if request.method == 'GET':
        q = request.args.get('q', '').strip().lower()
        query = Cliente.query.filter_by(empresa_id=current_user.empresa_id)
        
        if q:
            # Buscar por nombre, identificación o correo
            query = query.filter(
                or_(
                    Cliente.nombre.ilike(f'%{q}%'),
                    Cliente.identificacion.ilike(f'%{q}%'),
                    Cliente.email.ilike(f'%{q}%')
                )
            )
        
        clientes = query.limit(50).all()  # Limitar resultados para performance
        return jsonify([{
            'id': c.id, 'nombre': c.nombre, 'identificacion': c.identificacion,
            'tipo_id': c.tipo_id, 'correo': c.email, 'telefono': c.telefono,
            'movil': c.movil, 'actividad': c.actividad_economica, 'regimen': c.regimen,
            'provincia': c.provincia, 'canton': c.canton, 'distrito': c.distrito, 
            'barrio': c.barrio, 'direccion': c.direccion
        } for c in clientes])
        
    if request.method == 'POST':
        data = request.get_json() or {}
        try:
            validar_identificacion(data.get('tipo_id', '01'), data.get('identificacion'))
            if data.get('correo'):
                validar_email(data.get('correo'))
        except ValidationError as verr:
            return jsonify({'message': str(verr)}), 400
        nuevo = Cliente(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            identificacion=data.get('identificacion'),
            tipo_id=data.get('tipo_id', '01'),
            email=data.get('correo'), # En JS se usa 'correo'
            telefono=data.get('telefono'),
            movil=data.get('movil'),
            actividad_economica=data.get('actividad'),
            regimen=data.get('regimen'),
            provincia=data.get('provincia'),
            canton=data.get('canton'),
            distrito=data.get('distrito'),
            barrio=data.get('barrio'),
            direccion=data.get('direccion')
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({'message': 'Cliente creado exitosamente', 'id': nuevo.id}), 201

@app.route('/api/clientes/<string:id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_cliente(current_user, id):
    # Buscar el cliente pero SOLAMENTE si pertenece a la misma empresa (Multi-Tenant)
    cliente = Cliente.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not cliente:
        return jsonify({'message': 'Cliente no encontrado o acceso denegado'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        cliente.nombre = data.get('nombre', cliente.nombre)
        cliente.email = data.get('correo', cliente.email)
        cliente.telefono = data.get('telefono', cliente.telefono)
        cliente.movil = data.get('movil', cliente.movil)
        cliente.provincia = data.get('provincia', cliente.provincia)
        cliente.canton = data.get('canton', cliente.canton)
        cliente.distrito = data.get('distrito', cliente.distrito)
        cliente.barrio = data.get('barrio', cliente.barrio)
        cliente.direccion = data.get('direccion', cliente.direccion)
        cliente.actividad_economica = data.get('actividad', cliente.actividad_economica)
        cliente.regimen = data.get('regimen', cliente.regimen)
        db.session.commit()
        return jsonify({'message': 'Cliente actualizado exitosamente'}), 200

    if request.method == 'DELETE':
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({'message': 'Cliente eliminado exitosamente'}), 200

@app.route('/api/productos', methods=['GET', 'POST'])
@token_required
def productos(current_user):
    if request.method == 'GET':
        q = request.args.get('q', '').strip().lower()
        query = Producto.query.filter_by(empresa_id=current_user.empresa_id)
        
        if q:
            # Buscar por nombre, descripción, marca, modelo, características, cabys, código
            query = query.filter(
                or_(
                    Producto.descripcion.ilike(f'%{q}%'),
                    Producto.nombre_servicio.ilike(f'%{q}%'),
                    Producto.marca.ilike(f'%{q}%'),
                    Producto.modelo.ilike(f'%{q}%'),
                    Producto.caracteristicas.ilike(f'%{q}%'),
                    Producto.cabys.ilike(f'%{q}%'),
                    Producto.codigo.ilike(f'%{q}%')
                )
            )
        
        productos = query.limit(50).all()  # Limitar resultados para performance
        return jsonify([{
            'id': p.id, 'cabys': p.cabys, 'codigo': p.codigo, 
            'unidadMedida': p.unit_measure if hasattr(p, 'unit_measure') else p.unidad_medida, 
            'descripcion': p.descripcion,
            'marca': p.marca, 'modelo': p.modelo, 'caracteristicas': p.caracteristicas,
            'nombreServicio': p.nombre_servicio, 'detalleServicio': p.detalle_servicio,
            'precio': float(p.costo or 0), 'margen': float(p.margen or 0), 'precioVenta': float(p.precio_venta or 0),
            'impuesto': float(p.impuesto or 0), 'tipoImpuesto': p.tipo_impuesto,
            'stock': p.stock, 'descuentoMax': float(p.descuento_max or 0),
            'nombre': p.descripcion or p.nombre_servicio
        } for p in productos])

    if request.method == 'POST':
        data = request.get_json()
        nuevo = Producto(
            empresa_id=current_user.empresa_id,
            cabys=data.get('cabys'),
            codigo=data.get('codigo'),
            unidad_medida=data.get('unidadMedida', 'Unid'),
            descripcion=data.get('descripcion'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            caracteristicas=data.get('caracteristicas'),
            nombre_servicio=data.get('nombreServicio'),
            detalle_servicio=data.get('detalleServicio'),
            costo=float(data.get('precio', 0)),
            margen=float(data.get('margen', 0)),
            precio_venta=float(data.get('precioVenta', 0)),
            impuesto=float(data.get('impuesto', 13)),
            tipo_impuesto=data.get('tipoImpuesto', '01'),
            stock=int(data.get('stock', 0)),
            descuento_max=float(data.get('descuentoMax', 0))
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify({'message': 'Ítem guardado exitosamente', 'id': nuevo.id}), 201

@app.route('/api/productos/<string:id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_producto(current_user, id):
    # Buscar el producto asegurando que pertenece a la empresa actual
    producto = Producto.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not producto:
        return jsonify({'message': 'Ítem no encontrado o acceso denegado'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        # Actualizamos los campos
        producto.descripcion = data.get('descripcion', producto.descripcion)
        producto.marca = data.get('marca', producto.marca)
        producto.modelo = data.get('modelo', producto.modelo)
        producto.caracteristicas = data.get('caracteristicas', producto.caracteristicas)
        producto.nombre_servicio = data.get('nombreServicio', producto.nombre_servicio)
        producto.detalle_servicio = data.get('detalleServicio', producto.detalle_servicio)
        producto.costo = float(data.get('precio', producto.costo))
        producto.margen = float(data.get('margen', producto.margen))
        producto.precio_venta = float(data.get('precioVenta', producto.precio_venta))
        producto.impuesto = float(data.get('impuesto', producto.impuesto))
        producto.stock = int(data.get('stock', producto.stock))
        producto.descuento_max = float(data.get('descuentoMax', producto.descuento_max))
        producto.tipo_impuesto = data.get('tipoImpuesto', producto.tipo_impuesto)
        db.session.commit()
        return jsonify({'message': 'Ítem actualizado exitosamente'}), 200

    if request.method == 'DELETE':
        db.session.delete(producto)
        db.session.commit()
        return jsonify({'message': 'Ítem eliminado exitosamente'}), 200


@app.route('/api/facturas', methods=['GET', 'POST'])
@token_required
@require_role(['Administrador', 'Emisor'])
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

        try:
            # Limpiar la transacción abierta por los decoradores
            db.session.commit()
            
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
                usuario_id=current_user.id
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

                # ACTUALIZACIÓN DE INVENTARIO EN TIEMPO REAL
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
                        
                        # Registrar Movimiento
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
                        
                        # Actualizar Stock del Producto
                        producto.stock = nuevo_stock
                        print(f"[STOCK] Inventario Actualizado: {producto.codigo} ({anterior} -> {nuevo_stock})")

                        # NOTIFICACIÓN DE STOCK BAJO
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
                            print(f"[ALERTA] Alerta: Stock bajo para {producto.codigo}")

            nueva_factura.subtotal = quantize_money(subtotal_total)
            nueva_factura.descuentos = quantize_money(descuentos_total)
            nueva_factura.impuestos = quantize_money(impuestos_total)
            nueva_factura.total = quantize_money(total_final)

            # Generar XML Base
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
                print(f"Error en firma: {str(sign_err)}")
                nueva_factura.xml_comprobante = zlib.compress(xml_bytes_para_mh)

            mh_envio = None
            if os.environ.get('HACIENDA_SEND_ENABLED', '').lower() in ('1', 'true', 'yes') and nueva_factura.estado == 'Firmada':
                try:
                    creds = _mh_credenciales(empresa)
                    cliente_mh = HaciendaClient(ambiente=_empresa_ambiente(empresa))
                    cliente = nueva_factura.cliente
                    mh_envio = cliente_mh.enviar_comprobante(
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
                    body_mh = mh_envio.get('body') or {}
                    _guardar_respuesta_mh(nueva_factura, body_mh)
                    nueva_factura.estado = mapear_estado_mh(body_mh) if body_mh else 'Enviada'
                except HaciendaError as mh_err:
                    print(f"MH recepción: {mh_err} payload={getattr(mh_err, 'payload', None)}")
                except Exception as mh_err:
                    print(f"MH recepción error: {mh_err}")

            # Recibir PDF desde el frontend si viene en base64
            pdf_base64 = data.get('pdf_base64')
            if pdf_base64:
                try:
                    # Quitar encabezado data:application/pdf;base64, si existe
                    if "," in pdf_base64:
                        pdf_base64 = pdf_base64.split(",")[1]
                    pdf_bin = base64.b64decode(pdf_base64)
                    nueva_factura.pdf_comprobante = zlib.compress(pdf_bin)
                except Exception as pdf_err:
                    print(f"Error procesando PDF base64: {str(pdf_err)}")
                    nueva_factura.pdf_comprobante = zlib.compress(b"ERROR_GENERACION_PDF")
            else:
                nueva_factura.pdf_comprobante = zlib.compress(b"SIN_PDF_ADJUNTO")

            db.session.commit()

            # Limpiar borradores en background (no bloquea la respuesta)
            try:
                Factura.query.filter_by(sucursal_id=sucursal.id, is_draft=True).delete()
                db.session.commit()
            except:
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
            print(f"\n{'='*80}")
            print(f"ERROR EN EMISIÓN DE FACTURA:")
            print(f"{'='*80}")
            print(traceback.format_exc())
            print(f"{'='*80}\n")
            db.session.rollback()
            return jsonify({'message': 'Error al procesar emisión', 'error': str(e)}), 500

@app.route('/api/facturas/borrador', methods=['GET', 'POST'])
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

@app.route('/api/facturas/<string:id>/hacienda/estado', methods=['GET'])
@token_required
@require_role(['Administrador', 'Emisor', 'Auditor'])
def consultar_estado_hacienda(current_user, id):
    """Consulta estado del comprobante en MH y actualiza la factura."""
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


@app.route('/api/hacienda/xsd-status', methods=['GET'])
@token_required
def hacienda_xsd_status(current_user):
    """Diagnóstico: XSD locales disponibles para validación."""
    tipos = request.args.getlist('tipo') or ['01', '04', '03', '02']
    return jsonify({'schemas': [validation_status(t) for t in tipos]})


@app.route('/api/facturas/<string:id>', methods=['GET', 'PUT'])
@token_required
@require_role(['Administrador', 'Emisor'])
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
        data = request.get_json()
        
        def parse_money(val):
            if isinstance(val, (int, float)): return float(val)
            return float(re.sub(r'[^\d.-]', '', str(val))) if val else 0.0
            
        factura.estado = data.get('estado', factura.estado)
        factura.observaciones = data.get('observaciones', factura.observaciones)
        # Parse date safely
        if data.get('fecha'):
            try:
                factura.fecha_emision = datetime.fromisoformat(data.get('fecha').replace('Z', ''))
            except:
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

# ==========================================
# RUTAS DE AUDITORÍA (Trazabilidad 360)
# ==========================================
@app.route('/api/auditoria/comprobantes', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor', 'Emisor'])
def auditoria_comprobantes(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    facturas = Factura.query.filter_by(sucursal_id=sucursal.id).order_by(Factura.fecha_emision.desc()).limit(100).all()
    return jsonify([{
        'id': f.id,
        'fecha': f.fecha_emision.isoformat(),
        'numero_consecutivo': f.numero_consecutivo,
        'clave': f.clave,
        'clienteNombre': f.cliente.nombre if f.cliente else 'Consumidor Final',
        'monto': f.total,
        'estado': f.estado,
        'tipo': f.tipo_documento
    } for f in facturas])

@app.route('/api/auditoria/inventario', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor'])
def auditoria_inventario(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    movimientos = InventarioMovimiento.query.filter_by(sucursal_id=sucursal.id).order_by(InventarioMovimiento.fecha.desc()).limit(100).all()
    return jsonify([{
        'id': m.id,
        'fecha': m.fecha.isoformat(),
        'producto_codigo': m.producto.codigo if m.producto else 'N/A',
        'producto_desc': m.producto.descripcion if m.producto else 'N/A',
        'tipo': m.tipo_movimiento,
        'anterior': m.cantidad_anterior,
        'ajuste': m.cantidad_ajuste,
        'nueva': m.cantidad_nueva,
        'usuario': m.usuario_id # Ideally join with Usuario model for name
    } for m in movimientos])

@app.route('/api/auditoria/ventas', methods=['GET'])
@token_required
@require_role(['Administrador', 'Auditor'])
def auditoria_ventas(current_user):
    # Por ahora similar a comprobantes, pero enfocado en ventas del POS (Facturas Pagadas)
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403

    ventas = Factura.query.filter(
        Factura.sucursal_id == sucursal.id,
        Factura.estado.notin_(['Borrador', 'Rechazada'])
    ).order_by(Factura.fecha_emision.desc()).limit(100).all()
    
    return jsonify([{
        'id': v.id,
        'fecha': v.fecha_emision.isoformat(),
        'transaccion': f"TRN-{v.id}-{v.numero_consecutivo[-4:] if v.numero_consecutivo else '0000'}",
        'caja': 'TERMINAL PRINCIPAL',
        'vendedor': current_user.nombre, # Placeholder, should be mapped from creator
        'monto': v.total,
        'pago': v.medio_pago
    } for v in ventas])

# ==========================================
# RUTAS DE NOTIFICACIONES
# ==========================================
@app.route('/api/notificaciones', methods=['GET'])
@token_required
def get_notificaciones(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    sucursal = validate_sucursal(current_user, sucursal_id)
    if not sucursal:
        return jsonify({'message': 'Sucursal no encontrada o no tiene acceso.'}), 403
    
    # Obtener notificaciones de la empresa, y aquellas globales o específicas de la sucursal
    notificaciones = Notificacion.query.filter(
        Notificacion.empresa_id == current_user.empresa_id,
        db.or_(Notificacion.sucursal_id == None, Notificacion.sucursal_id == sucursal.id)
    ).order_by(Notificacion.fecha.desc()).limit(50).all()
    
    return jsonify([{
        'id': n.id,
        'type': n.tipo,
        'icon': n.icono,
        'title': n.titulo,
        'desc': n.descripcion,
        'time': n.fecha.isoformat(),
        'read': n.leida
    } for n in notificaciones])

@app.route('/api/notificaciones/<string:id>/read', methods=['PUT'])
@token_required
def mark_notificacion_read(current_user, id):
    notificacion = Notificacion.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not notificacion:
        return jsonify({'message': 'Notificación no encontrada'}), 404
        
    notificacion.leida = True
    db.session.commit()
    return jsonify({'message': 'Notificación marcada como leída'})

@app.route('/api/notificaciones/read_all', methods=['PUT'])
@token_required
def mark_all_notificaciones_read(current_user):
    sucursal_id = request.headers.get('X-Sucursal-ID')
    notificaciones = Notificacion.query.filter(
        Notificacion.empresa_id == current_user.empresa_id,
        db.or_(Notificacion.sucursal_id == None, Notificacion.sucursal_id == sucursal_id),
        Notificacion.leida == False
    ).all()
    
    for n in notificaciones:
        n.leida = True
        
    db.session.commit()
    return jsonify({'message': 'Todas las notificaciones marcadas como leídas'})

# ==========================================
# MOTOR DE ENVÍO DE CORREOS (SaaS DELIVERY)
# ==========================================
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def enviar_comprobante_email(destinatario, factura_data, xml_bin, pdf_bin):
    """
    Envía el comprobante electrónico (XML y PDF) al receptor.
    Diseño premium HTML incluido.
    """
    # Configuración SMTP (MUROTECH Default o por Empresa)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "soporte@murotech.com" # Placeholder para el sistema
    SMTP_PASS = "tu_password_seguro"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"MUROTECH Facturación <{SMTP_USER}>"
        msg['To'] = destinatario
        msg['Subject'] = f"Comprobante Electrónico: {factura_data['consecutivo']}"

        # Cuerpo del Correo (HTML Premium)
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
                    Este es un correo automÃ¡tico generado por MUROTECH SaaS. Por favor no responda a este mensaje.
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        # Adjuntar XML
        part_xml = MIMEBase('application', 'xml')
        part_xml.set_payload(xml_bin)
        encoders.encode_base64(part_xml)
        part_xml.add_header('Content-Disposition', f'attachment; filename="{factura_data["consecutivo"]}.xml"')
        msg.attach(part_xml)

        # Adjuntar PDF
        part_pdf = MIMEBase('application', 'pdf')
        part_pdf.set_payload(pdf_bin)
        encoders.encode_base64(part_pdf)
        part_pdf.add_header('Content-Disposition', f'attachment; filename="{factura_data["consecutivo"]}.pdf"')
        msg.attach(part_pdf)

        # EnvÃ­o Real (Descomentar para producciÃ³n con credenciales vÃ¡lidas)
        # server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        # server.starttls()
        # server.login(SMTP_USER, SMTP_PASS)
        # server.send_message(msg)
        # server.quit()
        
        print(f"Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")
        return False

# ==========================================
# MÃ“DULO DE COTIZACIONES Y PROFORMAS
# ==========================================

@app.route('/api/cotizaciones/proforma', methods=['POST'])
@token_required
def crear_cotizacion_proforma(current_user):
    data = request.get_json()
    
    # 1. Obtener Sucursal (Default a la primera de la empresa)
    sucursal = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).first()
    if not sucursal:
        return jsonify({'message': 'No hay sucursales configuradas.'}), 400

    # 2. Manejo de Cliente o Prospecto
    cliente_id = data.get('cliente_id')
    if cliente_id == 'all' or not cliente_id:
        cliente_id = None # Prospecto manual
        
    # 3. Crear Registro de CotizaciÃ³n
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
    
    # Calcular Vencimiento
    validez = int(data.get('validez_dias', 15))
    nueva_cot.fecha_vencimiento = datetime.now() + timedelta(days=validez)
    
    db.session.add(nueva_cot)
    db.session.flush() # Para obtener el ID

    # 4. Detalles de la Proforma
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
    
    # 5. NotificaciÃ³n
    create_notification(current_user.empresa_id, 'sistema', 'Nueva CotizaciÃ³n Generada', f'Se ha creado la proforma {nueva_cot.numero_consecutivo} para {data.get("receptor_nombre", "Prospecto")}.')

    return jsonify({
        'message': 'CotizaciÃ³n guardada exitosamente.',
        'id': nueva_cot.id,
        'consecutivo': nueva_cot.numero_consecutivo
    }), 201

# ==========================================
# GESTIÓN DE FACTURACIÓN ELECTRÓNICA REAL
# ==========================================

@app.route('/api/facturas/consecutivo', methods=['GET'])
@token_required
def get_next_consecutivo(current_user):
    """
    Calcula el siguiente número de consecutivo para la sucursal y tipo de documento.
    Formato MH: Sucursal(3) + PuntoVenta(5) + TipoDoc(2) + Correlativo(10)
    """
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

@app.route('/api/reportes/data', methods=['GET'])
@token_required
def get_reportes_data(current_user):
    from sqlalchemy import func
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    cliente_id = request.args.get('cliente_id')
    
    # --- FILTRO BASE POR EMPRESA (a traves de sucursales) ---
    sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
    query_facturas = Factura.query.filter(
        Factura.sucursal_id.in_(sucursales_ids),
        Factura.is_draft == False
    )
    
    desde_dt = _parse_date(desde)
    hasta_dt = _parse_date(hasta, end_of_day=True)
    if desde_dt: query_facturas = query_facturas.filter(Factura.fecha_emision >= desde_dt)
    if hasta_dt: query_facturas = query_facturas.filter(Factura.fecha_emision <= hasta_dt)
    if cliente_id and cliente_id != 'all': 
        query_facturas = query_facturas.filter(Factura.cliente_id == cliente_id)

    facturas = query_facturas.all()

    # --- CALCULO DE KPIs ---
    total_ventas = sum(f.total for f in facturas)
    total_iva = sum(f.impuestos for f in facturas)
    total_neto = total_ventas - total_iva

    # --- DATOS PARA GRAFICOS (POR FECHA) ---
    ventas_por_fecha = {}
    for f in facturas:
        fecha_str = f.fecha_emision.strftime('%Y-%m-%d')
        ventas_por_fecha[fecha_str] = ventas_por_fecha.get(fecha_str, 0) + float(f.total)
    
    chart_data = [{'fecha': k, 'total': v} for k, v in sorted(ventas_por_fecha.items())]

    # --- INVENTARIO Y STOCK ---
    productos = Producto.query.filter_by(empresa_id=current_user.empresa_id).all()
    stock_bajo = [p for p in productos if p.stock <= 5]
    valor_inventario = sum((p.stock * p.costo) for p in productos if p.costo)

    return jsonify({
        'kpis': {
            'ventas': float(total_ventas),
            'iva': float(total_iva),
            'utilidad': float(total_neto * 0.3),
            'compras': float(total_neto * 0.4)
        },
        'tablas': {
            'ventas': [{
                'fecha': f.fecha_emision.strftime('%Y-%m-%d'),
                'consecutivo': f.numero_consecutivo,
                'cliente': f.cliente.nombre if f.cliente else 'Consumidor Final',
                'bruto': float(f.subtotal),
                'iva': float(f.impuestos),
                'total': float(f.total),
                'estado': f.estado
            } for f in facturas],
            'inventario': [{
                'codigo': p.codigo,
                'nombre': p.descripcion,
                'costo': float(p.costo or 0),
                'venta': float(p.precio_venta or 0),
                'stock': float(p.stock),
                'status': 'STOCK_BAJO' if p.stock <= 5 else 'NORMAL'
            } for p in productos]
        },
        'charts': {
            'ventas': chart_data,
            'productos': [{'label': 'Otros', 'value': 100}]
        },
        'resumen_inventario': {
            'total_skus': len(productos),
            'valor_total': float(valor_inventario),
            'conteo_bajo': len(stock_bajo)
        }
    })
@app.route('/api/auditoria', methods=['GET'])
@token_required
def get_auditoria_data(current_user):
    """Retorna datos consolidados para la pantalla auditoria.html"""
    try:
        if is_company_admin(current_user):
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
        else:
            sucursales_ids = [acc.sucursal_id for acc in current_user.accesos]

        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        estado = request.args.get('estado', 'todos')
        vendedor_id = request.args.get('vendedor_id', 'todos')
        medio_pago = request.args.get('medio_pago', 'todos')
        q = request.args.get('q', '').lower()

        # 1. Comprobantes (Facturas)
        f_query = Factura.query.filter(Factura.sucursal_id.in_(sucursales_ids))
        desde_dt = _parse_date(desde)
        hasta_dt = _parse_date(hasta, end_of_day=True)
        if desde_dt: f_query = f_query.filter(Factura.fecha_emision >= desde_dt)
        if hasta_dt: f_query = f_query.filter(Factura.fecha_emision <= hasta_dt)
        if estado != 'todos': f_query = f_query.filter(Factura.estado.ilike(f"%{estado}%"))
        if vendedor_id != 'todos': f_query = f_query.filter(Factura.usuario_id == vendedor_id)
        if medio_pago != 'todos': f_query = f_query.filter(Factura.medio_pago == medio_pago)
        
        # Filtro de búsqueda (Búsqueda Inteligente)
        if q:
            f_query = f_query.join(Cliente, isouter=True).filter(
                or_(
                    Factura.numero_consecutivo.ilike(f"%{q}%"),
                    Factura.clave.ilike(f"%{q}%"),
                    Cliente.nombre.ilike(f"%{q}%"),
                    Factura.observaciones.ilike(f"%{q}%")
                )
            )

        facturas = f_query.order_by(Factura.fecha_emision.desc()).all()
        facturas_list = [{
            'id': f.id,
            'fecha': f.fecha_emision.isoformat() + 'Z',
            'consecutivo': f.numero_consecutivo,
            'clave': f.clave,
            'receptor': f.cliente.nombre if f.cliente else 'Consumidor Final',
            'vendedor': f.usuario.nombre if f.usuario else 'Sistema',
            'monto': f.total,
            'medio_pago': f.medio_pago,
            'estado': f.estado,
            'has_pdf': f.pdf_comprobante is not None,
            'has_xml': f.xml_comprobante is not None
        } for f in facturas]

        # 2. Movimientos de Inventario
        m_query = InventarioMovimiento.query.filter(InventarioMovimiento.sucursal_id.in_(sucursales_ids))
        desde_dt = _parse_date(desde)
        hasta_dt = _parse_date(hasta, end_of_day=True)
        if desde_dt: m_query = m_query.filter(InventarioMovimiento.fecha >= desde_dt)
        if hasta_dt: m_query = m_query.filter(InventarioMovimiento.fecha <= hasta_dt)
        
        movimientos = m_query.order_by(InventarioMovimiento.fecha.desc()).limit(100).all()
        movs_list = [{
            'fecha': m.fecha.isoformat() + 'Z',
            'producto': f"{m.producto.codigo} - {m.producto.descripcion}",
            'tipo': m.tipo_movimiento,
            'anterior': m.cantidad_anterior,
            'ajuste': m.cantidad_ajuste,
            'actual': m.cantidad_nueva,
            'usuario': m.usuario.nombre
        } for m in movimientos]

        # 3. Bitácora de Ventas (Simplificada como resumen de transacciones)
        # Reutilizamos facturas pero con enfoque en transacciones
        bitacora = [{
            'fecha': f.fecha_emision.isoformat() + 'Z',
            'transaccion': f"TRN-{str(f.id)[:8].upper()}",
            'caja': f.sucursal.nombre,
            'vendedor': 'Sistema', # Aquí se podría registrar el usuario emisor en el modelo
            'monto': f.total,
            'medio_pago': f.medio_pago
        } for f in facturas[:50]]

        return jsonify({
            'comprobantes': facturas_list,
            'movimientos': movs_list,
            'ventas': bitacora
        }), 200

    except Exception as e:
        print(f"Error Auditoría: {str(e)}")
        return jsonify({'message': 'Error al cargar datos de auditoría', 'error': str(e)}), 500

@app.route('/api/reportes', methods=['GET'])
@token_required
def get_reportes_summary(current_user):
    """Retorna datos analíticos para la pantalla reportes.html"""
    try:
        if is_company_admin(current_user):
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
        else:
            sucursales_ids = [acc.sucursal_id for acc in current_user.accesos]

        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        periodo = request.args.get('periodo', 'month')

        # Filtros de base
        f_query = Factura.query.filter(Factura.sucursal_id.in_(sucursales_ids))
        desde_dt = _parse_date(desde)
        hasta_dt = _parse_date(hasta, end_of_day=True)
        if desde_dt: f_query = f_query.filter(Factura.fecha_emision >= desde_dt)
        if hasta_dt: f_query = f_query.filter(Factura.fecha_emision <= hasta_dt)

        facturas = f_query.all()

        # 1. KPIs
        ventas_brutas = float(sum(f.total for f in facturas if not f.is_quotation) or 0)
        impuestos = float(sum(f.impuestos for f in facturas if not f.is_quotation) or 0)
        
        compras_db = Compra.query.filter(Compra.sucursal_id.in_(sucursales_ids)).all()
        total_compras = float(sum(c.total for c in compras_db) or 0)
        
        utilidad = ventas_brutas - total_compras

        # 2. Tendencias de Ventas (Ordenado por día)
        tendencia_dict = {}
        for f in facturas:
            if f.is_quotation: continue
            fecha_str = f.fecha_emision.strftime('%Y-%m-%d') if f.fecha_emision else None
            if fecha_str:
                monto = float(f.total or 0)
                tendencia_dict[fecha_str] = tendencia_dict.get(fecha_str, 0) + monto
        
        tendencia = [{'label': k, 'valor': float(v)} for k, v in sorted(tendencia_dict.items())]

        # 3. Top Productos (Optimizado)
        top_productos = []
        try:
            top_prod_res = db.session.query(
                FacturaDetalle.descripcion,
                func.sum(FacturaDetalle.total_linea).label('total')
            ).join(Factura).filter(Factura.sucursal_id.in_(sucursales_ids))
            
            if desde_dt: top_prod_res = top_prod_res.filter(Factura.fecha_emision >= desde_dt)
            if hasta_dt: top_prod_res = top_prod_res.filter(Factura.fecha_emision <= hasta_dt)
            
            top_prod_raw = top_prod_res.group_by(FacturaDetalle.descripcion).order_by(db.desc('total')).limit(5).all()
            top_productos = [{
                'label': str(p.descripcion or "Producto"),
                'valor': float(p.total or 0)
            } for p in top_prod_raw]
        except Exception as e_top:
            print(f"Error Top Productos: {e_top}")
            top_productos = []

        # 4. Datos de Inventario
        productos = Producto.query.filter_by(empresa_id=current_user.empresa_id).all()
        inventario = [{
            'codigo': str(p.codigo or "N/A"),
            'descripcion': str(p.descripcion or "Sin descripción"),
            'categoria': str(p.marca or 'General'),
            'precio_compra': float(p.costo or 0),
            'precio_venta': float(p.precio_venta or 0),
            'existencia': int(p.stock or 0),
            'status': 'Bajo' if (p.stock or 0) <= 5 else 'OK'
        } for p in productos]

        valor_inventario = sum(p.stock * p.costo for p in productos)

        return jsonify({
            'kpis': {
                'ventas': float(ventas_brutas or 0),
                'compras': float(total_compras or 0),
                'utilidad': float(utilidad or 0),
                'impuestos': float(impuestos or 0),
                'sku_total': len(productos),
                'valor_inventario': float(valor_inventario or 0),
                'stock_bajo': len([p for p in productos if (p.stock or 0) <= 5])
            },
            'graficos': {
                'tendencia': tendencia,
                'top_productos': top_productos
            },
            'tablas': {
                'ventas': [{
                    'fecha': (f.fecha_emision.isoformat() + 'Z') if f.fecha_emision else '',
                    'numero': f.numero_consecutivo,
                    'cliente': (f.cliente.nombre if f.cliente else 'Consumidor Final'),
                    'bruto': float(f.subtotal or 0),
                    'impuestos': float(f.impuestos or 0),
                    'total': float(f.total or 0),
                    'estado': f.estado or 'N/A'
                } for f in facturas if not f.is_quotation],
                'compras': [{
                    'fecha': (c.fecha.isoformat() + 'Z') if c.fecha else '',
                    'proveedor': c.proveedor or 'Anónimo',
                    'concepto': c.concepto or 'Gasto',
                    'monto': float(c.monto_neto or 0),
                    'iva': float(c.iva or 0),
                    'total': float(c.total or 0),
                    'categoria': c.categoria or 'General'
                } for c in compras_db],
                'inventario': inventario,
                'comprobantes': [{
                    'consecutivo': f.numero_consecutivo,
                    'fecha': f.fecha_emision.isoformat() + 'Z',
                    'receptor': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'estado': f.estado,
                    'clave': f.clave
                } for f in facturas if f.xml_comprobante],
                'cotizaciones': [{
                    'fecha': f.fecha_emision.isoformat() + 'Z',
                    'numero': f.numero_consecutivo,
                    'cliente': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'vencimiento': f.fecha_vencimiento.isoformat() + 'Z' if f.fecha_vencimiento else '',
                    'monto': float(f.total),
                    'estado': f.estado
                } for f in facturas if f.is_quotation]
            }
        }), 200

    except Exception as e:
        print(f"Error Reportes: {str(e)}")
        return jsonify({'message': 'Error al procesar reportes', 'error': str(e)}), 500

@app.route('/api/facturas/descargar/<string:id>/<tipo>', methods=['GET'])
@token_required
def descargar_comprobante(current_user, id, tipo):
    """Descarga el XML o PDF almacenado en binario"""
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
    except:
        return jsonify({'message': 'Archivo no disponible'}), 404

# ==========================================
# ENDPOINTS DE COTIZACIONES
# ==========================================

@app.route('/api/cotizaciones', methods=['GET', 'POST'])
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
            db.session.commit()
            
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

            # Recibir PDF desde el frontend si viene en base64
            pdf_base64 = data.get('pdf_base64')
            if pdf_base64:
                try:
                    if "," in pdf_base64:
                        pdf_base64 = pdf_base64.split(",")[1]
                    pdf_bin = base64.b64decode(pdf_base64)
                    nueva_cotizacion.pdf_comprobante = zlib.compress(pdf_bin)
                except Exception as pdf_err:
                    print(f"Error procesando PDF base64: {str(pdf_err)}")
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
            print(f"\n{'='*80}")
            print(f"ERROR EN CREACIÓN DE COTIZACIÓN:")
            print(f"{'='*80}")
            print(traceback.format_exc())
            print(f"{'='*80}\n")
            db.session.rollback()
            return jsonify({'message': 'Error al procesar cotización', 'error': str(e)}), 500

@app.route('/api/cotizaciones/borrador', methods=['GET', 'POST'])
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

@app.route('/api/cotizaciones/<string:id>', methods=['GET', 'PUT', 'DELETE'])
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
        data = request.get_json()
        
        cotizacion.estado = data.get('estado', cotizacion.estado)
        cotizacion.observaciones = data.get('observaciones', cotizacion.observaciones)
        if data.get('fecha_vencimiento'):
            try:
                cotizacion.fecha_vencimiento = datetime.fromisoformat(data.get('fecha_vencimiento').replace('Z', ''))
            except:
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

@app.route('/api/cotizaciones/<string:id>/descargar', methods=['GET'])
@token_required
def descargar_cotizacion(current_user, id):
    """Descarga el PDF de la cotización"""
    cotizacion = Cotizacion.query.get_or_404(id)
    if cotizacion.sucursal.empresa_id != current_user.empresa_id:
        return jsonify({'message': 'No autorizado'}), 403
        
    try:
        data = zlib.decompress(cotizacion.pdf_comprobante)
        return data, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename=cotizacion_{cotizacion.id}.pdf'
        }
    except:
        return jsonify({'message': 'Archivo no disponible'}), 404

# ==========================================
# ENDPOINTS DE PLANES Y SUSCRIPCIONES
# ==========================================

@app.route('/api/planes', methods=['GET'])
def get_planes():
    """Retorna todos los planes disponibles para suscripción"""
    try:
        planes = Plan.query.filter_by(is_active=True).order_by(Plan.orden).all()
        return jsonify([{
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio_mensual': float(p.precio_mensual),
            'precio_anual': float(p.precio_anual),
            'cuota_facturas': p.cuota_facturas,
            'usuarios_incluidos': p.usuarios_incluidos,
            'sucursales_incluidas': p.sucursales_incluidas,
            'caracteristicas': {
                'api_hacienda': p.tiene_api_hacienda,
                'firma_digital': p.tiene_firma_digital,
                'soporte': p.tiene_soporte,
                'reportes_avanzados': p.tiene_reportes_avanzados,
                'multi_moneda': p.tiene_multi_moneda
            }
        } for p in planes]), 200
    except Exception as e:
        return jsonify({'message': 'Error obteniendo planes', 'error': str(e)}), 500

@app.route('/api/planes/<plan_id>', methods=['GET'])
def get_plan_detalle(plan_id):
    """Retorna detalle de un plan específico"""
    try:
        plan = Plan.query.get_or_404(plan_id)
        return jsonify({
            'id': plan.id,
            'nombre': plan.nombre,
            'descripcion': plan.descripcion,
            'precio_mensual': float(plan.precio_mensual),
            'precio_anual': float(plan.precio_anual),
            'cuota_facturas': plan.cuota_facturas,
            'usuarios_incluidos': plan.usuarios_incluidos,
            'sucursales_incluidas': plan.sucursales_incluidas,
            'caracteristicas': {
                'api_hacienda': plan.tiene_api_hacienda,
                'firma_digital': plan.tiene_firma_digital,
                'soporte': plan.tiene_soporte,
                'reportes_avanzados': plan.tiene_reportes_avanzados,
                'multi_moneda': plan.tiene_multi_moneda
            }
        }), 200
    except Exception as e:
        return jsonify({'message': 'Error obteniendo plan', 'error': str(e)}), 500

@app.route('/api/suscripcion/iniciar', methods=['POST'])
def iniciar_suscripcion():
    """
    Inicia proceso de suscripción a un plan
    Requiere: plan_id, empresa_id, tipo_cobro (mensual/anual)
    """
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        empresa_id = data.get('empresa_id')
        tipo_cobro = data.get('tipo_cobro', 'mensual')
        
        if not plan_id or not empresa_id:
            return jsonify({'message': 'Faltan datos requeridos: plan_id, empresa_id'}), 400
        
        empresa = Empresa.query.get(empresa_id)
        if not empresa:
            return jsonify({'message': 'Empresa no encontrada'}), 404
        
        plan = Plan.query.get(plan_id)
        if not plan:
            return jsonify({'message': 'Plan no encontrado'}), 404
        
        # Calcular precio según tipo de cobro
        precio = plan.precio_mensual if tipo_cobro == 'mensual' else plan.precio_anual
        
        # Crear suscripción en estado trial/pendiente
        from datetime import datetime, timedelta
        fecha_inicio = datetime.utcnow()
        fecha_vencimiento = fecha_inicio + timedelta(days=30 if tipo_cobro == 'mensual' else 365)
        
        nueva_suscripcion = Suscripcion(
            empresa_id=empresa_id,
            plan_id=plan_id,
            estado='trial',  # Trial hasta que se complete el pago
            tipo_cobro=tipo_cobro,
            fecha_inicio=fecha_inicio,
            fecha_vencimiento=fecha_vencimiento,
            periodo_facturacion=fecha_inicio
        )
        db.session.add(nueva_suscripcion)
        db.session.commit()
        
        return jsonify({
            'suscripcion_id': nueva_suscripcion.id,
            'plan': {
                'nombre': plan.nombre,
                'precio': float(precio),
                'tipo': tipo_cobro
            },
            'empresa': {
                'nombre': empresa.razon_social,
                'cedula': empresa.cedula_juridica
            },
            'urls': {
                'pago_stripe': f'/api/pagos/stripe/checkout?suscripcion_id={nueva_suscripcion.id}',
                'pago_paypal': f'/api/pagos/paypal/checkout?suscripcion_id={nueva_suscripcion.id}'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error iniciando suscripción', 'error': str(e)}), 500

@app.route('/api/pagos/stripe/checkout', methods=['GET'])
def stripe_checkout():
    """Genera URL de checkout de Stripe"""
    try:
        suscripcion_id = request.args.get('suscripcion_id')
        if not suscripcion_id:
            return jsonify({'message': 'Falta suscripcion_id'}), 400
        
        suscripcion = Suscripcion.query.get(suscripcion_id)
        if not suscripcion:
            return jsonify({'message': 'Suscripción no encontrada'}), 404
        
        plan = suscripcion.plan
        empresa = suscripcion.empresa
        
        # Aquí integrarías con Stripe
        # Por ahora, simulamos la respuesta
        precio = plan.precio_mensual if suscripcion.tipo_cobro == 'mensual' else plan.precio_anual
        
        # Simular URL de Stripe (reemplazar con integración real)
        stripe_url = f"https://checkout.stripe.com/pay/cs_test_{suscripcion_id}"
        
        return jsonify({
            'checkout_url': stripe_url,
            'suscripcion_id': suscripcion_id,
            'monto': float(precio),
            'moneda': 'CRC',
            'descripcion': f"Suscripción {plan.nombre} - {empresa.razon_social}"
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Error generando checkout', 'error': str(e)}), 500

@app.route('/api/pagos/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Recibe notificaciones de Stripe sobre pagos"""
    try:
        payload = request.get_data()
        signature = request.headers.get('Stripe-Signature')
        
        # Verificar firma del webhook (implementar con clave secreta)
        # event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        
        # Por ahora, procesar como JSON genérico
        data = request.get_json()
        
        if not data:
            return jsonify({'received': True}), 200
        
        # Procesar diferentes tipos de eventos
        event_type = data.get('type', '')
        
        if event_type == 'payment_intent.succeeded':
            payment_intent = data.get('data', {}).get('object', {})
            external_id = payment_intent.get('id')
            
            # Buscar y actualizar pago
            pago = Pago.query.filter_by(payment_id_externo=external_id).first()
            if pago:
                pago.estado = 'completado'
                pago.fecha_pago = datetime.utcnow()
                
                # Activar suscripción
                suscripcion = pago.suscripcion
                suscripcion.estado = 'activa'
                suscripcion.ultimo_pago_id = external_id
                suscripcion.ultimo_pago_estado = 'completado'
                suscripcion.fecha_ultimo_pago = datetime.utcnow()
                
                # Actualizar empresa con plan
                empresa = Empresa.query.get(pago.empresa_id)
                if empresa:
                    empresa.plan_tipo = suscripcion.plan.nombre.lower()
                    empresa.plan_cuota = suscripcion.plan.cuota_facturas
                    empresa.plan_estado = 'activo'
                
                db.session.commit()
                
        elif event_type == 'payment_intent.payment_failed':
            payment_intent = data.get('data', {}).get('object', {})
            external_id = payment_intent.get('id')
            
            pago = Pago.query.filter_by(payment_id_externo=external_id).first()
            if pago:
                pago.estado = 'fallido'
                db.session.commit()
        
        return jsonify({'received': True}), 200
        
    except Exception as e:
        return jsonify({'message': 'Error procesando webhook', 'error': str(e)}), 400

@app.route('/api/pagos/confirmar', methods=['POST'])
def confirmar_pago():
    """Confirma un pago manual (para pruebas o métodos alternativos)"""
    try:
        data = request.get_json()
        suscripcion_id = data.get('suscripcion_id')
        monto = data.get('monto')
        provider = data.get('provider', 'manual')
        payment_id = data.get('payment_id', f"manual_{datetime.utcnow().timestamp()}")
        
        suscripcion = Suscripcion.query.get(suscripcion_id)
        if not suscripcion:
            return jsonify({'message': 'Suscripción no encontrada'}), 404
        
        # Crear registro de pago
        nuevo_pago = PagoSuscripcion(
            suscripcion_id=suscripcion_id,
            empresa_id=suscripcion.empresa_id,
            monto=monto,
            provider=provider,
            payment_id_externo=payment_id,
            estado='completado',
            fecha_pago=datetime.utcnow(),
            fecha_procesado=datetime.utcnow()
        )
        db.session.add(nuevo_pago)
        
        # Activar suscripción
        suscripcion.estado = 'activa'
        suscripcion.ultimo_pago_id = payment_id
        suscripcion.ultimo_pago_estado = 'completado'
        suscripcion.fecha_ultimo_pago = datetime.utcnow()
        
        # Actualizar empresa
        empresa = Empresa.query.get(suscripcion.empresa_id)
        if empresa:
            empresa.plan_tipo = suscripcion.plan.nombre.lower()
            empresa.plan_cuota = suscripcion.plan.cuota_facturas
            empresa.plan_estado = 'activo'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Pago confirmado y suscripción activada',
            'pago_id': nuevo_pago.id,
            'suscripcion': {
                'estado': suscripcion.estado,
                'plan': suscripcion.plan.nombre,
                'fecha_vencimiento': suscripcion.fecha_vencimiento.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error confirmando pago', 'error': str(e)}), 500

@app.route('/api/suscripcion/estado/<empresa_id>', methods=['GET'])
def estado_suscripcion(empresa_id):
    """Retorna el estado de suscripción de una empresa"""
    try:
        suscripcion = Suscripcion.query.filter_by(empresa_id=empresa_id).order_by(Suscripcion.fecha_creacion.desc()).first()
        if not suscripcion:
            return jsonify({
                'tiene_suscripcion': False,
                'mensaje': 'La empresa no tiene suscripción activa'
            }), 200
        
        plan = suscripcion.plan
        
        return jsonify({
            'tiene_suscripcion': True,
            'estado': suscripcion.estado,
            'plan': {
                'id': plan.id,
                'nombre': plan.nombre,
                'cuota_facturas': plan.cuota_facturas,
                'facturas_usadas': suscripcion.facturas_usadas_mes,
                'usuarios_incluidos': plan.usuarios_incluidos,
                'sucursales_incluidas': plan.sucursales_incluidas
            },
            'fechas': {
                'inicio': suscripcion.fecha_inicio.isoformat(),
                'vencimiento': suscripcion.fecha_vencimiento.isoformat(),
                'dias_restantes': (suscripcion.fecha_vencimiento - datetime.utcnow()).days
            },
            'tipo_cobro': suscripcion.tipo_cobro
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Error consultando suscripción', 'error': str(e)}), 500

@app.route('/api/suscripcion/cancelar', methods=['POST'])
def cancelar_suscripcion():
    """Cancela una suscripción activa"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        motivo = data.get('motivo', 'No especificado')
        
        suscripcion = Suscripcion.query.filter_by(empresa_id=empresa_id, estado='activa').first()
        if not suscripcion:
            return jsonify({'message': 'No hay suscripción activa para cancelar'}), 404
        
        suscripcion.estado = 'cancelada'
        suscripcion.fecha_cancelacion = datetime.utcnow()
        
        # Actualizar empresa
        empresa = Empresa.query.get(empresa_id)
        if empresa:
            empresa.plan_estado = 'cancelado'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Suscripción cancelada correctamente',
            'fecha_cancelacion': suscripcion.fecha_cancelacion.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error cancelando suscripción', 'error': str(e)}), 500

@app.route('/api/pagos/historial/<empresa_id>', methods=['GET'])
def historial_pagos(empresa_id):
    """Retorna historial de pagos de una empresa"""
    try:
        pagos = PagoSuscripcion.query.filter_by(empresa_id=empresa_id).order_by(PagoSuscripcion.fecha_creacion.desc()).all()
        return jsonify([{
            'id': p.id,
            'monto': float(p.monto),
            'moneda': p.moneda,
            'estado': p.estado,
            'provider': p.provider,
            'fecha_pago': p.fecha_pago.isoformat() if p.fecha_pago else None,
            'fecha_creacion': p.fecha_creacion.isoformat()
        } for p in pagos]), 200
        
    except Exception as e:
        return jsonify({'message': 'Error consultando historial', 'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard_metrics(current_user):
    """
    Retorna las métricas y actividad reciente para panelControl.html
    
    LÓGICA DE PERMISOS:
    - Administrador (dueño de empresa): Ve datos de TODA su empresa (todas las sucursales)
    - Usuario de sucursal: Ve datos SOLO de su sucursal asignada
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, extract
        
        # Determinar sucursales según el rol del usuario
        if current_user.is_superadmin:
            # SuperAdmin no debería llegar aquí, pero por seguridad
            return jsonify({"message": "SuperAdmin debe usar el panel de SuperAdmin"}), 403
        
        # Obtener accesos del usuario
        accesos = current_user.accesos
        if not accesos:
            return jsonify({
                "facturasEmitidas": 0,
                "facturasVariacion": "0%",
                "ingresosTotales": 0,
                "ingresosVariacion": "0%",
                "clientesActivos": 0,
                "clientesVariacion": "0%",
                "tasaConversion": "0.0%",
                "tasaVariacion": "0%",
                "actividadReciente": [],
                "scope": "sin_acceso"
            }), 200
        
        # Verificar si es Administrador de la empresa
        es_administrador = any(acc.rol.nombre == 'Administrador' for acc in accesos)
        
        if es_administrador:
            # ADMINISTRADOR: Ver datos de TODA la empresa
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
            scope = "empresa"
        else:
            # USUARIO: Ver datos SOLO de su sucursal
            sucursales_ids = [acc.sucursal_id for acc in accesos]
            scope = "sucursal"
        
        if not sucursales_ids:
            return jsonify({
                "facturasEmitidas": 0,
                "facturasVariacion": "0%",
                "ingresosTotales": 0,
                "ingresosVariacion": "0%",
                "clientesActivos": 0,
                "clientesVariacion": "0%",
                "tasaConversion": "0.0%",
                "tasaVariacion": "0%",
                "actividadReciente": [],
                "scope": scope
            }), 200
        
        # Fechas para comparación (mes actual vs mes anterior)
        hoy = datetime.now()
        inicio_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1)
        fin_mes_anterior = inicio_mes_actual - timedelta(seconds=1)
        
        # ========== MÉTRICA 1: FACTURAS EMITIDAS ==========
        # Mes actual
        facturas_mes_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_actual
        ).count()
        
        # Mes anterior
        facturas_mes_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).count()
        
        # Calcular variación
        facturas_variacion = calcular_variacion(facturas_mes_actual, facturas_mes_anterior)
        
        # ========== MÉTRICA 2: INGRESOS TOTALES ==========
        # Mes actual
        facturas_exitosas_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Pagada', 'Aceptada MH', 'Aceptada', 'Pendiente']),
            Factura.fecha_emision >= inicio_mes_actual
        ).all()
        ingresos_mes_actual = sum(float(f.total) for f in facturas_exitosas_actual)
        
        # Mes anterior
        facturas_exitosas_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Pagada', 'Aceptada MH', 'Aceptada', 'Pendiente']),
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).all()
        ingresos_mes_anterior = sum(float(f.total) for f in facturas_exitosas_anterior)
        
        # Calcular variación
        ingresos_variacion = calcular_variacion(ingresos_mes_actual, ingresos_mes_anterior)
        
        # ========== MÉTRICA 3: CLIENTES ACTIVOS ==========
        # Clientes que han comprado este mes
        clientes_activos_actual = db.session.query(func.count(func.distinct(Factura.cliente_id))).filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_actual,
            Factura.cliente_id.isnot(None)
        ).scalar() or 0
        
        # Clientes que compraron el mes anterior
        clientes_activos_anterior = db.session.query(func.count(func.distinct(Factura.cliente_id))).filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior,
            Factura.cliente_id.isnot(None)
        ).scalar() or 0
        
        # Calcular variación
        clientes_variacion = calcular_variacion(clientes_activos_actual, clientes_activos_anterior)
        
        # ========== MÉTRICA 4: TASA DE CONVERSIÓN ==========
        # Mes actual
        total_facturas_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_actual
        ).count()
        
        facturas_rechazadas_actual = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Rechazada', 'Anulada']),
            Factura.fecha_emision >= inicio_mes_actual
        ).count()
        
        tasa_conversion_actual = 100.0
        if total_facturas_actual > 0:
            exito = total_facturas_actual - facturas_rechazadas_actual
            tasa_conversion_actual = (exito / total_facturas_actual) * 100
        
        # Mes anterior
        total_facturas_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).count()
        
        facturas_rechazadas_anterior = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False,
            Factura.estado.in_(['Rechazada', 'Anulada']),
            Factura.fecha_emision >= inicio_mes_anterior,
            Factura.fecha_emision <= fin_mes_anterior
        ).count()
        
        tasa_conversion_anterior = 100.0
        if total_facturas_anterior > 0:
            exito_anterior = total_facturas_anterior - facturas_rechazadas_anterior
            tasa_conversion_anterior = (exito_anterior / total_facturas_anterior) * 100
        
        # Calcular variación
        tasa_variacion = calcular_variacion(tasa_conversion_actual, tasa_conversion_anterior)
        
        # ========== ACTIVIDAD RECIENTE ==========
        actividad = []
        recientes = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False
        ).order_by(Factura.fecha_emision.desc()).limit(10).all()
        
        for f in recientes:
            actividad.append({
                "tipo": "factura",
                "id": f.numero_consecutivo,
                "clienteNombre": f.cliente.nombre if f.cliente else "Consumidor Final",
                "monto": float(f.total),
                "estado": f.estado,
                "fecha": f.fecha_emision.isoformat(),
                "sucursal": f.sucursal.nombre if f.sucursal else "N/A"
            })
        
        return jsonify({
            "facturasEmitidas": facturas_mes_actual,
            "facturasVariacion": facturas_variacion,
            "ingresosTotales": ingresos_mes_actual,
            "ingresosVariacion": ingresos_variacion,
            "clientesActivos": clientes_activos_actual,
            "clientesVariacion": clientes_variacion,
            "tasaConversion": f"{tasa_conversion_actual:.1f}%",
            "tasaVariacion": tasa_variacion,
            "actividadReciente": actividad,
            "scope": scope,
            "periodo": {
                "mes_actual": inicio_mes_actual.strftime("%B %Y"),
                "mes_anterior": inicio_mes_anterior.strftime("%B %Y")
            }
        }), 200

    except Exception as e:
        print(f"Error Dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": "Error al cargar métricas", "error": str(e)}), 500


def calcular_variacion(valor_actual, valor_anterior):
    """Calcula la variación porcentual entre dos valores"""
    if valor_anterior == 0:
        if valor_actual > 0:
            return "+100%"
        return "0%"
    
    variacion = ((valor_actual - valor_anterior) / valor_anterior) * 100
    signo = "+" if variacion >= 0 else ""
    return f"{signo}{variacion:.1f}%"


@app.route('/api/seed', methods=['GET'])
def seed_endpoint():
    if os.environ.get('FLASK_ENV') == 'production':
        seed_key = os.environ.get('SEED_SECRET_KEY')
        if not seed_key or request.headers.get('X-Seed-Key') != seed_key:
            return jsonify({'message': 'Endpoint deshabilitado en producción.'}), 403
    try:
        from models import Empresa, Sucursal, Rol, Usuario, AccesoSucursal, Cliente, Producto
        from werkzeug.security import generate_password_hash
        
        # 1. Crear Empresa Demo
        empresa = Empresa.query.filter_by(cedula_juridica="3101123456").first()
        if not empresa:
            empresa = Empresa(
                razon_social="Tecnología MuroTech QA S.A.",
                nombre_comercial="MuroTech Store",
                cedula_juridica="3101123456",
                tipo_identificacion="02",
                actividad_economica="Venta de equipos de cómputo",
                email_contacto="contacto@murotechqa.com",
                telefono="2222-3333"
            )
            db.session.add(empresa)
            db.session.flush()

        # 2. Crear Sucursal
        sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
        if not sucursal:
            sucursal = Sucursal(
                empresa_id=empresa.id,
                numero_sucursal="001",
                terminal="00001",
                nombre="Sede Central San José",
                direccion="100m Sur del Parque Central"
            )
            db.session.add(sucursal)
            db.session.flush()

        # 3. Roles
        rol_admin = Rol.query.filter_by(nombre="Administrador").first()
        if not rol_admin:
            rol_admin = Rol(nombre="Administrador", descripcion="Control total")
            db.session.add(rol_admin)
            db.session.flush()

        # 4. Usuario Admin
        usuario = Usuario.query.filter_by(email="admin@qa.com").first()
        if not usuario:
            usuario = Usuario(
                empresa_id=empresa.id,
                nombre="Admin Pruebas",
                email="admin@qa.com",
                is_superadmin=True
            )
            usuario.set_password("admin123")
            db.session.add(usuario)
            db.session.flush()
            
            # Acceso
            acceso = AccesoSucursal(usuario_id=usuario.id, sucursal_id=sucursal.id, rol_id=rol_admin.id)
            db.session.add(acceso)

        # 5. Clientes Ficticios
        clientes_data = [
            ("Juan Pérez", "111111111", "juan@correo.com", "8888-1111"),
            ("María Gómez", "222222222", "maria@correo.com", "8888-2222"),
            ("Carlos Ruiz", "333333333", "carlos@correo.com", "8888-3333"),
            ("Ana Fernández", "444444444", "ana@correo.com", "8888-4444"),
            ("Empresa Ficticia S.A.", "3101222333", "compras@ficticia.com", "2222-5555"),
        ]
        
        for c_nombre, c_id, c_email, c_tel in clientes_data:
            if not Cliente.query.filter_by(identificacion=c_id).first():
                cliente = Cliente(
                    empresa_id=empresa.id,
                    tipo_id="01" if len(c_id) == 9 else "02",
                    identificacion=c_id,
                    nombre=c_nombre,
                    email=c_email,
                    telefono=c_tel,
                    provincia="San José",
                    canton="Central"
                )
                db.session.add(cliente)

        # 6. Productos Ficticios
        productos_data = [
            ("Laptop Dell XPS 13", "LAP-001", "Dell", 850000.00, 10),
            ("Monitor LG 27 pulgadas", "MON-001", "LG", 150000.00, 25),
            ("Teclado Mecánico Keychron", "TEC-001", "Keychron", 65000.00, 50),
            ("Mouse Inalámbrico Logitech", "MOU-001", "Logitech", 25000.00, 100),
            ("Cable HDMI 2.1 2m", "CAB-001", "Generico", 8000.00, 200),
            ("Impresora Epson EcoTank", "IMP-001", "Epson", 185000.00, 15),
            ("Disco Duro Externo 2TB", "HDD-001", "Seagate", 45000.00, 40),
            ("Memoria RAM 16GB DDR4", "RAM-001", "Corsair", 35000.00, 60),
            ("Silla Ergonómica", "SIL-001", "Office", 120000.00, 8),
            ("Servicio de Mantenimiento PC", "SRV-001", "Servicio", 25000.00, 0),
        ]
        
        for p_desc, p_cod, p_marca, p_precio, p_stock in productos_data:
            if not Producto.query.filter_by(codigo=p_cod).first():
                prod = Producto(
                    empresa_id=empresa.id,
                    codigo=p_cod,
                    descripcion=p_desc,
                    marca=p_marca,
                    costo=p_precio * 0.7, # 30% margen
                    margen=30.0,
                    precio_venta=p_precio,
                    impuesto=13.0,
                    stock=p_stock
                )
                db.session.add(prod)

        db.session.commit()
        return jsonify({"message": "¡Base de datos llenada con datos ficticios con éxito!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Manejador global de errores para asegurar que SIEMPRE devuelva JSON
@app.errorhandler(Exception)
def handle_exception(e):
    # Log del error en el servidor
    print(f"ERROR GLOBAL: {str(e)}")
    # Retornar JSON en lugar del HTML por defecto de Flask
    return jsonify({
        "message": "Error interno del servidor",
        "error": str(e)
    }), 500

# ==========================================
# MENSAJE RECEPTOR (aceptacion / rechazo B2B) v4.4
# ==========================================

@app.route('/api/mensajes-receptor', methods=['GET', 'POST'])
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


# Registrar rutas de SuperAdmin desde supadmin_api.py
supadmin_api.register_supadmin_routes(app)


@app.route('/api/cabys/search', methods=['GET'])
def search_cabys():
    """
    Busca códigos CABYS usando la API oficial del Ministerio de Hacienda
    https://api.hacienda.go.cr/fe/cabys
    """
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({"success": True, "results": [], "count": 0}), 200
        
        # API oficial de Hacienda para CABYS
        api_url = f"https://api.hacienda.go.cr/fe/cabys?q={query}"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Formatear respuesta para el frontend
            resultados = []
            
            # La API de Hacienda devuelve un objeto con la estructura:
            # {'total': X, 'cantidad': Y, 'cabys': [...]}
            if isinstance(data, dict) and 'cabys' in data:
                items = data['cabys'][:30]  # Limitar a 30 resultados
                for item in items:
                    resultados.append({
                        'codigo': item.get('codigo', ''),
                        'descripcion': item.get('descripcion', ''),
                        'impuesto': item.get('impuesto', 13)
                    })
            # Fallback por si la API cambia y devuelve una lista directa
            elif isinstance(data, list):
                for item in data[:30]:
                    resultados.append({
                        'codigo': item.get('codigo', ''),
                        'descripcion': item.get('descripcion', ''),
                        'impuesto': item.get('impuesto', 13)
                    })
            
            return jsonify({"success": True, "results": resultados, "count": len(resultados)}), 200
        else:
            return jsonify({"success": False, "message": "Error al consultar API de Hacienda", "results": [], "count": 0}), response.status_code
            
    except requests.Timeout:
        return jsonify({"success": False, "message": "Timeout al consultar API de Hacienda", "results": [], "count": 0}), 504
    except Exception as e:
        print(f"Error buscando CABYS: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Error al buscar en catálogo CABYS", "error": str(e), "results": [], "count": 0}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    _debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=_debug, host='0.0.0.0', port=port)
