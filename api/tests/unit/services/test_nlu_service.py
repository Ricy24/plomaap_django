# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio NLU (Gemini + fallback determinista)."""
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from api.models import AppEvent
from api.services import nlu_service
from api.services.nlu_service import (
    _call_gemini_nlu,
    _fallback_local_nlu,
    _get_gemini_api_key,
    understand_text,
)
from api.tests.factories import AssetTypeCatalogFactory, ServiceFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

SERVICES = [
    {'id': 1, 'name': 'Fugas de agua', 'category': 'plumbing', 'description': 'Fugas', 'base_price': 80000.0},
    {'id': 2, 'name': 'Destapes', 'category': 'plumbing', 'description': 'Destapes', 'base_price': 90000.0},
    {'id': 3, 'name': 'Duchas y banos', 'category': 'plumbing', 'description': 'Duchas', 'base_price': 70000.0},
    {'id': 4, 'name': 'Instalaciones', 'category': 'gas', 'description': 'Instalaciones', 'base_price': 120000.0},
]

ASSETS = [
    {'id': 1, 'code': 'sanitario', 'name': 'Sanitario', 'category': 'plumbing'},
    {'id': 2, 'code': 'calentador', 'name': 'Calentador', 'category': 'gas'},
    {'id': 3, 'code': 'ducha', 'name': 'Ducha', 'category': 'plumbing'},
]


def create_catalog():
    ServiceFactory(id=1, name='Fugas de agua', category='plumbing', description='Fugas', base_price=80000)
    ServiceFactory(id=2, name='Destapes', category='plumbing', description='Destapes', base_price=90000)
    ServiceFactory(id=3, name='Duchas y banos', category='plumbing', description='Duchas', base_price=70000)
    ServiceFactory(id=4, name='Instalaciones', category='gas', description='Instalaciones', base_price=120000)
    AssetTypeCatalogFactory(id=1, code='sanitario', name='Sanitario', category='plumbing')
    AssetTypeCatalogFactory(id=2, code='calentador', name='Calentador', category='gas')
    AssetTypeCatalogFactory(id=3, code='ducha', name='Ducha', category='plumbing')


# --------------------------------------------------------------------------- #
# _get_gemini_api_key
# --------------------------------------------------------------------------- #
@override_settings(GEMINI_API_KEY='clave-gemini')
def test_get_gemini_api_key_desde_settings():
    assert _get_gemini_api_key() == 'clave-gemini'


