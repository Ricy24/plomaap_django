# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio de citas (agenda y disponibilidad)."""
from datetime import datetime as real_datetime
from unittest.mock import MagicMock, patch

import pytest

from api.services.appointment_service import (
    _normalize_schedule,
    check_technician_availability,
    find_available_technician,
    get_available_time_slots,
    get_smart_time_slots,
    validate_appointment_transition,
)
from api.tests.factories import (
    AppointmentFactory,
    ServiceFactory,
    TechnicianProfileFactory,
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

# 2026-11-02 es lunes; 2026-11-09 también.
MONDAY = '2026-11-02'
NEXT_MONDAY = '2026-11-09'


def make_technician(rating=4.5, schedule=None, available=True, status='active'):
    profile = TechnicianProfileFactory(
        user__status=status,
        rating=rating,
        available=available,
        schedule={'mon': [[8, 18]]} if schedule is None else schedule,
    )
    return profile.user


# --------------------------------------------------------------------------- #
# _normalize_schedule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('schedule', [None, {}])
def test_normalize_schedule_vacio_retorna_dict_vacio(schedule):
    assert _normalize_schedule(schedule) == {}


def test_normalize_schedule_dia_sin_rangos_se_omite():
    assert _normalize_schedule({'mon': []}) == {}


def test_normalize_schedule_convierte_dia_a_minusculas():
    assert _normalize_schedule({'MON': [[8, 18]]}) == {'mon': [[8, 18]]}


def test_normalize_schedule_convierte_strings_a_enteros():
    assert _normalize_schedule({'mon': [('8', '18')]}) == {'mon': [[8, 18]]}


def test_normalize_schedule_descarta_items_invalidos():
    schedule = {'mon': [[8], 'x', [8, 'abc'], [8, 18]]}

    assert _normalize_schedule(schedule) == {'mon': [[8, 18]]}


def test_normalize_schedule_conserva_dia_sin_items_validos():
    assert _normalize_schedule({'mon': ['x']}) == {'mon': []}


# --------------------------------------------------------------------------- #
# find_available_technician
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    'date_str,time_str',
    [
        ('2026-13-01', '09:00'),
        ('02/11/2026', '09:00'),
        (None, '09:00'),
        (MONDAY, '25:00'),
        (MONDAY, '09:60'),
        (MONDAY, None),
    ],
)
def test_find_available_technician_formato_invalido(date_str, time_str):
    assert find_available_technician(date_str, time_str) is None


def test_find_available_technician_sin_tecnicos_retorna_none():
    assert find_available_technician(MONDAY, '09:00') is None


def test_find_available_technician_elige_el_mejor_rating():
    low = make_technician(rating=3.0)
    high = make_technician(rating=5.0)

    selected = find_available_technician(MONDAY, '09:00')

    assert selected in (low, high)
    assert selected == high


def test_find_available_technician_excluye_tecnico_indicado():
    low = make_technician(rating=3.0)
    high = make_technician(rating=5.0)

    selected = find_available_technician(
        MONDAY, '09:00', exclude_technician_id=high.id
    )

    assert selected == low


def test_find_available_technician_ignora_perfil_no_disponible():
    make_technician(rating=5.0, available=False)
    disponible = make_technician(rating=4.0)

    assert find_available_technician(MONDAY, '09:00') == disponible


def test_find_available_technician_ignora_dia_sin_horario():
    make_technician(schedule={'tue': [[8, 18]]})
    lunes = make_technician(schedule={'mon': [[8, 18]]})

    assert find_available_technician(MONDAY, '09:00') == lunes


def test_find_available_technician_ignora_hora_fuera_de_horario():
    make_technician(schedule={'mon': [[8, 10]]})

    assert find_available_technician(MONDAY, '15:00') is None


def test_find_available_technician_ignora_tecnico_con_conflicto():
    ocupado = make_technician(rating=5.0)
    libre = make_technician(rating=4.0)
    AppointmentFactory(technician=ocupado, date=real_datetime(2026, 11, 2).date())

    assert find_available_technician(MONDAY, '09:00') == libre


def test_find_available_technician_ignora_usuario_no_tecnico():
    UserFactory(role='customer', status='active')

    assert find_available_technician(MONDAY, '09:00') is None


# --------------------------------------------------------------------------- #
# get_available_time_slots
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize('date_str', ['2026-13-01', '02/11/2026', None, ''])
def test_get_available_time_slots_fecha_invalida(date_str):
    assert get_available_time_slots(1, date_str) == []


def test_get_available_time_slots_tecnico_inexistente():
    assert get_available_time_slots(999999, MONDAY) == []


def test_get_available_time_slots_usuario_no_tecnico():
    user = UserFactory(role='customer')

    assert get_available_time_slots(user.id, MONDAY) == []


