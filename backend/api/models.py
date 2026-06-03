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

class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.Text, unique=True, nullable=False)
    fecha_revocado = db.Column(db.DateTime, default=datetime.utcnow)

class AccesoSucursal(db.Model):
    """Tabla pivote que asigna a un Usuario un Rol dentro de una Sucursal específica."""
    __tablename__ = 'accesos_sucursal'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=False)
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    rol_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False)

    rol = db.relationship('Rol', backref='accesos', lazy=True)

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
    costo = db.Column(db.Numeric(14, 2), default=0.00) # precio_linea
    margen = db.Column(db.Numeric(5, 2), default=0.00) # ganancia %
    precio_venta = db.Column(db.Numeric(14, 2), nullable=False)
    descuento_max = db.Column(db.Numeric(5, 2), default=0.00)
    
    # Impuestos
    impuesto = db.Column(db.Numeric(5, 2), default=13.00) # IVA %
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
    usuario = db.relationship('Usuario', backref='movimientos_inventario', lazy=True)
    
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
    monto_neto = db.Column(db.Numeric(14, 2), nullable=False)
    iva = db.Column(db.Numeric(14, 2), default=0.00)
    total = db.Column(db.Numeric(14, 2), nullable=False)
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
    subtotal = db.Column(db.Numeric(14, 2), default=0.00)
    descuentos = db.Column(db.Numeric(14, 2), default=0.00)
    impuestos = db.Column(db.Numeric(14, 2), default=0.00)
    total = db.Column(db.Numeric(14, 2), default=0.00)
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
    cantidad = db.Column(db.Numeric(14, 4), nullable=False)
    precio_unitario = db.Column(db.Numeric(14, 2), nullable=False)
    porcentaje_descuento = db.Column(db.Numeric(5, 2), default=0.00)
    porcentaje_impuesto = db.Column(db.Numeric(5, 2), default=13.00)
    tipo_impuesto = db.Column(db.String(10), default="01")  # 01=IVA, etc.
    total_linea = db.Column(db.Numeric(14, 2), nullable=False)

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

class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    plan_tipo = db.Column(db.String(50), nullable=False)
    plan_cuota = db.Column(db.Integer, nullable=False, default=0)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    currency = db.Column(db.String(10), default='CRC')
    status = db.Column(db.String(50), default='pending')
    provider = db.Column(db.String(50), default='manual')
    transaction_id = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    checkout_url = db.Column(db.String(250), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Cotizacion(db.Model):
    __tablename__ = 'cotizaciones'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sucursal_id = db.Column(db.String(36), db.ForeignKey('sucursales.id'), nullable=False)
    cliente_nombre = db.Column(db.String(200), nullable=False)
    cliente_cedula = db.Column(db.String(50), nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    moneda = db.Column(db.String(10), default="CRC")
    subtotal = db.Column(db.Numeric(14, 2), default=0.00)
    descuentos = db.Column(db.Numeric(14, 2), default=0.00)
    impuestos = db.Column(db.Numeric(14, 2), default=0.00)
    total = db.Column(db.Numeric(14, 2), default=0.00)
    estado = db.Column(db.String(50), default="Borrador") # Borrador, Enviada, Aceptada, Rechazada
    observaciones = db.Column(db.Text)
    
    # Trazabilidad
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=True)
    usuario = db.relationship('Usuario', backref='cotizaciones_emitidas', lazy=True)
    
    # Conversión de Moneda
    tipo_cambio = db.Column(db.Float, default=1.0)
    pdf_comprobante = db.Column(db.LargeBinary)
    
    detalles = db.relationship('CotizacionDetalle', backref='cotizacion', lazy=True, cascade='all, delete-orphan')

class CotizacionDetalle(db.Model):
    __tablename__ = 'cotizaciones_detalle'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cotizacion_id = db.Column(db.String(36), db.ForeignKey('cotizaciones.id'), nullable=False)
    producto_id = db.Column(db.String(36), db.ForeignKey('productos.id'))
    descripcion = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Numeric(14, 4), nullable=False)
    precio_unitario = db.Column(db.Numeric(14, 2), nullable=False)
    porcentaje_descuento = db.Column(db.Numeric(5, 2), default=0.00)
    porcentaje_impuesto = db.Column(db.Numeric(5, 2), default=13.00)
    tipo_impuesto = db.Column(db.String(10), default="01")  # 01=IVA, etc.
    total_linea = db.Column(db.Numeric(14, 2), nullable=False)

