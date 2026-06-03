#!/usr/bin/env python3
"""ambiente_hacienda + tabla mensajes_receptor."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect, text
from db_conn import get_database_url

engine = create_engine(get_database_url())
insp = inspect(engine)

with engine.begin() as conn:
    if 'empresas' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('empresas')}
        if 'ambiente_hacienda' not in cols:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN ambiente_hacienda VARCHAR(10) DEFAULT 'stag'"))
            print('empresas.ambiente_hacienda agregada')
        else:
            print('empresas.ambiente_hacienda ya existe')

    if 'mensajes_receptor' not in insp.get_table_names():
        conn.execute(text("""
            CREATE TABLE mensajes_receptor (
                id VARCHAR(36) PRIMARY KEY,
                empresa_id VARCHAR(36) NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
                clave_comprobante VARCHAR(50) NOT NULL,
                tipo_mensaje VARCHAR(2) NOT NULL,
                detalle_mensaje VARCHAR(80),
                consecutivo_receptor VARCHAR(20),
                estado VARCHAR(30) DEFAULT 'generado',
                xml_mensaje BYTEA,
                fecha_emision_doc TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print('tabla mensajes_receptor creada')
    else:
        print('tabla mensajes_receptor ya existe')

print('OK migrate_ambiente_mensaje')
