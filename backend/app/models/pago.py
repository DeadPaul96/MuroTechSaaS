from datetime import datetime
import uuid
from app.models.base import db

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
