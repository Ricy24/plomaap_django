# -*- coding: utf-8 -*-
"""UNIT-03: disponibilidad de citas y transiciones de estado."""
from datetime import date

import pytest
from freezegun import freeze_time

from api.models import Appointment
from api.services.appointment_service import (
    get_smart_time_slots,
    validate_appointment_transition,
)

pytestmark = pytest.mark.unit


@pytest.mark.django_db
def test_UNIT_03_slots_libres_y_conflicto(customer, technician, service):
    result = get_smart_time_slots(service.id, '2026-11-02', technician.id)

    assert isinstance(result, dict)
    slots = result['slots']
    assert len(slots) == 10
    assert slots[0]['start'] == '08:00'
    assert slots[-1]['start'] == '17:00'
    assert all(slot['available'] is True for slot in slots)

    Appointment.objects.create(
        user=customer,
        technician=technician,
        service=service,
        date=date(2026, 11, 2),
        time='09:00',
        status='scheduled',
    )

    result = get_smart_time_slots(service.id, '2026-11-02', technician.id)
    slot_9 = next(slot for slot in result['slots'] if slot['start'] == '09:00')
    assert slot_9['available'] is False


@pytest.mark.django_db
@freeze_time('2026-11-02 17:45:00')
def test_UNIT_03_hoy_no_ofrece_slots_pasados(technician, service):
    result = get_smart_time_slots(service.id, '2026-11-02', technician.id)

    assert all(slot['available'] is False for slot in result['slots'])


def test_UNIT_03_transiciones_validas_e_invalidas():
    assert validate_appointment_transition('pending', 'scheduled') is True
    assert validate_appointment_transition('scheduled', 'in_progress') is True
    assert validate_appointment_transition('in_progress', 'completed') is True
    assert validate_appointment_transition('completed', 'scheduled') is False
    assert validate_appointment_transition('cancelled', 'pending') is False
