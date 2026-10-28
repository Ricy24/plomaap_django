# -*- coding: utf-8 -*-
"""INT-03: pgvector, sincronización y búsqueda semántica."""
import pytest

from api.services import embedding_service
from api.services.embedding_service import (
    search_similar_entities,
    sync_catalog_embeddings,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


class FakeEmbeddingProvider:
    model_name = 'fake-test-embedding'
    dimension = 512

    def embed_text(self, text):
        return [1.0] + [0.0] * 511

    def embed_batch(self, texts):
        return [self.embed_text(text) for text in texts]


def test_INT_03_sync_y_busqueda_pgvector(pgvector, service):
    provider = FakeEmbeddingProvider()

    result = sync_catalog_embeddings(commit=True, provider=provider)

    assert result['services_synced'] >= 1
    assert embedding_service._pgvector_available() is True

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT embedding::text FROM entity_embeddings "
            "WHERE entity_type = 'service' AND entity_id = %s",
            [service.id],
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0].startswith('[')

        cursor.execute(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'entity_embeddings' "
            "AND indexname = 'idx_entity_embeddings_vector'"
        )
        assert cursor.fetchone() is not None

    results = search_similar_entities(
        'fuga de agua',
        entity_type='service',
        top_k=3,
        provider=provider,
    )

    assert results
    assert results[0]['entity_type'] == 'service'
    assert results[0]['entity_id'] == service.id
    assert results[0]['similarity'] == 1.0
