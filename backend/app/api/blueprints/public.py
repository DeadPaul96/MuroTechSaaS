import os
from datetime import datetime
from flask import Blueprint, jsonify, request
from app.models import db, Empresa, Sucursal, Rol, Usuario, Cliente, Producto, AccesoSucursal
from app.services.billing_plans import plans_public_payload
from app.extensions import limiter

bp = Blueprint('public', __name__)

@bp.route('/api')
def home():
    return jsonify({"message": "MUROTECH API is running", "status": "online"}), 200

@bp.route('/api/health')
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'ok'
    except Exception as e:
        db_status = f'error: {str(e)}'

    from flask import current_app
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    db_type = 'sqlite' if 'sqlite' in db_uri else 'postgresql' if 'postgresql' in db_uri else 'unknown'

    return jsonify({
        "status": "ok",
        "health": "healthy",
        "db_type": db_type,
        "db_status": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }), 200 if db_status == 'ok' else 503

@bp.route('/api/time')
def get_server_time():
    now = datetime.now()
    return jsonify({
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    }), 200

@bp.route('/api/planes', methods=['GET'])
@limiter.limit(os.environ.get('RATELIMIT_PUBLIC', '120 per hour'))
def obtener_planes():
    return jsonify({'planes': plans_public_payload()})

@bp.route('/api/tipo-cambio', methods=['GET'])
@limiter.limit(os.environ.get('RATELIMIT_PUBLIC', '120 per hour'))
def tipo_cambio():
    from app.api.blueprints.invoices import get_tipo_cambio
    rates = get_tipo_cambio()
    return jsonify(rates), 200

@bp.route('/api/seed', methods=['GET'])
def seed_endpoint():
    if os.environ.get('FLASK_ENV') == 'production':
        seed_key = os.environ.get('SEED_SECRET_KEY')
        if not seed_key or request.headers.get('X-Seed-Key') != seed_key:
            return jsonify({'message': 'Endpoint deshabilitado en producción.'}), 403
    try:
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
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
