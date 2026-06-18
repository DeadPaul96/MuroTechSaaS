from datetime import datetime
import os
import secrets
from flask import Blueprint, jsonify, request
from app.models import db, Pago, Empresa, Notificacion
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

# ── Suscripciones ──────────────────────────────────────────

@bp.route('/suscripcion/iniciar', methods=['POST'])
@token_required
def iniciar_suscripcion(current_user):
    """Inicia flujo de suscripción creando orden de pago."""
    data = request.get_json(force=True, silent=True) or {}
    empresa_id = data.get('empresa_id') or getattr(current_user, 'empresa_id', None)
    plan_tipo = data.get('plan_tipo', 'basico')
    provider = data.get('provider', 'stripe')

    if not empresa_id:
        return jsonify({'message': 'empresa_id es requerido.'}), 400

    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404

    payment = create_payment_order(empresa, usuario=current_user, plan_tipo=plan_tipo, provider=provider)
    db.session.commit()

    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'amount': str(payment.amount),
        'checkout_url': payment.checkout_url,
        'plan_tipo': payment.plan_tipo
    })


@bp.route('/pagos/stripe/checkout', methods=['GET'])
@token_required
def stripe_checkout(current_user):
    """Crea sesión de checkout Stripe para suscripción."""
    empresa_id = request.args.get('empresa_id') or getattr(current_user, 'empresa_id', None)
    if not empresa_id:
        return jsonify({'message': 'empresa_id es requerido.'}), 400

    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404

    payment = create_payment_order(empresa, usuario=current_user, provider='stripe')
    db.session.commit()

    stripe_api_key = os.environ.get('STRIPE_API_KEY')
    if stripe_api_key:
        # Integración real con Stripe
        import stripe
        stripe.api_key = stripe_api_key
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': payment.currency.lower(),
                        'product_data': {'name': f'Plan {payment.plan_tipo}'},
                        'unit_amount': int(payment.amount),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.host_url + 'html/panelControl.html?payment=success',
                cancel_url=request.host_url + 'html/planes.html?payment=cancel',
                metadata={'payment_id': payment.id, 'empresa_id': empresa_id},
            )
            payment.checkout_url = session.url
            payment.provider_ref = session.id
            db.session.commit()
            return jsonify({'checkout_url': session.url, 'payment_id': payment.id})
        except Exception as e:
            payment.status = 'failed'
            db.session.commit()
            return jsonify({'message': f'Error Stripe: {str(e)}'}), 502

    # Fallback simulado si no hay API key
    checkout_url = f'https://checkout.stripe.com/pay/cs_test_{payment.id}'
    payment.checkout_url = checkout_url
    db.session.commit()
    return jsonify({'checkout_url': checkout_url, 'payment_id': payment.id, 'mode': 'test'})


@bp.route('/pagos/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Recibe webhooks de Stripe para confirmar pagos."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature', '')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

    if webhook_secret:
        import stripe
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as e:
            return jsonify({'message': f'Firma inválida: {str(e)}'}), 400

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            payment_id = session.get('metadata', {}).get('payment_id')
            if payment_id:
                payment = Pago.query.filter_by(id=payment_id).first()
                if payment and payment.status == 'pending':
                    payment.status = 'completed'
                    payment.transaction_id = session.get('payment_intent')
                    empresa = Empresa.query.filter_by(id=payment.empresa_id).first()
                    if empresa:
                        activate_empresa(empresa, motivo='Stripe checkout completado')
                    db.session.commit()
        return jsonify({'received': True})

    # Fallback: procesar payload directamente (dev/testing)
    data = request.get_json(force=True, silent=True) or {}
    payment_id = data.get('metadata', {}).get('payment_id') or data.get('payment_id')
    if payment_id:
        payment = Pago.query.filter_by(id=payment_id).first()
        if payment and payment.status == 'pending':
            payment.status = 'completed'
            empresa = Empresa.query.filter_by(id=payment.empresa_id).first()
            if empresa:
                activate_empresa(empresa, motivo='Stripe webhook')
            db.session.commit()
    return jsonify({'received': True})


@bp.route('/suscripcion/estado/<int:empresa_id>', methods=['GET'])
@token_required
def estado_suscripcion(current_user, empresa_id):
    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404
    ultimo_pago = Pago.query.filter_by(empresa_id=empresa_id).order_by(Pago.created_at.desc()).first()
    return jsonify({
        'empresa_id': empresa.id,
        'plan_tipo': empresa.plan_tipo,
        'plan_estado': empresa.plan_estado,
        'plan_cuota': empresa.plan_cuota,
        'ultimo_pago': {
            'id': ultimo_pago.id,
            'status': ultimo_pago.status,
            'amount': str(ultimo_pago.amount),
            'created_at': ultimo_pago.created_at.isoformat() if ultimo_pago.created_at else None,
        } if ultimo_pago else None,
    })


@bp.route('/suscripcion/cancelar', methods=['POST'])
@token_required
@audit_log('cancelar_suscripcion')
def cancelar_suscripcion(current_user):
    data = request.get_json(force=True, silent=True) or {}
    empresa_id = data.get('empresa_id') or getattr(current_user, 'empresa_id', None)
    if not empresa_id:
        return jsonify({'message': 'empresa_id es requerido.'}), 400
    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404
    empresa.plan_estado = 'cancelado'
    empresa.is_active = False
    db.session.commit()
    return jsonify({'message': 'Suscripción cancelada.', 'empresa_id': empresa.id})


