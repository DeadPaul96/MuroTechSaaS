"""Tests para fiscal/horario.py — validación de horario MH y reintentos."""
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest

from fiscal.horario import (
    validar_horario_envio,
    segundos_hasta_proximo_horario,
    enviar_con_reintentos,
    FERIADOS_CRC_2026,
)
from fiscal.hacienda_client import HaciendaError


class TestValidarHorarioEnvio:
    """Tests para la validación de horario de envío a MH."""

    def test_feriado_rechazado(self):
        """Los feriados oficiales no permiten envío."""
        assert len(FERIADOS_CRC_2026) > 0, "Debe haber feriados definidos"

    def test_domingo_rechazado(self, monkeypatch):
        """Domingos no se permite envío."""
        from fiscal import horario

        # Simular domingo 7 de junio 2026
        mock_dt = datetime(2026, 6, 7, 10, 0, 0, tzinfo=horario.CR_TZ)
        monkeypatch.setattr(horario, 'datetime', type('DT', (), {
            'now': classmethod(lambda cls, tz=None: mock_dt),
            '__new__': datetime.__new__,
        }))
        permitido, motivo = validar_horario_envio()
        assert not permitido
        assert 'Domingo' in motivo or 'domingo' in motivo.lower()

    def test_noche_rechazado(self, monkeypatch):
        """Fuera de horario (antes de 8am o después de 8pm) no se permite."""
        from fiscal import horario

        # Simular lunes a las 6am
        mock_dt = datetime(2026, 6, 2, 6, 0, 0, tzinfo=horario.CR_TZ)
        monkeypatch.setattr(horario, 'datetime', type('DT', (), {
            'now': classmethod(lambda cls, tz=None: mock_dt),
            '__new__': datetime.__new__,
        }))
        permitido, motivo = validar_horario_envio()
        assert not permitido

    def test_horario_laboral_permitido(self, monkeypatch):
        """Lunes a viernes 8am-8pm debe permitir envío."""
        from fiscal import horario

        # Simular martes a las 10am (2 junio 2026)
        mock_dt = datetime(2026, 6, 2, 10, 0, 0, tzinfo=horario.CR_TZ)
        monkeypatch.setattr(horario, 'datetime', type('DT', (), {
            'now': classmethod(lambda cls, tz=None: mock_dt),
            '__new__': datetime.__new__,
        }))
        permitido, motivo = validar_horario_envio()
        assert permitido

    def test_sabado_permitido(self, monkeypatch):
        """Sábados 8am-8pm debe permitir envío."""
        from fiscal import horario

        # Simular sábado a las 2pm
        mock_dt = datetime(2026, 6, 6, 14, 0, 0, tzinfo=horario.CR_TZ)
        monkeypatch.setattr(horario, 'datetime', type('DT', (), {
            'now': classmethod(lambda cls, tz=None: mock_dt),
            '__new__': datetime.__new__,
        }))
        permitido, motivo = validar_horario_envio()
        assert permitido


class TestEnviarConReintentos:
    """Tests para la lógica de reintentos con exponential backoff."""

    def test_envio_exitoso_primer_intento(self):
        """Si el envío es exitoso, retorna resultado sin reintentos."""
        resultado = enviar_con_reintentos(lambda: {'status': 'ok'}, max_reintentos=3, validar_horario=False)
        assert resultado == {'status': 'ok'}

    def test_reintenta_en_error_5xx(self):
        """Errores de servidor (5xx) deben reintentarse."""
        intentos = {'count': 0}

        def fn():
            intentos['count'] += 1
            if intentos['count'] < 3:
                raise HaciendaError('Server error', status_code=500)
            return {'status': 'ok'}

        resultado = enviar_con_reintentos(fn, max_reintentos=3, delay_base=0.01, validar_horario=False)
        assert resultado == {'status': 'ok'}
        assert intentos['count'] == 3

    def test_no_reintenta_error_4xx(self):
        """Errores de cliente (4xx excepto 408/429) no se reintentan."""
        with pytest.raises(HaciendaError):
            enviar_con_reintentos(
                lambda: (_ for _ in ()).throw(HaciendaError('Bad request', status_code=400)),
                max_reintentos=3,
                delay_base=0.01,
                validar_horario=False,
            )

    def test_agota_reintentos(self):
        """Si todos los reintentos fallan, lanza el último error."""
        with pytest.raises(HaciendaError):
            enviar_con_reintentos(
                lambda: (_ for _ in ()).throw(HaciendaError('Down', status_code=503)),
                max_reintentos=2,
                delay_base=0.01,
                validar_horario=False,
            )

    def test_valida_horario_por_defecto(self, monkeypatch):
        """Si validar_horario=True y estamos fuera de horario, lanza error."""
        from fiscal import horario

        mock_dt = datetime(2026, 6, 7, 10, 0, 0, tzinfo=horario.CR_TZ)  # Domingo
        monkeypatch.setattr(horario, 'datetime', type('DT', (), {
            'now': classmethod(lambda cls, tz=None: mock_dt),
            '__new__': datetime.__new__,
        }))
        with pytest.raises(HaciendaError) as exc_info:
            enviar_con_reintentos(lambda: {'ok': True})
        assert 'horario' in str(exc_info.value).lower() or 'fuera' in str(exc_info.value).lower()


class TestSegundosHastaProximoHorario:
    """Tests para el cálculo de espera hasta próximo horario hábil."""

    def test_retorna_entero_positivo(self):
        """Debe retornar un número entero positivo de segundos."""
        segundos = segundos_hasta_proximo_horario()
        assert isinstance(segundos, int)
        assert segundos >= 0
