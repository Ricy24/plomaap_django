# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio de atributos de perfil y procedencia."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from api.models import ProfileAttribute
from api.services.profile_service import (
    VALID_SOURCES,
    _normalize_json_value,
    delete_entity_attributes,
    get_entity_attributes,
    record_attribute,
)
from api.tests.factories import ProfileAttributeFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# --------------------------------------------------------------------------- #
# _normalize_json_value
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    'value,expected',
    [
        (Decimal('2.00'), 2),
        (Decimal('2.50'), 2.5),
        (date(2026, 11, 2), '2026-11-02'),
        (datetime(2026, 11, 2, 9, 30), '2026-11-02T09:30:00'),
        ('texto', 'texto'),
        (10, 10),
        (None, None),
        (True, True),
    ],
)
def test_normalize_json_value_escalares(value, expected):
    assert _normalize_json_value(value) == expected


def test_normalize_json_value_dict_anidado():
    value = {'precio': Decimal('3.00'), 'fecha': date(2026, 1, 2)}

    assert _normalize_json_value(value) == {
        'precio': 3,
        'fecha': '2026-01-02',
    }


def test_normalize_json_value_lista_tupla_y_set():
    value = [Decimal('1.5'), (date(2026, 1, 1),), {Decimal('2.00')}]

    assert _normalize_json_value(value) == [
        1.5,
        ['2026-01-01'],
        [2],
    ]


# --------------------------------------------------------------------------- #
# record_attribute
# --------------------------------------------------------------------------- #
def test_record_attribute_crea_registro():
    ok = record_attribute(
        'home',
        1,
        'type',
        'apartment',
        source='onboarding',
        confidence=0.9,
    )

    assert ok is True
    attr = ProfileAttribute.objects.get()
    assert attr.entity_type == 'home'
    assert attr.entity_id == 1
    assert attr.attribute_key == 'type'
    assert attr.attribute_value == 'apartment'
    assert attr.source == 'onboarding'
    assert float(attr.confidence) == 0.9


def test_record_attribute_actualiza_si_ya_existe():
    record_attribute('home', 1, 'type', 'apartment')
    record_attribute('home', 1, 'type', 'house')

    assert ProfileAttribute.objects.count() == 1
    assert ProfileAttribute.objects.get().attribute_value == 'house'


def test_record_attribute_normaliza_el_valor():
    record_attribute('home', 1, 'area', Decimal('75.50'))

    assert ProfileAttribute.objects.get().attribute_value == 75.5


@pytest.mark.parametrize('source', ['', 'inventada', 'ONBOARDING', None])
def test_record_attribute_fuente_invalida_lanza_error(source):
    with pytest.raises(ValueError, match='no valida'):
        record_attribute('home', 1, 'type', 'apartment', source=source)


@pytest.mark.parametrize('confidence', [-0.1, 1.1, 2])
def test_record_attribute_confianza_fuera_de_rango(confidence):
    with pytest.raises(ValueError, match='fuera de rango'):
        record_attribute('home', 1, 'type', 'apartment', confidence=confidence)


@pytest.mark.parametrize('confidence', [0, 0.0, 1, 1.0, Decimal('0.500')])
def test_record_attribute_confianza_en_rango(confidence):
    assert record_attribute('home', 1, 'type', 'apartment', confidence=confidence)


def test_record_attribute_error_de_bd_relanza():
    with patch(
        'api.services.profile_service.ProfileAttribute.objects.update_or_create',
        side_effect=RuntimeError('boom'),
    ):
        with pytest.raises(RuntimeError, match='boom'):
            record_attribute('home', 1, 'type', 'apartment')


def test_todas_las_fuentes_declaradas_son_aceptadas():
    for source in VALID_SOURCES:
        assert record_attribute('user', 1, f'attr_{source}', 1, source=source)


# --------------------------------------------------------------------------- #
# get_entity_attributes
# --------------------------------------------------------------------------- #
def test_get_entity_attributes_retorna_diccionario():
    ProfileAttributeFactory(
        entity_type='home', entity_id=5, attribute_key='type', attribute_value='house'
    )
    ProfileAttributeFactory(
        entity_type='home', entity_id=5, attribute_key='zones', attribute_value=['bano']
    )
    ProfileAttributeFactory(entity_type='home', entity_id=6, attribute_key='otro')

    result = get_entity_attributes('home', 5)

    assert set(result) == {'type', 'zones'}
    assert result['type']['attribute_value'] == 'house'


def test_get_entity_attributes_sin_registros():
    assert get_entity_attributes('home', 999) == {}


def test_get_entity_attributes_convierte_entity_id_a_entero():
    ProfileAttributeFactory(entity_type='home', entity_id=8, attribute_key='type')

    assert 'type' in get_entity_attributes('home', '8')


# --------------------------------------------------------------------------- #
# delete_entity_attributes
# --------------------------------------------------------------------------- #
def test_delete_entity_attributes_elimina_los_de_la_entidad():
    ProfileAttributeFactory(entity_type='home', entity_id=1, attribute_key='a')
    ProfileAttributeFactory(entity_type='home', entity_id=1, attribute_key='b')
    ProfileAttributeFactory(entity_type='home', entity_id=2, attribute_key='c')

    deleted = delete_entity_attributes('home', 1)

    assert deleted == 2
    assert ProfileAttribute.objects.count() == 1


def test_delete_entity_attributes_sin_registros():
    assert delete_entity_attributes('home', 99) == 0


def test_delete_entity_attributes_error_relanza():
    manager = MagicMock()
    manager.filter.return_value.delete.side_effect = RuntimeError('boom')
    with patch('api.services.profile_service.ProfileAttribute.objects', manager):
        with pytest.raises(RuntimeError, match='boom'):
            delete_entity_attributes('home', 1)
