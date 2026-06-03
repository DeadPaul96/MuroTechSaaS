#!/usr/bin/env python3
"""Auditoría: tablas/columnas esperadas vs PostgreSQL actual."""
import sys

from sqlalchemy import create_engine, inspect
from db_conn import get_database_url

EXPECTED_TABLES = {
    'empresas', 'sucursales', 'roles', 'usuarios', 'revoked_tokens', 'accesos_sucursal',
    'clientes', 'productos', 'facturas', 'facturas_detalle', 'notificaciones', 'pagos',
    'inventario_movimientos', 'compras', 'cotizaciones', 'cotizaciones_detalle',
    'superadmin_empresas', 'mensajes_receptor',
}

EXPECTED_COLUMNS = {
    'empresas': {'ambiente_hacienda'},
    'sucursales': {'provincia', 'canton', 'distrito', 'barrio', 'otras_senas'},
    'facturas_detalle': {'tipo_impuesto'},
    'productos': {'tipo_impuesto'},
}

def main():
    engine = create_engine(get_database_url())
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    missing_tables = EXPECTED_TABLES - tables
    extra = tables - EXPECTED_TABLES

    print('=== TABLAS ===')
    if missing_tables:
        print('FALTAN:', ', '.join(sorted(missing_tables)))
    else:
        print('Todas las tablas esperadas existen.')
    if extra:
        print('Extra en BD:', ', '.join(sorted(extra)))

    print('\n=== COLUMNAS ===')
    ok = True
    for table, cols in EXPECTED_COLUMNS.items():
        if table not in tables:
            continue
        have = {c['name'] for c in insp.get_columns(table)}
        miss = cols - have
        if miss:
            ok = False
            print(f'{table}: faltan {miss}')
        else:
            print(f'{table}: OK')
    if ok and not missing_tables:
        print('\nEsquema alineado con models.py')
    else:
        print('\nEjecute: python scripts/run_all_migrations.py')
        sys.exit(1)


if __name__ == '__main__':
    main()
