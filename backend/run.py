#!/usr/bin/env python3
"""
Script de arranque para el backend de MUROTECH SaaS.

Este archivo configura el entorno de Python, carga las variables de
entorno desde .env y levanta la aplicación Flask principal.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio actual al path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv(current_dir / '.env')

# Importar la aplicación Flask desde la factory modernizada
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("Iniciando MUROTECH SaaS Backend...")
    print(f"URL: http://localhost:{port}")
    print("Asegurate de configurar SECRET_KEY y ENCRYPTION_KEY")
    print("Base de datos:", app.config.get('SQLALCHEMY_DATABASE_URI'))

    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(host=os.environ.get('HOST', '0.0.0.0'), port=port, debug=debug)