#!/usr/bin/env python3
from sqlalchemy import create_engine, inspect, text
from db_conn import get_database_url

engine = create_engine(get_database_url())
insp = inspect(engine)
if 'productos' not in insp.get_table_names():
    print('tabla productos no existe')
    raise SystemExit(1)

cols = {c['name'] for c in insp.get_columns('productos')}
with engine.begin() as conn:
    if 'tipo_impuesto' not in cols:
        conn.execute(text("ALTER TABLE productos ADD COLUMN tipo_impuesto VARCHAR(10) DEFAULT '01'"))
        print('productos.tipo_impuesto agregada')
    else:
        print('productos.tipo_impuesto ya existe')
