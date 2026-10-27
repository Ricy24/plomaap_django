# -*- coding: utf-8 -*-
"""Pruebas unitarias del validador de fecha y hora."""
import pytest

from api.utils.validators import validate_date_time

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'date_str,time_str',
    [
        ('2026-11-02', '09:00'),
        ('2026-01-01', '00:00'),
        ('2026-12-31', '23:59'),
        ('2024-02-29', '12:30'),
    ],
)
def test_fecha_hora_valida(date_str, time_str):
    assert validate_date_time(date_str, time_str) is True


@pytest.mark.parametrize(
    'date_str,time_str',
    [
        ('2026-13-01', '09:00'),
        ('2026-02-30', '09:00'),
        ('2026-11-02', '25:00'),
        ('2026-11-02', '09:60'),
        ('02/11/2026', '09:00'),
        ('', '09:00'),
        ('2026-11-02', ''),
        (None, None),
        (20261102, 900),
    ],
)
def test_fecha_hora_invalida(date_str, time_str):
    assert validate_date_time(date_str, time_str) is False
