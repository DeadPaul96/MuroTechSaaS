from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

# ==========================================
# MODELOS DE AUTORIZACIÓN Y MULTITENANCY
# ==========================================

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
    # Consecutivos por tipo (v4.4)
    c_factura = db.Column(db.Integer, default=0)
    c_tiquete = db.Column(db.Integer, default=0)
    c_nota_credito = db.Column(db.Integer, default=0)
    c_nota_debito = db.Column(db.Integer, default=0)
    
    accesos = db.relationship('AccesoSucursal', backref='sucursal', lazy=True, cascade='all, delete-orphan')
    facturas = db.relationship('Factura', backref='sucursal', lazy=True)

class Rol(db.Model):
    """Roles del sistema: 'Admin', 'Emisor', 'Auditor'"""
    __tablename__ = 'roles'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))

class Usuario(db.Model):
    """Usuarios del sistema. Pertenecen a una Empresa."""
    __tablename__ = 'usuarios'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_superadmin = db.Column(db.Boolean, default=False) # Admin de toda la empresa
    pantallas_asignadas = db.Column(db.String(255), default="facturacion,inventario") # Lista de módulos permitidos (separados por coma)
    
    accesos = db.relationship('AccesoSucursal', backref='usuario', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AccesoSucursal(db.Model):
    """Tabla pivote que asigna a un Usuario un Rol dentro de una Sucursal específica."""
    __tablename__ = 'accesos_sucursal'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    rol_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False)

# ==========================================
# MODELOS DE NEGOCIO (FACTURACIÓN E INVENTARIO)
# ==========================================

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    tipo_id = db.Column(db.String(10)) # 01, 02, etc.
    identificacion = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150))
    telefono = db.Column(db.String(50))
    movil = db.Column(db.String(50))
    actividad_economica = db.Column(db.Text)
    regimen = db.Column(db.String(200))
    provincia = db.Column(db.String(100))
    canton = db.Column(db.String(100))
    distrito = db.Column(db.String(100))
    barrio = db.Column(db.String(100))
    direccion = db.Column(db.Text)
    
    facturas = db.relationship('Factura', backref='cliente', lazy=True)

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    
    # Datos Principales MH
    cabys = db.Column(db.String(20))
    codigo = db.Column(db.String(50), nullable=False) # Interno
    unidad_medida = db.Column(db.String(10), default='Unid')
    descripcion = db.Column(db.String(200), nullable=False) # Resumen MH
    
    # Atributos de Producto Físico
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    caracteristicas = db.Column(db.Text)
    
    # Atributos de Servicio
    nombre_servicio = db.Column(db.String(200))
    detalle_servicio = db.Column(db.Text)
    
    # Precios y Finanzas
    costo = db.Column(db.Float, default=0.0) # precio_linea
    margen = db.Column(db.Float, default=0.0) # ganancia %
    precio_venta = db.Column(db.Float, nullable=False)
    descuento_max = db.Column(db.Float, default=0.0)
    
    # Impuestos
    impuesto = db.Column(db.Float, default=13.0) # IVA %
    tipo_impuesto = db.Column(db.String(10), default="01") # 01=IVA
    
    # Operación
    stock = db.Column(db.Integer, default=0)
    
    factura_detalles = db.relationship('FacturaDetalle', backref='producto_rel', lazy=True)
    movimientos = db.relationship('InventarioMovimiento', backref='producto', lazy=True, cascade='all, delete-orphan')

class InventarioMovimiento(db.Model):
    __tablename__ = 'inventario_movimientos'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    producto_id = db.Column(db.String(36), db.ForeignKey('productos.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=False)
    
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_movimiento = db.Column(db.String(50)) # Venta, Ajuste, Devolución, Ingreso
    cantidad_anterior = db.Column(db.Integer, nullable=False)
    cantidad_ajuste = db.Column(db.Integer, nullable=False)
    cantidad_nueva = db.Column(db.Integer, nullable=False)
    referencia = db.Column(db.String(100)) # ID Factura, etc.

class Compra(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    proveedor = db.Column(db.String(150), nullable=False)
    concepto = db.Column(db.String(200), nullable=False)
    monto_neto = db.Column(db.Float, nullable=False)
    iva = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), default="Operativo")

class Factura(db.Model):
    __tablename__ = 'facturas'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    cliente_id = db.Column(db.String(36), db.ForeignKey('clientes.id'))
    numero_consecutivo = db.Column(db.String(50), unique=True, nullable=False)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    tipo_documento = db.Column(db.String(50), default="Factura Electrónica")
    condicion_venta = db.Column(db.String(50), default="Contado")
    medio_pago = db.Column(db.String(50), default="Efectivo")
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True) # Específico para Cotizaciones/Proformas
    moneda = db.Column(db.String(10), default="CRC")
    subtotal = db.Column(db.Float, default=0.0)
    descuentos = db.Column(db.Float, default=0.0)
    impuestos = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(50), default="Borrador") # Borrador, Emitida, Pendiente, Aceptada MH, Rechazada
    is_draft = db.Column(db.Boolean, default=False)
    observaciones = db.Column(db.Text)
    
    # Trazabilidad
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    usuario = db.relationship('Usuario', backref='facturas_emitidas', lazy=True)

    # Conversión de Moneda
    tipo_cambio = db.Column(db.Float, default=1.0)
    is_quotation = db.Column(db.Boolean, default=False)
    xml_comprobante = db.Column(db.LargeBinary)
    pdf_comprobante = db.Column(db.LargeBinary)
    respuesta_hacienda = db.Column(db.LargeBinary)
    
    # Para Notas de Crédito / Débito
    referencia_id = db.Column(db.String(50))
    referencia_codigo = db.Column(db.String(10))
    referencia_razon = db.Column(db.String(200))
    
    detalles = db.relationship('FacturaDetalle', backref='factura', lazy=True, cascade='all, delete-orphan')

class FacturaDetalle(db.Model):
    __tablename__ = 'facturas_detalle'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    factura_id = db.Column(db.String(36), db.ForeignKey('facturas.id'), nullable=False)
    producto_id = db.Column(db.String(36), db.ForeignKey('productos.id'))
    descripcion = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    porcentaje_descuento = db.Column(db.Float, default=0.0)
    porcentaje_impuesto = db.Column(db.Float, default=13.0)
    total_linea = db.Column(db.Float, nullable=False)

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=True) # Puede ser global a la empresa
    
    tipo = db.Column(db.String(50), nullable=False) # hacienda, inventario, sistema, pago
    icono = db.Column(db.String(50), default='fas fa-bell')
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    leida = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(200), nullable=True)
