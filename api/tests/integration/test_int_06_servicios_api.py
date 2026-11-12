# -*- coding: utf-8 -*-
"""INT-06: listado de servicios.

Idea en una frase: si hay un servicio guardado en la base de datos,
la API lo devuelve en el listado.
"""
import pytest

from api.tests.factories import ServiceFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_INT_06_listado_devuelve_el_servicio_creado(client):
    ServiceFactory(name='Destape de tuberías')

    response = client.get('/api/services')

    assert response.status_code == 200
    nombres = [servicio['name'] for servicio in response.json()['services']]
    assert 'Destape de tuberías' in nombres