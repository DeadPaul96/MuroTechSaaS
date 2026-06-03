from datetime import datetime
import uuid
from app.models.base import db

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
