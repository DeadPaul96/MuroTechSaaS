from datetime import datetime
import uuid
from app.models.base import db

class Factura(db.Model):
    __tablename__ = 'facturas'
    __table_args__ = (
        db.Index('ix_facturas_sucursal_estado', 'sucursal_id', 'estado'),
        db.Index('ix_facturas_fecha_emision', 'fecha_emision'),
        db.Index('ix_facturas_sucursal_draft', 'sucursal_id', 'is_draft'),
    )
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
