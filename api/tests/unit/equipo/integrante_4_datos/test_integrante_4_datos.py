"""Pruebas base de normalización de perfiles y registro de eventos."""
from datetime import date
from decimal import Decimal

import pytest

from api.models import AppEvent, ProfileAttribute
from api.services.event_service import track_event
from api.services.profile_service import delete_entity_attributes, record_attribute

pytestmark = pytest.mark.unit


@pytest.mark.django_db
def test_decimal_entero_se_guarda_como_entero():
    """Caso: valor decimal sin fracción.
    Entrada: Decimal('25.00') en un atributo de perfil.
    Esperado: el JSON almacenado contiene el entero 25.
    Cubre: api/services/profile_service.py::record_attribute
    """
    record_attribute('home', 1, 'area', Decimal('25.00'))

    assert ProfileAttribute.objects.get().attribute_value == 25


@pytest.mark.django_db
def test_decimal_con_fraccion_conserva_decimales():
    """Caso: valor decimal con fracción.
    Entrada: Decimal('25.75') en un atributo de perfil.
    Esperado: el JSON almacenado conserva el valor 25.75.
    Cubre: api/services/profile_service.py::record_attribute
    """
    record_attribute('home', 1, 'area', Decimal('25.75'))

    assert ProfileAttribute.objects.get().attribute_value == 25.75


@pytest.mark.django_db
def test_fecha_se_guarda_en_iso():
    """Caso: una fecha nativa se normaliza al formato ISO.
    Entrada: date(2026, 11, 6) en un atributo de perfil.
    Esperado: el JSON almacenado contiene '2026-11-06'.
    Cubre: api/services/profile_service.py::record_attribute
    """
    record_attribute('home', 1, 'renovation_date', date(2026, 11, 6))

    assert ProfileAttribute.objects.get().attribute_value == '2026-11-06'


@pytest.mark.django_db
def test_segundo_registro_actualiza_sin_duplicar():
    """Caso: se registra dos veces la misma clave de entidad.
    Entrada: dos valores para home 1 y la clave 'type'.
    Esperado: existe un solo registro y contiene el último valor.
    Cubre: api/services/profile_service.py::record_attribute
    """
    record_attribute('home', 1, 'type', 'apartment')
    record_attribute('home', 1, 'type', 'house')

    assert ProfileAttribute.objects.count() == 1
    assert ProfileAttribute.objects.get().attribute_value == 'house'


@pytest.mark.django_db
def test_fuente_fuera_del_catalogo_es_rechazada():
    """Caso: se intenta guardar un atributo con una fuente no permitida.
    Entrada: source='unknown'.
    Esperado: record_attribute lanza ValueError antes de guardar.
    Cubre: api/services/profile_service.py::record_attribute
    """
    with pytest.raises(ValueError, match='no valida'):
        record_attribute('home', 1, 'type', 'house', source='unknown')

    assert ProfileAttribute.objects.count() == 0


@pytest.mark.django_db
def test_confianza_fuera_de_rango_es_rechazada():
    """Caso: se intenta guardar confianza superior al máximo permitido.
    Entrada: confidence=1.1.
    Esperado: record_attribute lanza ValueError y no crea el atributo.
    Cubre: api/services/profile_service.py::record_attribute
    """
    with pytest.raises(ValueError, match='fuera de rango'):
        record_attribute('home', 1, 'type', 'house', confidence=1.1)

    assert ProfileAttribute.objects.count() == 0


@pytest.mark.django_db
def test_eliminar_atributos_devuelve_la_cantidad():
    """Caso: se eliminan atributos de una entidad específica.
    Entrada: dos atributos de home 1 y uno de home 2.
    Esperado: devuelve 2 y conserva el registro de home 2.
    Cubre: api/services/profile_service.py::delete_entity_attributes
    """
    record_attribute('home', 1, 'type', 'house')
    record_attribute('home', 1, 'area', 80)
    record_attribute('home', 2, 'type', 'apartment')

    assert delete_entity_attributes('home', 1) == 2
    assert list(ProfileAttribute.objects.values_list('entity_id', flat=True)) == [2]


@pytest.mark.django_db
def test_evento_invalido_no_lanza_sin_strict():
    """Caso: se registra un evento que no pertenece al catálogo.
    Entrada: event_type='UNKNOWN_EVENT' y strict=False.
    Esperado: devuelve None y no persiste eventos.
    Cubre: api/services/event_service.py::track_event
    """
    resultado = track_event('UNKNOWN_EVENT')

    assert resultado is None
    assert AppEvent.objects.count() == 0


@pytest.mark.django_db
def test_evento_invalido_lanza_en_strict():
    """Caso: un evento inválido se registra con modo estricto.
    Entrada: event_type='UNKNOWN_EVENT' y strict=True.
    Esperado: lanza ValueError y no persiste eventos.
    Cubre: api/services/event_service.py::track_event
    """
    with pytest.raises(ValueError, match='Tipo de evento inválido'):
        track_event('UNKNOWN_EVENT', strict=True)

    assert AppEvent.objects.count() == 0


@pytest.mark.django_db
def test_metadata_vacia_se_guarda_como_dict():
    """Caso: se registra un evento sin metadatos explícitos.
    Entrada: event_type='SERVICE_VIEWED' y metadata=None.
    Esperado: el evento persistido contiene un diccionario vacío.
    Cubre: api/services/event_service.py::track_event
    """
    evento = track_event('SERVICE_VIEWED')

    assert evento.metadata == {}
    assert AppEvent.objects.get().metadata == {}
