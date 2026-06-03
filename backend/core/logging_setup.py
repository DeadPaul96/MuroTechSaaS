"""Logging centralizado y captura de errores opcional con Sentry."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(app=None):
    level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    log_file = os.environ.get('LOG_FILE')
    if log_file:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding='utf-8')
        fh.setFormatter(fmt)
        root.addHandler(fh)
    dsn = os.environ.get('SENTRY_DSN')
    if dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(dsn=dsn, integrations=[FlaskIntegration()], environment=os.environ.get('FLASK_ENV', 'development'))
        except ImportError:
            logging.warning('sentry-sdk no instalado')
    if app:
        from flask import request
        @app.after_request
        def _log_api(response):
            if request.path.startswith('/api/'):
                logging.getLogger('murotech.api').info('%s %s %s', request.method, request.path, response.status_code)
            return response
    return root
