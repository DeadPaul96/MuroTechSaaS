#!/usr/bin/env python3
"""
Script de prueba de conexion a Supabase
"""
import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()
from app import create_app
app = create_app()
from app.models import db
from api.models import Usuario, Rol, Empresa

def test_connection():
    """Prueba la conexion a Supabase"""
    print("=" * 60)
    print("TEST: PRUEBA DE CONEXION A SUPABASE")
    print("=" * 60)
    
    try:
        with app.app_context():
            # Probar conexion
            result = db.session.execute(db.text("SELECT 1"))
            print("[OK] Conexion a base de datos: OK")
            
            # Verificar tablas
            tablas = ['usuarios', 'roles', 'empresas', 'sucursales']
            for tabla in tablas:
                try:
                    count = db.session.execute(db.text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
                    print(f"  [INFO] {tabla}: {count} registros")
                except Exception as e:
                    print(f"  [ERROR] {tabla}: Error - {e}")
            
            # Verificar SuperAdmin
            superadmin = Usuario.query.filter_by(email='superadmin@murotech.com').first()
            if superadmin:
                print(f"\n[OK] SuperAdmin encontrado:")
                print(f"   ID: {superadmin.id}")
                print(f"   Email: {superadmin.email}")
                print(f"   SuperAdmin: {superadmin.is_superadmin}")
            else:
                print("\n[FAIL] SuperAdmin no encontrado!")
            
            # Verificar roles
            roles = Rol.query.all()
            print(f"\n[INFO] Roles en el sistema:")
            for rol in roles:
                print(f"   - {rol.nombre}: {rol.descripcion}")
            
            return True
            
    except Exception as e:
        print(f"\n[FAIL] Error de conexion: {e}")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)