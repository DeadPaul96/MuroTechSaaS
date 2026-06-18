#!/usr/bin/env python3
"""
Script para crear perfiles de usuario según requerimientos
"""
import sys
import os
from pathlib import Path
from werkzeug.security import generate_password_hash

# Agregar el directorio actual al path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv(current_dir / '.env')

from dotenv import load_dotenv
load_dotenv()
from app import create_app
app = create_app()
from app.models import db
from api.models import Empresa, Usuario, Rol, Sucursal, AccesoSucursal

def create_profiles():
    with app.app_context():
        db.create_all()

        # Crear roles si no existen
        roles = [
            {'nombre': 'Administrador', 'descripcion': 'Control total de la sucursal/empresa'},
            {'nombre': 'Emisor', 'descripcion': 'Solo puede emitir facturas y gestionar clientes'},
            {'nombre': 'Auditor', 'descripcion': 'Solo lectura para revisar métricas y facturas'},
            {'nombre': 'SuperUsuario', 'descripcion': 'Administrador de sistema, acceso limitado'}
        ]
        for rd in roles:
            if not Rol.query.filter_by(nombre=rd['nombre']).first():
                rol = Rol(nombre=rd['nombre'], descripcion=rd['descripcion'])
                db.session.add(rol)
        db.session.commit()

        # Crear empresa ficticia con info tributaria
        empresa = Empresa(
            razon_social="Empresa Demo S.A.",
            nombre_comercial="Demo Corp",
            cedula_juridica="3101234567",
            tipo_identificacion="02",
            actividad_economica="Desarrollo de software",
            regimen="General",
            email_contacto="contacto@demo.com",
            telefono="2222-3333",
            api_usuario="demo_user",
            api_password="demo_pass",
            api_pin_p12="1234",
            rep_nombre="Juan",
            rep_apellidos="Pérez",
            rep_telefono="8888-9999",
            rep_email="juan@demo.com",
            is_active=True,
            plan_tipo="mensual",
            plan_cuota=500,
            plan_estado="activo"
        )
        db.session.add(empresa)
        db.session.commit()

        # Crear sucursal
        sucursal = Sucursal(
            empresa_id=empresa.id,
            numero_sucursal="001",
            terminal="00001",
            nombre="Sucursal Central",
            direccion="San José, Costa Rica"
        )
        db.session.add(sucursal)
        db.session.commit()

        # Crear administrador
        admin = Usuario(
            empresa_id=empresa.id,
            nombre="Administrador Demo",
            email="admin@demo.com",
            password_hash=generate_password_hash("admin123"),
            is_active=True,
            is_superadmin=False,
            pantallas_asignadas="auditoria,clientes,configuracion,cotizaciones,editarFactura,inventario,notificaciones,panelControl,pantallaFacturacion,pos,registro,reportes"
        )
        db.session.add(admin)
        db.session.commit()

        # Asignar acceso a sucursal para admin
        acceso_admin = AccesoSucursal(
            usuario_id=admin.id,
            sucursal_id=sucursal.id,
            rol_id=Rol.query.filter_by(nombre="Administrador").first().id
        )
        db.session.add(acceso_admin)
        db.session.commit()

        # Crear super usuario
        super_user = Usuario(
            empresa_id=empresa.id,
            nombre="Super Usuario",
            email="super@demo.com",
            password_hash=generate_password_hash("super123"),
            is_active=True,
            is_superadmin=True,
            pantallas_asignadas="superAdmin"
        )
        db.session.add(super_user)
        db.session.commit()

        print("✅ Perfiles creados exitosamente")
        print("Administrador:")
        print("  Email: admin@demo.com")
        print("  Password: admin123")
        print("  Pantallas: Todas menos superAdmin")
        print("")
        print("Super Usuario:")
        print("  Email: super@demo.com")
        print("  Password: super123")
        print("  Pantallas: Solo superAdmin")

if __name__ == '__main__':
    create_profiles()