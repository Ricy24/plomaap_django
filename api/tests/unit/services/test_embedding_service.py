# -*- coding: utf-8 -*-
"""Pruebas unitarias del servicio de embeddings y búsqueda vectorial."""
import json
from unittest.mock import MagicMock, patch

import pytest

from api.models import EntityEmbedding
from api.services import embedding_service
from api.services.embedding_service import (
    _cosine_similarity,
    _is_postgres,
    _parse_vector,
    _pgvector_available,
    _vector_to_sql_str,
    search_similar_entities,
    store_entity_embedding,
    sync_catalog_embeddings,
)
from api.tests.factories import (
    AssetTypeCatalogFactory,
    EntityEmbeddingFactory,
    ServiceFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class StubProvider:
    """Proveedor de embeddings controlado para pruebas deterministas."""

    model_name = 'stub-model'
    dimension = 3

    def __init__(self, vector=None):
        self.vector = vector or [1.0, 0.0, 0.0]

    def embed_text(self, text):
        return list(self.vector)

    def embed_batch(self, texts):
        return [list(self.vector) for _ in texts]


@pytest.fixture(autouse=True)
def reset_vector_cache():
    embedding_service._VECTOR_TYPE_OK = None
    yield
    embedding_service._VECTOR_TYPE_OK = None


def _cursor_context(cursor):
    manager = MagicMock()
    manager.__enter__.return_value = cursor
    manager.__exit__.return_value = False
    return manager


def _fake_connection(cursor):
    """Conexión falsa que aísla el cursor simulado del resto del ORM."""
    fake = MagicMock()
    fake.cursor.return_value = _cursor_context(cursor)
    return fake


def _failing_connection(error):
    fake = MagicMock()
    fake.cursor.side_effect = error
    return fake


# --------------------------------------------------------------------------- #
# Utilidades vectoriales puras
# --------------------------------------------------------------------------- #
def test_vector_to_sql_str_formatea_con_seis_decimales():
    assert _vector_to_sql_str([0.1234567, 1.0, -0.5]) == '[0.123457,1.0,-0.5]'


def test_vector_to_sql_str_convierte_enteros_y_strings():
    assert _vector_to_sql_str([1, '2.5']) == '[1.0,2.5]'


@pytest.mark.parametrize(
    'value,expected',
    [
        ([1, 2, 3], [1.0, 2.0, 3.0]),
        ((1.5, 2.5), [1.5, 2.5]),
        ('[1, 2, 3]', [1, 2, 3]),
        ('[0.1,0.2]', [0.1, 0.2]),
        ('', None),
        (None, None),
        ('no-es-json', None),
        ('{invalido}', None),
    ],
)
def test_parse_vector(value, expected):
    assert _parse_vector(value) == expected


def test_cosine_similarity_vectores_iguales():
    assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)


def test_cosine_similarity_vectores_ortogonales():
    assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_calcula_angulo():
    assert _cosine_similarity([1, 1], [1, 0]) == pytest.approx(0.7071, abs=1e-4)


@pytest.mark.parametrize(
    'a,b',
    [
        (None, [1]),
        ([1], None),
        ([], []),
        ([1, 2], [1]),
        ([0, 0], [1, 0]),
        ([1, 0], [0, 0]),
    ],
)
def test_cosine_similarity_casos_invalidos_retornan_cero(a, b):
    assert _cosine_similarity(a, b) == 0.0


def test_is_postgres_refleja_el_motor():
    from django.db import connection

    assert _is_postgres() is (connection.vendor == 'postgresql')


# --------------------------------------------------------------------------- #
# Detección de pgvector
# --------------------------------------------------------------------------- #
def test_pgvector_no_disponible_en_sqlite():
    assert _pgvector_available() is False


def test_pgvector_cachea_el_resultado_negativo():
    assert _pgvector_available() is False
    assert embedding_service._VECTOR_TYPE_OK is False
    assert _pgvector_available() is False


def test_pgvector_disponible_en_postgres():
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)

    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(
            embedding_service, 'connection', _fake_connection(cursor)
        ):
            assert _pgvector_available() is True


def test_pgvector_ausente_en_postgres():
    cursor = MagicMock()
    cursor.fetchone.return_value = None

    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(
            embedding_service, 'connection', _fake_connection(cursor)
        ):
            assert _pgvector_available() is False


def test_pgvector_error_de_consulta_retorna_false():
    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(
            embedding_service, 'connection', _failing_connection(RuntimeError('boom'))
        ):
            assert _pgvector_available() is False


# --------------------------------------------------------------------------- #
# store_entity_embedding
# --------------------------------------------------------------------------- #
def test_store_entity_embedding_texto_vacio_lanza_error():
    with pytest.raises(ValueError, match='content_text no puede estar vacío'):
        store_entity_embedding('service', 1, '   ', provider=StubProvider())


