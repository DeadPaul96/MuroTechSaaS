from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)


@celery.task(name='workers.hacienda_tasks.enviar_a_hacienda')
def enviar_a_hacienda(payload):
    return {'status': 'pendiente', 'payload': payload}
