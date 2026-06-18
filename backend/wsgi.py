"""Punto de entrada WSGI para producción (Gunicorn/uWSGI)."""
import os
from dotenv import load_dotenv

# Cargar variables de entorno antes de crear la app
env_file = os.environ.get('ENV_FILE', '.env.production')
load_dotenv(env_file)

from app import create_app

application = create_app()