def test_store_entity_embedding_guarda_vector_precalculado():
    ok = store_entity_embedding(
        'service', 1, 'Servicio de prueba', provider=StubProvider(), precomputed_vector=[1, 2, 3]
    )

    assert ok is True
    row = EntityEmbedding.objects.get()
    assert row.entity_type == 'service'
    assert row.entity_id == 1
    assert row.content_text == 'Servicio de prueba'
    assert row.embedding == '[1.0,2.0,3.0]'
    assert row.model_name == 'stub-model'
    assert row.dimension == 3


def test_store_entity_embedding_calcula_vector_si_no_se_provee():
    ok = store_entity_embedding('service', 2, 'Ducha', provider=StubProvider([0.5, 0.5, 0.5]))

    assert ok is True
    assert EntityEmbedding.objects.get().embedding == '[0.5,0.5,0.5]'


def test_store_entity_embedding_hace_upsert():
    store_entity_embedding('service', 1, 'Primero', provider=StubProvider())
    store_entity_embedding('service', 1, 'Segundo', provider=StubProvider())

    assert EntityEmbedding.objects.count() == 1
    assert EntityEmbedding.objects.get().content_text == 'Segundo'


def test_store_entity_embedding_commit_false():
    ok = store_entity_embedding(
        'service', 3, 'Sin commit', provider=StubProvider(), commit=False
    )

    assert ok is True
    assert EntityEmbedding.objects.count() == 1


def test_store_entity_embedding_usa_proveedor_por_defecto():
    with patch(
        'api.services.embedding_service.get_embedding_provider',
        return_value=StubProvider(),
    ) as factory:
        assert store_entity_embedding('service', 4, 'Texto') is True

    factory.assert_called_once()


def test_store_entity_embedding_error_de_bd_relanza():
    with patch(
        'api.services.embedding_service.EntityEmbedding.objects.update_or_create',
        side_effect=RuntimeError('boom'),
    ):
        with pytest.raises(RuntimeError, match='boom'):
            store_entity_embedding('service', 1, 'Texto', provider=StubProvider())


@pytest.mark.parametrize('commit', [True, False])
def test_store_entity_embedding_ruta_postgres(commit):
    cursor = MagicMock()

    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(embedding_service, '_pgvector_available', return_value=True):
            with patch.object(
                embedding_service, 'connection', _fake_connection(cursor)
            ):
                ok = store_entity_embedding(
                    'service', 1, 'Texto', provider=StubProvider(), commit=commit
                )

    assert ok is True
    sqls = [call.args[0] for call in cursor.execute.call_args_list]
    assert any('CAST(%(embedding)s AS vector)' in sql for sql in sqls)


# --------------------------------------------------------------------------- #
# search_similar_entities
# --------------------------------------------------------------------------- #
def test_search_similar_entities_texto_vacio_retorna_lista():
    assert search_similar_entities('   ', provider=StubProvider()) == []


def test_search_similar_entities_sin_embeddings_retorna_lista():
    assert search_similar_entities('fuga', provider=StubProvider()) == []


def test_search_similar_entities_ordena_por_similitud():
    service = ServiceFactory(id=1, name='Fugas')
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=service.id,
        model_name='stub-model',
        embedding='[1.0,0.0,0.0]',
        dimension=3,
    )
    other = ServiceFactory(id=2, name='Otro')
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=other.id,
        model_name='stub-model',
        embedding='[0.0,1.0,0.0]',
        dimension=3,
    )

    results = search_similar_entities('fuga', provider=StubProvider())

    assert [r['entity_id'] for r in results] == [1, 2]
    assert results[0]['similarity'] == 1.0
    assert results[1]['similarity'] == 0.0
    assert results[0]['entity']['name'] == 'Fugas'


def test_search_similar_entities_filtra_por_entity_type():
    service = ServiceFactory(id=1)
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=service.id,
        model_name='stub-model',
        embedding='[1.0,0.0,0.0]',
        dimension=3,
    )
    EntityEmbeddingFactory(
        entity_type='asset_type',
        entity_id=1,
        model_name='stub-model',
        embedding='[1.0,0.0,0.0]',
        dimension=3,
    )

    results = search_similar_entities('fuga', entity_type='asset_type', provider=StubProvider())

    assert len(results) == 1
    assert results[0]['entity_type'] == 'asset_type'


def test_search_similar_entities_resuelve_activos():
    asset = AssetTypeCatalogFactory(id=1, code='ducha', name='Ducha')
    EntityEmbeddingFactory(
        entity_type='asset_type',
        entity_id=asset.id,
        model_name='stub-model',
        embedding='[1.0,0.0,0.0]',
        dimension=3,
    )

    results = search_similar_entities('ducha', provider=StubProvider())

    assert results[0]['entity']['code'] == 'ducha'


def test_search_similar_entities_respeta_min_similarity():
    service = ServiceFactory(id=1)
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=service.id,
        model_name='stub-model',
        embedding='[0.0,1.0,0.0]',
        dimension=3,
    )

    assert search_similar_entities(
        'fuga', provider=StubProvider(), min_similarity=0.5
    ) == []


