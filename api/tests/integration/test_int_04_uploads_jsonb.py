# -*- coding: utf-8 -*-
"""INT-04: upload de evidencias y persistencia JSONB."""
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from api.models import Appointment
from api.tests.factories import AppointmentFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32


def _upload(client, name='evidence.png', content=PNG):
    return client.post(
        '/api/upload/evidence',
        data={'image': SimpleUploadedFile(name, content, content_type='image/png')},
    )


def test_INT_04_png_valido_retorna_201(client, settings, tmp_path):
    settings.UPLOADS_STATIC_DIR = tmp_path

    response = _upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body['success'] is True
    assert body['url'].endswith('.png')
    assert list(tmp_path.glob('*.png'))


def test_INT_04_contenido_falso_retorna_400(client, settings, tmp_path):
    settings.UPLOADS_STATIC_DIR = tmp_path

    response = _upload(client, content=b'<html>no soy una imagen</html>')

    assert response.status_code == 400
    assert 'Invalid image content' in response.json()['error']


def test_INT_04_archivo_mayor_a_10mb_retorna_400(client, settings, tmp_path):
    settings.UPLOADS_STATIC_DIR = tmp_path

    with patch('api.views.upload_views.MAX_EVIDENCE_BYTES', 100):
        response = _upload(client, content=PNG + b'\x00' * 200)

    assert response.status_code == 400
    assert 'too large' in response.json()['error']


def test_INT_04_evidence_photos_se_lee_como_lista(customer, technician, service):
    url = '/static/uploads/evidence/evidencia.png'
    appointment = AppointmentFactory(
        user=customer,
        technician=technician,
        service=service,
        evidence_photos=[url],
    )

    appointment.refresh_from_db()
    assert appointment.evidence_photos == [url]

    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'appointments'
                  AND column_name = 'evidence_photos'
                """
            )
            assert cursor.fetchone()[0] == 'jsonb'
