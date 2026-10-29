# -*- coding: utf-8 -*-
"""
Integrante 3 - Citas y disponibilidad.

Cubre las reglas de ``api/services/appointment_service.py``: transiciones de
estado, franjas horarias y verificacion de disponibilidad de un tecnico.
Usa SQLite en memoria y las fabricas del proyecto.
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

# Lunes 2 de noviembre de 2026: los tecnicos de prueba atienden de 8:00 a 18:00.
LUNES = date(2026, 11, 2)


def test_pendiente_puede_pasar_a_agendada():
    """Caso: confirmacion de una cita pendiente.
    Entrada: estado actual 'pending' y nuevo estado 'scheduled'.
    Esperado: True, porque es una transicion permitida.
    Cubre: api/services/appointment_service.py::validate_appointment_transition
    """
    assert validate_appointment_transition('pending', 'scheduled') is True


def test_agendada_puede_pasar_a_en_progreso():
    """Caso: inicio del servicio de una cita confirmada.
    Entrada: 'scheduled' y 'in_progress'.
    Esperado: True, porque el tecnico ya puede iniciar el trabajo.
    Cubre: api/services/appointment_service.py::validate_appointment_transition
    """
    assert validate_appointment_transition('scheduled', 'in_progress') is True


def test_cita_completada_no_puede_cancelarse():
    """Caso: intento de cancelar una cita ya terminada.
    Entrada: 'completed' y 'cancelled'.
    Esperado: False, porque completed es un estado final.
    Cubre: api/services/appointment_service.py::validate_appointment_transition
    """
    assert validate_appointment_transition('completed', 'cancelled') is False


def test_cita_cancelada_no_puede_reabrirse():
    """Caso: intento de reabrir una cita cancelada.
    Entrada: 'cancelled' y 'scheduled'.
    Esperado: False, porque cancelled es un estado final.
    Cubre: api/services/appointment_service.py::validate_appointment_transition
    """
    assert validate_appointment_transition('cancelled', 'scheduled') is False


def test_fecha_invalida_no_genera_horarios(db):
    """Caso: fecha con separadores incorrectos.
    Entrada: tecnico 1 y '02-11-2026'.
    Esperado: lista vacia, porque el formato no se puede interpretar.
    Cubre: api/services/appointment_service.py::get_available_time_slots
    """
    assert get_available_time_slots(1, '02-11-2026') == []


def test_usuario_que_no_es_tecnico_no_tiene_horarios(db):
    """Caso: se piden horarios para un cliente.
    Entrada: id de un usuario con rol customer y una fecha valida.
    Esperado: [], porque solo los tecnicos tienen agenda.
    Cubre: api/services/appointment_service.py::get_available_time_slots
    """
    cliente = UserFactory(role='customer')

    assert get_available_time_slots(cliente.id, '2026-11-02') == []


def test_jornada_laboral_genera_diez_franjas(db):
    """Caso: tecnico con jornada de 8:00 a 18:00.
    Entrada: id del tecnico y '2026-11-02'.
    Esperado: 10 franjas, desde '08:00' hasta '17:00'.
    Cubre: api/services/appointment_service.py::get_available_time_slots
    """
    tecnico = TechnicianProfileFactory().user

    horarios = get_available_time_slots(tecnico.id, '2026-11-02')

    assert len(horarios) == 10
    assert horarios[0] == '08:00'
    assert horarios[-1] == '17:00'


def test_hora_ocupada_no_se_ofrece(db):
    """Caso: el tecnico ya tiene una cita activa a las 09:00.
    Entrada: cita scheduled a las 09:00 y consulta del mismo dia.
    Esperado: 9 franjas y '09:00' fuera de la lista.
    Cubre: api/services/appointment_service.py::get_available_time_slots
    """
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
    """Caso: tecnico activo, dentro de su horario y sin choques.
    Entrada: id del tecnico, '2026-11-02' y '09:00'.
    Esperado: disponible, sin mensaje de error y con el tecnico encontrado.
    Cubre: api/services/appointment_service.py::check_technician_availability
    """
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
    """Caso: se solicita una hora antes de abrir la jornada.
    Entrada: id del tecnico, '2026-11-02' y '07:00'.
    Esperado: no disponible, mensaje de horario y sin tecnico.
    Cubre: api/services/appointment_service.py::check_technician_availability
    """
    tecnico = TechnicianProfileFactory().user

    disponible, mensaje, tecnico_encontrado = check_technician_availability(
        tecnico.id,
        '2026-11-02',
        '07:00',
    )

    assert disponible is False
    assert 'horario' in mensaje.lower()
    assert tecnico_encontrado is None