def test_search_similar_entities_respeta_top_k():
    for index in range(3):
        service = ServiceFactory(id=index + 1)
        EntityEmbeddingFactory(
            entity_type='service',
            entity_id=service.id,
            model_name='stub-model',
            embedding='[1.0,0.0,0.0]',
            dimension=3,
        )

    results = search_similar_entities('fuga', provider=StubProvider(), top_k=2)

    assert len(results) == 2


def test_search_similar_entities_vector_invalido_cuenta_como_cero():
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=1,
        model_name='stub-model',
        embedding='no-es-vector',
        dimension=3,
    )

    results = search_similar_entities('fuga', provider=StubProvider())

    assert results[0]['similarity'] == 0.0


def test_search_similar_entities_ignora_otro_modelo():
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=1,
        model_name='otro-modelo',
        embedding='[1.0,0.0,0.0]',
        dimension=3,
    )

    assert search_similar_entities('fuga', provider=StubProvider()) == []


def test_search_similar_entities_ruta_postgres():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (1, 'service', 1, 'Fugas', 'stub-model', 3, 0.95),
    ]
    ServiceFactory(id=1, name='Fugas')

    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(embedding_service, '_pgvector_available', return_value=True):
            with patch.object(
                embedding_service, 'connection', _fake_connection(cursor)
            ):
                results = search_similar_entities('fuga', provider=StubProvider())

    assert results[0]['similarity'] == 0.95
    assert results[0]['entity']['name'] == 'Fugas'


def test_search_similar_entities_ruta_postgres_con_error_usa_fallback():
    cursor = MagicMock()
    cursor.execute.side_effect = RuntimeError('pgvector roto')
    EntityEmbeddingFactory(
        entity_type='service',
        entity_id=1,
        model_name='stub-model',
        embedding='[1.0,0.0,0.0]',
        dimension=3,
    )

    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(embedding_service, '_pgvector_available', return_value=True):
            with patch.object(
                embedding_service, 'connection', _fake_connection(cursor)
            ):
                results = search_similar_entities('fuga', provider=StubProvider())

    assert len(results) == 1


def test_search_similar_entities_similitud_nula_se_reporta_como_cero():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (1, 'service', 1, 'Fugas', 'stub-model', 3, None),
    ]

    with patch.object(embedding_service, '_is_postgres', return_value=True):
        with patch.object(embedding_service, '_pgvector_available', return_value=True):
            with patch.object(
                embedding_service, 'connection', _fake_connection(cursor)
            ):
                results = search_similar_entities('fuga', provider=StubProvider())

    assert results[0]['similarity'] == 0.0


# --------------------------------------------------------------------------- #
# sync_catalog_embeddings
# --------------------------------------------------------------------------- #
def test_sync_catalog_embeddings_sin_entidades():
    result = sync_catalog_embeddings(provider=StubProvider())

    assert result == {
        'services_synced': 0,
        'assets_synced': 0,
        'total_synced': 0,
    }


def test_sync_catalog_embeddings_sincroniza_servicios_y_activos():
    ServiceFactory(id=1, name='Fugas', description='Fugas de agua')
    ServiceFactory(id=2, name='Destapes', description='Destapes')
    AssetTypeCatalogFactory(id=1, code='ducha', name='Ducha')
    AssetTypeCatalogFactory(id=2, code='inactivo', is_active=False)

    result = sync_catalog_embeddings(provider=StubProvider())

    assert result['provider'] == 'stub-model'
    assert result['dimension'] == 3
    assert result['services_synced'] == 2
    assert result['assets_synced'] == 1
    assert result['total_synced'] == 3
    assert EntityEmbedding.objects.count() == 3


def test_sync_catalog_embeddings_commit_false():
    ServiceFactory(id=1)

    result = sync_catalog_embeddings(provider=StubProvider(), commit=False)

    assert result['total_synced'] == 1


def test_sync_catalog_embeddings_usa_proveedor_por_defecto():
    ServiceFactory()

    with patch(
        'api.services.embedding_service.get_embedding_provider',
        return_value=StubProvider(),
    ) as factory:
        result = sync_catalog_embeddings()

    factory.assert_called_once()
    assert result['total_synced'] == 1


def test_sync_catalog_embeddings_usa_embed_batch_una_vez():
    ServiceFactory(id=1)
    ServiceFactory(id=2)
    provider = StubProvider()

    with patch.object(provider, 'embed_batch', wraps=provider.embed_batch) as batch:
        sync_catalog_embeddings(provider=provider)

    batch.assert_called_once()
    assert len(batch.call_args.args[0]) == 2


def test_sync_catalog_embeddings_serializa_el_vector():
    ServiceFactory(id=1)

    sync_catalog_embeddings(provider=StubProvider([0.25, 0.5, 0.75]))

    assert json.loads(EntityEmbedding.objects.get().embedding) == [0.25, 0.5, 0.75]
