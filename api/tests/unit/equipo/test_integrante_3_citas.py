# -*- coding: utf-8 -*-
"""
Integrante 3 - Citas y disponibilidad.

Cubre las reglas de ``api/services/appointment_service.py``: transiciones de
estado, franjas horarias y verificación de disponibilidad de un técnico.
Usa SQLite en memoria y las fábricas del proyecto.
"""
from datetime import date

import pytest

from api.services.appointment_service import (
    check_technician_availability,
    get_available_time_slots,
    validate_appointment_transition,
)
from api.tests.factories import AppointmentFactory, TechnicianProfileFactory, UserFactory

pytestmark = pytest.mark.unit

# Lunes 2 de noviembre de 2026: los técnicos de prueba atienden de 8:00 a 18:00.
LUNES = date(2026, 11, 2)


def test_pendiente_puede_pasar_a_agendada():
    """Una cita pendiente puede confirmarse."""
    assert validate_appointment_transition('pending', 'scheduled') is True


def test_agendada_puede_pasar_a_en_progreso():
    """Una cita confirmada puede iniciar el servicio."""
    assert validate_appointment_transition('scheduled', 'in_progress') is True


def test_cita_completada_no_puede_cancelarse():
    """Una cita completada es un estado final."""
    assert validate_appointment_transition('completed', 'cancelled') is False


def test_cita_cancelada_no_puede_reabrirse():
    """Una cita cancelada también es un estado final."""
    assert validate_appointment_transition('cancelled', 'scheduled') is False


def test_fecha_invalida_no_genera_horarios(db):
    """Si la fecha no tiene formato YYYY-MM-DD se devuelve una lista vacía."""
    assert get_available_time_slots(1, '02-11-2026') == []


def test_usuario_que_no_es_tecnico_no_tiene_horarios(db):
    """Solo los usuarios con rol technician tienen agenda."""
    cliente = UserFactory(role='customer')

    assert get_available_time_slots(cliente.id, '2026-11-02') == []


def test_jornada_laboral_genera_diez_franjas(db):
    """De 8:00 a 18:00 se ofrecen las franjas 08:00 ... 17:00."""
    tecnico = TechnicianProfileFactory().user

    horarios = get_available_time_slots(tecnico.id, '2026-11-02')

    assert len(horarios) == 10
    assert horarios[0] == '08:00'
    assert horarios[-1] == '17:00'


def test_hora_ocupada_no_se_ofrece(db):
    """Una cita activa bloquea su franja horaria."""
    tecnico = TechnicianProfileFactory().user
    AppointmentFactory(
        technician=tecnico,
        date=LUNES,
        time='09:00',
        status='scheduled',
    )

    horarios = get_available_time_slots(tecnico.id, '2026-11-02')

    assert '09:00' not in horarios
    assert len(horarios) == 9


def test_tecnico_libre_esta_disponible(db):
    """Un técnico activo, dentro de su horario y sin choques está disponible."""
    tecnico = TechnicianProfileFactory().user

    disponible, mensaje, tecnico_encontrado = check_technician_availability(
        tecnico.id,
        '2026-11-02',
        '09:00',
    )

    assert disponible is True
    assert mensaje is None
    assert tecnico_encontrado.id == tecnico.id


def test_tecnico_fuera_de_horario_no_esta_disponible(db):
    """Antes de las 8:00 el técnico no atiende."""
    tecnico = TechnicianProfileFactory().user

    disponible, mensaje, tecnico_encontrado = check_technician_availability(
        tecnico.id,
        '2026-11-02',
        '07:00',
    )

    assert disponible is False
    assert 'horario' in mensaje.lower()
    assert tecnico_encontrado is None
