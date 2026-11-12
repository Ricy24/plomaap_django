# -*- coding: utf-8 -*-
"""INT-08: guardar una dirección.

Idea en una frase: el cliente guarda una dirección y queda registrada
en la base de datos.
"""
import json

import pytest

from api.models import UserAddress

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def test_INT_08_guardar_direccion_retorna_201(client, customer, auth_header):
    response = client.post(
        '/api/user/addresses',
        data=json.dumps({'label': 'Casa', 'address': 'Calle 1 #2-3'}),
        content_type='application/json',
        **auth_header,
    )

    assert response.status_code == 201
    assert UserAddress.objects.filter(user_id=customer.id, address='Calle 1 #2-3').exists()