# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio de búsqueda híbrida (léxica + vectorial)."""
from unittest.mock import patch

import pytest

from api.services.hybrid_search_service import (
    _normalize_text,
    compute_lexical_score,
    detect_assets_and_symptoms,
    perform_hybrid_search,
)
from api.tests.factories import AssetTypeCatalogFactory, ServiceFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def create_catalog_services():
    return [
        ServiceFactory(
            id=1,
            name='Fugas de agua',
            category='plumbing',
            description='Reparacion de fugas y goteras',
            base_price=80000,
            duration_minutes=60,
        ),
        ServiceFactory(
            id=2,
            name='Destapes',
            category='plumbing',
            description='Destape de sanitarios y tuberias',
            base_price=90000,
            duration_minutes=90,
        ),
        ServiceFactory(
            id=3,
            name='Duchas y banos',
            category='plumbing',
            description='Instalacion y reparacion de duchas',
            base_price=70000,
            duration_minutes=60,
        ),
        ServiceFactory(
            id=4,
            name='Instalaciones',
            category='gas',
            description='Instalacion de calentadores y lavadoras',
            base_price=120000,
            duration_minutes=120,
        ),
    ]


# --------------------------------------------------------------------------- #
# _normalize_text
# --------------------------------------------------------------------------- #
def test_normalize_text_quita_acentos_y_pasa_a_minusculas():
    assert _normalize_text('AÑEJO Época') == 'anejo epoca'


def test_normalize_text_reemplaza_caracteres_especiales():
    assert _normalize_text('fuga!! en la ducha?') == 'fuga   en la ducha '


def test_normalize_text_recorta_espacios_exteriores():
    assert _normalize_text('  fuga  ') == 'fuga'


def test_normalize_text_convierte_a_string():
    assert _normalize_text(123) == '123'


# --------------------------------------------------------------------------- #
# detect_assets_and_symptoms
# --------------------------------------------------------------------------- #
def test_detect_assets_por_codigo():
    AssetTypeCatalogFactory(code='ducha', name='Ducha')

    result = detect_assets_and_symptoms('se rompio la ducha')

    assert [a['code'] for a in result['detected_assets']] == ['ducha']


def test_detect_assets_por_nombre():
    AssetTypeCatalogFactory(code='calentador', name='Calentador de agua')

    result = detect_assets_and_symptoms('el calentador de agua no enciende')

    assert result['detected_assets'][0]['code'] == 'calentador'


def test_detect_assets_por_sinonimo():
    AssetTypeCatalogFactory(code='sanitario', name='Sanitario')

    result = detect_assets_and_symptoms('el wc esta tapado')

    assert result['detected_assets'][0]['code'] == 'sanitario'


def test_detect_assets_ignora_inactivos():
    AssetTypeCatalogFactory(code='ducha', name='Ducha', is_active=False)

    result = detect_assets_and_symptoms('la ducha gotea')

    assert result['detected_assets'] == []


def test_detect_sintomas_por_palabra_clave():
    result = detect_assets_and_symptoms('hay una fuga de agua')

    assert 'fuga' in result['detected_symptoms']


def test_detect_sintomas_por_sinonimo():
    result = detect_assets_and_symptoms('el lavaplatos esta atascado')

    assert 'destape' in result['detected_symptoms']


def test_detect_assets_y_sintomas_multiples():
    AssetTypeCatalogFactory(code='ducha', name='Ducha')

    result = detect_assets_and_symptoms('la ducha esta rota y gotea')

    assert result['detected_assets'][0]['code'] == 'ducha'
    assert 'fuga' in result['detected_symptoms']
    assert 'reparacion' in result['detected_symptoms']


def test_detect_assets_retorna_tokens_normalizados():
    result = detect_assets_and_symptoms('Fuga en la DUCHA')

    assert 'ducha' in result['tokens']
    assert result['normalized_query'] == 'fuga en la ducha'


# --------------------------------------------------------------------------- #
# compute_lexical_score
# --------------------------------------------------------------------------- #
def test_compute_lexical_score_sin_tokens_retorna_cero():
    service = ServiceFactory(id=1, name='Fugas')

    score = compute_lexical_score(
        service, {'tokens': [], 'detected_symptoms': [], 'detected_assets': []}
    )

    assert score == 0.0


def test_compute_lexical_score_suma_coincidencia_en_nombre():
    service = ServiceFactory(id=1, name='Fugas de agua', description='', category='')

    score = compute_lexical_score(
        service,
        {'tokens': ['fugas'], 'detected_symptoms': [], 'detected_assets': []},
    )

    assert score == pytest.approx(0.35)


def test_compute_lexical_score_suma_coincidencia_en_descripcion():
    service = ServiceFactory(id=1, name='Servicio', description='fugas de agua', category='')

    score = compute_lexical_score(
        service,
        {'tokens': ['fugas'], 'detected_symptoms': [], 'detected_assets': []},
    )

    assert score == pytest.approx(0.2)


