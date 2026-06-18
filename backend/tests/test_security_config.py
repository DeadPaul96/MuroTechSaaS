"""Configuración de seguridad (CORS, secretos)."""
import os

import pytest

from app.config import Config, ProductionConfig


def test_cors_development_defaults():
    origins = Config.cors_origins()
    assert origins
    assert '*' not in origins


def test_cors_production_rejects_wildcard(monkeypatch):
    monkeypatch.setenv('CORS_ORIGINS', '*')
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    monkeypatch.setenv('ENCRYPTION_KEY', 'y' * 32)
    with pytest.raises(RuntimeError, match='CORS_ORIGINS'):
        ProductionConfig.cors_origins()


def test_require_secrets_production(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'production')
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        ProductionConfig.validate()


def test_production_requires_redis(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'a' * 32)
    monkeypatch.setenv('ENCRYPTION_KEY', 'b' * 32)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://localhost/test')
    monkeypatch.delenv('RATELIMIT_STORAGE_URL', raising=False)
    monkeypatch.delenv('REDIS_URL', raising=False)
    with pytest.raises(RuntimeError, match='RATELIMIT_STORAGE_URL'):
        ProductionConfig.validate()
