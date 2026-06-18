"""Tareas asíncronas de limpieza y mantenimiento."""
import logging
from datetime import datetime, timedelta

from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)
logger = logging.getLogger(__name__)


@celery.task(name='workers.cleanup_tasks.cleanup_old_records')
def cleanup_old_records(days=30):
    """Elimina registros antiguos: tokens revocados, borradores viejos, etc."""
    from app.models import RevokedToken, Factura
    from app.extensions import db

    cutoff = datetime.utcnow() - timedelta(days=days)
    results = {}

    # Limpiar tokens revocados viejos
    revoked = RevokedToken.query.filter(RevokedToken.fecha_revocado < cutoff).delete()
    results['revoked_tokens_deleted'] = revoked

    # Limpiar borradores de facturas viejos (>7 días)
    cutoff_drafts = datetime.utcnow() - timedelta(days=7)
    drafts = Factura.query.filter(
        Factura.is_draft == True,
        Factura.fecha_emision < cutoff_drafts,
    ).delete(synchronize_session=False)
    results['old_drafts_deleted'] = drafts

    db.session.commit()

    logger.info(
        'Limpieza completada: %d tokens, %d borradores eliminados',
        revoked, drafts,
    )
    return {'status': 'completed', 'deleted': results}


@celery.task(name='workers.cleanup_tasks.cleanup_expired_sessions')
def cleanup_expired_sessions(hours=24):
    """Elimina sesiones expiradas (tokens revocados con más de N horas)."""
    from app.models import RevokedToken
    from app.extensions import db

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    deleted = RevokedToken.query.filter(RevokedToken.fecha_revocado < cutoff).delete()
    db.session.commit()

    logger.info('Sesiones expiradas limpiadas: %d eliminadas', deleted)
    return {'status': 'completed', 'deleted': deleted}
