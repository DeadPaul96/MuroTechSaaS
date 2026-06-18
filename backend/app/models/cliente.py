import uuid
from app.models.base import db

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
