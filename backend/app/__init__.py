import os
from pathlib import Path

from flask import Flask, send_from_directory

from .config import Config
from .extensions import db, migrate, limiter, cors
from .middleware import setup_middleware
from .error_handlers import register_error_handlers
from .api.blueprints import register_blueprints

# Ruta al frontend (../frontend relativo a backend/app)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / 'frontend'


def create_app(config_name=None):
    """Crea la aplicación Flask usando el patrón factory.

    En desarrollo sirve también los archivos estáticos del frontend
    desde ``../frontend``, de modo que un único servidor en el puerto 5001
    atiende tanto la API como la interfaz web.
    """
    env = config_name or os.environ.get('FLASK_ENV', 'development')
    config_class = Config.get_config(env)

    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path='',
    )
    app.config.from_object(config_class)
    app.config['FLASK_ENV'] = env
    app.config['CORS_ORIGINS'] = config_class.cors_origins()

    if env.lower() in ('production', 'prod') and hasattr(config_class, 'validate'):
        config_class.validate()

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    cors.init_app(app, resources={r'/api/*': {'origins': config_class.cors_origins()}})

    setup_middleware(app)
    register_error_handlers(app)
    register_blueprints(app)

    # ── Rutas para servir el frontend ──────────────────────────
    @app.route('/')
    def serve_index():
        return send_from_directory(str(FRONTEND_DIR), 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        """Sirve archivos estáticos del frontend.
        Si la ruta no coincide con un archivo real (ej. rutas SPA),
        devuelve index.html para que el cliente pueda navegar.
        """
        file_path = FRONTEND_DIR / path
        if file_path.is_file():
            return send_from_directory(str(FRONTEND_DIR), path)
        # Fallback para rutas no encontradas
        return send_from_directory(str(FRONTEND_DIR), 'index.html')

    if env.lower() in ('testing', 'development'):
        with app.app_context():
            db.create_all()

    return app
