"""Servicio de notificaciones del sistema."""
import logging

from app.extensions import db
from app.models import Notificacion
from app.utils.validators import ValidationError

logger = logging.getLogger(__name__)


class NotificacionService:
    @staticmethod
    def get_notifications(empresa_id, sucursal_id=None, limit=50, unread_only=False):
        query = Notificacion.query.filter_by(empresa_id=empresa_id)
        if sucursal_id:
            query = query.filter(
                db.or_(
                    Notificacion.sucursal_id == None,
                    Notificacion.sucursal_id == sucursal_id,
                )
            )
        if unread_only:
            query = query.filter_by(leida=False)
        return query.order_by(Notificacion.fecha.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count(empresa_id):
        return Notificacion.query.filter_by(empresa_id=empresa_id, leida=False).count()

    @staticmethod
    def mark_read(empresa_id, notification_id):
        notif = Notificacion.query.filter_by(
            id=notification_id, empresa_id=empresa_id,
        ).first()
        if not notif:
            raise ValidationError('Notificación no encontrada.')
        notif.leida = True
        db.session.commit()
        return notif

    @staticmethod
    def mark_all_read(empresa_id, sucursal_id=None):
        query = Notificacion.query.filter_by(empresa_id=empresa_id, leida=False)
        if sucursal_id:
            query = query.filter(
                db.or_(
                    Notificacion.sucursal_id == None,
                    Notificacion.sucursal_id == sucursal_id,
                )
            )
        count = query.update({Notificacion.leida: True})
        db.session.commit()
        return count

    @staticmethod
    def notify(empresa_id, tipo, titulo, descripcion, sucursal_id=None, icono=None, link=None):
        """Crea una notificación y la retorna."""
        notif = Notificacion(
            empresa_id=empresa_id,
            sucursal_id=sucursal_id,
            tipo=tipo,
            icono=icono or 'fas fa-bell',
            titulo=titulo,
            descripcion=descripcion,
            link=link,
        )
        db.session.add(notif)
        db.session.commit()
        return notif