# ==========================================
# MODELOS DE PLANES Y SUSCRIPCIONES
# ==========================================

class Plan(db.Model):
    """Planes de suscripción disponibles"""
    __tablename__ = 'planes'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = db.Column(db.String(50), nullable=False)  # Básico, Profesional, Enterprise, Corporativo
    descripcion = db.Column(db.Text)
    precio_mensual = db.Column(db.Numeric(10, 2), nullable=False)
    precio_anual = db.Column(db.Numeric(10, 2), nullable=False)
    cuota_facturas = db.Column(db.Integer, nullable=False)  # Límite de facturas mensuales
    usuarios_incluidos = db.Column(db.Integer, default=1)
    sucursales_incluidas = db.Column(db.Integer, default=1)
    tiene_api_hacienda = db.Column(db.Boolean, default=True)
    tiene_firma_digital = db.Column(db.Boolean, default=False)
    tiene_soporte = db.Column(db.Boolean, default=False)
    tiene_reportes_avanzados = db.Column(db.Boolean, default=False)
    tiene_multi_moneda = db.Column(db.Boolean, default=False)
    orden = db.Column(db.Integer, default=0)  # Para mostrar en orden
    is_active = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Suscripcion(db.Model):
    """Suscripciones activas de empresas a planes"""
    __tablename__ = 'suscribciones'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    plan_id = db.Column(db.String(36), db.ForeignKey('planes.id'), nullable=False)
    
    estado = db.Column(db.String(20), default='activa')  # activa, suspendida, cancelada, trial
    tipo_cobro = db.Column(db.String(10), default='mensual')  # mensual, anual
    
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=False)
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)
    
    # Contador de uso
    facturas_usadas_mes = db.Column(db.Integer, default=0)
    periodo_facturacion = db.Column(db.DateTime, nullable=True)
    
    # Datos de pago
    provider_pago = db.Column(db.String(50))  # stripe, paypal
    subscription_id_externo = db.Column(db.String(100))
    ultimo_pago_id = db.Column(db.String(100))
    ultimo_pago_estado = db.Column(db.String(50))
    fecha_ultimo_pago = db.Column(db.DateTime, nullable=True)
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    empresa = db.relationship('Empresa', backref='suscripcion_actual', lazy=True)
    plan = db.relationship('Plan', backref='suscribciones', lazy=True)

class PagoSuscripcion(db.Model):
    """Historial de pagos de suscripciones"""
    __tablename__ = 'pagos_suscripciones'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    suscripcion_id = db.Column(db.String(36), db.ForeignKey('suscribciones.id'), nullable=False)
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    moneda = db.Column(db.String(3), default='CRC')
    tipo_cobro = db.Column(db.String(10))  # mensual, anual
    
    provider = db.Column(db.String(50))  # stripe, paypal
    payment_id_externo = db.Column(db.String(100))
    payment_method = db.Column(db.String(50))  # card, paypal
    
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, completado, fallido, reembolsado
    descripcion = db.Column(db.Text)
    
    metadata_json = db.Column(db.Text)  # JSON con datos adicionales del provider
    
    fecha_pago = db.Column(db.DateTime, nullable=True)
    fecha_procesado = db.Column(db.DateTime, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    suscripcion = db.relationship('Suscripcion', backref='pagos', lazy=True)
    empresa = db.relationship('Empresa', backref='pagos_suscripcion', lazy=True)

class MensajeReceptor(db.Model):
    __tablename__ = 'mensajes_receptor'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    clave_comprobante = db.Column(db.String(50), nullable=False)
    tipo_mensaje = db.Column(db.String(2), nullable=False)
    detalle_mensaje = db.Column(db.String(80))
    consecutivo_receptor = db.Column(db.String(20))
    estado = db.Column(db.String(30), default='generado')
    xml_mensaje = db.Column(db.LargeBinary)
    fecha_emision_doc = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    empresa = db.relationship('Empresa', backref=db.backref('mensajes_receptor', lazy=True))


class SuperAdminEmpresa(db.Model):
    """Mapeo de asignacion de empresas (emisores) a SuperAdministradores"""
    __tablename__ = 'superadmin_empresas'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    superadmin_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=False)
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    
    superadmin = db.relationship('Usuario', backref=db.backref('empresas_asignadas_rel', lazy=True, cascade='all, delete-orphan'))
    empresa = db.relationship('Empresa', backref=db.backref('superadmins_asignados_rel', lazy=True, cascade='all, delete-orphan'))