def test_compute_lexical_score_suma_coincidencia_en_categoria():
    service = ServiceFactory(id=1, name='Servicio', description='', category='plumbing')

    score = compute_lexical_score(
        service,
        {'tokens': ['plumbing'], 'detected_symptoms': [], 'detected_assets': []},
    )

    assert score == pytest.approx(0.25)


def test_compute_lexical_score_suma_afinidad_de_sintoma():
    service = ServiceFactory(id=1, name='Fugas', description='', category='')

    score = compute_lexical_score(
        service,
        {'tokens': ['zzz'], 'detected_symptoms': ['fuga'], 'detected_assets': []},
    )

    assert score == pytest.approx(0.65)


def test_compute_lexical_score_suma_afinidad_principal_de_activo():
    service = ServiceFactory(id=3, name='Duchas', description='', category='')

    score = compute_lexical_score(
        service,
        {
            'tokens': ['zzz'],
            'detected_symptoms': [],
            'detected_assets': [{'code': 'ducha', 'name': 'Ducha'}],
        },
    )

    assert score == pytest.approx(0.35)


def test_compute_lexical_score_suma_afinidad_secundaria_de_activo():
    service = ServiceFactory(id=1, name='Fugas', description='', category='')

    score = compute_lexical_score(
        service,
        {
            'tokens': ['zzz'],
            'detected_symptoms': [],
            'detected_assets': [{'code': 'ducha', 'name': 'Ducha'}],
        },
    )

    assert score == pytest.approx(0.2)


def test_compute_lexical_score_se_capa_en_uno():
    service = ServiceFactory(id=1, name='fuga', description='fuga fuga', category='fuga')

    score = compute_lexical_score(
        service,
        {
            'tokens': ['fuga', 'fuga2'],
            'detected_symptoms': ['fuga'],
            'detected_assets': [{'code': 'ducha', 'name': 'Ducha'}],
        },
    )

    assert score == 1.0


# --------------------------------------------------------------------------- #
# perform_hybrid_search
# --------------------------------------------------------------------------- #
def test_perform_hybrid_search_consulta_vacia_lista_todo():
    create_catalog_services()

    result = perform_hybrid_search('   ')

    assert result['query'] == ''
    assert result['total_results'] == 4
    assert all(item['hybrid_score'] == 1.0 for item in result['results'])
    assert result['results'][0]['match_reasons'] == ['Listado predeterminado']


def test_perform_hybrid_search_encuentra_por_sintoma():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('tengo una fuga de agua')

    assert result['total_results'] > 0
    assert result['results'][0]['service_id'] == 1
    assert 'Síntoma clave: fuga' in result['results'][0]['match_reasons']


def test_perform_hybrid_search_detecta_activos_en_la_respuesta():
    create_catalog_services()
    AssetTypeCatalogFactory(code='ducha', name='Ducha')

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('la ducha gotea')

    assert result['detected_assets'] == ['Ducha']
    assert any(
        'Afinidad con equipo: Ducha' in reason
        for item in result['results']
        for reason in item['match_reasons']
    )


def test_perform_hybrid_search_usa_resultados_vectoriales():
    create_catalog_services()

    def fake_search(**kwargs):
        return [
            {'entity_id': 1, 'similarity': 0.6},
            {'entity_id': 2, 'similarity': 0.3},
        ]

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        side_effect=fake_search,
    ):
        result = perform_hybrid_search('problema de agua')

    reasons = {item['service_id']: item['match_reasons'] for item in result['results']}
    assert 'Alta coincidencia semántica (60%)' in reasons[1]
    assert 'Coincidencia contextual (30%)' in reasons[2]


def test_perform_hybrid_search_sin_razones_usa_sugerencia_generica():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('xyz')

    assert all(
        'Sugerencia por especialidad' in item['match_reasons']
        for item in result['results']
    )


def test_perform_hybrid_search_filtra_por_categoria():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('servicio', category_filter='gas')

    assert result['total_results'] == 1
    assert result['results'][0]['service_id'] == 4


@pytest.mark.parametrize('category', ['todo', 'todos', '', None])
def test_perform_hybrid_search_categoria_todo_no_filtra(category):
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('servicio', category_filter=category)

    assert result['total_results'] == 4


def test_perform_hybrid_search_respeta_top_k():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('servicio', top_k=2)

    assert len(result['results']) == 2


def test_perform_hybrid_search_devuelve_campos_del_servicio():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('fuga')

    item = result['results'][0]
    assert item['name']
    assert item['service']['id'] == item['service_id']
    assert isinstance(item['base_price'], float)
    assert item['duration_minutes'] > 0


def test_perform_hybrid_search_tolera_error_vectorial():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        side_effect=RuntimeError('pgvector caido'),
    ):
        result = perform_hybrid_search('fuga de agua')

    assert result['total_results'] > 0
    assert result['results'][0]['vector_score'] == 0.0


def test_perform_hybrid_search_orden_descendente():
    create_catalog_services()

    with patch(
        'api.services.hybrid_search_service.search_similar_entities',
        return_value=[],
    ):
        result = perform_hybrid_search('fuga de agua')

    scores = [item['hybrid_score'] for item in result['results']]
    assert scores == sorted(scores, reverse=True)
