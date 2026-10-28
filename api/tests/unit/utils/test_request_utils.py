# -*- coding: utf-8 -*-
"""Pruebas unitarias de los helpers de request."""
import json
from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from api.utils.request_utils import json_body, query_int, query_str

pytestmark = pytest.mark.unit


def test_json_body_vacio_retorna_dict_vacio():
    request = SimpleNamespace(body=b'')

    assert json_body(request) == {}


def test_json_body_valido_retorna_dict():
    request = RequestFactory().post(
        '/',
        data=json.dumps({'name': 'Andrés'}),
        content_type='application/json',
    )

    assert json_body(request) == {'name': 'Andrés'}


@pytest.mark.parametrize(
    'body',
    [b'[]', b'"texto"', b'123', b'null', b'no-es-json'],
)
def test_json_body_no_dict_retorna_dict_vacio(body):
    request = SimpleNamespace(body=body)

    assert json_body(request) == {}


def test_query_int_valido():
    request = SimpleNamespace(GET={'page': '3'})

    assert query_int(request, 'page') == 3


@pytest.mark.parametrize('raw', [None, '', 'abc', '3.5'])
def test_query_int_invalido_retorna_default(raw):
    request = SimpleNamespace(GET={'page': raw})

    assert query_int(request, 'page', default=1) == 1


def test_query_str_presente():
    request = SimpleNamespace(GET={'q': 'fuga'})

    assert query_str(request, 'q') == 'fuga'


def test_query_str_ausente_retorna_default():
    request = SimpleNamespace(GET={})

    assert query_str(request, 'q', default='todo') == 'todo'


def test_query_str_none_retorna_default():
    request = SimpleNamespace(GET={'q': None})

    assert query_str(request, 'q', default='todo') == 'todo'
