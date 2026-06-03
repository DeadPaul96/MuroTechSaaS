"""Configuración de seguridad (CORS, secretos)."""
import os
from pathlib import Path

import pytest

from core.config import Config


def test_cors_development_defaults():
    cfg = Config(Path('.'))
    cfg.flask_env = 'development'
    origins = cfg.cors_origins()
    assert origins
    assert '*' not in origins


def test_cors_production_rejects_wildcard(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('CORS_ORIGINS', '*')
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    monkeypatch.setenv('ENCRYPTION_KEY', 'y' * 32)
    cfg = Config(Path('.'))
    cfg.flask_env = 'production'
    cfg.is_production = True
    with pytest.raises(RuntimeError, match='CORS_ORIGINS'):
        cfg.cors_origins()


def test_require_secrets_production(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    cfg = Config(Path('.'))
    cfg.flask_env = 'production'
    cfg.is_production = True
    cfg.secret_key = None
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        cfg.require_secrets()
