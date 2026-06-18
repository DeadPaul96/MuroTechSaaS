#!/usr/bin/env python3
"""
Script para crear datos iniciales en MUROTECH SaaS
"""
import sys
import os

# Agregar el directorio del backend al path
backend_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_path)

# Configurar variables de entorno si no existen (opcional)
if os.path.exists(os.path.join(backend_path, '.env')):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(backend_path, '.env'))
elif os.path.exists(os.path.join(os.path.dirname(backend_path), '.env')):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(backend_path), '.env'))

from dotenv import load_dotenv
load_dotenv()
from app import create_app
app = create_app()
db = app.extensions['sqlalchemy']

from api.models import Empresa, Usuario, Rol, Sucursal
from werkzeug.security import generate_password_hash

def create_initial_data():
    with app.app_context():
        # Crear todas las tablas
        db.create_all()

        # Verificar si ya existe un SuperAdmin
        superadmin = Usuario.query.filter_by(is_superadmin=True).first()
        if superadmin:
            print("[OK] SuperAdmin ya existe")
            return

        print("Creando datos iniciales...")

        # Crear empresa por defecto si no existe
        empresa = Empresa.query.filter_by(cedula_juridica="3100000000").first()
        if not empresa:
            empresa = Empresa(
                razon_social="MUROTECH DEMO S.A.",
                cedula_juridica="3100000000",
                plan_tipo="mensual",
                plan_cuota=100,
                plan_estado="activo",
                is_active=True
            )
            db.session.add(empresa)
            db.session.commit()

        # Crear rol de administrador si no existe
        rol_admin = Rol.query.filter_by(nombre="Administrador").first()
        if not rol_admin:
            rol_admin = Rol(
                nombre="Administrador",
                descripcion="Administrador de empresa"
            )
            db.session.add(rol_admin)
            db.session.commit()

        # Crear sucursal principal si no existe
        sucursal = Sucursal.query.filter_by(nombre="Sucursal Principal", empresa_id=empresa.id).first()
        if not sucursal:
            sucursal = Sucursal(
                nombre="Sucursal Principal",
                direccion="San José, Costa Rica",
                empresa_id=empresa.id
            )
            db.session.add(sucursal)
            db.session.commit()

        # Crear SuperAdmin si no existe
        superadmin = Usuario.query.filter_by(is_superadmin=True).first()
        if not superadmin:
            superadmin = Usuario(
                nombre="SuperAdmin",
                email="admin@murotech.com",
                password_hash=generate_password_hash("admin123"),
                is_superadmin=True,
                empresa_id=empresa.id,
                is_active=True
            )
            db.session.add(superadmin)
            db.session.commit()

        print("[OK] Datos iniciales creados exitosamente")
        print("Credenciales SuperAdmin:")
        print("   Email: admin@murotech.com")
        print("   Password: admin123")
        print("Frontend: file:///c:/Users/danie/OneDrive/Escritorio/Practica-Profeciona-Facturacion-MUROTECH--main/Practica-Profeciona-Facturacion-MUROTECH--main/frontend/index.html")
        print("Ojo de Dios: file:///c:/Users/danie/OneDrive/Escritorio/Practica-Profeciona-Facturacion-MUROTECH--main/Practica-Profeciona-Facturacion-MUROTECH--main/frontend/html/superAdmin.html")

if __name__ == '__main__':
    create_initial_data()