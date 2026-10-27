# -*- coding: utf-8 -*-
"""UNIT-01: validadores de registro (api/utils/validators.py)."""
import pytest

from api.utils.validators import (
    validate_date_time,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'email,expected',
    [
        ('usuario@plomaap.com', True),
        ('andres.test+qa@plomaap.co', True),
        ('usuario@', False),
        ('sin-arroba.com', False),
        ('', False),
        (None, False),
    ],
)
def test_UNIT_01_email(email, expected):
    assert validate_email(email) is expected


@pytest.mark.parametrize(
    'phone,expected',
    [
        ('3229874810', True),
        ('+573229874810', True),
        ('123', False),
        ('', False),
        (None, False),
    ],
)
def test_UNIT_01_phone(phone, expected):
    assert validate_phone(phone) is expected


@pytest.mark.parametrize(
    'password,expected',
    [
        ('PlomApp2026*', True),
        ('12345678', True),
        ('1234567', False),
        ('', False),
        (None, False),
    ],
)
def test_UNIT_01_password(password, expected):
    assert validate_password(password) is expected


@pytest.mark.parametrize(
    'name,expected',
    [
        ('Andrés', True),
        ('A', False),
        ('  ', False),
        (None, False),
    ],
)
def test_UNIT_01_name(name, expected):
    assert validate_name(name) is expected


@pytest.mark.parametrize(
    'date_str,time_str,expected',
    [
        ('2026-11-02', '09:00', True),
        ('2026-13-01', '09:00', False),
        ('2026-11-02', '25:00', False),
    ],
)
def test_UNIT_01_date_time(date_str, time_str, expected):
    assert validate_date_time(date_str, time_str) is expected
