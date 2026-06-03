from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base import db

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

    rol = db.relationship('Rol', backref='accesos', lazy=True)

class SuperAdminEmpresa(db.Model):
    """Mapeo de asignacion de empresas (emisores) a SuperAdministradores"""
    __tablename__ = 'superadmin_empresas'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    superadmin_id = db.Column(db.String(36), db.ForeignKey('usuarios.id'), nullable=False)
    empresa_id = db.Column(db.String(36), db.ForeignKey('empresas.id'), nullable=False)
    
    superadmin = db.relationship('Usuario', backref=db.backref('empresas_asignadas_rel', lazy=True, cascade='all, delete-orphan'))
    empresa = db.relationship('Empresa', backref=db.backref('superadmins_asignados_rel', lazy=True, cascade='all, delete-orphan'))
