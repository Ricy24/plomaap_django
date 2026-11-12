# -*- coding: utf-8 -*-
"""INT-05: estado de salud de la API.

Idea en una frase: la API responde que está viva y conectada a la base de datos.
"""
import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_INT_05_health_responde_ok(client):
    response = client.get('/api/health')

    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'healthy'
    assert body['database'] == 'connected'