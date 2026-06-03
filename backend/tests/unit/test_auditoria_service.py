"""Tests para app/services/auditoria_service.py — registro de auditoría."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest

from app.services.auditoria_service import AuditoriaService


class TestAuditoriaServiceSanitize:
    """Tests para la sanitización de campos sensibles."""

    def test_enmascara_password(self):
        data = {'username': 'admin', 'password': 'secret123'}
        result = AuditoriaService._sanitize(data)
        assert result['password'] == '***'
        assert result['username'] == 'admin'

    def test_enmascara_api_password(self):
        data = {'api_usuario': 'user', 'api_password': 'pass123'}
        result = AuditoriaService._sanitize(data)
        assert result['api_password'] == '***'
        assert result['api_usuario'] == 'user'

    def test_enmascara_api_pin(self):
        data = {'api_pin_p12': '1234', 'api_pin': '5678'}
        result = AuditoriaService._sanitize(data)
        assert result['api_pin_p12'] == '***'
        assert result['api_pin'] == '***'

    def test_no_modifica_campos_normales(self):
        data = {'nombre': 'Empresa S.A.', 'email': 'test@test.com', 'plan_tipo': 'emisor'}
        result = AuditoriaService._sanitize(data)
        assert result == data

    def test_none_retorna_none(self):
        assert AuditoriaService._sanitize(None) is None

    def test_dict_vacio(self):
        assert AuditoriaService._sanitize({}) == {}

    def test_campos_sensibles_completos(self):
        """Verifica que todos los campos definidos como sensibles se enmascaran."""
        for field in AuditoriaService.SENSITIVE_FIELDS:
            data = {field: 'sensitive_value', 'normal_field': 'visible'}
            result = AuditoriaService._sanitize(data)
            assert result[field] == '***', f"Campo {field} no fue enmascarado"
            assert result['normal_field'] == 'visible'


class TestAuditoriaServiceLogChange:
    """Tests para el registro de cambios en auditoría (requiere app context)."""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Se ejecuta dentro del app context de Flask."""
        from app.extensions import db
        with app.app_context():
            db.create_all()
            yield

    def test_log_change_crea_registro(self, app):
        from app.extensions import db
        with app.app_context():
            result = AuditoriaService.log_change(
                usuario_id=None,
                entidad='test_entity',
                accion='CREATE',
                valores_antes={'name': 'old'},
                valores_despues={'name': 'new'},
            )
            assert result is not None
            assert result.entidad == 'test_entity'
            assert result.accion == 'CREATE'

    def test_log_change_sanitiza_valores(self, app):
        from app.extensions import db
        with app.app_context():
            result = AuditoriaService.log_change(
                usuario_id=None,
                entidad='empresa',
                accion='UPDATE',
                valores_despues={'api_password': 'secret', 'nombre': 'Test'},
            )
            assert result is not None
            assert result.valores_despues['api_password'] == '***'
            assert result.valores_despues['nombre'] == 'Test'

    def test_log_change_error_no_rompe(self, app):
        """Si hay error (ej: DB no disponible), retorna None sin romper."""
        result = AuditoriaService.log_change(
            usuario_id=None,
            entidad='test',
            accion='TEST',
        )
        # Puede ser None o un objeto, pero no debe lanzar excepción
        assert result is None or result.entidad == 'test'
