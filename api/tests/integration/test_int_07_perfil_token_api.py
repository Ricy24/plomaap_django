# -*- coding: utf-8 -*-
"""INT-07: el perfil exige iniciar sesión.

Idea en una frase: sin token no se puede ver el perfil; con token sí.
"""
import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_INT_07_perfil_sin_token_retorna_401(client):
    response = client.get('/api/auth/profile')

    assert response.status_code == 401


def test_INT_07_perfil_con_token_retorna_200(client, customer, auth_header):
    response = client.get('/api/auth/profile', **auth_header)

    assert response.status_code == 200
    assert response.json()['email'] == customer.email