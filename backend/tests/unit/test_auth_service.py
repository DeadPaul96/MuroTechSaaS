import pytest

import app.services.auth_service as auth_module
from app.services.auth_service import AuthService, AuthenticationError


class DummyEmpresa:
    def __init__(self):
        self.id = 'empresa-1'
        self.razon_social = 'Empresa Test'
        self.is_active = True
        self.plan_estado = 'activo'
        self.plan_tipo = 'basico'
        self.plan_cuota = 50


class DummyRol:
    def __init__(self, nombre):
        self.nombre = nombre


class DummySucursal:
    def __init__(self, sucursal_id, nombre):
        self.id = sucursal_id
        self.nombre = nombre


class DummyAcceso:
    def __init__(self, sucursal, rol):
        self.sucursal_id = sucursal.id
        self.sucursal = sucursal
        self.rol = rol


class DummyUser:
    def __init__(self, email, password):
        self.id = 'user-1'
        self.email = email
        self.nombre = 'Usuario Prueba'
        self.password = password
        self.empresa_id = 'empresa-1'
        self.is_active = True
        self.is_superadmin = False
        self.pantallas_asignadas = 'facturacion,inventario'
        self.empresa = DummyEmpresa()
        self.accesos = []

    def check_password(self, password):
        return password == self.password


class DummyQuery:
    def __init__(self, result):
        self._result = result

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._result


def test_login_invalid_credentials(app, monkeypatch):
    dummy_query = DummyQuery(None)
    monkeypatch.setattr(auth_module.Usuario, 'query', dummy_query)

    with pytest.raises(AuthenticationError):
        AuthService.login('test@test.com', 'incorrect-password')


def test_login_success_returns_token_and_accesses(app, monkeypatch):
    user = DummyUser('test@test.com', 'secret')
    sucursal = DummySucursal('sucursal-1', 'Sucursal Test')
    rol = DummyRol('Administrador')
    user.accesos = [DummyAcceso(sucursal, rol)]

    monkeypatch.setattr(auth_module.Usuario, 'query', DummyQuery(user))
    monkeypatch.setattr(auth_module.Sucursal, 'query', DummyQuery([sucursal]))

    result = AuthService.login('test@test.com', 'secret')

    assert 'token' in result
    assert result['user']['email'] == 'test@test.com'
    assert result['user']['perfil'] in ('Usuario', 'Emisor')
    assert result['accesos']
    assert result['accesos'][0]['nombre'] == 'Sucursal Test'
