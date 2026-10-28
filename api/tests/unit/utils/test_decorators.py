# -*- coding: utf-8 -*-
"""Pruebas unitarias de los decoradores de autenticación."""
import json

import pytest
from django.test import RequestFactory

from api.tests.factories import UserFactory
from api.utils.decorators import (
    admin_only,
    customer_only,
    jwt_optional,
    jwt_required,
    jwt_required_custom,
    technician_only,
)
from api.utils.jwt_utils import generate_token

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _request_for(user=None, token=None):
    request = RequestFactory().get('/')
    if token is not None:
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return request


def _view(request, user, *args, **kwargs):
    return {'user': user, 'args': args, 'kwargs': kwargs}


def _plain_view(request, *args, **kwargs):
    return {'request': request}


def _json(response):
    return json.loads(response.content)


def test_jwt_required_custom_permite_usuario_activo():
    user = UserFactory(role='customer', status='active')
    request = _request_for(token=generate_token(user.id))

    result = jwt_required_custom(_view)(request)

    assert result['user'] == user


def test_jwt_required_custom_sin_token_retorna_401():
    response = jwt_required_custom(_view)(_request_for())

    assert response.status_code == 401
    assert _json(response)['error'] == 'Unauthorized'


def test_jwt_required_custom_usuario_inexistente_retorna_401():
    response = jwt_required_custom(_view)(_request_for(token=generate_token(999999)))

    assert response.status_code == 401


def test_jwt_required_custom_sub_no_numerico_retorna_401():
    response = jwt_required_custom(_view)(_request_for(token=generate_token('abc')))

    assert response.status_code == 401


def test_jwt_required_custom_usuario_inactivo_retorna_401():
    user = UserFactory(status='inactive')
    request = _request_for(token=generate_token(user.id))

    response = jwt_required_custom(_view)(request)

    assert response.status_code == 401
    assert 'not active' in _json(response)['message']


def test_jwt_required_permite_usuario_activo():
    user = UserFactory(status='active')
    request = _request_for(token=generate_token(user.id))

    result = jwt_required(_view)(request)

    assert result['user'] == user


def test_jwt_required_sin_token_retorna_401():
    response = jwt_required(_view)(_request_for())

    assert response.status_code == 401


def test_jwt_optional_sin_token_deja_usuario_none():
    request = _request_for()

    result = jwt_optional(_plain_view)(request)

    assert result['request'].jwt_user is None


def test_jwt_optional_con_token_asigna_usuario():
    user = UserFactory(status='active')
    request = _request_for(token=generate_token(user.id))

    result = jwt_optional(_plain_view)(request)

    assert result['request'].jwt_user == user


def test_admin_only_permite_admin_activo():
    user = UserFactory(role='admin', status='active')
    request = _request_for(token=generate_token(user.id))

    result = admin_only(_view)(request)

    assert result['user'] == user


@pytest.mark.parametrize('role', ['customer', 'technician'])
def test_admin_only_rechaza_otro_rol(role):
    user = UserFactory(role=role, status='active')
    request = _request_for(token=generate_token(user.id))

    response = admin_only(_view)(request)

    assert response.status_code == 403
    assert _json(response)['error'] == 'Forbidden'


def test_admin_only_rechaza_admin_inactivo():
    user = UserFactory(role='admin', status='inactive')
    request = _request_for(token=generate_token(user.id))

    response = admin_only(_view)(request)

    assert response.status_code == 403


def test_technician_only_permite_tecnico_activo():
    user = UserFactory(role='technician', status='active')
    request = _request_for(token=generate_token(user.id))

    result = technician_only(_view)(request)

    assert result['user'] == user


@pytest.mark.parametrize('role', ['customer', 'admin'])
def test_technician_only_rechaza_otro_rol(role):
    user = UserFactory(role=role, status='active')
    request = _request_for(token=generate_token(user.id))

    response = technician_only(_view)(request)

    assert response.status_code == 403


def test_technician_only_rechaza_tecnico_inactivo():
    user = UserFactory(role='technician', status='inactive')
    request = _request_for(token=generate_token(user.id))

    response = technician_only(_view)(request)

    assert response.status_code == 403


def test_customer_only_permite_cliente_activo():
    user = UserFactory(role='customer', status='active')
    request = _request_for(token=generate_token(user.id))

    result = customer_only(_view)(request)

    assert result['user'] == user


@pytest.mark.parametrize('role', ['admin', 'technician'])
def test_customer_only_rechaza_otro_rol(role):
    user = UserFactory(role=role, status='active')
    request = _request_for(token=generate_token(user.id))

    response = customer_only(_view)(request)

    assert response.status_code == 403


def test_customer_only_rechaza_cliente_inactivo():
    user = UserFactory(role='customer', status='inactive')
    request = _request_for(token=generate_token(user.id))

    response = customer_only(_view)(request)

    assert response.status_code == 403


def test_decoradores_sin_token_retornan_401():
    for decorator in (admin_only, technician_only, customer_only):
        response = decorator(_view)(_request_for())
        assert response.status_code == 401
