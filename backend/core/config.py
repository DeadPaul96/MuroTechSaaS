"""Configuración centralizada — sin credenciales en código."""
import os
from pathlib import Path


class Config:
    def __init__(self, backend_root: Path):
        self.backend_root = backend_root
        self.flask_env = os.environ.get('FLASK_ENV', 'development')
        self.is_production = self.flask_env == 'production'
        self.secret_key = os.environ.get('SECRET_KEY')
        self.encryption_key = os.environ.get('ENCRYPTION_KEY')

    def require_secrets(self):
        if not self.secret_key:
            raise RuntimeError('SECRET_KEY no definida.')
        if self.is_production and not self.encryption_key:
            raise RuntimeError('ENCRYPTION_KEY obligatoria en producción.')

    def cors_origins(self) -> list:
        raw = os.environ.get('CORS_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
        origins = [o.strip() for o in raw.split(',') if o.strip()]
        if self.is_production and (not origins or '*' in origins):
            raise RuntimeError('En producción use CORS_ORIGINS sin *.')
        return origins or ['http://localhost:8000']

    def database_uri(self) -> str:
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
            elif db_url.startswith('postgresql://'):
                db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
            return db_url
        user = os.environ.get('SUPABASE_USER')
        password = os.environ.get('SUPABASE_PASS')
        host = os.environ.get('SUPABASE_HOST')
        port = os.environ.get('SUPABASE_PORT', '5432')
        database = os.environ.get('SUPABASE_DB', 'postgres')
        if user and password and host:
            return f'postgresql+psycopg://{user}:{password}@{host}:{port}/{database}'
        if self.is_production:
            raise RuntimeError('Configure DATABASE_URL o SUPABASE_* en producción.')
        return f'sqlite:///{(self.backend_root / "murotech_saas.db").as_posix()}'

    def apply_flask(self, app):
        self.require_secrets()
        app.config['SECRET_KEY'] = self.secret_key
        app.config['ENCRYPTION_KEY'] = self.encryption_key
        app.config['SQLALCHEMY_DATABASE_URI'] = self.database_uri()
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['FLASK_ENV'] = self.flask_env
