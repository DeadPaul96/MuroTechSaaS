"""Tareas asíncronas para envío de correos electrónicos."""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app import create_app
from .celery_app import create_celery

app = create_app()
celery = create_celery(app)
logger = logging.getLogger(__name__)


@celery.task(
    name='workers.email_tasks.send_email',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_email(self, payload):
    """Envía un correo electrónico de forma asíncrona."""
    destinatario = payload.get('to')
    asunto = payload.get('subject', 'MUROTECH')
    cuerpo_html = payload.get('html', '')
    cuerpo_texto = payload.get('text', '')

    if not destinatario:
        return {'status': 'error', 'message': 'Destinatario no especificado'}

    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_user or not smtp_pass:
        logger.warning('SMTP no configurado, no se envió correo a %s', destinatario)
        return {'status': 'skipped', 'reason': 'SMTP not configured'}

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f'MUROTECH <{smtp_user}>'
        msg['To'] = destinatario
        msg['Subject'] = asunto

        if cuerpo_texto:
            msg.attach(MIMEText(cuerpo_texto, 'plain'))
        if cuerpo_html:
            msg.attach(MIMEText(cuerpo_html, 'html'))

        # Adjuntos
        for adjunto in payload.get('attachments', []):
            part = MIMEBase('application', adjunto.get('mime', 'octet-stream'))
            part.set_payload(adjunto.get('data', b''))
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{adjunto.get("filename", "adjunto")}"',
            )
            msg.attach(part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, destinatario, msg.as_string())

        logger.info('Correo enviado a %s', destinatario)
        return {'status': 'sent', 'to': destinatario}

    except smtplib.SMTPException as err:
        logger.warning('Error SMTP enviando a %s: %s', destinatario, err)
        try:
            self.retry(exc=err)
        except self.MaxRetriesExceededError:
            return {'status': 'error', 'message': str(err)}

    except Exception as err:
        logger.error('Error inesperado enviando correo a %s: %s', destinatario, err)
        return {'status': 'error', 'message': str(err)}
