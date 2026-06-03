from datetime import datetime
import uuid
from app.models.base import db

class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.Text, unique=True, nullable=False)
    fecha_revocado = db.Column(db.DateTime, default=datetime.utcnow)
