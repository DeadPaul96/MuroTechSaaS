"""Tests de integración: autenticación completa (login → profile → logout)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
import jwt
from datetime import datetime, timezone, timedelta

from app.models import db, Empresa, Sucursal, Usuario, Rol, AccesoSucursal, RevokedToken


@pytest.fixture
def setup_data(app):
    """Crea datos de prueba: empresa, sucursal, rol, usuario."""
    with app.app_context():
        empresa = Empresa(
            razon_social='Test Corp SA',
            nombre_comercial='TestCorp',
            cedula_juridica='3101123456',
            tipo_identificacion='02',
            email_contacto='admin@test.com',
            plan_tipo='mensual',
            plan_cuota=100,
            plan_estado='activo',
            is_active=True,
            ambiente_hacienda='stag',
        )
        db.session.add(empresa)
        db.session.flush()

        sucursal = Sucursal(
            empresa_id=empresa.id,
            nombre='Sede Principal',
            numero_sucursal='001',
            terminal='00001',
            provincia='1',
            canton='01',
            distrito='01',
        )
        db.session.add(sucursal)
        db.session.flush()

        rol = Rol.query.filter_by(nombre='Administrador').first()
        if not rol:
            rol = Rol(nombre='Administrador', descripcion='Admin total')
            db.session.add(rol)
            db.session.flush()

        usuario = Usuario(
            empresa_id=empresa.id,
            nombre='Admin Test',
            email='admin@test.com',
            is_active=True,
        )
        usuario.set_password('Admin123!')
        db.session.add(usuario)
        db.session.flush()

        acceso = AccesoSucursal(
            usuario_id=usuario.id,
            sucursal_id=sucursal.id,
            rol_id=rol.id,
        )
        db.session.add(acceso)
        db.session.commit()

        return {
            'empresa_id': empresa.id,
            'sucursal_id': sucursal.id,
            'usuario_id': usuario.id,
            'email': 'admin@test.com',
            'password': 'Admin123!',
        }


class TestLoginFlow:
    """Tests del flujo de login completo."""

    def test_login_exitoso(self, client, setup_data, app):
        resp = client.post('/api/login', json={
            'email': setup_data['email'],
            'password': setup_data['password'],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['user']['email'] == 'admin@test.com'
        assert len(data['accesos']) > 0

    def test_login_password_incorrecta(self, client, setup_data):
        resp = client.post('/api/login', json={
            'email': setup_data['email'],
            'password': 'WrongPass!',
        })
        assert resp.status_code == 401

    def test_login_email_inexistente(self, client, setup_data):
        resp = client.post('/api/login', json={
            'email': 'noexist@test.com',
            'password': 'whatever',
        })
        assert resp.status_code == 401

    def test_login_campos_vacios(self, client, setup_data):
        resp = client.post('/api/login', json={})
        assert resp.status_code == 401


class TestTokenValidation:
    """Tests de validación de token JWT."""

    def _get_token(self, client, setup_data):
        resp = client.post('/api/login', json={
            'email': setup_data['email'],
            'password': setup_data['password'],
        })
        return resp.get_json()['token']

    def test_token_contiene_claims_requeridas(self, client, setup_data, app):
        token = self._get_token(client, setup_data)
        with app.app_context():
            decoded = jwt.decode(
                token,
                app.config['SECRET_KEY'],
                algorithms=['HS256'],
                audience='murotech-api',
                issuer='murotech',
            )
            assert 'exp' in decoded
            assert 'iat' in decoded
            assert 'aud' in decoded
            assert 'iss' in decoded
            assert decoded['user_id'] == setup_data['usuario_id']

    def test_token_expirado_rechazado(self, client, setup_data, app):
        with app.app_context():
            usuario = db.session.get(Usuario, setup_data['usuario_id'])
            expired_payload = {
                'user_id': usuario.id,
                'empresa_id': usuario.empresa_id,
                'exp': datetime.now(timezone.utc) - timedelta(hours=1),
                'iat': datetime.now(timezone.utc) - timedelta(hours=2),
                'aud': 'murotech-api',
                'iss': 'murotech',
            }
            expired_token = jwt.encode(expired_payload, app.config['SECRET_KEY'], algorithm='HS256')

        resp = client.get(f'/api/roles?token={expired_token}')
        assert resp.status_code == 401
        assert 'expirado' in resp.get_json().get('message', '').lower()
