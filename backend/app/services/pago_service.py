"""Servicio de gestión de pagos y suscripciones."""
import logging

from app.extensions import db
from app.models import Pago, Empresa, Notificacion
from app.utils.validators import ValidationError
from app.services.billing_plans import get_plan_info

logger = logging.getLogger(__name__)


class PagoService:
    @staticmethod
    def list_payments(empresa_id, status=None, limit=50):
        query = Pago.query.filter_by(empresa_id=empresa_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(Pago.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_payment(payment_id):
        return Pago.query.filter_by(id=payment_id).first()

    @staticmethod
    def confirm_payment(payment_id, provider=None, transaction_id=None):
        payment = PagoService.get_payment(payment_id)
        if not payment:
            raise ValidationError('Pago no encontrado.')

        if payment.status != 'pending':
            raise ValidationError('El pago ya fue procesado o no está en estado pendiente.')

        payment.status = 'completed'
        if provider:
            payment.provider = provider
        if transaction_id:
            payment.transaction_id = transaction_id

        empresa = Empresa.query.get(payment.empresa_id)
        if empresa:
            empresa.plan_tipo = payment.plan_tipo
            empresa.plan_cuota = payment.plan_cuota
            empresa.plan_estado = 'activo'
            empresa.is_active = True
            for usuario in empresa.usuarios:
                usuario.is_active = True

            notif = Notificacion(
                empresa_id=empresa.id,
                tipo='pago',
                titulo='Cuenta reactivada',
                descripcion='La cuenta fue reactivada: Pago confirmado',
            )
            db.session.add(notif)

        db.session.commit()
        logger.info('Pago %s confirmado para empresa %s', payment_id, payment.empresa_id)
        return payment

    @staticmethod
    def reject_payment(payment_id, motivo='Pago rechazado'):
        payment = PagoService.get_payment(payment_id)
        if not payment:
            raise ValidationError('Pago no encontrado.')

        payment.status = 'rejected'
        db.session.commit()
        logger.info('Pago %s rechazado', payment_id)
        return payment
