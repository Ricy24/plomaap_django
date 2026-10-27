# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio de registro de eventos."""
from unittest.mock import patch

import pytest

from api.models import AppEvent
from api.services.event_service import VALID_EVENT_TYPES, track_event

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_track_event_crea_evento_valido():
    event = track_event(
        'SERVICE_VIEWED',
        user_id=None,
        entity_type='service',
        entity_id=7,
        session_id='sesion-1',
        metadata={'origin': 'test'},
    )

    assert event is not None
    assert event.event_type == 'SERVICE_VIEWED'
    assert event.entity_id == 7
    assert event.metadata == {'origin': 'test'}
    assert AppEvent.objects.count() == 1


def test_track_event_sin_metadata_guarda_dict_vacio():
    event = track_event('USER_REGISTERED')

    assert event.metadata == {}


def test_track_event_tipo_invalido_retorna_none():
    assert track_event('NO_EXISTE') is None
    assert AppEvent.objects.count() == 0


def test_track_event_tipo_invalido_estricto_lanza_error():
    with pytest.raises(ValueError, match='Tipo de evento inválido'):
        track_event('NO_EXISTE', strict=True)


def test_track_event_error_de_bd_retorna_none():
    with patch(
        'api.services.event_service.AppEvent.objects.create',
        side_effect=RuntimeError('boom'),
    ):
        assert track_event('SERVICE_VIEWED') is None


def test_track_event_error_de_bd_estricto_relanza():
    with patch(
        'api.services.event_service.AppEvent.objects.create',
        side_effect=RuntimeError('boom'),
    ):
        with pytest.raises(RuntimeError, match='boom'):
            track_event('SERVICE_VIEWED', strict=True)


def test_catalogo_de_eventos_contiene_los_flujos_principales():
    assert {'USER_REGISTERED', 'BOOKING_CREATED', 'ONBOARDING_COMPLETED'} <= VALID_EVENT_TYPES
