"""
Email helpers - direct port of app/utils/email_utils.py (Flask version).

Sends multipart (plain + HTML) emails over SMTP with the same env config
(MAIL_SERVER / MAIL_PORT / MAIL_USE_SSL / MAIL_USE_TLS / MAIL_USERNAME /
MAIL_PASSWORD), rendering templates from api/templates/emails/<name>.html.
Falls back to a plain <p> body when the template cannot be rendered.
Sends asynchronously in a daemon thread by default (async_send=True).
"""
import logging
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from django.conf import settings
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist

logger = logging.getLogger('api.email')


def _render_template(template_name, context):
    try:
        return render_to_string(f'emails/{template_name}.html', context or {})
    except TemplateDoesNotExist:
        # Built-in fallback used by the Flask version as well
        return None
    except Exception as te:  # render error -> fallback
        logger.warning('Template render failed (%s), using fallback text', te)
        return None


def _send_email_worker(to, subject, template_name, context):
    context = context or {}

    html_body = _render_template(template_name, context)
    if html_body is None:
        text_val = context.get('text_body', subject)
        html_body = f'<p>{text_val}</p>'

    sender = settings.MAIL_USERNAME
    password = settings.MAIL_PASSWORD
    if not sender or not password:
        logger.warning('Mail credentials are not configured; skipping email send.')
        return False

    recipients = [to] if isinstance(to, str) else list(to)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'PlomApp <{sender}>'
    msg['To'] = ', '.join(recipients)
    msg['Reply-To'] = sender
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='zohomail.com')

    text_body = context.get('text_body') or 'Gracias por usar PlomApp.'
    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        mail_server = settings.MAIL_SERVER
        mail_port = settings.MAIL_PORT
        mail_use_ssl = settings.MAIL_USE_SSL
        mail_use_tls = settings.MAIL_USE_TLS

        if mail_use_ssl:
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=settings.EMAIL_TIMEOUT)
        else:
            server = smtplib.SMTP(mail_server, mail_port, timeout=settings.EMAIL_TIMEOUT)
            if mail_use_tls:
                server.starttls()

        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
        logger.info('Email sent successfully to %s: %s', recipients, subject)
        return True
    except smtplib.SMTPDataError as exc:
        if exc.smtp_code == 550 and b'Unusual sending activity' in getattr(exc, 'smtp_error', b''):
            logger.error(
                'ZOHO BLOQUEADO POR ACTIVIDAD PREVIA: Desbloquear en '
                'https://mail.zoho.com/UnblockMe para restaurar envíos.'
            )
        else:
            logger.error('SMTPDataError sending email: %s', exc)
        return False
    except Exception as exc:
        logger.error('Error sending email to %s: %s', recipients, exc)
        return False


def send_template_email(to, subject, template_name, context=None, async_send=True):
    if not to:
        return False

    context = context or {}

    if async_send:
        thread = threading.Thread(
            target=_send_email_worker,
            args=(to, subject, template_name, context),
        )
        thread.daemon = True
        thread.start()
        return True
    return _send_email_worker(to, subject, template_name, context)
