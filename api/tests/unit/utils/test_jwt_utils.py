# -*- coding: utf-8 -*-
"""Pruebas unitarias de los helpers JWT."""
from datetime import timedelta

import pytest
from django.test import override_settings

from api.utils.jwt_utils import (
    decode_token,
    generate_token,
    get_current_user_id,
    get_jwt_identity,
    get_token_from_request,
)

pytestmark = pytest.mark.unit


def test_token_valido_tiene_sub_string():
    token = generate_token(7)
    payload = decode_token(token)

    assert payload is not None
    assert payload['sub'] == '7'
    assert isinstance(payload['sub'], str)
    assert 'iat' in payload
    assert 'exp' in payload


def test_token_expirado_retorna_none():
    with override_settings(JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=-1)):
        token = generate_token(1)

    assert decode_token(token) is None


def test_token_con_firma_alterada_retorna_none():
    token = generate_token(1)
    last = token[-1]
    tampered = token[:-1] + ('A' if last != 'A' else 'B')

    assert decode_token(tampered) is None


@pytest.mark.parametrize('token', ['', 'no-es-un-jwt', 'a.b.c', None])
def test_token_invalido_retorna_none(token):
    assert decode_token(token) is None


def test_header_bearer_extrae_token():
    class Request:
        META = {'HTTP_AUTHORIZATION': 'Bearer abc.def.ghi'}

    assert get_token_from_request(Request()) == 'abc.def.ghi'


def test_header_bearer_minusculas_extrae_token():
    class Request:
        META = {'HTTP_AUTHORIZATION': 'bearer abc.def.ghi'}

    assert get_token_from_request(Request()) == 'abc.def.ghi'


def test_header_sin_bearer_devuelve_el_texto():
    class Request:
        META = {'HTTP_AUTHORIZATION': 'abc.def.ghi'}

    assert get_token_from_request(Request()) == 'abc.def.ghi'


@pytest.mark.parametrize('header', ['', '   ', None])
def test_header_vacio_retorna_none(header):
    class Request:
        META = {} if header is None else {'HTTP_AUTHORIZATION': header}

    assert get_token_from_request(Request()) is None


def test_identidad_desde_token_valido():
    token = generate_token(3)

    class Request:
        META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    assert get_jwt_identity(Request()) == '3'


def test_identidad_sin_token_retorna_none():
    class Request:
        META = {}

    assert get_jwt_identity(Request()) is None


def test_identidad_con_token_invalido_retorna_none():
    class Request:
        META = {'HTTP_AUTHORIZATION': 'Bearer no-es-un-jwt'}

    assert get_jwt_identity(Request()) is None


def test_current_user_id_valido():
    token = generate_token(9)

    class Request:
        META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    assert get_current_user_id(Request()) == 9


def test_current_user_id_sin_token_retorna_none():
    class Request:
        META = {}

    assert get_current_user_id(Request()) is None


def test_current_user_id_con_sub_no_numerico_retorna_none():
    token = generate_token('abc')

    class Request:
        META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    assert get_current_user_id(Request()) is None