def test_get_available_time_slots_tecnico_sin_perfil():
    fake_tech = MagicMock()
    fake_tech.role = 'technician'
    fake_tech.technician_profile = None

    with patch('api.services.appointment_service.User.objects.filter') as filter_mock:
        filter_mock.return_value.first.return_value = fake_tech
        assert get_available_time_slots(1, MONDAY) == []


def test_get_available_time_slots_dia_sin_horario():
    tech = make_technician(schedule={'tue': [[8, 18]]})

    assert get_available_time_slots(tech.id, MONDAY) == []


def test_get_available_time_slots_genera_horas_libres():
    tech = make_technician(schedule={'mon': [[8, 11]]})

    assert get_available_time_slots(tech.id, MONDAY) == [
        '08:00',
        '09:00',
        '10:00',
    ]


def test_get_available_time_slots_omite_horas_ocupadas():
    tech = make_technician(schedule={'mon': [[8, 11]]})
    AppointmentFactory(
        technician=tech,
        date=real_datetime(2026, 11, 2).date(),
        time='09:00',
        status='scheduled',
    )

    assert get_available_time_slots(tech.id, MONDAY) == ['08:00', '10:00']


def test_get_available_time_slots_ignora_citas_canceladas():
    tech = make_technician(schedule={'mon': [[8, 9]]})
    AppointmentFactory(
        technician=tech,
        date=real_datetime(2026, 11, 2).date(),
        time='08:00',
        status='cancelled',
    )

    assert get_available_time_slots(tech.id, MONDAY) == ['08:00']


# --------------------------------------------------------------------------- #
# get_smart_time_slots
# --------------------------------------------------------------------------- #
def test_get_smart_time_slots_fecha_invalida():
    result, status = get_smart_time_slots(None, '2026-13-01')

    assert status == 400
    assert result == {'error': 'Invalid date format'}


def test_get_smart_time_slots_sin_tecnicos_todos_no_disponibles():
    ServiceFactory(id=1, duration_minutes=60)

    result = get_smart_time_slots(1, NEXT_MONDAY)

    assert result['duration_minutes'] == 60
    assert len(result['slots']) == 10
    assert all(slot['available'] is False for slot in result['slots'])


def test_get_smart_time_slots_usa_duracion_por_defecto_sin_servicio():
    make_technician()

    result = get_smart_time_slots(None, NEXT_MONDAY)

    assert result['duration_minutes'] == 60
    assert result['service_id'] is None


def test_get_smart_time_slots_marca_horas_dentro_del_horario():
    make_technician(schedule={'mon': [[8, 12]]})
    ServiceFactory(id=1, duration_minutes=60)

    result = get_smart_time_slots(1, NEXT_MONDAY)

    disponibles = [slot['start'] for slot in result['slots'] if slot['available']]
    assert disponibles == ['08:00', '09:00', '10:00', '11:00']


def test_get_smart_time_slots_clasifica_periodos():
    make_technician(schedule={'mon': [[8, 18]]})
    ServiceFactory(id=1)

    result = get_smart_time_slots(1, NEXT_MONDAY)
    periodos = {slot['start']: slot['period'] for slot in result['slots']}

    assert periodos['08:00'] == 'morning'
    assert periodos['12:00'] == 'afternoon'
    assert periodos['17:00'] == 'evening'


def test_get_smart_time_slots_calcula_hora_fin_con_duracion():
    make_technician(schedule={'mon': [[8, 18]]})
    ServiceFactory(id=1, duration_minutes=90)

    result = get_smart_time_slots(1, NEXT_MONDAY)
    slot = next(s for s in result['slots'] if s['start'] == '17:00')

    assert slot['end'] == '18:30'


def test_get_smart_time_slots_filtra_tecnico_indicado():
    tech = make_technician(schedule={'mon': [[8, 10]]})
    make_technician(schedule={'mon': [[8, 18]]})
    ServiceFactory(id=1)

    result = get_smart_time_slots(1, NEXT_MONDAY, technician_id=tech.id)
    disponibles = [slot['start'] for slot in result['slots'] if slot['available']]

    assert disponibles == ['08:00', '09:00']


def test_get_smart_time_slots_tecnico_indicado_invalido():
    ServiceFactory(id=1)
    customer = UserFactory(role='customer')

    result = get_smart_time_slots(1, NEXT_MONDAY, technician_id=customer.id)

    assert all(slot['available'] is False for slot in result['slots'])


def test_get_smart_time_slots_ignora_tecnico_no_disponible():
    make_technician(schedule={'mon': [[8, 18]]}, available=False)
    ServiceFactory(id=1)

    result = get_smart_time_slots(1, NEXT_MONDAY)

    assert all(slot['available'] is False for slot in result['slots'])


def test_get_smart_time_slots_ignora_dia_sin_horario():
    make_technician(schedule={'tue': [[8, 18]]})
    ServiceFactory(id=1)

    result = get_smart_time_slots(1, NEXT_MONDAY)

    assert all(slot['available'] is False for slot in result['slots'])


