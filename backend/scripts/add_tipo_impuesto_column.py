#!/usr/bin/env python3
"""
Script para agregar la columna tipo_impuesto a la tabla facturas_detalle
"""
import os
from dotenv import load_dotenv
from sqlalchemy import text, create_engine

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL no está configurada")
    exit(1)

print("\n" + "="*80)
print("AGREGANDO COLUMNA tipo_impuesto A facturas_detalle")
print("="*80 + "\n")

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Verificar si la columna ya existe
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='facturas_detalle' AND column_name='tipo_impuesto'
        """)
        
        result = connection.execute(check_query)
        if result.fetchone():
            print("✓ La columna tipo_impuesto ya existe en la tabla facturas_detalle")
        else:
            print("⚠️  La columna tipo_impuesto NO existe. Agregando...")
            
            # Agregar la columna
            alter_query = text("""
                ALTER TABLE facturas_detalle 
                ADD COLUMN tipo_impuesto VARCHAR(10) DEFAULT '01'
            """)
            
            connection.execute(alter_query)
            connection.commit()
            print("✓ Columna tipo_impuesto agregada exitosamente")
            print("  - Tipo: VARCHAR(10)")
            print("  - Valor por defecto: '01'")
    
    print("\n" + "="*80)
    print("OPERACIÓN COMPLETADA")
    print("="*80 + "\n")
    
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    print("\nDetalles del error:")
    import traceback
    traceback.print_exc()
    exit(1)