@override_settings(GEMINI_API_KEY='')
def test_get_gemini_api_key_sin_configuracion(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with patch('dotenv.load_dotenv'):
        assert _get_gemini_api_key() is None


@override_settings(GEMINI_API_KEY='')
def test_get_gemini_api_key_si_dotenv_no_esta_disponible(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with patch.dict('sys.modules', {'dotenv': None}):
        assert _get_gemini_api_key() is None


# --------------------------------------------------------------------------- #
# _call_gemini_nlu
# --------------------------------------------------------------------------- #
def test_call_gemini_sin_api_key_retorna_none():
    with patch('api.services.nlu_service._get_gemini_api_key', return_value=None):
        assert _call_gemini_nlu('fuga', SERVICES, ASSETS) is None


def test_call_gemini_respuesta_exitosa_con_bloque_markdown():
    response = MagicMock(status_code=200)
    response.json.return_value = {
        'candidates': [
            {'content': {'parts': [{'text': '```json\n{"intent": "repair"}\n```'}]}}
        ]
    }

    with patch('api.services.nlu_service._get_gemini_api_key', return_value='clave'):
        with patch('api.services.nlu_service.requests.post', return_value=response):
            result = _call_gemini_nlu('fuga', SERVICES, ASSETS)

    assert result['intent'] == 'repair'
    assert result['_model_used'] == 'gemini-3.6-flash'


def test_call_gemini_respuesta_sin_candidatos_prueba_segundo_modelo():
    response = MagicMock(status_code=200)
    response.json.return_value = {'candidates': []}

    with patch('api.services.nlu_service._get_gemini_api_key', return_value='clave'):
        with patch(
            'api.services.nlu_service.requests.post', return_value=response
        ) as post:
            result = _call_gemini_nlu('fuga', SERVICES, ASSETS)

    assert result is None
    assert post.call_count == 2


def test_call_gemini_error_http_retorna_none():
    response = MagicMock(status_code=500, text='error')

    with patch('api.services.nlu_service._get_gemini_api_key', return_value='clave'):
        with patch('api.services.nlu_service.requests.post', return_value=response):
            assert _call_gemini_nlu('fuga', SERVICES, ASSETS) is None


def test_call_gemini_excepcion_retorna_none():
    with patch('api.services.nlu_service._get_gemini_api_key', return_value='clave'):
        with patch(
            'api.services.nlu_service.requests.post',
            side_effect=RuntimeError('sin red'),
        ):
            assert _call_gemini_nlu('fuga', SERVICES, ASSETS) is None


def test_call_gemini_json_invalido_retorna_none():
    response = MagicMock(status_code=200)
    response.json.return_value = {
        'candidates': [{'content': {'parts': [{'text': 'no-json'}]}}]
    }

    with patch('api.services.nlu_service._get_gemini_api_key', return_value='clave'):
        with patch('api.services.nlu_service.requests.post', return_value=response):
            assert _call_gemini_nlu('fuga', SERVICES, ASSETS) is None


# --------------------------------------------------------------------------- #
# _fallback_local_nlu
# --------------------------------------------------------------------------- #
def test_fallback_por_defecto_es_reparacion_de_fuga():
    result = _fallback_local_nlu('tengo un problema', SERVICES, ASSETS)

    assert result['intent'] == 'repair'
    assert result['issue'] == 'water_leak'
    assert result['urgency'] == 'medium'
    assert result['recommended_service_ids'] == [1]
    assert result['confidence'] == 0.88


def test_fallback_detecta_fuga_por_palabra_clave():
    result = _fallback_local_nlu('hay una fuga en la cocina', SERVICES, ASSETS)

    assert result['intent'] == 'repair'
    assert result['issue'] == 'water_leak'
    assert 'fuga' in result['symptoms']


def test_fallback_detecta_emergencia_por_inundacion():
    result = _fallback_local_nlu('se esta inundando el bano', SERVICES, ASSETS)

    assert result['intent'] == 'emergency'
    assert result['urgency'] == 'emergency'
    assert result['confidence'] == 0.95


def test_fallback_detecta_destape():
    result = _fallback_local_nlu('el sanitario esta tapado', SERVICES, ASSETS)

    assert result['intent'] == 'unblock'
    assert result['issue'] == 'blockage'
    assert result['urgency'] == 'high'
    assert result['recommended_service_ids'] == [2]


def test_fallback_detecta_instalacion_de_calentador():
    result = _fallback_local_nlu('quiero instalar un calentador', SERVICES, ASSETS)

    assert result['intent'] == 'installation'
    assert result['asset_code'] == 'calentador'
    assert result['recommended_service_ids'] == [4]


def test_fallback_detecta_activo_por_sinonimo_inodoro():
    result = _fallback_local_nlu('el inodoro no funciona', SERVICES, ASSETS)

    assert result['asset_code'] == 'sanitario'
    assert result['asset_id'] == 1


def test_fallback_detecta_activo_por_sinonimo_boiler():
    result = _fallback_local_nlu('el boiler no calienta', SERVICES, ASSETS)

    assert result['asset_code'] == 'calentador'


def test_fallback_prefill_incluye_el_texto():
    result = _fallback_local_nlu('hay una fuga', SERVICES, ASSETS)

    assert result['suggested_action']['prefill_notes'] == 'Solicitud asistida: hay una fuga'


def test_fallback_agravante_urgente():
    result = _fallback_local_nlu('necesito auxilio urgente', SERVICES, ASSETS)

    assert result['intent'] == 'emergency'
    assert result['urgency'] == 'emergency'


# --------------------------------------------------------------------------- #
# understand_text
# --------------------------------------------------------------------------- #
def test_understand_text_vacio_retorna_error():
    result = understand_text('   ')

    assert result == {
        'success': False,
        'error': 'El texto a analizar no puede estar vacío',
    }


def test_understand_text_usa_fallback_si_gemini_no_responde():
    create_catalog()

    with patch('api.services.nlu_service._call_gemini_nlu', return_value=None):
        result = understand_text('hay una fuga de agua', user_id=None)

    assert result['success'] is True
    assert result['provider'] == 'local-deterministic-rules'
    assert result['intent'] == 'repair'
    assert result['recommended_service_ids'] == [1]
    assert result['recommended_services'][0]['id'] == 1
    assert AppEvent.objects.filter(event_type='NLU_QUERY_PROCESSED').count() == 1


def test_understand_text_normaliza_intencion_y_urgencia_invalidas():
    create_catalog()

    gemini_data = {
        'intent': 'inventada',
        'urgency': 'altisima',
        'asset_id': 999,
        'asset_code': 'no-existe',
        'issue': 'water_leak',
        'confidence': 0.8,
        'recommended_service_ids': [2],
        'reasoning': 'porque si',
        'suggested_action': {},
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('texto')

    assert result['intent'] == 'repair'
    assert result['urgency'] == 'medium'
    assert result['asset'] is None
    assert result['asset_id'] is None
    assert result['recommended_service_ids'] == [2]


def test_understand_text_usa_modelo_gemini_reportado():
    create_catalog()
    gemini_data = {
        'intent': 'maintenance',
        'urgency': 'low',
        'recommended_service_ids': [1],
        '_model_used': 'gemini-3.5-flash-lite',
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('mantenimiento')

    assert result['provider'] == 'gemini-3.5-flash-lite'
    assert result['intent'] == 'maintenance'
    assert result['urgency'] == 'low'


def test_understand_text_resuelve_activo_por_codigo():
    create_catalog()
    gemini_data = {
        'intent': 'repair',
        'urgency': 'medium',
        'asset_code': 'ducha',
        'recommended_service_ids': [3],
        'reasoning': 'ducha rota',
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('la ducha esta rota')

    assert result['asset'] == 'ducha'
    assert result['asset_id'] == 3
    assert result['asset_name'] == 'Ducha'


def test_understand_text_agrega_activo_y_urgencia_al_prefill():
    create_catalog()
    gemini_data = {
        'intent': 'repair',
        'urgency': 'high',
        'asset_code': 'ducha',
        'recommended_service_ids': [3],
        'suggested_action': {'prefill_notes': 'Revisar ducha'},
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('la ducha esta rota')

    notes = result['suggested_action']['prefill_notes']
    assert 'Revisar ducha' in notes
    assert 'Activo: Ducha' in notes
    assert 'Urgencia: high' in notes


def test_understand_text_no_duplica_datos_en_prefill():
    create_catalog()
    gemini_data = {
        'intent': 'repair',
        'urgency': 'high',
        'asset_code': 'ducha',
        'recommended_service_ids': [3],
        'suggested_action': {'prefill_notes': 'Ducha con urgencia high'},
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('la ducha esta rota')

    assert result['suggested_action']['prefill_notes'] == 'Ducha con urgencia high'


def test_understand_text_normaliza_id_de_servicio_entero():
    create_catalog()
    gemini_data = {
        'intent': 'repair',
        'urgency': 'medium',
        'recommended_service_ids': 2,
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('destape')

    assert result['recommended_service_ids'] == [2]
    assert result['suggested_action']['target_service_id'] == 2


def test_understand_text_descarta_lista_de_servicios_invalida():
    create_catalog()
    gemini_data = {
        'intent': 'repair',
        'urgency': 'medium',
        'recommended_service_ids': 'todo',
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('problema')

    assert result['recommended_service_ids'] == [1]


def test_understand_text_sin_servicios_no_recomienda():
    gemini_data = {
        'intent': 'repair',
        'urgency': 'medium',
        'recommended_service_ids': [1],
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('problema')

    assert result['recommended_service_ids'] == []
    assert result['recommended_services'] == []
    assert result['suggested_action']['target_service_id'] == 1


def test_understand_text_tolera_fallo_al_registrar_evento():
    create_catalog()

    with patch('api.services.nlu_service._call_gemini_nlu', return_value=None):
        with patch(
            'api.services.nlu_service.track_event',
            side_effect=RuntimeError('bd caida'),
        ):
            result = understand_text('fuga')

    assert result['success'] is True


def test_understand_text_usa_notas_por_defecto():
    create_catalog()
    gemini_data = {
        'intent': 'repair',
        'urgency': 'medium',
        'recommended_service_ids': [1],
    }
    with patch('api.services.nlu_service._call_gemini_nlu', return_value=gemini_data):
        result = understand_text('fuga')

    assert result['suggested_action']['prefill_notes'].startswith('Diagnóstico PlomApp: fuga')


def test_understand_text_incluye_entidades_estructuradas():
    create_catalog()

    with patch('api.services.nlu_service._call_gemini_nlu', return_value=None):
        result = understand_text('el inodoro esta tapado')

    tipos = [entity['type'] for entity in result['entities'] if entity]
    assert {'asset', 'urgency', 'issue'} <= set(tipos)
