# -*- coding: utf-8 -*-
"""UNIT-02: JWT HS256 (api/utils/jwt_utils.py)."""
from datetime import timedelta

import pytest
from django.test import override_settings

from api.utils.jwt_utils import decode_token, generate_token

pytestmark = pytest.mark.unit


def test_UNIT_02_token_valido_tiene_sub_string():
    token = generate_token(1)
    payload = decode_token(token)

    assert payload is not None
    assert payload['sub'] == '1'
    assert isinstance(payload['sub'], str)
    assert 'iat' in payload
    assert 'exp' in payload


def test_UNIT_02_token_expirado_retorna_none():
    with override_settings(JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=-1)):
        token = generate_token(1)

    assert decode_token(token) is None


def test_UNIT_02_firma_alterada_retorna_none():
    token = generate_token(1)
    last = token[-1]
    tampered = token[:-1] + ('A' if last != 'A' else 'B')

    assert decode_token(tampered) is None


def test_UNIT_02_token_basura_retorna_none():
    assert decode_token('no-es-un-jwt') is None
