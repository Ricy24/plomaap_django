# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio de onboarding adaptativo."""
from unittest.mock import patch

import pytest

from api.models import (
    AppEvent,
    AssetTypeCatalog,
    Home,
    HomeAsset,
    HomeMember,
    HomeRoom,
    ProfileAttribute,
    RoomTypeCatalog,
)
from api.services.onboarding_service import (
    ONBOARDING_CONFIDENCE,
    complete_onboarding,
    get_adaptive_questions,
    get_user_onboarding_status,
    skip_onboarding,
    start_onboarding,
)
from api.tests.factories import (
    AssetTypeCatalogFactory,
    HomeFactory,
    ProfileAttributeFactory,
    RoomTypeCatalogFactory,
    UserFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def create_catalogs():
    RoomTypeCatalogFactory(code='bano', name='Baños')
    RoomTypeCatalogFactory(code='cocina', name='Cocina')
    AssetTypeCatalogFactory(code='ducha', name='Ducha', category='plumbing')
    AssetTypeCatalogFactory(code='calentador', name='Calentador', category='gas')


# --------------------------------------------------------------------------- #
# get_adaptive_questions
# --------------------------------------------------------------------------- #
def test_get_adaptive_questions_estructura_general():
    result = get_adaptive_questions()

    assert result['total_steps'] == 5
    assert len(result['questions']) == 5
    assert [q['step'] for q in result['questions']] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize('home_type', ['apartment', 'apartamento', 'APARTMENT'])
def test_get_adaptive_questions_variante_apartamento(home_type):
    result = get_adaptive_questions(home_type)
    question_3 = result['questions'][2]

    assert 'apartamento' in question_3['title']
    assert question_3['all_variants'] is not None


@pytest.mark.parametrize('home_type', ['house', 'casa', 'CASA'])
def test_get_adaptive_questions_variante_casa(home_type):
    result = get_adaptive_questions(home_type)

    assert 'casa' in result['questions'][2]['title']


@pytest.mark.parametrize('home_type', [None, '', 'other', 'castillo'])
def test_get_adaptive_questions_variante_por_defecto(home_type):
    result = get_adaptive_questions(home_type)
    question_3 = result['questions'][2]

    assert 'espacio' in question_3['title']


def test_get_adaptive_questions_pregunta_3_es_multiselect():
    result = get_adaptive_questions('house')

    assert result['questions'][2]['is_multi_select'] is True


# --------------------------------------------------------------------------- #
# get_user_onboarding_status
# --------------------------------------------------------------------------- #
def test_status_sin_atributo_ni_hogar():
    user = UserFactory()

    status = get_user_onboarding_status(user.id)

    assert status == {
        'completed': False,
        'skipped': False,
        'completed_at': None,
        'has_home': False,
    }


def test_status_detecta_hogar_existente():
    home = HomeFactory()

    status = get_user_onboarding_status(home.owner_id)

    assert status['has_home'] is True


def test_status_lee_atributo_de_onboarding():
    user = UserFactory()
    ProfileAttributeFactory(
        entity_type='user',
        entity_id=user.id,
        attribute_key='onboarding_status',
        attribute_value={
            'completed': True,
            'skipped': False,
            'completed_at': '2026-01-01T00:00:00',
        },
    )

    status = get_user_onboarding_status(user.id)

    assert status['completed'] is True
    assert status['skipped'] is False
    assert status['completed_at'] == '2026-01-01T00:00:00'


def test_status_con_valor_vacio():
    user = UserFactory()
    ProfileAttributeFactory(
        entity_type='user',
        entity_id=user.id,
        attribute_key='onboarding_status',
        attribute_value={},
    )

    status = get_user_onboarding_status(user.id)

    assert status['completed'] is False
    assert status['skipped'] is False


# --------------------------------------------------------------------------- #
# start_onboarding
# --------------------------------------------------------------------------- #
def test_start_onboarding_emite_evento_y_retorna_preguntas():
    user = UserFactory()

    with patch('api.services.onboarding_service.track_event') as track:
        result = start_onboarding(user.id, session_id='sesion-1')

    assert result['total_steps'] == 5
    track.assert_called_once()
    assert track.call_args.kwargs['event_type'] == 'ONBOARDING_STARTED'


def test_start_onboarding_tolera_error_del_evento():
    user = UserFactory()

    with patch(
        'api.services.onboarding_service.track_event',
        side_effect=RuntimeError('bd caida'),
    ):
        result = start_onboarding(user.id)

    assert result['total_steps'] == 5


# --------------------------------------------------------------------------- #
# skip_onboarding
# --------------------------------------------------------------------------- #
def test_skip_onboarding_guarda_estado():
    user = UserFactory()

    result = skip_onboarding(user.id, session_id='sesion-2')

    assert result == {
        'success': True,
        'message': 'Onboarding postergado exitosamente',
        'skipped': True,
    }
    attr = ProfileAttribute.objects.get(
        entity_type='user',
        entity_id=user.id,
        attribute_key='onboarding_status',
    )
    assert attr.attribute_value['skipped'] is True
    assert attr.attribute_value['completed'] is False
    assert attr.source == 'onboarding'
    assert float(attr.confidence) == 1.0


# --------------------------------------------------------------------------- #
# complete_onboarding
# --------------------------------------------------------------------------- #
def test_complete_onboarding_crea_hogar_habitaciones_y_activos():
    create_catalogs()
    user = UserFactory()

    result = complete_onboarding(
        user.id,
        {
            'home_type': 'casa',
            'needs_frequency': 'mantenimiento',
            'key_zones': ['bano', 'cocina', 'inventado'],
            'assets_present': ['ducha', 'no_estoy_seguro', 'inventado'],
            'maintenance_philosophy': 'preventivo',
        },
        session_id='sesion-3',
    )

    assert result['success'] is True
    assert result['onboarding_completed'] is True
    assert result['home']['type'] == 'house'
    assert result['home']['name'] == 'Mi Casa'
    assert result['home']['rooms_count'] == 3
    assert result['created_rooms_count'] == 2
    assert result['created_assets_count'] == 1

    home = Home.objects.get(owner_id=user.id)
    assert HomeMember.objects.filter(home=home, user=user, role='owner').exists()
    assert HomeRoom.objects.filter(home=home).count() == 2
    asset = HomeAsset.objects.get(home=home)
    assert asset.asset_type == 'ducha'
    assert asset.room.type == 'bano'


def test_complete_onboarding_registra_atributos_de_perfil():
    create_catalogs()
    user = UserFactory()

    complete_onboarding(
        user.id,
        {
            'home_type': 'apartment',
            'needs_frequency': 'emergencias',
            'key_zones': ['bano'],
            'assets_present': ['calentador'],
            'maintenance_philosophy': 'reactivo',
        },
    )

    home = Home.objects.get(owner_id=user.id)
    home_attrs = {
        a.attribute_key: a for a in ProfileAttribute.objects.filter(
            entity_type='home', entity_id=home.id
        )
    }
    user_attrs = {
        a.attribute_key: a for a in ProfileAttribute.objects.filter(
            entity_type='user', entity_id=user.id
        )
    }

    assert home_attrs['type'].attribute_value == 'apartment'
    assert home_attrs['key_zones'].attribute_value == ['bano']
    assert home_attrs['declared_assets'].attribute_value == ['calentador']
    assert user_attrs['needs_preference'].attribute_value == 'emergencias'
    assert user_attrs['maintenance_philosophy'].attribute_value == 'reactivo'
    assert user_attrs['onboarding_status'].attribute_value['completed'] is True
    assert float(user_attrs['needs_preference'].confidence) == ONBOARDING_CONFIDENCE


def test_complete_onboarding_registra_evento():
    create_catalogs()
    user = UserFactory()

    complete_onboarding(user.id, {'home_type': 'apartment', 'key_zones': ['bano']})

    event = AppEvent.objects.get(event_type='ONBOARDING_COMPLETED')
    assert event.user_id == user.id
    assert event.entity_type == 'home'
    assert event.metadata['home_type'] == 'apartment'


def test_complete_onboarding_reutiliza_hogar_existente():
    create_catalogs()
    home = HomeFactory(type='house', rooms_count=1)
    user = home.owner

    result = complete_onboarding(
        user.id,
        {
            'home_type': 'apartment',
            'key_zones': ['bano', 'cocina'],
            'assets_present': [],
        },
    )

    assert Home.objects.filter(owner_id=user.id).count() == 1
    home.refresh_from_db()
    assert home.type == 'apartment'
    assert home.rooms_count == 2
    assert result['created_rooms_count'] == 2


def test_complete_onboarding_no_duplica_habitaciones_existentes():
    create_catalogs()
    home = HomeFactory()
    HomeRoom.objects.create(home=home, name='Baños', type='bano')

    result = complete_onboarding(
        home.owner_id,
        {'home_type': 'apartment', 'key_zones': ['bano']},
    )

    assert result['created_rooms_count'] == 0
    assert HomeRoom.objects.filter(home=home, type='bano').count() == 1


def test_complete_onboarding_no_duplica_activos_existentes():
    create_catalogs()
    home = HomeFactory()
    HomeAsset.objects.create(home=home, asset_type='ducha')

    result = complete_onboarding(
        home.owner_id,
        {'home_type': 'apartment', 'assets_present': ['ducha']},
    )

    assert result['created_assets_count'] == 0
    assert HomeAsset.objects.filter(home=home, asset_type='ducha').count() == 1


def test_complete_onboarding_acepta_strings_simples():
    create_catalogs()
    user = UserFactory()

    result = complete_onboarding(
        user.id,
        {'home_type': 'apartamento', 'key_zones': 'bano', 'assets_present': 'ducha'},
    )

    assert result['created_rooms_count'] == 1
    assert result['created_assets_count'] == 1
    assert result['home']['name'] == 'Mi Apartamento'


def test_complete_onboarding_tipo_desconocido_usa_otro():
    user = UserFactory()

    result = complete_onboarding(user.id, {'home_type': 'castillo'})

    assert result['home']['type'] == 'apartment'
    assert result['home']['name'] == 'Mi Apartamento'


def test_complete_onboarding_sin_respuestas():
    user = UserFactory()

    result = complete_onboarding(user.id, None)

    assert result['success'] is True
    assert result['created_rooms_count'] == 0


def test_complete_onboarding_error_relanza():
    create_catalogs()
    user = UserFactory()

    with patch(
        'api.services.onboarding_service.record_attribute',
        side_effect=RuntimeError('boom'),
    ):
        with pytest.raises(RuntimeError, match='boom'):
            complete_onboarding(
                user.id,
                {'home_type': 'apartment', 'key_zones': ['bano']},
            )


def test_complete_onboarding_tolera_error_de_evento():
    create_catalogs()
    user = UserFactory()

    with patch(
        'api.services.onboarding_service.track_event',
        side_effect=RuntimeError('evento caido'),
    ):
        result = complete_onboarding(
            user.id,
            {'home_type': 'apartment', 'key_zones': ['bano']},
        )

    assert result['success'] is True
