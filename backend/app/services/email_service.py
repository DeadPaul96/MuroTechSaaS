"""Servicio de envío de correos electrónicos."""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str = '',
    attachments: Optional[list] = None,
    cc: Optional[list] = None,
) -> bool:
    """Envía un correo electrónico vía SMTP configurado."""
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    smtp_from = os.environ.get('SMTP_FROM', smtp_user)
    smtp_tls = os.environ.get('SMTP_TLS', 'true').lower() in ('true', '1', 'yes')

    if not smtp_user or not smtp_password:
        logger.warning('SMTP no configurado. Email a %s no enviado.', to)
        return False

    msg = MIMEMultipart('alternative')
    msg['From'] = smtp_from
    msg['To'] = to
    msg['Subject'] = subject
    if cc:
        msg['Cc'] = ', '.join(cc)

    if body_text:
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    if attachments:
        for att in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(att.get('data', b''))
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{att.get("filename", "file")}"')
            msg.attach(part)

    try:
        if smtp_tls:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        server.ehlo()
        server.login(smtp_user, smtp_password)
        recipients = [to] + (cc or [])
        server.sendmail(smtp_from, recipients, msg.as_string())
        server.quit()
        logger.info('Email enviado a %s: %s', to, subject)
        return True
    except Exception as e:
        logger.error('Error enviando email a %s: %s', to, e)
        return False


def send_comprobante_email(to_email: str, clave: str, tipo: str, xml_bytes: bytes = None, empresa_nombre: str = 'MUROTECH') -> bool:
    """Envía comprobante electrónico por email al cliente."""
    subject = f'Comprobante Electrónico {tipo} — {clave[:20]}...'
    body_html = f'''
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #1e40af; color: white; padding: 20px; text-align: center;">
        <h1>{empresa_nombre}</h1>
    </div>
    <div style="padding: 20px;">
        <h2>Comprobante Electrónico</h2>
        <p>Tipo: <strong>{tipo}</strong></p>
        <p>Clave: <strong>{clave}</strong></p>
        <p>Adjunto encontrará el comprobante electrónico en formato XML.</p>
        <p>Este comprobante fue emitido de acuerdo con la normativa del Ministerio de Hacienda de Costa Rica.</p>
    </div>
    <div style="background: #f3f4f6; padding: 10px; text-align: center; font-size: 12px;">
        Generado por MUROTECH SaaS — Facturación Electrónica Costa Rica
    </div>
    </body></html>
    '''
    attachments = []
    if xml_bytes:
        attachments.append({'filename': f'{clave}.xml', 'data': xml_bytes})
    return send_email(to=to_email, subject=subject, body_html=body_html, attachments=attachments)
