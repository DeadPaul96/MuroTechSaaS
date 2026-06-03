import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

def _parse_float(value, default=0.0):
    """Normaliza diferentes formatos de número a float seguro."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r'[^\d\.-]', '', str(value))
    try:
        return float(cleaned) if cleaned not in ('', '.', '-', '-0') else default
    except ValueError:
        return default

def _parse_int(value, default=0):
    """Convierte un valor a entero o retorna un valor por defecto."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _parse_decimal(value, default=Decimal('0.00')):
    """Convierte una cadena numérica a Decimal con dos decimales."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = re.sub(r'[^\d\.-]', '', str(value))
        if cleaned in ('', '.', '-', '-0'):
            return default
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return default

def quantize_money(value):
    """Normaliza un Decimal financiero al formato de dos decimales."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_variacion(valor_actual, valor_anterior):
    """Calcula la variación porcentual entre dos valores"""
    if valor_anterior == 0:
        if valor_actual > 0:
            return "+100%"
        return "0%"
    
    variacion = ((valor_actual - valor_anterior) / valor_anterior) * 100
    signo = "+" if variacion >= 0 else ""
    return f"{signo}{variacion:.1f}%"
