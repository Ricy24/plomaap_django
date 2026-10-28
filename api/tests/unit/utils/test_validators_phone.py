# -*- coding: utf-8 -*-
"""Pruebas unitarias del validador de teléfono."""
import pytest

from api.utils.validators import validate_phone

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'phone',
    [
        '3229874810',
        '+573229874810',
        '123456789',
        '123456789012345',
        '+11234567890',
    ],
)
def test_telefono_valido(phone):
    assert validate_phone(phone) is True


@pytest.mark.parametrize(
    'phone',
    [
        '123',
        '12345678',
        '12345678901234567',
        'abc123456789',
        '+57 322 987 4810',
        '',
        None,
        3001234567,
        [],
    ],
)
def test_telefono_invalido(phone):
    assert validate_phone(phone) is False
