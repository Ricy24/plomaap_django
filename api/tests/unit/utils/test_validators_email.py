# -*- coding: utf-8 -*-
"""Pruebas unitarias del validador de email."""
import pytest

from api.utils.validators import validate_email

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'email',
    [
        'usuario@plomaap.com',
        'andres.test+qa@plomaap.co',
        'a@b.co',
        'nombre.apellido@subdominio.empresa.com',
    ],
)
def test_email_valido(email):
    assert validate_email(email) is True


@pytest.mark.parametrize(
    'email',
    [
        'usuario@',
        'sin-arroba.com',
        '@plomaap.com',
        'usuario@plomaap',
        'usuario@.com',
        'usuario con espacio@plomaap.com',
        '',
        None,
        123,
        [],
    ],
)
def test_email_invalido(email):
    assert validate_email(email) is False
