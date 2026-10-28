# -*- coding: utf-8 -*-
"""Pruebas unitarias de los helpers de correo."""
import smtplib
from unittest.mock import MagicMock, patch

import pytest
from django.template import TemplateDoesNotExist
from django.test import override_settings

from api.utils.email_utils import (
    _render_template,
    _send_email_worker,
    send_template_email,
)

pytestmark = pytest.mark.unit


@override_settings()
def test_render_template_existente():
    with patch('api.utils.email_utils.render_to_string', return_value='<p>Hola</p>'):
        assert _render_template('bienvenida', {'name': 'Ana'}) == '<p>Hola</p>'


def test_render_template_inexistente_retorna_none():
    with patch(
        'api.utils.email_utils.render_to_string',
        side_effect=TemplateDoesNotExist('no existe'),
    ):
        assert _render_template('no-existe', {}) is None


def test_render_template_con_error_retorna_none():
    with patch(
        'api.utils.email_utils.render_to_string',
        side_effect=RuntimeError('error'),
    ):
        assert _render_template('roto', {}) is None


@override_settings(MAIL_USERNAME='', MAIL_PASSWORD='')
def test_send_worker_sin_credenciales_retorna_false():
    assert _send_email_worker('a@example.com', 'Asunto', 'bienvenida', {}) is False


@override_settings(
    MAIL_USERNAME='plomapp@example.com',
    MAIL_PASSWORD='secret',
    MAIL_SERVER='smtp.example.com',
    MAIL_PORT=587,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=False,
    EMAIL_TIMEOUT=10,
)
def test_send_worker_envia_correo_sin_ssl_ni_tls():
    server = MagicMock()
    with patch('api.utils.email_utils.smtplib.SMTP', return_value=server):
        result = _send_email_worker(
            ['a@example.com', 'b@example.com'],
            'Asunto',
            'bienvenida',
            {'text_body': 'Hola'},
        )

    assert result is True
    server.login.assert_called_once_with('plomapp@example.com', 'secret')
    server.sendmail.assert_called_once()
    server.quit.assert_called_once()


@override_settings(
    MAIL_USERNAME='plomapp@example.com',
    MAIL_PASSWORD='secret',
    MAIL_SERVER='smtp.example.com',
    MAIL_PORT=587,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=True,
    EMAIL_TIMEOUT=10,
)
def test_send_worker_inicia_tls():
    server = MagicMock()
    with patch('api.utils.email_utils.smtplib.SMTP', return_value=server):
        result = _send_email_worker('a@example.com', 'Asunto', 'bienvenida', {})

    assert result is True
    server.starttls.assert_called_once()


@override_settings(
    MAIL_USERNAME='plomapp@example.com',
    MAIL_PASSWORD='secret',
    MAIL_SERVER='smtp.example.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USE_TLS=False,
    EMAIL_TIMEOUT=10,
)
def test_send_worker_usa_ssl():
    server = MagicMock()
    with patch('api.utils.email_utils.smtplib.SMTP_SSL', return_value=server):
        result = _send_email_worker('a@example.com', 'Asunto', 'bienvenida', {})

    assert result is True
    server.login.assert_called_once()


@override_settings(
    MAIL_USERNAME='plomapp@example.com',
    MAIL_PASSWORD='secret',
    MAIL_SERVER='smtp.example.com',
    MAIL_PORT=587,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=False,
    EMAIL_TIMEOUT=10,
)
def test_send_worker_maneja_bloqueo_de_zoho():
    server = MagicMock()
    server.sendmail.side_effect = smtplib.SMTPDataError(
        550, b'Unusual sending activity detected'
    )
    with patch('api.utils.email_utils.smtplib.SMTP', return_value=server):
        result = _send_email_worker('a@example.com', 'Asunto', 'bienvenida', {})

    assert result is False


@override_settings(
    MAIL_USERNAME='plomapp@example.com',
    MAIL_PASSWORD='secret',
    MAIL_SERVER='smtp.example.com',
    MAIL_PORT=587,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=False,
    EMAIL_TIMEOUT=10,
)
def test_send_worker_maneja_error_smtp_generico():
    server = MagicMock()
    server.sendmail.side_effect = smtplib.SMTPDataError(500, b'otro error')
    with patch('api.utils.email_utils.smtplib.SMTP', return_value=server):
        result = _send_email_worker('a@example.com', 'Asunto', 'bienvenida', {})

    assert result is False


@override_settings(
    MAIL_USERNAME='plomapp@example.com',
    MAIL_PASSWORD='secret',
    MAIL_SERVER='smtp.example.com',
    MAIL_PORT=587,
    MAIL_USE_SSL=False,
    MAIL_USE_TLS=False,
    EMAIL_TIMEOUT=10,
)
def test_send_worker_maneja_excepcion_generica():
    with patch('api.utils.email_utils.smtplib.SMTP', side_effect=OSError('sin red')):
        result = _send_email_worker('a@example.com', 'Asunto', 'bienvenida', {})

    assert result is False


def test_send_template_email_sin_destinatario_retorna_false():
    assert send_template_email('', 'Asunto', 'bienvenida') is False


def test_send_template_email_asincrono_retorna_true():
    thread = MagicMock()
    with patch('api.utils.email_utils.threading.Thread', return_value=thread) as thread_cls:
        result = send_template_email('a@example.com', 'Asunto', 'bienvenida')

    assert result is True
    thread_cls.assert_called_once()
    thread.start.assert_called_once()


def test_send_template_email_sincrono_llama_worker():
    with patch('api.utils.email_utils._send_email_worker', return_value=True) as worker:
        result = send_template_email(
            'a@example.com', 'Asunto', 'bienvenida', {'x': 1}, async_send=False
        )

    assert result is True
    worker.assert_called_once_with(
        'a@example.com', 'Asunto', 'bienvenida', {'x': 1}
    )
