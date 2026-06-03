#!/usr/bin/env python3
"""Índices recomendados para producción."""
from sqlalchemy import create_engine, inspect, text
from db_conn import get_database_url

INDEXES = [
    ('ix_facturas_clave', 'facturas', 'clave'),
    ('ix_facturas_consecutivo', 'facturas', 'numero_consecutivo'),
    ('ix_facturas_sucursal_fecha', 'facturas', 'sucursal_id, fecha_emision'),
    ('ix_clientes_empresa_ident', 'clientes', 'empresa_id, identificacion'),
    ('ix_productos_empresa_cabys', 'productos', 'empresa_id, cabys'),
    ('ix_pagos_empresa_status', 'pagos', 'empresa_id, status'),
]

engine = create_engine(get_database_url())
tables = set(inspect(engine).get_table_names())

with engine.begin() as conn:
    for name, table, cols in INDEXES:
        if table not in tables:
            print(f'omitido {name}: sin tabla {table}')
            continue
        conn.execute(text(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})'))
        print(f'índice {name} OK')

print('OK migrate_indexes')
