# -*- coding: utf-8 -*-
"""INT-02: citas, disponibilidad y prevención de doble reserva."""
import json
from datetime import date

import pytest
from django.db import connection

from api.models import Appointment
from api.utils.jwt_utils import generate_token

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _require_postgres():
    if connection.vendor != 'postgresql':
        pytest.skip('Esta prueba requiere PostgreSQL (select_for_update)')


def test_INT_02_agendar_y_rechazar_doble_reserva(client, customer, technician, service):
    _require_postgres()
    headers = {'HTTP_AUTHORIZATION': f'Bearer {generate_token(customer.id)}'}

    response = client.get(
        '/api/appointments/availability',
        {
            'service_id': service.id,
            'date': '2026-11-02',
            'technician_id': technician.id,
        },
        **headers,
    )
    assert response.status_code == 200
    slots = response.json()['slots']
    assert any(slot['start'] == '09:00' and slot['available'] for slot in slots)

    payload = {
        'service_id': service.id,
        'date': '2026-11-02',
        'time': '09:00',
        'technician_id': technician.id,
        'address': 'Calle 1 #2-3',
    }
    response = client.post(
        '/api/appointments',
        data=json.dumps(payload),
        content_type='application/json',
        **headers,
    )
    assert response.status_code == 201
    appointment_id = response.json()['appointment']['id']
    assert appointment_id
    assert Appointment.objects.count() == 1

    response = client.post(
        '/api/appointments',
        data=json.dumps(payload),
        content_type='application/json',
        **headers,
    )
    assert response.status_code == 409
    body = response.json()
    assert body['success'] is False
    assert body['code'] == 'SLOT_UNAVAILABLE'
    assert Appointment.objects.count() == 1
