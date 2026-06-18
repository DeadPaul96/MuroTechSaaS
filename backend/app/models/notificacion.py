from datetime import datetime
import uuid
from app.models.base import db

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    __table_args__ = (
        db.Index('ix_notificaciones_empresa_leida', 'empresa_id', 'leida'),
    )
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

    empresa = db.relationship('Empresa', backref=db.backref('notificaciones', lazy=True))
    sucursal = db.relationship('Sucursal', backref=db.backref('notificaciones', lazy=True))
