#!/usr/bin/env python3
"""
Script de migración de base de datos para la API 4.4 de Hacienda Costa Rica
Agrega soporte para ubicaciones estructuradas en sucursales y tabla de asignaciones de SuperAdmin
"""
import os
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, '.env'))

DATABASE_URL = os.getenv('DATABASE_URL')

def get_connection():
    if not DATABASE_URL:
        raise RuntimeError('Configure DATABASE_URL en backend/.env')
    print('Conectando usando DATABASE_URL...')
    return psycopg2.connect(DATABASE_URL)

def main():
    print("=" * 80)
    print("EJECUTANDO MIGRACION DE BASE DE DATOS (API 4.4)")
    print("=" * 80)
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # 1. Agregar columnas de ubicación estructurada a sucursales
        columnas_sucursal = [
            ('provincia', 'VARCHAR(10) DEFAULT \'1\''),
            ('canton', 'VARCHAR(10) DEFAULT \'01\''),
            ('distrito', 'VARCHAR(10) DEFAULT \'01\''),
            ('barrio', 'VARCHAR(10) DEFAULT \'01\''),
            ('otras_senas', 'VARCHAR(250)')
        ]
        
        for col_name, col_type in columnas_sucursal:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='sucursales' AND column_name='{col_name}'
            """)
            if cur.fetchone():
                print(f"La columna '{col_name}' ya existe en la tabla 'sucursales'.")
            else:
                print(f"Agregando columna '{col_name}' ({col_type}) a la tabla 'sucursales'...")
                cur.execute(f"ALTER TABLE sucursales ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"Columna '{col_name}' agregada con exito.")

        # 2. Crear tabla superadmin_empresas para asignaciones de SuperAdmin
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'superadmin_empresas'
            )
        """)
        exists = cur.fetchone()[0]
        
        if exists:
            print("La tabla 'superadmin_empresas' ya existe.")
        else:
            print("Creando tabla 'superadmin_empresas'...")
            cur.execute("""
                CREATE TABLE superadmin_empresas (
                    id VARCHAR(36) PRIMARY KEY,
                    superadmin_id VARCHAR(36) NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    empresa_id VARCHAR(36) NOT NULL REFERENCES empresas(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            print("Tabla 'superadmin_empresas' creada con exito.")
            
        cur.close()
        conn.close()
        print("\n" + "=" * 80)
        print("MIGRACION COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nERROR EN LA MIGRACION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
