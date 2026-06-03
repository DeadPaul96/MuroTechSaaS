"""Tests JWT — expiración y audience."""
from datetime import datetime, timedelta, timezone
import uuid

import jwt
import os
import pytest


def test_login_token_has_aud_and_exp(client, app):
    """El login debe emitir JWT con exp y aud."""
    with app.app_context():
        from app.models import db, Empresa, Usuario, Rol, AccesoSucursal, Sucursal

        emp = Empresa(
            cedula_juridica='3101999888',
            razon_social='Test SA',
            nombre_comercial='Test',
            tipo_identificacion='02',
            plan_estado='activo',
            is_active=True,
        )
        db.session.add(emp)
        db.session.flush()
        suc = Sucursal(empresa_id=emp.id, numero_sucursal='001', terminal='00001', nombre='Central')
        db.session.add(suc)
        db.session.flush()
        rol = Rol(nombre='Administrador', descripcion='Admin')
        db.session.add(rol)
        db.session.flush()
        user = Usuario(empresa_id=emp.id, nombre='Admin', email='jwt@test.com', is_active=True)
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.flush()
        db.session.add(AccesoSucursal(usuario_id=user.id, sucursal_id=suc.id, rol_id=rol.id))
        db.session.commit()

        res = client.post('/api/login', json={'email': 'jwt@test.com', 'password': 'Test1234!'})
        assert res.status_code == 200
        token = res.json['token']
        payload = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256'],
            audience='murotech-api',
        )
        assert payload['aud'] == 'murotech-api'
        assert payload['exp'] > datetime.now(timezone.utc).timestamp()


def test_invalid_token_rejected(client):
    res = client.get('/api/clientes', headers={'Authorization': 'Bearer invalid-token'})
    assert res.status_code == 401


def test_invalid_token_issuer_rejected(client, app):
    token = jwt.encode(
        {
            'user_id': 1,
            'aud': app.config['JWT_AUDIENCE'],
            'iss': 'invalid-issuer',
            'exp': datetime.utcnow() + timedelta(minutes=5),
            'iat': datetime.utcnow(),
        },
        app.config['SECRET_KEY'],
        algorithm=app.config['JWT_ALGORITHM'],
    )
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    res = client.get('/api/clientes', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 401
    assert res.json.get('message') == 'Token con emisor inválido.'


def test_invalid_origin_on_mutation_rejected(client):
    res = client.post(
        '/api/login',
        headers={'Origin': 'http://evil.com'},
        json={'email': 'test@example.com', 'password': 'invalid'},
    )
    assert res.status_code == 403
    assert res.json.get('code') == 'CSRF_ORIGIN'


def test_security_headers_present_for_api_requests(client):
    res = client.get('/api/health')
    assert res.status_code == 200
    assert res.headers.get('X-Frame-Options') == 'DENY'
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert 'Content-Security-Policy' in res.headers
    assert res.headers.get('Cache-Control') == 'no-store'


def test_csrf_token_endpoint_returns_token_for_allowed_origin(client, app):
    with app.app_context():
        from app.models import db, Empresa, Usuario, Rol, AccesoSucursal, Sucursal

        unique_suffix = uuid.uuid4().hex[:8]
        emp = Empresa(
            cedula_juridica=f'310199988{unique_suffix}',
            razon_social=f'CSRF SA {unique_suffix}',
            nombre_comercial='CSRF',
            tipo_identificacion='02',
            plan_estado='activo',
            is_active=True,
        )
        db.session.add(emp)
        db.session.flush()
        suc = Sucursal(empresa_id=emp.id, numero_sucursal='001', terminal='00001', nombre='Central')
        db.session.add(suc)
        db.session.flush()
        rol = Rol.query.filter_by(nombre='Administrador').first()
        if not rol:
            rol = Rol(nombre='Administrador', descripcion='Admin')
            db.session.add(rol)
            db.session.flush()
        user = Usuario(empresa_id=emp.id, nombre='Admin CSRF', email=f'csrf-{unique_suffix}@test.com', is_active=True)
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.flush()
        db.session.add(AccesoSucursal(usuario_id=user.id, sucursal_id=suc.id, rol_id=rol.id))
        db.session.commit()

        res = client.get('/api/csrf-token', headers={'Origin': 'http://localhost:8000'})
        assert res.status_code == 200
        assert 'csrf_token' in res.json
        assert res.json['csrf_token'] == app.config.get('CSRF_SECRET') or os.environ.get('CSRF_SECRET')


def test_audit_index_requires_authentication(client):
    res = client.get('/api/v1/auditoria')
    assert res.status_code == 401


def test_production_config_requires_redis_for_rate_limiting(monkeypatch):
    from app.config import ProductionConfig

    monkeypatch.delenv('RATELIMIT_STORAGE_URL', raising=False)
    monkeypatch.delenv('REDIS_URL', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'prod-secret-key-12345678901234567890')
    monkeypatch.setenv('ENCRYPTION_KEY', 'prod-encryption-key-12345678901234567890')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host:5432/db')

    with pytest.raises(RuntimeError, match='RATELIMIT_STORAGE_URL debe configurarse como una URL Redis en producción'):
        ProductionConfig.validate()


def test_database_url_normalizes_legacy_postgres_scheme(monkeypatch):
    from app.config import get_database_uri

    monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@host:5432/db')
    assert get_database_uri('production') == 'postgresql+psycopg://user:pass@host:5432/db'


def test_production_config_accepts_supabase_env_vars(monkeypatch):
    from app.config import ProductionConfig, get_database_uri

    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('SUPABASE_USER', 'supabase-user')
    monkeypatch.setenv('SUPABASE_PASS', 'supabase-pass')
    monkeypatch.setenv('SUPABASE_HOST', 'db.supabase.co')
    monkeypatch.setenv('SUPABASE_PORT', '5432')
    monkeypatch.setenv('SUPABASE_DB', 'postgres')
    monkeypatch.setenv('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/0')
    monkeypatch.setenv('SECRET_KEY', 'prod-secret-key-12345678901234567890')
    monkeypatch.setenv('ENCRYPTION_KEY', 'prod-encryption-key-12345678901234567890')

    assert get_database_uri('production').startswith('postgresql+psycopg://')
    ProductionConfig.validate()
