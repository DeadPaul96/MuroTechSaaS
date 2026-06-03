from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)


@celery.task(name='workers.cleanup_tasks.cleanup_old_records')
def cleanup_old_records(days=30):
    return {'status': 'cleanup queued', 'days': days}
