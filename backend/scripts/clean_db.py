#!/usr/bin/env python3
"""
Script para limpiar todos los datos de la base de datos MUROTECH
"""
import os
import sys
from pathlib import Path

# Agregar el directorio actual al path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv(current_dir / '.env')

# Importar la aplicación Flask
from api.app import app, db

if __name__ == '__main__':
    with app.app_context():
        print("Limpiando base de datos...")
        # Eliminar en orden inverso de dependencias
        try:
            db.session.execute(db.text("DELETE FROM notificaciones"))
            db.session.execute(db.text("DELETE FROM inventario_movimientos"))
            db.session.execute(db.text("DELETE FROM facturas_detalle"))
            db.session.execute(db.text("DELETE FROM facturas"))
            db.session.execute(db.text("DELETE FROM compras"))
            db.session.execute(db.text("DELETE FROM productos"))
            db.session.execute(db.text("DELETE FROM clientes"))
            db.session.execute(db.text("DELETE FROM accesos_sucursal"))
            db.session.execute(db.text("DELETE FROM usuarios"))
            db.session.execute(db.text("DELETE FROM sucursales"))
            db.session.execute(db.text("DELETE FROM empresas"))
            db.session.execute(db.text("DELETE FROM revoked_tokens"))
            # Roles no eliminar, son fijos
            db.session.commit()
            print("✅ Base de datos limpiada exitosamente")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error limpiando base de datos: {e}")