# -*- coding: utf-8 -*-
"""Pruebas unitarias del validador de nombre."""
import pytest

from api.utils.validators import validate_name

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'name',
    [
        'Andrés',
        'Ana',
        'José Pérez',
        '  Carlos  ',
    ],
)
def test_nombre_valido(name):
    assert validate_name(name) is True


@pytest.mark.parametrize(
    'name',
    [
        'A',
        ' ',
        '   ',
        '',
        None,
        123,
        [],
    ],
)
def test_nombre_invalido(name):
    assert validate_name(name) is False
