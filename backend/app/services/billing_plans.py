"""Definición de planes y la carga de datos públicos de suscripciones.

Este módulo define la oferta comercial y exporta utilitarios para generar
el payload que consume el frontend.
"""
from decimal import Decimal

AVAILABLE_PLANS = {
    'basico': {'label': 'Plan Básico', 'description': 'Ideal para pequeñas empresas', 'amount': Decimal('15000'), 'plan_cuota': 50, 'periodo': 'mensual'},
    'emisor': {'label': 'Plan Emisor', 'description': 'Para empresas en crecimiento', 'amount': Decimal('35000'), 'plan_cuota': 200, 'periodo': 'mensual'},
    'premium': {'label': 'Plan Premium', 'description': 'Para grandes volúmenes', 'amount': Decimal('65000'), 'plan_cuota': 500, 'periodo': 'mensual'},
    'enterprise': {'label': 'Plan Enterprise', 'description': 'Solución personalizada', 'amount': Decimal('120000'), 'plan_cuota': 1000, 'periodo': 'mensual'},
}
PLAN_ALIASES = {'start': 'basico', 'mensual': 'basico', 'basico': 'basico', 'básico': 'basico', 'emisor': 'emisor', 'pro': 'premium', 'premium': 'premium', 'enterprise': 'enterprise'}
DEFAULT_PLAN_TYPE = 'basico'

def get_plan_info(plan_tipo):
    plan_tipo = PLAN_ALIASES.get((plan_tipo or DEFAULT_PLAN_TYPE).strip().lower(), (plan_tipo or DEFAULT_PLAN_TYPE).strip().lower())
    if plan_tipo not in AVAILABLE_PLANS:
        plan_tipo = DEFAULT_PLAN_TYPE
    p = AVAILABLE_PLANS[plan_tipo].copy()
    p['type'] = plan_tipo
    return p

def plans_public_payload():
    return [{'tipo': k, 'label': v['label'], 'description': v['description'], 'amount': str(v['amount']), 'plan_cuota': v['plan_cuota'], 'periodo': v['periodo']} for k, v in AVAILABLE_PLANS.items()]
