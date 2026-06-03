"""Conexión PostgreSQL para scripts — solo DATABASE_URL en .env."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / '.env')
sys.path.insert(0, str(_ROOT))


def get_database_url():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('Configure DATABASE_URL en backend/.env')
    return url


def get_psycopg2_connection():
    import psycopg2
    return psycopg2.connect(get_database_url())
