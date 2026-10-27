# -*- coding: utf-8 -*-
"""Pruebas unitarias de los catálogos de roles y estados."""
import pytest

from api.utils.validators import (
    validate_appointment_status,
    validate_role,
    validate_status,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('role', ['customer', 'technician', 'admin'])
def test_rol_valido(role):
    assert validate_role(role) is True


@pytest.mark.parametrize('role', ['', 'cliente', 'superadmin', None, 1])
def test_rol_invalido(role):
    assert validate_role(role) is False


@pytest.mark.parametrize('status', ['active', 'inactive', 'suspended'])
def test_estado_usuario_valido(status):
    assert validate_status(status) is True


@pytest.mark.parametrize('status', ['', 'activo', 'deleted', None, 1])
def test_estado_usuario_invalido(status):
    assert validate_status(status) is False


@pytest.mark.parametrize(
    'status',
    ['pending', 'scheduled', 'in_progress', 'completed', 'cancelled'],
)
def test_estado_cita_valido(status):
    assert validate_appointment_status(status) is True


@pytest.mark.parametrize('status', ['', 'en_progreso', 'deleted', None, 1])
def test_estado_cita_invalido(status):
    assert validate_appointment_status(status) is False
