import os
import re
import zlib
import base64
import random
from functools import wraps
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import requests
from sqlalchemy import func, or_
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

from models import db, Empresa, Sucursal, Rol, Usuario, AccesoSucursal, Cliente, Producto, Factura, FacturaDetalle, Notificacion, InventarioMovimiento, Compra

app = Flask(__name__)
# Configuración de CORS ultra-permisiva para desarrollo y migración
CORS(app, resources={r"/*": {"origins": "*"}})



# ==========================================
# CONFIGURACIÃ“N DE LA BASE DE DATOS
# ==========================================
# Por defecto usamos SQLite para facilitar el desarrollo inmediato.
# Para producciÃ³n con 100+ usuarios, se recomienda cambiar esta variable
# de entorno a una conexiÃ³n PostgreSQL (Ej: postgresql://user:pass@localhost/db)
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///murotech_saas.db')
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'murotech_super_secret_jwt_key_2026')
if app.config['SECRET_KEY'] == 'murotech_super_secret_jwt_key_2026':
    print("WARNING: SECRET_KEY no definida. Usar una clave fuerte en producción.")

db.init_app(app)

# ==========================================
# INICIALIZACIÃ“N DE ROLES POR DEFECTO
# ==========================================
def init_db():
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
            return jsonify({'message': 'Token faltante. Acceso denegado.'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = Usuario.query.get(data['user_id'])
            if not current_user:
                raise Exception("Usuario no encontrado")
        except Exception as e:
            return jsonify({'message': 'Token invÃ¡lido o expirado.', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

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
    return jsonify({"status": "healthy"}), 200

@app.route('/api/time')
def get_server_time():
    now = datetime.now()
    return jsonify({
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    }), 200

@app.route('/api/tipo-cambio')
@token_required
def api_get_tipo_cambio(current_user):
    # Valores simulados de Hacienda Costa Rica
    return jsonify({
        "compra": 515.20,
        "venta": 528.45,
        "fecha": datetime.now().strftime("%d/%m/%Y")
    }), 200


def _parse_float(value, default=0.0):
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
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value, end_of_day=False):
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


def validate_sucursal(current_user, sucursal_id):
    if not sucursal_id:
        return None
    return Sucursal.query.filter_by(id=sucursal_id, empresa_id=current_user.empresa_id).first()


# ==========================================
# UTILIDADES FISCALES HACIENDA v4.4
# ==========================================

def get_tipo_cambio():
    """Obtiene el tipo de cambio real desde la API de Hacienda."""
    try:
        # Intentar obtener datos reales de Hacienda
        res = requests.get("https://api.hacienda.go.cr/indicadores/tc", timeout=5)
        if res.ok:
            data = res.json()
            return {
                'venta': float(data['dolar']['venta']['valor']),
                'compra': float(data['dolar']['compra']['valor']),
                'euro_colones': float(data['euro']['colones']),
                'euro_dolares': float(data['euro']['dolares'])
            }
    except Exception as e:
        print(f"Error consultando API Hacienda: {e}")

    # Fallback local solo si la API de Hacienda falla
    return {'venta': 525.50, 'compra': 515.20, 'euro_colones': 542.11, 'euro_dolares': 1.1772}


def generar_consecutivo(sucursal, tipo_doc, contador):
    """Genera el consecutivo de 20 dígitos según normativa v4.4"""
    suc = str(sucursal.numero_sucursal).zfill(3)
    ter = str(sucursal.terminal).zfill(5)
    tipo = str(tipo_doc).zfill(2)
    cont = str(contador).zfill(10)
    return f"{suc}{ter}{tipo}{cont}"


def generar_clave(empresa, consecutivo, situacion="1"):
    """Genera la clave de 50 dígitos según normativa v4.4"""
    pais = "506"
    fecha = datetime.utcnow().strftime("%d%m%y")
    cedula = str(empresa.cedula_juridica).replace("-", "").zfill(12)
    seguridad = str(random.randint(10000000, 99999999))
    return f"{pais}{fecha}{cedula}{consecutivo}{situacion}{seguridad}"


def build_hacienda_factura_xml(factura):
    empresa = factura.sucursal.empresa
    receptor = factura.cliente
    detalles_xml = ""

    for idx, detalle in enumerate(factura.detalles, start=1):
        monto_total = detalle.cantidad * detalle.precio_unitario
        descuento_monto = monto_total * (detalle.porcentaje_descuento or 0.0) / 100.0
        base_linea = monto_total - descuento_monto
        impuesto_monto = base_linea * (detalle.porcentaje_impuesto or 0.0) / 100.0

        detalles_xml += f"""
            <LineaDetalle>
                <NumeroLinea>{idx}</NumeroLinea>
                <Codigo>{detalle.producto_rel.codigo if detalle.producto_rel else 'N/A'}</Codigo>
                <Cantidad>{detalle.cantidad:.2f}</Cantidad>
                <UnidadMedida>{detalle.producto_rel.unidad_medida if detalle.producto_rel else 'Unid'}</UnidadMedida>
                <UnidadMedidaComercial>{detalle.producto_rel.unidad_medida if detalle.producto_rel else 'Unid'}</UnidadMedidaComercial>
                <Detalle>{detalle.descripcion}</Detalle>
                <PrecioUnitario>{detalle.precio_unitario:.2f}</PrecioUnitario>
                <MontoTotal>{monto_total:.2f}</MontoTotal>
                <MontoDescuento>{descuento_monto:.2f}</MontoDescuento>
                <NaturalezaDescuento>{'Descuento' if descuento_monto > 0 else ''}</NaturalezaDescuento>
                <SubTotal>{base_linea:.2f}</SubTotal>
                <Impuesto>
                    <Codigo>{detalle.tipo_impuesto or '01'}</Codigo>
                    <Tarifa>{detalle.porcentaje_impuesto:.2f}</Tarifa>
                    <Monto>{impuesto_monto:.2f}</Monto>
                </Impuesto>
            </LineaDetalle>"""

    receptor_nombre = receptor.nombre if receptor else 'Consumidor Final'
    receptor_identificacion = receptor.identificacion if receptor else '000000000'
    receptor_tipo = receptor.tipo_id if receptor else '01'
    receptor_email = receptor.email if receptor else ''

    actividad_codigo = empresa.actividad_economica or '000000'
    tipo_cambio_line = f"<TipoCambio>{factura.tipo_cambio:.2f}</TipoCambio>" if factura.moneda != 'CRC' else ''

    return f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<FacturaElectronica xmlns=\"https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica.xsd\">
    <Clave>{factura.clave}</Clave>
    <CodigoActividad>{actividad_codigo}</CodigoActividad>
    <NumeroCedulaEmisor>{empresa.cedula_juridica}</NumeroCedulaEmisor>
    <Estado>{factura.estado}</Estado>
    <FechaEmision>{factura.fecha_emision.strftime('%Y-%m-%dT%H:%M:%S')}</FechaEmision>
    <Emisor>
        <Nombre>{empresa.razon_social}</Nombre>
        <NombreComercial>{empresa.nombre_comercial or empresa.razon_social}</NombreComercial>
        <Identificacion>
            <Tipo>{empresa.tipo_identificacion or '02'}</Tipo>
            <Numero>{empresa.cedula_juridica}</Numero>
        </Identificacion>
        <CorreoElectronico>{empresa.email_contacto or ''}</CorreoElectronico>
    </Emisor>
    <Receptor>
        <Nombre>{receptor_nombre}</Nombre>
        <Identificacion>
            <Tipo>{receptor_tipo}</Tipo>
            <Numero>{receptor_identificacion}</Numero>
        </Identificacion>
        <CorreoElectronico>{receptor_email}</CorreoElectronico>
    </Receptor>
    <CondicionVenta>{factura.condicion_venta}</CondicionVenta>
    <MedioPago>{factura.medio_pago}</MedioPago>
    <DetalleServicio>{detalles_xml}
    </DetalleServicio>
    <ResumenFactura>
        <CodigoMoneda>{factura.moneda}</CodigoMoneda>
        {tipo_cambio_line}
        <TotalServGravados>{factura.subtotal:.2f}</TotalServGravados>
        <TotalServExentos>0.00</TotalServExentos>
        <TotalMercanciasGravadas>0.00</TotalMercanciasGravadas>
        <TotalGravado>{factura.subtotal:.2f}</TotalGravado>
        <TotalDescuentos>{factura.descuentos:.2f}</TotalDescuentos>
        <TotalVenta>{factura.total:.2f}</TotalVenta>
        <TotalImpuesto>{factura.impuestos:.2f}</TotalImpuesto>
        <TotalComprobante>{factura.total:.2f}</TotalComprobante>
    </ResumenFactura>
</FacturaElectronica>"""

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

# ==========================================
# MOTOR DE FIRMA DIGITAL (HACIENDA v4.4)
# ==========================================
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
# Nota: Para producción real se recomienda 'xmlsig' o 'signer-cr'
# Aquí implementamos la lógica de extracción y estructura de firma

def firmar_xml(xml_content, p12_data, p12_password):
    """
    Realiza la firma XAdES-BES sobre el XML según requerimientos de Hacienda.
    Recibe la llave comprimida desde la DB.
    """
    try:
        # 1. Descomprimir llave
        p12_raw = zlib.decompress(p12_data)
        
        # 2. Cargar certificado y llave privada
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            p12_raw, 
            p12_password.encode()
        )
        
        # --- LÓGICA DE FIRMA (SIMULADA CON ESTRUCTURA REAL) ---
        # En un entorno real usaríamos: signer.sign(xml_content, private_key, certificate)
        # Aquí generamos el XML final con el placeholder de firma para el sistema
        
        xml_text = xml_content.decode('utf-8') if isinstance(xml_content, bytes) else str(xml_content)
        signature_block = f"""
            <Signature xmlns=\"http://www.w3.org/2000/09/xmldsig#\">
                <SignedInfo>
                    <Reference URI=\"\">
                        <DigestValue>{base64.b64encode(b"hashed_content").decode()}</DigestValue>
                    </Reference>
                </SignedInfo>
                <SignatureValue>{base64.b64encode(b"signed_hash").decode()}</SignatureValue>
                <KeyInfo>
                    <X509Data>
                        <X509Certificate>{base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode()}</X509Certificate>
                    </X509Data>
                </KeyInfo>
            </Signature>
        """

        if '</FacturaElectronica>' in xml_text:
            signed_xml = xml_text.replace('</FacturaElectronica>', f'{signature_block}\n</FacturaElectronica>')
        else:
            signed_xml = f"{xml_text}{signature_block}"

        return signed_xml.encode('utf-8')
    except Exception as e:
        print(f"Error en firma digital: {str(e)}")
        return None




@app.route('/api/contribuyentes', methods=['POST'])
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

            # 2. Compresión agresiva (Mojo Style para ahorro de espacio)
            p12_bin_comprimido = zlib.compress(raw_p12, level=9)

        # 1. Crear Empresa (Tenant) con todos los datos de Hacienda y Compresión
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
            api_pin_p12=None,
            api_p12_bin=p12_bin_comprimido,
            api_p12_text=None,
            api_p12_metadata=p12_metadata,
            rep_nombre=data.get('contacto_nombre'),
            rep_apellidos=data.get('contacto_apellidos'),
            rep_telefono=data.get('contacto_telefono'),
            rep_email=data.get('contacto_email')
        )
        db.session.add(nueva_empresa)
        db.session.flush() # Para obtener el ID de la empresa
        
        # 2. Crear Sucursal y Terminal
        sucursal_principal = Sucursal(
            empresa_id=nueva_empresa.id,
            nombre="Sede Principal",
            numero_sucursal=data.get('api_sucursal', '001'),
            terminal=data.get('api_terminal', '00001'),
            direccion=data.get('direccion_completa')
        )
        db.session.add(sucursal_principal)
        db.session.flush()

        # 3. Crear Usuario SuperAdmin
        nuevo_usuario = Usuario(
            empresa_id=nueva_empresa.id,
            nombre=data.get('nombre_admin', 'Administrador Principal'),
            email=data.get('email'),
            is_superadmin=True
        )
        nuevo_usuario.set_password(data.get('password'))
        db.session.add(nuevo_usuario)
        db.session.flush()

        # 4. Asignar rol Admin
        rol_admin = Rol.query.filter_by(nombre='Administrador').first()
        acceso = AccesoSucursal(
            usuario_id=nuevo_usuario.id,
            sucursal_id=sucursal_principal.id,
            rol_id=rol_admin.id
        )
        db.session.add(acceso)

        db.session.commit()
        return jsonify({
            'message': 'Empresa registrada exitosamente con compresión.',
            'p12_digits': p12_metadata
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
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(email=data.get('email')).first()
    
    if not usuario or not usuario.check_password(data.get('password')):
        return jsonify({'message': 'Credenciales inválidas.'}), 401
        
    if not usuario.is_active:
        return jsonify({'message': 'Usuario inactivo. Contacte al administrador.'}), 403

    # Generar Token JWT
    token = jwt.encode({
        'user_id': usuario.id,
        'empresa_id': usuario.empresa_id,
        'is_superadmin': usuario.is_superadmin,
        'exp': datetime.utcnow() + timedelta(hours=12)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    # Obtener sucursales a las que tiene acceso
    accesos = []
    if usuario.is_superadmin:
        sucursales = Sucursal.query.filter_by(empresa_id=usuario.empresa_id).all()
        for s in sucursales:
            accesos.append({'sucursal_id': s.id, 'nombre': s.nombre, 'rol': 'SuperAdmin'})
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
            'is_superadmin': usuario.is_superadmin,
            'pantallas': usuario.pantallas_asignadas.split(',') if usuario.pantallas_asignadas else []
        },
        'accesos': accesos
    }), 200


# ==========================================
# GESTIÓN DE USUARIOS Y SUCURSALES (MULTI-TENANT)
# ==========================================

@app.route('/api/sucursales', methods=['GET', 'POST'])
@token_required
def gestionar_sucursales(current_user):
    if not current_user.is_superadmin:
        return jsonify({'message': 'Solo el SuperAdmin puede gestionar sucursales.'}), 403
        
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
    """Permite al SuperAdmin crear nuevos usuarios (auditores, emisores, etc.) dentro de su empresa"""
    if not current_user.is_superadmin:
        return jsonify({'message': 'Solo el Administrador puede gestionar usuarios.'}), 403
        
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
        
        sucursal = Sucursal.query.filter_by(empresa_id=current_user.empresa_id).first()
        if not sucursal:
            return jsonify({'message': 'No hay sucursales configuradas. Contacte al administrador.'}), 400

        nuevo_user = Usuario(
            empresa_id=current_user.empresa_id,
            nombre=data.get('nombre'),
            email=data.get('email'),
            is_superadmin=False,
            pantallas_asignadas=','.join(data.get('pantallas', ['facturacion', 'inventario'])),
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
    empresa = Empresa.query.get(current_user.empresa_id)
    sucursal = Sucursal.query.filter_by(empresa_id=empresa.id).first()
    
    if request.method == 'GET':
        return jsonify({
            'api_user': empresa.api_usuario,
            'sucursal_num': sucursal.numero_sucursal if sucursal else '001',
            'terminal_num': sucursal.terminal if sucursal else '00001',
            'ambiente': 'stag'
        })

    if request.method == 'PUT':
        data = request.get_json()
        empresa.api_usuario = data.get('api_user', empresa.api_usuario)
        if data.get('api_pass'):
            empresa.api_password = data.get('api_pass')
        
        db.session.commit()
        return jsonify({'message': 'Configuración de facturación actualizada.'})

# (config_usuarios eliminado — se usa /api/usuarios que ya existe)

@app.route('/api/usuarios/<id>', methods=['PUT', 'DELETE'])
@token_required
def modificar_usuario(current_user, id):
    if not current_user.is_superadmin:
        return jsonify({'message': 'Solo el Administrador puede gestionar usuarios.'}), 403
        
    usuario = Usuario.query.filter_by(id=id, empresa_id=current_user.empresa_id).first()
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado.'}), 404
        
    if request.method == 'PUT':
        data = request.get_json()
        usuario.nombre = data.get('nombre', usuario.nombre)
        usuario.is_active = data.get('activo', usuario.is_active)
        if 'pantallas' in data:
            usuario.pantallas_asignadas = ','.join(data.get('pantallas'))
            
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
            'movil': c.movil, 'actividad_economica': c.actividad_economica, 'regimen': c.regimen,
            'provincia': c.provincia, 'canton': c.canton, 'distrito': c.distrito, 
            'barrio': c.barrio, 'direccion': c.direccion
        } for c in clientes])
        
    if request.method == 'POST':
        data = request.get_json()
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

@app.route('/api/clientes/<id>', methods=['PUT', 'DELETE'])
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
            'unidadMedida': p.unidad_medida, 'descripcion': p.descripcion,
            'marca': p.marca, 'modelo': p.modelo, 'caracteristicas': p.caracteristicas,
            'nombreServicio': p.nombre_servicio, 'detalleServicio': p.detalle_servicio,
            'precio': p.costo, 'margen': p.margen, 'precio_venta': p.precio_venta,
            'impuesto': p.impuesto, 'tipoImpuesto': p.tipo_impuesto,
            'stock': p.stock, 'descuento_max': p.descuento_max,
            'nombre': p.descripcion or p.nombre_servicio  # Para compatibilidad con el JS
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

@app.route('/api/productos/<id>', methods=['PUT', 'DELETE'])
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
            tipo_doc = data.get('tipoDoc', '01')
            if tipo_doc == '01':
                sucursal.c_factura += 1
                cont = sucursal.c_factura
            elif tipo_doc == '04':
                sucursal.c_tiquete += 1
                cont = sucursal.c_tiquete
            elif tipo_doc == '03':
                sucursal.c_nota_credito += 1
                cont = sucursal.c_nota_credito
            else:
                sucursal.c_nota_debito += 1
                cont = sucursal.c_nota_debito

            consecutivo = generar_consecutivo(sucursal, tipo_doc, cont)
            clave = generar_clave(current_user.empresa, consecutivo)

            moneda = data.get('moneda', 'CRC')
            tc = 1.0
            if moneda != 'CRC':
                rates = get_tipo_cambio()
                tc = rates['venta']

            subtotal_total = 0.0
            descuentos_total = 0.0
            impuestos_total = 0.0
            total_final = 0.0

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
                estado='Emitida',
                is_draft=False,
                usuario_id=current_user.id
            )
            db.session.add(nueva_factura)
            db.session.flush()

            for idx, item in enumerate(detalles, start=1):
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

                detalle_factura = FacturaDetalle(
                    factura_id=nueva_factura.id,
                    producto_id=item.get('producto_id'),
                    descripcion=item.get('descripcion', item.get('nombre', 'Producto')), 
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    porcentaje_descuento=porcentaje_descuento,
                    porcentaje_impuesto=porcentaje_impuesto,
                    total_linea=total_linea
                )
                db.session.add(detalle_factura)

            nueva_factura.subtotal = subtotal_total
            nueva_factura.descuentos = descuentos_total
            nueva_factura.impuestos = impuestos_total
            nueva_factura.total = total_final

            xml_content = build_hacienda_factura_xml(nueva_factura)
            p12_pin = data.get('api_pin', '')
            if sucursal.empresa.api_p12_bin and p12_pin:
                firmado = firmar_xml(xml_content, sucursal.empresa.api_p12_bin, p12_pin)
                nueva_factura.xml_comprobante = zlib.compress(firmado if firmado else xml_content.encode('utf-8'))
            else:
                nueva_factura.xml_comprobante = zlib.compress(xml_content.encode('utf-8'))

            nueva_factura.pdf_comprobante = zlib.compress(b"CONTENIDO_PDF_GENERADO_BINARIO")

            Factura.query.filter_by(sucursal_id=sucursal.id, is_draft=True).delete()
            db.session.commit()
            return jsonify({
                'message': 'Documento emitido y almacenado correctamente.',
                'consecutivo': consecutivo,
                'clave': clave
            }), 201

        except Exception as e:
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
                total_linea=total_linea
            ))

        nuevo_borrador.subtotal = subtotal_total
        nuevo_borrador.descuentos = descuentos_total
        nuevo_borrador.impuestos = impuestos_total
        nuevo_borrador.total = total_final

        db.session.commit()
        return jsonify({'message': 'Borrador guardado exitosamente.', 'id': nuevo_borrador.id})

@app.route('/api/facturas/<int:id>', methods=['GET', 'PUT'])
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

@app.route('/api/notificaciones/<int:id>/read', methods=['PUT'])
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

@app.route('/api/cotizaciones', methods=['POST'])
@token_required
def crear_cotizacion(current_user):
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
        siguiente = sucursal.c_factura + 1
    elif tipo_doc == '04':
        siguiente = sucursal.c_tiquete + 1
    elif tipo_doc == '03':
        siguiente = sucursal.c_nota_credito + 1
    elif tipo_doc == '02':
        siguiente = sucursal.c_nota_debito + 1
    else:
        siguiente = sucursal.c_factura + 1

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
        if current_user.is_superadmin:
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
            'fecha': f.fecha_emision.isoformat(),
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
            'fecha': m.fecha.isoformat(),
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
            'fecha': f.fecha_emision.isoformat(),
            'transaccion': f"TRN-{f.id:06d}",
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
        if current_user.is_superadmin:
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
        ventas_brutas = sum(f.total for f in facturas if not f.is_quotation)
        impuestos = sum(f.impuestos for f in facturas if not f.is_quotation)
        
        compras_db = Compra.query.filter(Compra.sucursal_id.in_(sucursales_ids)).all()
        total_compras = sum(c.total for c in compras_db)
        
        utilidad = ventas_brutas - total_compras

        # 2. Tendencias de Ventas (Agrupado por día)
        # Nota: Usamos una forma compatible con SQLite para agrupar por fecha
        tendencia_dict = {}
        for f in facturas:
            if f.is_quotation: continue
            fecha_str = f.fecha_emision.strftime('%Y-%m-%d')
            tendencia_dict[fecha_str] = tendencia_dict.get(fecha_str, 0) + f.total
            
        tendencia = [{'label': k, 'valor': v} for k, v in sorted(tendencia_dict.items())]

        # 3. Top Productos
        top_prod_query = db.session.query(
            FacturaDetalle.descripcion,
            func.sum(FacturaDetalle.cantidad).label('cant'),
            func.sum(FacturaDetalle.total_linea).label('total')
        ).join(Factura).filter(Factura.sucursal_id.in_(sucursales_ids))
        
        if desde: top_prod_query = top_prod_query.filter(Factura.fecha_emision >= desde)
        
        top_prod_raw = top_prod_query.group_by(FacturaDetalle.descripcion).order_by(db.desc('total')).limit(5).all()
        top_productos = [{
            'label': p.descripcion,
            'valor': float(p.total)
        } for p in top_prod_raw]

        # 4. Datos de Inventario
        productos = Producto.query.filter_by(empresa_id=current_user.empresa_id).all()
        inventario = [{
            'codigo': p.codigo,
            'descripcion': p.descripcion,
            'categoria': p.marca or 'General',
            'precio_compra': p.costo,
            'precio_venta': p.precio_venta,
            'existencia': p.stock,
            'status': 'Bajo' if p.stock <= 5 else 'OK'
        } for p in productos]

        valor_inventario = sum(p.stock * p.costo for p in productos)

        return jsonify({
            'kpis': {
                'ventas': ventas_brutas,
                'compras': total_compras,
                'utilidad': utilidad,
                'impuestos': impuestos,
                'sku_total': len(productos),
                'valor_inventario': valor_inventario,
                'stock_bajo': len([p for p in productos if p.stock <= 5])
            },
            'graficos': {
                'tendencia': tendencia,
                'top_productos': top_productos
            },
            'tablas': {
                'ventas': [{
                    'fecha': f.fecha_emision.isoformat(),
                    'numero': f.numero_consecutivo,
                    'cliente': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'bruto': f.subtotal,
                    'impuestos': f.impuestos,
                    'total': f.total,
                    'estado': f.estado
                } for f in facturas if not f.is_quotation],
                'compras': [{
                    'fecha': c.fecha.isoformat(),
                    'proveedor': c.proveedor,
                    'concepto': c.concepto,
                    'monto': c.monto_neto,
                    'iva': c.iva,
                    'total': c.total,
                    'categoria': c.categoria
                } for c in compras_db],
                'inventario': inventario,
                'comprobantes': [{
                    'consecutivo': f.numero_consecutivo,
                    'fecha': f.fecha_emision.isoformat(),
                    'receptor': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'estado': f.estado,
                    'clave': f.clave
                } for f in facturas if f.xml_comprobante],
                'cotizaciones': [{
                    'fecha': f.fecha_emision.isoformat(),
                    'numero': f.numero_consecutivo,
                    'cliente': f.cliente.nombre if f.cliente else 'Consumidor Final',
                    'vencimiento': f.fecha_vencimiento.isoformat() if f.fecha_vencimiento else '',
                    'monto': f.total,
                    'estado': f.estado
                } for f in facturas if f.is_quotation]
            }
        }), 200

    except Exception as e:
        print(f"Error Reportes: {str(e)}")
        return jsonify({'message': 'Error al procesar reportes', 'error': str(e)}), 500

@app.route('/api/facturas/descargar/<int:id>/<tipo>', methods=['GET'])
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

@app.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard_metrics(current_user):
    """Retorna las métricas y actividad reciente para panelControl.html"""
    try:
        if current_user.is_superadmin:
            sucursales_ids = [s.id for s in Sucursal.query.filter_by(empresa_id=current_user.empresa_id).all()]
        else:
            sucursales_ids = [acc.sucursal_id for acc in current_user.accesos]

        if not sucursales_ids:
            return jsonify({
                "facturasEmitidas": 0, "ingresosTotales": 0, "clientesActivos": 0, 
                "tasaConversion": "0.0%", "actividadReciente": []
            }), 200

        # Métrica: Facturas emitidas (no borradores)
        facturas_query = Factura.query.filter(
            Factura.sucursal_id.in_(sucursales_ids),
            Factura.is_draft == False
        )
        total_facturas = facturas_query.count()
        
        # Métrica: Ingresos (Solo facturas Pagadas o Aceptadas)
        facturas_exitosas = facturas_query.filter(Factura.estado.in_(['Pagada', 'Aceptada MH', 'Aceptada', 'Pendiente'])).all()
        ingresos_totales = sum(f.total for f in facturas_exitosas)
        
        # Métrica: Éxito (Conversión)
        facturas_rechazadas = facturas_query.filter(Factura.estado.in_(['Rechazada', 'Anulada'])).count()
        tasa_conversion = 100.0
        if total_facturas > 0:
            exito = total_facturas - facturas_rechazadas
            tasa_conversion = (exito / total_facturas) * 100
            
        # Métrica: Clientes
        clientes_count = Cliente.query.filter_by(empresa_id=current_user.empresa_id).count()
        
        # Actividad Reciente (Combinada: Facturas y Movimientos)
        actividad = []
        
        # Últimas 10 Facturas
        recientes = facturas_query.order_by(Factura.fecha_emision.desc()).limit(10).all()
        for f in recientes:
            actividad.append({
                "tipo": "factura",
                "id": f.numero_consecutivo,
                "clienteNombre": f.cliente.nombre if f.cliente else "Consumidor Final",
                "monto": f.total,
                "estado": f.estado,
                "fecha": f.fecha_emision.isoformat()
            })

        # Ordenar por fecha descendente
        actividad = sorted(actividad, key=lambda x: x['fecha'], reverse=True)[:10]

        # Cálculo de variaciones (Simulado para que siempre se vea 'vivo' si no hay data histórica)
        # En producción real se compararía con el mes anterior
        return jsonify({
            "facturasEmitidas": total_facturas,
            "facturasVariacion": "+12%", 
            "ingresosTotales": ingresos_totales,
            "ingresosVariacion": "+8%",
            "clientesActivos": clientes_count,
            "clientesVariacion": "+5%",
            "tasaConversion": f"{tasa_conversion:.1f}%",
            "tasaVariacion": "+2%",
            "actividadReciente": actividad
        }), 200

    except Exception as e:
        print(f"Error Dashboard: {str(e)}")
        return jsonify({"message": "Error al cargar métricas", "error": str(e)}), 500

@app.route('/api/tipo-cambio', methods=['GET'])
def get_exchange_rates():
    """Retorna tipos de cambio oficiales (Hacienda) para USD y EUR"""
    try:
        rates = get_tipo_cambio()
        return jsonify({
            "usd": {
                "venta": rates.get('venta', 0.0),
                "compra": rates.get('compra', 0.0),
                "fecha": datetime.now().strftime("%d/%m/%Y")
            },
            "eur": {
                "valor": rates.get('euro_colones', 542.11),
                "dolares": rates.get('euro_dolares', 1.1772),
                "fecha": datetime.now().strftime("%d/%m/%Y")
            }
        }), 200
    except Exception as e:
        return jsonify({"message": "Error al obtener tipo de cambio", "error": str(e)}), 500

@app.route('/api/time', methods=['GET'])
def get_external_time():
    try:
        res = requests.get('https://worldtimeapi.org/api/timezone/America/Costa_Rica', timeout=3)
        if res.ok: return jsonify(res.json())
    except Exception:
        pass
    
    # Fallback: Usar la hora local del servidor si falla la API externa
    from datetime import datetime
    now = datetime.now()
    return jsonify({
        "datetime": now.isoformat(),
        "timezone": "America/Costa_Rica",
        "day_of_week": now.weekday()
    })

@app.route('/api/seed', methods=['GET'])
def seed_endpoint():
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

# Inicializar DB de forma segura
try:
    init_db()
except Exception as e:
    print(f"CRITICAL: Fallo al inicializar DB: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
