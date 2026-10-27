# -*- coding: utf-8 -*-
"""Pruebas unitarias del motor de recomendaciones."""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from api.models import AppEvent, RecommendationEvent, Service
from api.services.recommendation_service import (
    RECOMMENDATION_WEIGHTS,
    _popularity_map,
    _user_asset_codes,
    generate_recommendations,
    track_recommendation_click,
    track_recommendation_conversion,
)
from api.tests.factories import (
    AppEventFactory,
    AppointmentFactory,
    AssetTypeCatalogFactory,
    HomeAssetFactory,
    HomeFactory,
    HomeMemberFactory,
    RecommendationEventFactory,
    ServiceFactory,
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def create_services():
    ServiceFactory(id=1, name='Fugas de agua', category='plumbing')
    ServiceFactory(id=2, name='Destapes', category='plumbing')
    ServiceFactory(id=3, name='Duchas y banos', category='plumbing')
    ServiceFactory(id=4, name='Instalaciones', category='gas')


# --------------------------------------------------------------------------- #
# _user_asset_codes
# --------------------------------------------------------------------------- #
def test_user_asset_codes_sin_hogares():
    user = UserFactory()

    assert _user_asset_codes(user.id) == []


def test_user_asset_codes_desde_hogar_propio():
    home = HomeFactory()
    AssetTypeCatalogFactory(code='ducha', name='Ducha')
    HomeAssetFactory(home=home, asset_type='ducha')

    assert 'ducha' in _user_asset_codes(home.owner_id)


def test_user_asset_codes_desde_membresia():
    owner = UserFactory()
    member = UserFactory()
    home = HomeFactory(owner=owner)
    HomeMemberFactory(home=home, user=member)
    HomeAssetFactory(home=home, asset_type='lavadora')

    assert 'lavadora' in _user_asset_codes(member.id)


def test_user_asset_codes_incluye_codigos_fuera_del_catalogo():
    home = HomeFactory()
    HomeAssetFactory(home=home, asset_type='codigo_raro')

    assert 'codigo_raro' in _user_asset_codes(home.owner_id)


def test_user_asset_codes_no_mezcla_hogares_de_otros():
    other_home = HomeFactory()
    HomeAssetFactory(home=other_home, asset_type='calentador')
    user = UserFactory()

    assert _user_asset_codes(user.id) == []


# --------------------------------------------------------------------------- #
# _popularity_map
# --------------------------------------------------------------------------- #
def test_popularity_map_cuenta_eventos_de_reserva():
    AppEventFactory(event_type='SERVICE_BOOKED', entity_type='service', entity_id=1)
    AppEventFactory(event_type='SERVICE_BOOKED', entity_type='service', entity_id=1)
    AppEventFactory(event_type='BOOKING_CREATED', entity_type='service', entity_id=2)
    AppEventFactory(event_type='SERVICE_VIEWED', entity_type='service', entity_id=3)

    assert _popularity_map() == {1: 2, 2: 1}


def test_popularity_map_ignora_otras_entidades():
    AppEventFactory(event_type='SERVICE_BOOKED', entity_type='home', entity_id=9)

    assert _popularity_map() == {}


# --------------------------------------------------------------------------- #
# generate_recommendations
# --------------------------------------------------------------------------- #
def test_generate_recommendations_sin_usuario_no_crea_eventos():
    create_services()

    result = generate_recommendations(limit=2)

    assert len(result) == 2
    assert all(item['recommendation_id'] is None for item in result)
    assert RecommendationEvent.objects.count() == 0


def test_generate_recommendations_sin_servicios():
    assert generate_recommendations() == []


def test_generate_recommendations_crea_eventos_para_usuario():
    create_services()
    user = UserFactory()

    result = generate_recommendations(user.id, limit=3)

    assert len(result) == 3
    assert RecommendationEvent.objects.filter(user=user).count() == 3
    assert all(item['recommendation_id'] is not None for item in result)
    assert all(item['recommendation_score'] >= 0 for item in result)


def test_generate_recommendations_prioriza_activos_del_hogar():
    create_services()
    home = HomeFactory()
    AssetTypeCatalogFactory(code='ducha', name='Ducha')
    HomeAssetFactory(home=home, asset_type='ducha')

    result = generate_recommendations(home.owner_id, limit=4)
    by_id = {item['id']: item for item in result}

    assert 'equipos de plomería' in by_id[1]['recommendation_reason']
    assert 'mantenimiento preventivo de tus baños' in by_id[2]['recommendation_reason']
    assert 'cuidado de los baños' in by_id[3]['recommendation_reason']
    assert by_id[1]['recommendation_score'] > by_id[4]['recommendation_score']


def test_generate_recommendations_recomienda_instalaciones_por_calentador():
    create_services()
    home = HomeFactory()
    HomeAssetFactory(home=home, asset_type='calentador')

    result = generate_recommendations(home.owner_id, limit=4)
    svc4 = next(item for item in result if item['id'] == 4)

    assert 'electrodomésticos y equipos de gas' in svc4['recommendation_reason']


def test_generate_recommendations_penaliza_reserva_reciente():
    create_services()
    user = UserFactory()
    AppointmentFactory(
        user=user,
        service=Service.objects.get(pk=1),
        created_at=datetime.utcnow(),
    )

    result = generate_recommendations(user.id, limit=4)
    svc1 = next(item for item in result if item['id'] == 1)

    assert 'Agendaste este servicio recientemente' in svc1['recommendation_reason']


def test_generate_recommendations_ignora_reserva_antigua():
    create_services()
    user = UserFactory()
    AppointmentFactory(
        user=user,
        service=Service.objects.get(pk=1),
        created_at=datetime.utcnow() - timedelta(days=90),
    )

    result = generate_recommendations(user.id, limit=4)
    svc1 = next(item for item in result if item['id'] == 1)

    assert 'Agendaste este servicio recientemente' not in svc1['recommendation_reason']


def test_generate_recommendations_usa_historial_de_eventos():
    create_services()
    user = UserFactory()
    for _ in range(5):
        AppEventFactory(
            user=user,
            event_type='SERVICE_VIEWED',
            entity_type='service',
            entity_id=2,
        )

    result = generate_recommendations(user.id, limit=4)
    svc2 = next(item for item in result if item['id'] == 2)

    assert 'búsquedas e intereses recientes' in svc2['recommendation_reason']


def test_generate_recommendations_usa_popularidad():
    create_services()
    AppEventFactory(event_type='SERVICE_BOOKED', entity_type='service', entity_id=4)
    AppEventFactory(event_type='SERVICE_BOOKED', entity_type='service', entity_id=4)

    result = generate_recommendations(limit=4)

    assert result[0]['id'] == 4


def test_generate_recommendations_fallback_ante_error():
    create_services()
    user = UserFactory()

    with patch(
        'api.services.recommendation_service._popularity_map',
        side_effect=RuntimeError('boom'),
    ):
        result = generate_recommendations(user.id, limit=2)

    assert len(result) == 2
    assert all(item['recommendation_score'] == 0.0 for item in result)
    assert all(item['recommendation_reason'] == 'Recomendación general.' for item in result)


def test_pesos_de_recomendacion_suman_uno():
    assert sum(RECOMMENDATION_WEIGHTS.values()) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# track_recommendation_click
# --------------------------------------------------------------------------- #
def test_track_click_marca_evento_y_crea_app_event():
    user = UserFactory()
    rec = RecommendationEventFactory(user=user, entity_id=3)

    assert track_recommendation_click(rec.id, user.id) is True

    rec.refresh_from_db()
    assert rec.clicked_at is not None
    assert AppEvent.objects.filter(
        user=user, event_type='SERVICE_CLICKED', entity_id=3
    ).exists()


def test_track_click_no_repite():
    user = UserFactory()
    rec = RecommendationEventFactory(user=user)

    assert track_recommendation_click(rec.id, user.id) is True
    assert track_recommendation_click(rec.id, user.id) is False


def test_track_click_inexistente_retorna_false():
    assert track_recommendation_click(999999, 1) is False


def test_track_click_de_otro_usuario_retorna_false():
    rec = RecommendationEventFactory(user=UserFactory())

    assert track_recommendation_click(rec.id, 999999) is False


def test_track_click_tolera_error():
    with patch(
        'api.services.recommendation_service.RecommendationEvent.objects.filter',
        side_effect=RuntimeError('bd caida'),
    ):
        assert track_recommendation_click(1, 1) is False


# --------------------------------------------------------------------------- #
# track_recommendation_conversion
# --------------------------------------------------------------------------- #
def test_track_conversion_marca_evento():
    user = UserFactory()
    rec = RecommendationEventFactory(user=user)

    assert track_recommendation_conversion(rec.id, user.id) is True

    rec.refresh_from_db()
    assert rec.converted_at is not None


def test_track_conversion_no_repite():
    user = UserFactory()
    rec = RecommendationEventFactory(user=user)

    assert track_recommendation_conversion(rec.id, user.id) is True
    assert track_recommendation_conversion(rec.id, user.id) is False


def test_track_conversion_inexistente_retorna_false():
    assert track_recommendation_conversion(999999, 1) is False


def test_track_conversion_tolera_error():
    with patch(
        'api.services.recommendation_service.RecommendationEvent.objects.filter',
        side_effect=RuntimeError('bd caida'),
    ):
        assert track_recommendation_conversion(1, 1) is False
