import os
from pathlib import Path

# Base backend directory path
BACKEND_ROOT = Path(__file__).resolve().parents[1]

def normalize_database_url(url):
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+psycopg://', 1)
    if url.startswith('postgresql://'):
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url


def get_database_uri(env):
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return normalize_database_url(db_url)

    user = os.environ.get('SUPABASE_USER')
    password = os.environ.get('SUPABASE_PASS')
    host = os.environ.get('SUPABASE_HOST')
    port = os.environ.get('SUPABASE_PORT', '5432')
    database = os.environ.get('SUPABASE_DB', 'postgres')
    if user and password and host:
        return f'postgresql+psycopg://{user}:{password}@{host}:{port}/{database}'

    if env == 'production':
        return None
    if env == 'testing':
        return 'sqlite:///:memory:'
    return f'sqlite:///{(BACKEND_ROOT / "murotech_saas.db").as_posix()}'

class Config:
    """Base Configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key')
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
    JWT_AUDIENCE = os.environ.get('JWT_AUDIENCE', 'murotech-api')
    JWT_ISSUER = os.environ.get('JWT_ISSUER', 'murotech')
    JWT_EXPIRY = int(os.environ.get('JWT_EXPIRY', '3600'))  # seconds
    JWT_LEEWAY = int(os.environ.get('JWT_LEEWAY', '30'))

    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/2')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/3')
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'

    @classmethod
    def cors_origins(cls):
        raw = os.environ.get('CORS_ORIGINS', 'http://localhost:5001,http://127.0.0.1:5001')
        origins = [o.strip() for o in raw.split(',') if o.strip()]
        # Simple verification
        if os.environ.get('FLASK_ENV') == 'production' and (not origins or '*' in origins):
            raise RuntimeError('In production, CORS_ORIGINS must not contain *.')
        return origins or ['http://localhost:5001']

    @staticmethod
    def get_config(env=None):
        if not env:
            env = os.environ.get('FLASK_ENV', 'development')
        env = env.lower()
        if env in ('production', 'prod'):
            return ProductionConfig
        elif env in ('testing', 'test'):
            return TestingConfig
        return DevelopmentConfig

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_database_uri('development')

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_database_uri('testing')
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_database_uri('production')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('SQLALCHEMY_POOL_SIZE', '10')),
        'max_overflow': int(os.environ.get('SQLALCHEMY_MAX_OVERFLOW', '20')),
        'pool_timeout': int(os.environ.get('SQLALCHEMY_POOL_TIMEOUT', '30')),
        'pool_pre_ping': True,
    }

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'default-dev-secret-key':
            raise RuntimeError('SECRET_KEY must be configured in production')
        if not cls.ENCRYPTION_KEY:
            raise RuntimeError('ENCRYPTION_KEY must be configured in production')
        if not get_database_uri('production'):
            raise RuntimeError('DATABASE_URL o SUPABASE_* deben configurarse en producción')
        ratelimit_uri = os.environ.get('RATELIMIT_STORAGE_URL') or os.environ.get('REDIS_URL')
        if not ratelimit_uri or not ratelimit_uri.startswith(('redis://', 'rediss://')):
            raise RuntimeError('RATELIMIT_STORAGE_URL debe configurarse como una URL Redis en producción')
