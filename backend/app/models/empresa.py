from datetime import datetime
import uuid
from app.models.base import db

class Empresa(db.Model):
    """Representa el inquilino principal (Tenant)"""
    __tablename__ = 'empresas'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    razon_social = db.Column(db.String(200), nullable=False)
    nombre_comercial = db.Column(db.String(200))
    cedula_juridica = db.Column(db.String(50), unique=True, nullable=False)
    tipo_identificacion = db.Column(db.String(5), default="02")
    actividad_economica = db.Column(db.String(200))
    regimen = db.Column(db.String(100))
    email_contacto = db.Column(db.String(150))
    telefono = db.Column(db.String(50))
    
    # Credenciales Hacienda API
    api_usuario = db.Column(db.String(200))
    api_password = db.Column(db.String(200))
    api_pin_p12 = db.Column(db.String(10))
    
    # Llave Criptográfica (Almacenamiento Comprimido)
    api_p12_bin = db.Column(db.LargeBinary)  # Binario comprimido (zlib)
    api_p12_text = db.Column(db.Text)         # Base64 comprimido
    api_p12_metadata = db.Column(db.Text)     # Dígitos/Serial extraídos
    
    # Contacto Administrativo (Representante)
    rep_nombre = db.Column(db.String(100))
    rep_apellidos = db.Column(db.String(100))
    rep_telefono = db.Column(db.String(50))
    rep_email = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    plan_tipo = db.Column(db.String(20), default='mensual')
    plan_cuota = db.Column(db.Integer, default=0)
    plan_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    plan_vencimiento = db.Column(db.DateTime, nullable=True)
    plan_estado = db.Column(db.String(20), default='activo')
    ambiente_hacienda = db.Column(db.String(10), default='stag')
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    sucursales = db.relationship('Sucursal', backref='empresa', lazy=True, cascade='all, delete-orphan')
    usuarios = db.relationship('Usuario', backref='empresa', lazy=True, cascade='all, delete-orphan')
    clientes = db.relationship('Cliente', backref='empresa', lazy=True, cascade='all, delete-orphan')
    productos = db.relationship('Producto', backref='empresa', lazy=True, cascade='all, delete-orphan')

class Sucursal(db.Model):
    """Sucursales físicas o lógicas de una empresa (Ej: 001, 002)"""
    __tablename__ = 'sucursales'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    numero_sucursal = db.Column(db.String(10), nullable=False, default="001")
    terminal = db.Column(db.String(10), default="00001")
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.Text)
    
    # Ubicación estructurada según API 4.4 de Hacienda Costa Rica
    provincia = db.Column(db.String(10), default="1")
    canton = db.Column(db.String(10), default="01")
    distrito = db.Column(db.String(10), default="01")
    barrio = db.Column(db.String(10), default="01")
    otras_senas = db.Column(db.String(250))
    
    # Consecutivos por tipo (v4.4)
    c_factura = db.Column(db.Integer, default=0)
    c_tiquete = db.Column(db.Integer, default=0)
    c_nota_credito = db.Column(db.Integer, default=0)
    c_nota_debito = db.Column(db.Integer, default=0)
    
    accesos = db.relationship('AccesoSucursal', backref='sucursal', lazy=True, cascade='all, delete-orphan')
    facturas = db.relationship('Factura', backref='sucursal', lazy=True)
