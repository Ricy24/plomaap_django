# -*- coding: utf-8 -*-
"""Pruebas unitarias del validador de contraseña."""
import pytest

from api.utils.validators import validate_password

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'password',
    [
        '12345678',
        'PlomApp2026*',
        'una-clave-larga-y-segura',
        '        ',
    ],
)
def test_password_valido(password):
    assert validate_password(password) is True


@pytest.mark.parametrize(
    'password',
    [
        '1234567',
        '',
        None,
        12345678,
        [],
    ],
)
def test_password_invalido(password):
    assert validate_password(password) is False
