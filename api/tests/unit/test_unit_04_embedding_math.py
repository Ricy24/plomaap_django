# -*- coding: utf-8 -*-
"""UNIT-04: matemática de embeddings (parseo y similitud coseno)."""
import math

import pytest

from api.services.embedding_service import _cosine_similarity, _parse_vector

pytestmark = pytest.mark.unit


def test_UNIT_04_parse_vector_json_valido():
    assert _parse_vector('[1.0, 2.0, 3.0]') == [1.0, 2.0, 3.0]
    assert _parse_vector([1, 2, 3]) == [1.0, 2.0, 3.0]


def test_UNIT_04_parse_vector_invalido_retorna_none():
    assert _parse_vector('abc') is None
    assert _parse_vector('') is None
    assert _parse_vector(None) is None


def test_UNIT_04_coseno_vectores_iguales():
    assert math.isclose(_cosine_similarity([1, 0, 0], [1, 0, 0]), 1.0)


def test_UNIT_04_coseno_vectores_ortogonales():
    assert math.isclose(_cosine_similarity([1, 0, 0], [0, 1, 0]), 0.0)


def test_UNIT_04_coseno_casos_limite():
    assert _cosine_similarity([], []) == 0.0
    assert _cosine_similarity([1, 0], [1, 0, 0]) == 0.0
    assert _cosine_similarity([0, 0], [1, 0]) == 0.0
