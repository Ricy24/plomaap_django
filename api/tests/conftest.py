# -*- coding: utf-8 -*-
"""Shared pytest fixtures for the PlomApp backend suite."""
import pytest

from api.utils.jwt_utils import generate_token


@pytest.fixture
def customer(db):
    from api.tests.factories import UserFactory

    return UserFactory(role='customer')


@pytest.fixture
def technician(db):
    from api.tests.factories import TechnicianProfileFactory

    profile = TechnicianProfileFactory()
    return profile.user


@pytest.fixture
def service(db):
    from api.tests.factories import ServiceFactory

    return ServiceFactory()


@pytest.fixture
def appointment(customer, technician, service):
    from api.tests.factories import AppointmentFactory

    return AppointmentFactory(
        user=customer,
        technician=technician,
        service=service,
    )


@pytest.fixture
def auth_header(customer):
    return {'HTTP_AUTHORIZATION': f'Bearer {generate_token(customer.id)}'}


@pytest.fixture
def pgvector(db):
    """
    Ensure the Django test database has pgvector enabled and the embeddings
    column uses the production type (vector(512)). Skipped on SQLite.
    """
    from django.db import connection

    if connection.vendor != 'postgresql':
        pytest.skip('Esta prueba requiere PostgreSQL con pgvector')

    try:
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')
            cursor.execute(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_name = 'entity_embeddings' AND column_name = 'embedding'
                """
            )
            row = cursor.fetchone()
            if row and row[0] != 'vector':
                cursor.execute(
                    'ALTER TABLE entity_embeddings '
                    'ALTER COLUMN embedding TYPE vector(512) '
                    'USING embedding::vector'
                )
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_entity_embeddings_vector '
                'ON entity_embeddings USING hnsw (embedding vector_cosine_ops)'
            )
    except Exception as exc:  # pragma: no cover - depends on DB permissions
        pytest.skip(f'No se pudo habilitar pgvector en la BD de pruebas: {exc}')

    from api.services import embedding_service

    embedding_service._VECTOR_TYPE_OK = None
    yield
    embedding_service._VECTOR_TYPE_OK = None
