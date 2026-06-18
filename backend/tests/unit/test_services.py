"""Tests para app/services/billing_plans.py y validators."""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest

from app.services.billing_plans import get_plan_info, plans_public_payload, DEFAULT_PLAN_TYPE, AVAILABLE_PLANS
from app.utils.validators import (
    validar_consecutivo, validar_clave, validar_cabys,
    validar_email, validar_identificacion, ValidationError,
    validar_monto, validar_porcentaje,
)
from app.utils.money import _parse_float, _parse_int, _parse_decimal, quantize_money


class TestBillingPlans:
    """Tests para el sistema de planes."""

    def test_get_plan_info_basico(self):
        info = get_plan_info('basico')
        assert info['type'] == 'basico'
        assert info['label'] == 'Plan Básico'
        assert info['amount'] == Decimal('15000')
        assert info['plan_cuota'] == 50

    def test_get_plan_info_alias(self):
        info = get_plan_info('start')
        assert info['type'] == 'basico'

    def test_get_plan_info_invalido_default(self):
        info = get_plan_info('no_existe')
        assert info['type'] == DEFAULT_PLAN_TYPE

    def test_get_plan_info_none_default(self):
        info = get_plan_info(None)
        assert info['type'] == DEFAULT_PLAN_TYPE

    def test_plans_public_payload(self):
        payload = plans_public_payload()
        assert len(payload) == len(AVAILABLE_PLANS)
        assert all('tipo' in p for p in payload)
        assert all('amount' in p for p in payload)
        assert all(isinstance(p['amount'], str) for p in payload)

    def test_todos_planes_tienen_cuota(self):
        for key, plan in AVAILABLE_PLANS.items():
            assert plan['plan_cuota'] > 0, f"Plan {key} debe tener cuota > 0"
            assert plan['amount'] > 0, f"Plan {key} debe tener monto > 0"


class TestValidators:
    """Tests para validators."""

    def test_validar_consecutivo_valido(self):
        assert validar_consecutivo('00100001010000000001') == '00100001010000000001'

    def test_validar_consecuito_corto(self):
        with pytest.raises(ValidationError):
            validar_consecutivo('123')

    def test_validar_clave_valida(self):
        clave = '5' * 50
        assert validar_clave(clave) == clave

    def test_validar_clave_corta(self):
        with pytest.raises(ValidationError):
            validar_clave('123')

    def test_validar_cabys_valido(self):
        assert validar_cabys('0000000000000') == '0000000000000'

    def test_validar_cabys_none(self):
        assert validar_cabys(None) is None

    def test_validar_email_valido(self):
        assert validar_email('Test@Test.com') == 'test@test.com'

    def test_validar_email_invalido(self):
        with pytest.raises(ValidationError):
            validar_email('not-an-email')

    def test_validar_identificacion_juridica(self):
        assert validar_identificacion('02', '3101123456') == '3101123456'

    def test_validar_identificacion_tipo_invalido(self):
        with pytest.raises(ValidationError):
            validar_identificacion('99', '12345')

    def test_validar_monto_valido(self):
        assert validar_monto(100.50) == Decimal('100.50')

    def test_validar_monto_negativo(self):
        with pytest.raises(ValidationError):
            validar_monto(-100)

    def test_validar_porcentaje_valido(self):
        assert validar_porcentaje(13) == Decimal('13')

    def test_validar_porcentaje_fuera_rango(self):
        with pytest.raises(ValidationError):
            validar_porcentaje(150)


class TestMoneyUtils:
    """Tests para utils/money.py."""

    def test_parse_float_none(self):
        assert _parse_float(None) == 0.0

    def test_parse_float_string(self):
        assert _parse_float('1.500,50') == 1500.50 or _parse_float('1.500,50') == 1.50

    def test_parse_int_none(self):
        assert _parse_int(None) == 0

    def test_parse_int_valid(self):
        assert _parse_int('42') == 42

    def test_parse_decimal_none(self):
        assert _parse_decimal(None) == Decimal('0.00')

    def test_parse_decimal_valid(self):
        assert _parse_decimal('100.50') == Decimal('100.50')

    def test_quantize_money_rounds(self):
        assert quantize_money(Decimal('10.005')) == Decimal('10.01')

    def test_quantize_money_from_float(self):
        result = quantize_money(15.5)
        assert isinstance(result, Decimal)
        assert result == Decimal('15.50')
