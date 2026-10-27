# -*- coding: utf-8 -*-
"""Pruebas unitarias de los proveedores de embeddings (Voyage y local)."""
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.test import override_settings

from api.services.embedding_provider import (
    BaseEmbeddingProvider,
    DeterministicLocalEmbeddingProvider,
    VoyageEmbeddingProvider,
    get_embedding_provider,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Proveedor local determinista
# --------------------------------------------------------------------------- #
def test_proveedor_local_expone_nombre_y_dimension():
    provider = DeterministicLocalEmbeddingProvider()

    assert provider.model_name == 'local-hash-512'
    assert provider.dimension == 512


def test_proveedor_local_respeta_dimension_personalizada():
    provider = DeterministicLocalEmbeddingProvider(dimension=8, model='custom')

    assert provider.dimension == 8
    assert provider.model_name == 'custom'
    assert len(provider.embed_text('fuga')) == 8


def test_proveedor_local_vector_tiene_dimension_correcta():
    vector = DeterministicLocalEmbeddingProvider().embed_text('fuga de agua')

    assert len(vector) == 512


def test_proveedor_local_vector_esta_normalizado_l2():
    vector = DeterministicLocalEmbeddingProvider().embed_text('fuga de agua')

    norma = sum(x * x for x in vector) ** 0.5
    assert norma == pytest.approx(1.0, abs=1e-4)


def test_proveedor_local_es_determinista():
    provider = DeterministicLocalEmbeddingProvider()

    assert provider.embed_text('tuberia rota') == provider.embed_text('tuberia rota')


def test_proveedor_local_textos_distintos_generan_vectores_distintos():
    provider = DeterministicLocalEmbeddingProvider()

    assert provider.embed_text('ducha') != provider.embed_text('lavadora')


@pytest.mark.parametrize('text', ['', '   ', '\n\t'])
def test_proveedor_local_texto_vacio_retorna_ceros(text):
    vector = DeterministicLocalEmbeddingProvider(dimension=16).embed_text(text)

    assert vector == [0.0] * 16


def test_proveedor_local_embed_batch():
    provider = DeterministicLocalEmbeddingProvider(dimension=4)

    vectors = provider.embed_batch(['a', 'b', 'c'])

    assert len(vectors) == 3
    assert all(len(v) == 4 for v in vectors)


def test_proveedor_local_convierte_a_texto():
    vector = DeterministicLocalEmbeddingProvider(dimension=8).embed_text(12345)

    assert len(vector) == 8


def test_proveedor_local_vectores_que_se_cancelan_retornan_cero():
    # Con dimensión 1, 'aab' y 'aaa' tienen signos opuestos y el mismo peso.
    vector = DeterministicLocalEmbeddingProvider(dimension=1).embed_text('aab aaa')

    assert vector == [0.0]


# --------------------------------------------------------------------------- #
# Proveedor Voyage
# --------------------------------------------------------------------------- #
def test_voyage_sin_api_key_lanza_error(monkeypatch):
    monkeypatch.delenv('VOYAGE_API_KEY', raising=False)
    with override_settings(VOYAGE_API_KEY=''):
        with pytest.raises(ValueError, match='VOYAGE_API_KEY'):
            VoyageEmbeddingProvider(api_key='')


def test_voyage_expone_nombre_y_dimension():
    provider = VoyageEmbeddingProvider(api_key='clave', model='voyage-3-lite')

    assert provider.model_name == 'voyage-3-lite'
    assert provider.dimension == 512


def test_voyage_embed_batch_vacio_retorna_lista_vacia():
    provider = VoyageEmbeddingProvider(api_key='clave')

    assert provider.embed_batch([]) == []


def test_voyage_embed_text_usa_embed_batch():
    provider = VoyageEmbeddingProvider(api_key='clave')

    with patch.object(provider, 'embed_batch', return_value=[[1.0, 2.0]]) as batch:
        assert provider.embed_text('hola') == [1.0, 2.0]

    batch.assert_called_once_with(['hola'])


def test_voyage_embed_batch_exitoso():
    provider = VoyageEmbeddingProvider(api_key='clave')
    response = MagicMock(status_code=200)
    response.json.return_value = {'data': [{'embedding': [0.1, 0.2]}, {'embedding': [0.3]}]}

    with patch('api.services.embedding_provider.requests.post', return_value=response) as post:
        result = provider.embed_batch(['a', 'b'])

    assert result == [[0.1, 0.2], [0.3]]
    payload = post.call_args.kwargs['json']
    assert payload == {'input': ['a', 'b'], 'model': 'voyage-3-lite'}


def test_voyage_hace_strip_del_texto():
    provider = VoyageEmbeddingProvider(api_key='clave')
    response = MagicMock(status_code=200)
    response.json.return_value = {'data': [{'embedding': [1]}]}

    with patch('api.services.embedding_provider.requests.post', return_value=response) as post:
        provider.embed_batch(['  hola  '])

    assert post.call_args.kwargs['json']['input'] == ['hola']


def test_voyage_reintenta_tras_429():
    provider = VoyageEmbeddingProvider(api_key='clave')
    limited = MagicMock(status_code=429)
    ok = MagicMock(status_code=200)
    ok.json.return_value = {'data': [{'embedding': [1.0]}]}

    with patch('api.services.embedding_provider.requests.post', side_effect=[limited, ok]):
        with patch('api.services.embedding_provider.time.sleep') as sleep:
            result = provider.embed_batch(['a'])

    assert result == [[1.0]]
    sleep.assert_called_once_with(21)


def test_voyage_error_http_lanza_runtime_error():
    provider = VoyageEmbeddingProvider(api_key='clave')
    response = MagicMock(status_code=500, text='fallo interno')

    with patch('api.services.embedding_provider.requests.post', return_value=response):
        with pytest.raises(RuntimeError, match='Voyage API error: 500'):
            provider.embed_batch(['a'])


def test_voyage_reintenta_errores_de_red_y_luego_falla():
    provider = VoyageEmbeddingProvider(api_key='clave')

    with patch(
        'api.services.embedding_provider.requests.post',
        side_effect=requests.RequestException('sin red'),
    ) as post:
        with patch('api.services.embedding_provider.time.sleep') as sleep:
            with pytest.raises(requests.RequestException):
                provider.embed_batch(['a'])

    assert post.call_count == 3
    assert sleep.call_count == 2


def test_voyage_se_recupera_de_error_de_red():
    provider = VoyageEmbeddingProvider(api_key='clave')
    ok = MagicMock(status_code=200)
    ok.json.return_value = {'data': [{'embedding': [9.0]}]}

    with patch(
        'api.services.embedding_provider.requests.post',
        side_effect=[requests.RequestException('sin red'), ok],
    ):
        with patch('api.services.embedding_provider.time.sleep'):
            assert provider.embed_batch(['a']) == [[9.0]]


# --------------------------------------------------------------------------- #
# Fábrica get_embedding_provider
# --------------------------------------------------------------------------- #
@override_settings(VOYAGE_API_KEY='', EMBEDDING_PROVIDER='voyage')
def test_factory_sin_clave_retorna_proveedor_local(monkeypatch):
    monkeypatch.delenv('VOYAGE_API_KEY', raising=False)

    assert isinstance(get_embedding_provider(), DeterministicLocalEmbeddingProvider)


def test_factory_tipo_local_retorna_proveedor_local():
    provider = get_embedding_provider(provider_type='local')

    assert isinstance(provider, DeterministicLocalEmbeddingProvider)


@override_settings(VOYAGE_API_KEY='clave-secreta', EMBEDDING_PROVIDER='voyage')
def test_factory_con_clave_retorna_voyage():
    provider = get_embedding_provider()

    assert isinstance(provider, VoyageEmbeddingProvider)
    assert provider.api_key == 'clave-secreta'


@override_settings(VOYAGE_API_KEY='clave-secreta')
def test_factory_hace_fallback_si_voyage_falla():
    with patch(
        'api.services.embedding_provider.VoyageEmbeddingProvider',
        side_effect=RuntimeError('sin conexion'),
    ):
        provider = get_embedding_provider(provider_type='voyage')

    assert isinstance(provider, DeterministicLocalEmbeddingProvider)


def test_base_embedding_provider_es_abstracta():
    with pytest.raises(TypeError):
        BaseEmbeddingProvider()


def test_base_embedding_provider_metodos_abstractos_sin_cuerpo():
    assert BaseEmbeddingProvider.model_name.fget(object()) is None
    assert BaseEmbeddingProvider.dimension.fget(object()) is None
    assert BaseEmbeddingProvider.embed_text(object(), 'texto') is None
    assert BaseEmbeddingProvider.embed_batch(object(), ['texto']) is None


def test_voyage_todos_los_intentos_limitados_retorna_lista_vacia():
    provider = VoyageEmbeddingProvider(api_key='clave')
    limited = MagicMock(status_code=429)

    with patch('api.services.embedding_provider.requests.post', return_value=limited):
        with patch('api.services.embedding_provider.time.sleep') as sleep:
            assert provider.embed_batch(['a']) == []

    assert sleep.call_count == 3
