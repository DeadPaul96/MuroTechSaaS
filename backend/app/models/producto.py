from datetime import datetime
import uuid
from app.models.base import db

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