def test_get_smart_time_slots_marca_conflicto_como_no_disponible():
    tech = make_technician(schedule={'mon': [[8, 18]]})
    ServiceFactory(id=1)
    AppointmentFactory(
        technician=tech,
        date=real_datetime(2026, 11, 9).date(),
        time='08:00',
        status='scheduled',
    )

    result = get_smart_time_slots(1, NEXT_MONDAY)
    slot = next(s for s in result['slots'] if s['start'] == '08:00')

    assert slot['available'] is False
    assert slot['available_technicians_count'] == 0


def test_get_smart_time_slots_hoy_descarta_horas_pasadas():
    make_technician(schedule={'mon': [[8, 18]]})
    ServiceFactory(id=1)

    with patch('api.services.appointment_service.datetime') as fake_dt:
        fake_dt.strptime.side_effect = real_datetime.strptime
        fake_dt.combine.side_effect = real_datetime.combine
        fake_dt.now.return_value = real_datetime(2026, 11, 9, 10, 45)
        result = get_smart_time_slots(1, NEXT_MONDAY)

    slots = {slot['start']: slot['available'] for slot in result['slots']}
    assert slots['08:00'] is False
    assert slots['11:00'] is False
    assert slots['12:00'] is True


# --------------------------------------------------------------------------- #
# validate_appointment_transition
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    'current,new',
    [
        ('pending', 'scheduled'),
        ('pending', 'cancelled'),
        ('scheduled', 'in_progress'),
        ('scheduled', 'cancelled'),
        ('in_progress', 'completed'),
        ('in_progress', 'cancelled'),
    ],
)
def test_transicion_de_cita_valida(current, new):
    assert validate_appointment_transition(current, new) is True


@pytest.mark.parametrize(
    'current,new',
    [
        ('pending', 'completed'),
        ('scheduled', 'pending'),
        ('completed', 'in_progress'),
        ('cancelled', 'scheduled'),
        ('desconocido', 'scheduled'),
    ],
)
def test_transicion_de_cita_invalida(current, new):
    assert validate_appointment_transition(current, new) is False


# --------------------------------------------------------------------------- #
# check_technician_availability
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    'date_str,time_str',
    [('2026-13-01', '09:00'), ('02/11/2026', '09:00'), (None, None)],
)
def test_check_technician_availability_formato_invalido(date_str, time_str):
    ok, message, tech = check_technician_availability(1, date_str, time_str)

    assert ok is False
    assert message == 'Formato de fecha u hora invalido'
    assert tech is None


def test_check_technician_availability_inexistente():
    ok, message, tech = check_technician_availability(999999, MONDAY, '09:00')

    assert ok is False
    assert message == 'El plomero seleccionado no existe'
    assert tech is None


def test_check_technician_availability_usuario_no_tecnico():
    customer = UserFactory(role='customer')

    ok, message, _ = check_technician_availability(customer.id, MONDAY, '09:00')

    assert ok is False
    assert message == 'El usuario seleccionado no es un tecnico plomero'


def test_check_technician_availability_tecnico_inactivo():
    tech = make_technician(status='inactive')

    ok, message, _ = check_technician_availability(tech.id, MONDAY, '09:00')

    assert ok is False
    assert message == 'El plomero seleccionado no se encuentra activo'


def test_check_technician_availability_perfil_no_disponible():
    tech = make_technician(available=False)

    ok, message, _ = check_technician_availability(tech.id, MONDAY, '09:00')

    assert ok is False
    assert 'no esta disponible para servicios' in message


def test_check_technician_availability_dia_sin_horario():
    tech = make_technician(schedule={'tue': [[8, 18]]})

    ok, message, _ = check_technician_availability(tech.id, MONDAY, '09:00')

    assert ok is False
    assert 'no atiende en el dia solicitado (mon)' in message


def test_check_technician_availability_fuera_de_horario():
    tech = make_technician(schedule={'mon': [[8, 10]]})

    ok, message, _ = check_technician_availability(tech.id, MONDAY, '15:00')

    assert ok is False
    assert 'fuera del horario de atencion' in message


def test_check_technician_availability_con_conflicto():
    tech = make_technician(schedule={'mon': [[8, 18]]})
    AppointmentFactory(
        technician=tech,
        date=real_datetime(2026, 11, 2).date(),
        time='09:00',
        status='scheduled',
    )

    ok, message, _ = check_technician_availability(tech.id, MONDAY, '09:00')

    assert ok is False
    assert 'ya no esta disponible para ese horario' in message


def test_check_technician_availability_exitosa():
    tech = make_technician(schedule={'mon': [[8, 18]]})

    ok, message, returned = check_technician_availability(tech.id, MONDAY, '09:00')

    assert ok is True
    assert message is None
    assert returned == tech
