from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)


@celery.task(name='workers.report_tasks.generate_report')
def generate_report(filters):
    return {'status': 'started', 'filters': filters}