@bp.route('/pagos/historial/<int:empresa_id>', methods=['GET'])
@token_required
def historial_pagos(current_user, empresa_id):
    pagos = Pago.query.filter_by(empresa_id=empresa_id).order_by(Pago.created_at.desc()).limit(50).all()
    return jsonify({
        'empresa_id': empresa_id,
        'pagos': [{
            'id': p.id,
            'status': p.status,
            'amount': str(p.amount),
            'provider': p.provider,
            'plan_tipo': p.plan_tipo,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        } for p in pagos]
    })


# ── PayPal ──────────────────────────────────────────────────

@bp.route('/pagos/paypal/checkout', methods=['GET'])
@token_required
def paypal_checkout(current_user):
    """Crea pago PayPal para suscripción."""
    empresa_id = request.args.get('empresa_id') or getattr(current_user, 'empresa_id', None)
    if not empresa_id:
        return jsonify({'message': 'empresa_id es requerido.'}), 400

    empresa = Empresa.query.filter_by(id=empresa_id).first()
    if not empresa:
        return jsonify({'message': 'Empresa no encontrada.'}), 404

    payment = create_payment_order(empresa, usuario=current_user, provider='paypal')
    db.session.commit()

    paypal_mode = os.environ.get('PAYPAL_MODE', 'sandbox')
    paypal_client_id = os.environ.get('PAYPAL_CLIENT_ID')
    paypal_client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')

    if paypal_client_id and paypal_client_secret:
        try:
            import paypalrestsdk
            paypalrestsdk.configure({
                'mode': paypal_mode,
                'client_id': paypal_client_id,
                'client_secret': paypal_client_secret,
            })
            paypal_payment = paypalrestsdk.Payment({
                'intent': 'sale',
                'payer': {'payment_method': 'paypal'},
                'redirect_urls': {
                    'return_url': request.host_url + 'api/pagos/paypal/execute?payment_id=' + str(payment.id),
                    'cancel_url': request.host_url + 'html/planes.html?payment=cancel',
                },
                'transactions': [{
                    'amount': {
                        'total': str(payment.amount),
                        'currency': payment.currency,
                    },
                    'description': f'Plan {payment.plan_tipo} — MUROTECH',
                }],
            })
            if paypal_payment.create():
                for link in paypal_payment.links:
                    if link.rel == 'approval_url':
                        payment.checkout_url = link.href
                        payment.provider_ref = paypal_payment.id
                        db.session.commit()
                        return jsonify({'checkout_url': link.href, 'payment_id': payment.id})
            return jsonify({'message': 'Error creando pago PayPal.'}), 502
        except Exception as e:
            return jsonify({'message': f'Error PayPal: {str(e)}'}), 502

    # Fallback simulado
    checkout_url = f'https://www.sandbox.paypal.com/checkout?paymentId=PAY-{payment.id}'
    payment.checkout_url = checkout_url
    db.session.commit()
    return jsonify({'checkout_url': checkout_url, 'payment_id': payment.id, 'mode': 'test'})


@bp.route('/pagos/paypal/execute', methods=['GET'])
@token_required
def paypal_execute(current_user):
    """Ejecuta pago PayPal después de aprobación del usuario."""
    payer_id = request.args.get('PayerID')
    paypal_payment_id = request.args.get('paymentId')
    local_payment_id = request.args.get('payment_id')

    payment = Pago.query.filter_by(id=local_payment_id).first() if local_payment_id else None
    if not payment:
        payment = Pago.query.filter_by(provider_ref=paypal_payment_id).first()

    if not payment:
        return jsonify({'message': 'Pago no encontrado.'}), 404

    if payer_id and payment.provider_ref:
        try:
            import paypalrestsdk
            paypal_payment = paypalrestsdk.Payment.find(payment.provider_ref)
            if paypal_payment.execute({'payer_id': payer_id}):
                payment.status = 'completed'
                payment.transaction_id = paypal_payment.id
                empresa = Empresa.query.filter_by(id=payment.empresa_id).first()
                if empresa:
                    activate_empresa(empresa, motivo='PayPal checkout completado')
                db.session.commit()
                return jsonify({'message': 'Pago completado vía PayPal.', 'payment_id': payment.id})
        except Exception as e:
            return jsonify({'message': f'Error ejecutando PayPal: {str(e)}'}), 502

    return jsonify({'message': 'No se pudo completar el pago PayPal.'}), 400


@bp.route('/pagos/paypal/webhook', methods=['POST'])
def paypal_webhook():
    """Recibe notificaciones webhook de PayPal."""
    data = request.get_json(force=True, silent=True) or {}
    event_type = data.get('event_type', '')
    resource = data.get('resource', {})

    if event_type == 'PAYMENT.SALE.COMPLETED':
        sale_id = resource.get('id')
        payment = Pago.query.filter_by(provider_ref=sale_id).first()
        if payment and payment.status == 'pending':
            payment.status = 'completed'
            payment.transaction_id = sale_id
            empresa = Empresa.query.filter_by(id=payment.empresa_id).first()
            if empresa:
                activate_empresa(empresa, motivo='PayPal webhook')
            db.session.commit()

    return jsonify({'received': True})
