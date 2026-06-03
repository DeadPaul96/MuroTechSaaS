from datetime import datetime
import os
import secrets
from flask import Blueprint, jsonify, request
from app.models import db, Pago, Empresa
from app.api.decorators.auth import token_required
from app.api.decorators.audit import audit_log
from app.services.billing_plans import get_plan_info
from app.extensions import limiter

bp = Blueprint('payments', __name__, url_prefix='/api')

def create_payment_order(empresa, usuario=None, plan_tipo=None, provider='manual'):
    """Crea un objeto de pago de suscripción en estado pendiente."""
    plan_info = get_plan_info(plan_tipo or empresa.plan_tipo)
    checkout_code = secrets.token_urlsafe(16)
    payment = Pago(
        empresa_id=empresa.id,
        usuario_id=getattr(usuario, 'id', None) if usuario else None,
        plan_tipo=plan_info['type'],
        plan_cuota=plan_info['plan_cuota'],
        amount=plan_info['amount'],
        currency='CRC',
        status='pending',
        provider=provider,
        description=f'Pago de activación para plan {plan_info["label"]}',
        checkout_url=f'https://pagos.murotech.local/checkout/{checkout_code}'
    )
    db.session.add(payment)
    db.session.flush()
    return payment

def activate_empresa(empresa, motivo='Plan reactivado'):
    from app.models import Notificacion
    empresa.plan_estado = 'activo'
    empresa.is_active = True
    for usuario in empresa.usuarios:
        usuario.is_active = True
    
    notif = Notificacion(
        empresa_id=empresa.id,
        tipo='pago',
        titulo='Cuenta reactivada',
        descripcion=f'La cuenta fue reactivada: {motivo}'
    )
    db.session.add(notif)

@bp.route('/pagos/checkout', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_CHECKOUT', '10 per hour'))
def crear_checkout_pago():
    data = request.get_json(force=True, silent=True) or {}
    empresa_id = data.get('empresa_id')
    plan_tipo = data.get('plan_tipo')

    if not empresa_id:
        return jsonify({'message': 'Se requiere empresa_id para iniciar un pago.'}), 400

    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404

    payment = create_payment_order(empresa, plan_tipo=plan_tipo)
    db.session.commit()

    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'amount': str(payment.amount),
        'currency': payment.currency,
        'checkout_url': payment.checkout_url,
        'plan_tipo': payment.plan_tipo,
        'plan_cuota': payment.plan_cuota
    })

@bp.route('/pagos/confirmar', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_CONFIRM', '10 per hour'))
@audit_log('pago')
def confirmar_pago():
    data = request.get_json(force=True, silent=True) or {}
    payment_id = data.get('payment_id')

    if not payment_id:
        return jsonify({'message': 'payment_id es requerido.'}), 400

    payment = Pago.query.filter_by(id=payment_id).first()
    if not payment:
        return jsonify({'message': 'Pago no encontrado.'}), 404

    if payment.status != 'pending':
        return jsonify({'message': 'El pago ya fue procesado o no está en estado pendiente.'}), 400

    payment.status = 'completed'
    payment.provider = data.get('provider', payment.provider)
    payment.transaction_id = data.get('transaction_id')
    payment.updated_at = datetime.utcnow()

    empresa = Empresa.query.filter_by(id=payment.empresa_id).first()
    if empresa:
        empresa.plan_tipo = payment.plan_tipo
        empresa.plan_cuota = payment.plan_cuota
        empresa.plan_estado = 'activo'
        empresa.is_active = True
        activate_empresa(empresa, motivo='Pago confirmado')

    db.session.commit()

    return jsonify({
        'message': 'Pago confirmado y cuenta activada.',
        'payment_id': payment.id,
        'plan_tipo': payment.plan_tipo,
        'plan_cuota': payment.plan_cuota,
        'empresa_id': payment.empresa_id
    })

@bp.route('/pagos/estatus/<string:payment_id>', methods=['GET'])
def estado_pago(payment_id):
    payment = Pago.query.filter_by(id=payment_id).first()
    if not payment:
        return jsonify({'message': 'Pago no encontrado.'}), 404
    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'amount': str(payment.amount),
        'currency': payment.currency,
        'checkout_url': payment.checkout_url,
        'plan_tipo': payment.plan_tipo,
        'plan_cuota': payment.plan_cuota,
        'empresa_id': payment.empresa_id
    })
