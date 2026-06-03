#!/usr/bin/env python3
"""Orquestador de migraciones (ejecutar tras cada deploy)."""
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    'migrate_db_v44.py',
    'add_tipo_impuesto_column.py',
    'migrate_productos_tipo_impuesto.py',
    'migrate_ambiente_mensaje.py',
    'migrate_auditoria.py',
    'migrate_indexes.py',
]
OPTIONAL = ['encrypt_empresa_secrets.py']


def run(name: Path) -> int:
    print('\n>>', name.name)
    return subprocess.call([sys.executable, str(name)], cwd=str(name.parent))


def main():
    d = Path(__file__).parent
    for s in SCRIPTS:
        code = run(d / s)
        if code != 0:
            sys.exit(code)
    if '--encrypt-secrets' in sys.argv:
        run(d / 'encrypt_empresa_secrets.py')
    print('\nMigraciones completadas.')


if __name__ == '__main__':
    main()
