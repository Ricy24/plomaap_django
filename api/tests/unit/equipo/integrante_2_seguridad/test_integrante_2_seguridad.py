# -*- coding: utf-8 -*-
"""
Integrante 2 - Seguridad y sesión.

Cubre la creación/lectura de tokens JWT (``api/utils/jwt_utils.py``) y los
decoradores de autorización (``api/utils/decorators.py``). Se usa
``RequestFactory`` para simular peticiones HTTP sin levantar el servidor.
"""
import json
from datetime import datetime, timedelta

import jwt
import pytest
from django.conf import settings
from django.http import JsonResponse
from django.test import RequestFactory

from api.tests.factories import UserFactory
from api.utils.decorators import admin_only, jwt_optional, jwt_required_custom
from api.utils.jwt_utils import (
    decode_token,
    generate_token,
    get_current_user_id,
    get_token_from_request,
)

pytestmark = pytest.mark.unit


def test_generar_token_devuelve_texto():
    """Un token JWT es una cadena de texto."""
    token = generate_token(1)

    assert isinstance(token, str)
    assert token.count('.') == 2


def test_token_contiene_id_del_usuario():
    """El claim ``sub`` guarda el id del usuario como texto."""
    token = generate_token(42)

    payload = decode_token(token)

    assert payload is not None
    assert payload['sub'] == '42'


def test_token_alterado_es_rechazado():
    """Si se modifica el token, la firma deja de ser válida."""
    token = generate_token(7)

    assert decode_token(token + 'x') is None


def test_token_expirado_es_rechazado():
    """Un token con ``exp`` en el pasado no debe aceptarse."""
    payload = {
        'sub': '1',
        'exp': datetime.utcnow() - timedelta(minutes=5),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    assert decode_token(token) is None


def test_extraer_token_con_bearer():
    """El encabezado Authorization usa el formato ``Bearer <token>``."""
    request = RequestFactory().get(
        '/perfil/',
        HTTP_AUTHORIZATION='Bearer abc.def.ghi',
    )

    assert get_token_from_request(request) == 'abc.def.ghi'


def test_extraer_token_sin_encabezado_retorna_none():
    """Sin encabezado Authorization no hay token que extraer."""
    request = RequestFactory().get('/perfil/')

    assert get_token_from_request(request) is None


def test_get_current_user_id_devuelve_entero():
    """El id del usuario se recupera como entero desde el token."""
    request = RequestFactory().get(
        '/perfil/',
        HTTP_AUTHORIZATION=f'Bearer {generate_token(25)}',
    )

    assert get_current_user_id(request) == 25


def test_decorador_sin_token_responde_401(db):
    """Una vista protegida no debe ejecutarse si falta el token."""
    request = RequestFactory().get('/perfil/')

    @jwt_required_custom
    def vista(request, user):
        return JsonResponse({'ok': True})

    respuesta = vista(request)

    assert respuesta.status_code == 401


def test_admin_only_rechaza_a_un_cliente(db):
    """Un usuario con rol customer no puede entrar a una vista de admin."""
    cliente = UserFactory(role='customer')
    request = RequestFactory().get(
        '/admin/',
        HTTP_AUTHORIZATION=f'Bearer {generate_token(cliente.id)}',
    )

    @admin_only
    def vista(request, user):
        return JsonResponse({'ok': True})

    respuesta = vista(request)

    assert respuesta.status_code == 403


def test_jwt_optional_permite_peticion_sin_token(db):
    """La vista opcional se ejecuta y deja ``jwt_user`` en None."""
    request = RequestFactory().get('/servicios/')

    @jwt_optional
    def vista(request):
        return JsonResponse({'tiene_usuario': request.jwt_user is not None})

    respuesta = vista(request)

    assert respuesta.status_code == 200
    assert json.loads(respuesta.content) == {'tiene_usuario': False}