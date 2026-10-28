# -*- coding: utf-8 -*-
"""Pruebas unitarias del despachador por método HTTP."""
import json

import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from api.utils.dispatch import methods

pytestmark = pytest.mark.unit


def _ok(request, *args, **kwargs):
    return JsonResponse({'method': request.method, 'args': args, 'kwargs': kwargs})


def test_get_ejecuta_handler_correcto():
    dispatcher = methods(GET=_ok, POST=_ok)
    request = RequestFactory().get('/')

    response = dispatcher(request)

    assert response.status_code == 200
    assert json.loads(response.content)['method'] == 'GET'


def test_head_usa_handler_get():
    dispatcher = methods(GET=_ok)
    request = RequestFactory().head('/')

    response = dispatcher(request)

    assert response.status_code == 200
    assert response.content


def test_metodo_no_permitido_retorna_405_y_allow():
    dispatcher = methods(GET=_ok, POST=_ok)
    request = RequestFactory().delete('/')

    response = dispatcher(request)

    assert response.status_code == 405
    assert 'GET' in response['Allow']
    assert 'POST' in response['Allow']
    assert 'HEAD' in response['Allow']
    assert 'OPTIONS' in response['Allow']
    assert json.loads(response.content)['error'] == 'Method not allowed'


def test_nombre_del_dispatcher_es_estable():
    dispatcher = methods(GET=_ok, POST=_ok)

    assert dispatcher.__name__ == 'dispatch_get_post'


def test_args_y_kwargs_se_pasan_al_handler():
    dispatcher = methods(GET=_ok)
    request = RequestFactory().get('/')

    response = dispatcher(request, 1, 2, extra='x')

    body = json.loads(response.content)
    assert body['args'] == [1, 2]
    assert body['kwargs'] == {'extra': 'x'}
