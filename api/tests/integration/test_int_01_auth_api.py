# -*- coding: utf-8 -*-
"""INT-01: autenticación (registro, login, perfil y JWT)."""
import json

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_INT_01_registro_login_y_perfil(client):
    register_payload = {
        'name': 'Andrés Test',
        'email': 'andres.test@plomaap.test',
        'password': 'PlomApp2026*',
    }
    response = client.post(
        '/api/auth/register',
        data=json.dumps(register_payload),
        content_type='application/json',
    )

    assert response.status_code == 201
    body = response.json()
    assert body['success'] is True
    assert body['user']['email'] == register_payload['email']
    assert 'password' not in body['user']
    assert 'password_hash' not in body['user']
    token = body['token']
    assert token

    response = client.post(
        '/api/auth/login',
        data=json.dumps({
            'email': register_payload['email'],
            'password': register_payload['password'],
        }),
        content_type='application/json',
    )

    assert response.status_code == 200
    login_body = response.json()
    assert login_body['success'] is True
    assert login_body['token']
    assert login_body['user']['email'] == register_payload['email']

    response = client.get(
        '/api/auth/profile',
        HTTP_AUTHORIZATION=f'Bearer {login_body["token"]}',
    )

    assert response.status_code == 200
    assert response.json()['email'] == register_payload['email']


def test_INT_01_password_incorrecta_retorna_401(client):
    from api.tests.factories import UserFactory

    UserFactory(email='login.fail@plomaap.test')

    response = client.post(
        '/api/auth/login',
        data=json.dumps({
            'email': 'login.fail@plomaap.test',
            'password': 'PasswordIncorrecta!',
        }),
        content_type='application/json',
    )

    assert response.status_code == 401
    assert response.json()['success'] is False
