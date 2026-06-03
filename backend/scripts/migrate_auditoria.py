#!/usr/bin/env python3
"""Crea tabla auditoria_logs si no existe."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect, text
from db_conn import get_database_url

engine = create_engine(get_database_url())
insp = inspect(engine)

with engine.begin() as conn:
    if 'auditoria_logs' not in insp.get_table_names():
        conn.execute(text("""
            CREATE TABLE auditoria_logs (
                id VARCHAR(36) PRIMARY KEY,
                usuario_id VARCHAR(36) REFERENCES usuarios(id),
                entidad VARCHAR(50),
                accion VARCHAR(50),
                valores_antes JSON,
                valores_despues JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(50),
                user_agent VARCHAR(500)
            )
        """))
        print('tabla auditoria_logs creada')
    else:
        print('tabla auditoria_logs ya existe')

print('OK migrate_auditoria')
