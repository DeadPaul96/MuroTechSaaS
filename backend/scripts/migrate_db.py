"""
Script de migración automática.
Agrega columnas faltantes a tablas existentes sin borrar datos.
Se ejecuta cada vez que arranca el servidor.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')

from app import create_app
from app.models.base import db

MIGRACIONES = [
    # (tabla, columna, definicion_sql)
    ("usuarios",  "fecha_creacion", "TIMESTAMP DEFAULT NOW()"),
    ("empresas",  "fecha_creacion", "TIMESTAMP DEFAULT NOW()"),
]

def run():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            for tabla, columna, definicion in MIGRACIONES:
                try:
                    # Verificar si la columna ya existe
                    result = conn.execute(db.text(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name='{tabla}' AND column_name='{columna}'"
                    ))
                    existe = result.fetchone()
                    if not existe:
                        conn.execute(db.text(
                            f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"
                        ))
                        conn.commit()
                        print(f"  [OK] Columna '{columna}' agregada a '{tabla}'")
                    else:
                        print(f"  [OK] Columna '{columna}' en '{tabla}' ya existe")
                except Exception as e:
                    print(f"  [WARN] {tabla}.{columna}: {e}")
        print("  Migracion completada.")

if __name__ == '__main__':
    run()
