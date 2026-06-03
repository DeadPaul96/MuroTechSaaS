from datetime import datetime
import uuid
from app.models.base import db

class AuditoriaLog(db.Model):
    """Registro de auditoría para cambios en entidades críticas"""
    __tablename__ = 'auditoria_logs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'))
    entidad = db.Column(db.String(50))  # 'empresa', 'factura', etc
    accion = db.Column(db.String(50))   # 'CREATE', 'UPDATE', 'DELETE'
    valores_antes = db.Column(db.JSON)
    valores_despues = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    usuario = db.relationship('Usuario', backref='auditoria_logs', lazy=True)
