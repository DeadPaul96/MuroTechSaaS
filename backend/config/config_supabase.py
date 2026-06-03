# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS - SUPABASE
# ==========================================
# Este archivo contiene la configuración para conectar a Supabase
# NO incluir en control de versiones por seguridad

import os

# Credenciales de Supabase (Production)
# Estas variables pueden ser sobreescritas por variables de entorno

SUPABASE_CONFIG = {
    'host': os.environ.get('SUPABASE_HOST', 'aws-1-us-east-1.pooler.supabase.com'),
    'port': os.environ.get('SUPABASE_PORT', '5432'),
    'database': os.environ.get('SUPABASE_DB', 'postgres'),
    'user': os.environ.get('SUPABASE_USER', 'postgres.zglpwtytytqrwfsqcbxa'),
    'password': os.environ.get('SUPABASE_PASS'),
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800
}

# Construir URL de conexión para SQLAlchemy
def get_database_url():
    user = SUPABASE_CONFIG['user']
    password = SUPABASE_CONFIG['password']
    host = SUPABASE_CONFIG['host']
    port = SUPABASE_CONFIG['port']
    database = SUPABASE_CONFIG['database']
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"

# Clave de encriptación para certificados (cambiar en producción!)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'tu-clave-de-encriptacion-aqui-32-caracteres!')

# Configuración JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'murotech-jwt-secret-key-2026-produccion!')
JWT_EXPIRATION_HOURS = 12
JWT_ALGORITHM = "HS256"

# Configuración de Firma Digital
FIRMA_DIGITAL_PIN_DEFAULT = "1234"

# Configuración SMTP (para envío de comprobantes)
SMTP_CONFIG = {
    'server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
    'port': int(os.environ.get('SMTP_PORT', 587)),
    'sender': os.environ.get('SMTP_SENDER', 'soporte@murotech.com'),
    'password': os.environ.get('SMTP_PASSWORD', '')
}

# API de Hacienda
HACIENDA_API = {
    'base_url': 'https://api.hacienda.go.cr',
    'indicadores': '/indicadores/tc',
    'timeout': 30
}

# Configuración de la aplicación
APP_CONFIG = {
    'debug': os.environ.get('APP_DEBUG', 'False').lower() == 'true',
    'secret_key': os.environ.get('APP_SECRET_KEY', 'murotech-secret-key-2026'),
    'max_content_length': 16 * 1024 * 1024,  # 16MB max
}