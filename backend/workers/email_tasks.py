from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)


@celery.task(name='workers.email_tasks.send_email')
def send_email(payload):
    return {'status': 'queued', 'payload': payload}
