#!/usr/bin/env python3
"""Cifra api_password y api_pin_p12 en texto plano."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from api.app import app, db
from api.models import Empresa
from core.crypto_utils import ENC_PREFIX, encrypt_text


def main():
    key = app.config.get('ENCRYPTION_KEY')
    if not key:
        print('ERROR: ENCRYPTION_KEY no configurada')
        sys.exit(1)
    with app.app_context():
        n = 0
        for emp in Empresa.query.all():
            ch = False
            for field in ('api_password', 'api_pin_p12'):
                val = getattr(emp, field, None)
                if val and not str(val).startswith(ENC_PREFIX):
                    setattr(emp, field, encrypt_text(str(val), key))
                    ch = True
            if ch:
                n += 1
        db.session.commit()
        print(f'Empresas actualizadas: {n}')


if __name__ == '__main__':
    main()
