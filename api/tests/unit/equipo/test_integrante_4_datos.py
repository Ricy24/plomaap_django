# -*- coding: utf-8 -*-
"""
Integrante 4 - Perfil, eventos y recomendaciones.

Cubre tres servicios de negocio que escriben en la base de datos:
``profile_service`` (atributos del hogar/usuario), ``event_service``
(bitácora de acciones) y ``recommendation_service`` (clics y sugerencias).
"""
import pytest

from api.models import AppEvent, ProfileAttribute
from api.services.event_service import track_event
from api.services.profile_service import (
    delete_entity_attributes,
    get_entity_attributes,
    record_attribute,
)
from api.services.recommendation_service import (
    generate_recommendations,
    track_recommendation_click,
)
from api.tests.factories import RecommendationEventFactory, ServiceFactory, UserFactory

pytestmark = pytest.mark.unit


def test_record_attribute_guarda_el_valor(db):
    """Un atributo nuevo se guarda y se puede consultar."""
    # Arrange - no se requiere preparación adicional

    # Act
    guardado = record_attribute('user', 1, 'ciudad', 'Bogota')

    # Assert
    atributos = get_entity_attributes('user', 1)
    assert guardado is True
    assert atributos['ciudad']['attribute_value'] == 'Bogota'
    assert atributos['ciudad']['source'] == 'explicit_user_input'


def test_record_attribute_actualiza_si_ya_existe(db):
    """Registrar dos veces la misma clave actualiza el valor, no duplica filas."""
    record_attribute('user', 1, 'ciudad', 'Bogota')

    record_attribute('user', 1, 'ciudad', 'Medellin')

    atributos = get_entity_attributes('user', 1)
    assert atributos['ciudad']['attribute_value'] == 'Medellin'
    assert ProfileAttribute.objects.filter(
        entity_type='user',
        entity_id=1,
        attribute_key='ciudad',
    ).count() == 1


def test_record_attribute_rechaza_fuente_invalida(db):
    """La fuente debe pertenecer al catálogo VALID_SOURCES."""
    with pytest.raises(ValueError, match='Fuente'):
        record_attribute('user', 1, 'ciudad', 'Bogota', source='whatsapp')


def test_record_attribute_rechaza_confianza_fuera_de_rango(db):
    """La confianza solo admite valores entre 0.0 y 1.0."""
    with pytest.raises(ValueError, match='Confianza'):
        record_attribute('user', 1, 'ciudad', 'Bogota', confidence=1.5)


def test_delete_entity_attributes_elimina_los_atributos(db):
    """Al borrar una entidad se eliminan todos sus atributos y se informa cuántos."""
    record_attribute('user', 1, 'ciudad', 'Bogota')
    record_attribute('user', 1, 'estrato', 3)

    eliminados = delete_entity_attributes('user', 1)

    assert eliminados == 2
    assert get_entity_attributes('user', 1) == {}


def test_track_event_crea_el_evento(db):
    """Un tipo de evento válido se registra en app_events."""
    evento = track_event(
        'SEARCH_PERFORMED',
        entity_type='service',
        entity_id=3,
        metadata={'texto': 'fuga de agua'},
    )

    assert evento is not None
    assert evento.event_type == 'SEARCH_PERFORMED'
    assert evento.metadata == {'texto': 'fuga de agua'}
    assert AppEvent.objects.count() == 1


def test_track_event_invalido_retorna_none(db):
    """Un tipo desconocido se ignora y no rompe la petición."""
    evento = track_event('EVENTO_QUE_NO_EXISTE')

    assert evento is None
    assert AppEvent.objects.count() == 0


def test_track_event_invalido_en_modo_estricto_lanza_error(db):
    """En modo estricto el tipo desconocido sí debe fallar."""
    with pytest.raises(ValueError, match='inválido'):
        track_event('EVENTO_QUE_NO_EXISTE', strict=True)


def test_click_en_recomendacion_se_registra(db):
    """Al hacer clic se marca la recomendación y se crea el evento asociado."""
    usuario = UserFactory()
    recomendacion = RecommendationEventFactory(user=usuario)

    registrado = track_recommendation_click(recomendacion.id, usuario.id)

    recomendacion.refresh_from_db()
    assert registrado is True
    assert recomendacion.clicked_at is not None
    assert AppEvent.objects.filter(event_type='SERVICE_CLICKED').count() == 1


def test_generate_recommendations_respeta_el_limite(db):
    """El servicio devuelve como máximo la cantidad solicitada."""
    ServiceFactory.create_batch(3)

    recomendaciones = generate_recommendations(user_id=None, limit=2)

    assert len(recomendaciones) == 2
