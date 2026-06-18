#!/usr/bin/env python3
"""
Script de backup automático de la base de datos MUROTECH.

Soporta PostgreSQL (Supabase) y SQLite como fallback.
Diseñado para ejecutarse vía cron job.

Uso:
    python scripts/backup_db.py
    python scripts/backup_db.py --retention-days 30 --output /backups

Variables de entorno:
    DATABASE_URL       URL de conexión PostgreSQL
    BACKUP_RETENTION_DAYS  Días de retención (default: 30)
    BACKUP_OUTPUT_DIR  Directorio de salida (default: ./backups)
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_database_url():
    url = os.environ.get('DATABASE_URL', '')
    if url:
        return url
    user = os.environ.get('SUPABASE_USER')
    password = os.environ.get('SUPABASE_PASS')
    host = os.environ.get('SUPABASE_HOST')
    port = os.environ.get('SUPABASE_PORT', '5432')
    db = os.environ.get('SUPABASE_DB', 'postgres')
    if user and password and host:
        return f'postgresql://{user}:{password}@{host}:{port}/{db}'
    return ''


def backup_postgresql(db_url, output_dir):
    """Dump PostgreSQL usando pg_dump."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'murotech_backup_{timestamp}.sql'
    filepath = output_dir / filename

    env = os.environ.copy()
    env['PGPASSWORD'] = db_url.split(':')[2].split('@')[0] if '://' in db_url else ''

    cmd = ['pg_dump', '--no-owner', '--no-privileges', '-f', str(filepath)]
    if db_url.startswith('postgres'):
        cmd.insert(1, db_url)
    else:
        cmd.insert(1, f'--dbname={db_url}')

    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        # Comprimir
        compressed = filepath.with_suffix('.sql.gz')
        subprocess.run(['gzip', str(filepath)], check=True)
        print(f'Backup creado: {compressed}')
        return compressed
    except FileNotFoundError:
        print('pg_dump no encontrado. Instale postgresql-client.', file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f'Error en pg_dump: {e.stderr}', file=sys.stderr)
        return None


def backup_sqlite(db_url, output_dir):
    """Copia archivo SQLite."""
    db_path = db_url.replace('sqlite:///', '')
    if not os.path.exists(db_path):
        print(f'Base de datos SQLite no encontrada: {db_path}', file=sys.stderr)
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'murotech_backup_{timestamp}.db'
    filepath = output_dir / filename

    shutil.copy2(db_path, filepath)
    print(f'Backup SQLite creado: {filepath}')
    return filepath


def cleanup_old_backups(output_dir, retention_days):
    """Elimina backups más antiguos que retention_days."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    for f in output_dir.iterdir():
        if f.is_file() and 'murotech_backup_' in f.name:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
    if deleted:
        print(f'Backups antiguos eliminados: {deleted}')
    return deleted


def main():
    parser = argparse.ArgumentParser(description='Backup automático de BD MUROTECH')
    parser.add_argument('--output', default=os.environ.get('BACKUP_OUTPUT_DIR', './backups'),
                        help='Directorio de salida')
    parser.add_argument('--retention-days', type=int,
                        default=int(os.environ.get('BACKUP_RETENTION_DAYS', '30')),
                        help='Días de retención')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    db_url = get_database_url()
    if not db_url:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'murotech_saas.db')
        db_url = f'sqlite:///{db_path}'

    print(f'Iniciando backup ({datetime.now().isoformat()})...')
    print(f'  Output: {output_dir}')
    print(f'  Retention: {args.retention_days} días')

    if db_url.startswith(('postgresql://', 'postgres://')):
        result = backup_postgresql(db_url, output_dir)
    elif db_url.startswith('sqlite:///'):
        result = backup_sqlite(db_url, output_dir)
    else:
        print(f'Tipo de BD no soportado: {db_url[:50]}', file=sys.stderr)
        sys.exit(1)

    if not result:
        print('Backup fallido.', file=sys.stderr)
        sys.exit(1)

    cleanup_old_backups(output_dir, args.retention_days)
    print(f'Backup completado: {result}')


if __name__ == '__main__':
    main()
