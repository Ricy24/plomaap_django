"""
Vector Embedding and Semantic Search Service for PlomApp - FASE 9.
Direct port of app/services/embedding_service.py (Flask version).

Uses raw SQL against PostgreSQL + pgvector (CAST(... AS vector)) exactly like
the Flask version. If pgvector/PostgreSQL is unavailable (e.g. SQLite dev DB),
it transparently falls back to storing/reading plain-text vectors and computing
cosine similarity in Python, so the API never breaks.
"""
import json
import logging
from datetime import datetime

from django.db import connection, transaction

from api.models import AssetTypeCatalog, EntityEmbedding, Service, utcnow
from api.services.embedding_provider import BaseEmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


def _vector_to_sql_str(vec: list) -> str:
    """Convierte lista de floats en formato string para pgvector [0.1,0.2,...]"""
    return '[' + ','.join(str(round(float(x), 6)) for x in vec) + ']'


def _is_postgres():
    return connection.vendor == 'postgresql'


_VECTOR_TYPE_OK = None


def _pgvector_available() -> bool:
    """Detecta (una sola vez) si la extensión pgvector está instalada en el
    servidor PostgreSQL. Si no lo está, las escrituras usan el mismo fallback
    texto + cosine Python que ya usa la lectura, para que la API nunca falle."""
    global _VECTOR_TYPE_OK
    if _VECTOR_TYPE_OK is None:
        if not _is_postgres():
            _VECTOR_TYPE_OK = False
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM pg_type WHERE typname = 'vector'")
                    _VECTOR_TYPE_OK = cursor.fetchone() is not None
            except Exception:
                _VECTOR_TYPE_OK = False
        if not _VECTOR_TYPE_OK:
            logger.warning(
                'pgvector no disponible en el servidor: los embeddings se '
                'guardarán como texto y la similitud se calculará en Python.'
            )
    return _VECTOR_TYPE_OK


def store_entity_embedding(
    entity_type: str,
    entity_id: int,
    content_text: str,
    provider: BaseEmbeddingProvider = None,
    precomputed_vector: list = None,
    commit=True,
):
    """
    Guarda el embedding para una entidad y realiza upsert en public.entity_embeddings.
    Si precomputed_vector es provisto, evita llamar a la API externa.
    """
    prov = provider or get_embedding_provider()
    content_clean = str(content_text).strip()
    if not content_clean:
        raise ValueError('content_text no puede estar vacío')

    vec = precomputed_vector if precomputed_vector is not None else prov.embed_text(content_clean)
    vec_sql = _vector_to_sql_str(vec)
    now = utcnow()

    params = {
        'entity_type': str(entity_type),
        'entity_id': int(entity_id),
        'content_text': content_clean,
        'embedding': vec_sql,
        'model_name': prov.model_name,
        'dimension': prov.dimension,
        'created_at': now,
        'updated_at': now,
    }

    try:
        if _is_postgres() and _pgvector_available():
            # Usar CAST(:embedding AS vector) para evitar colisión de dos puntos (::)
            # con bind params (mismo SQL que la versión Flask).
            sql = """
                INSERT INTO public.entity_embeddings (
                    entity_type, entity_id, content_text, embedding, model_name,
                    dimension, created_at, updated_at
                ) VALUES (
                    %(entity_type)s, %(entity_id)s, %(content_text)s,
                    CAST(%(embedding)s AS vector), %(model_name)s, %(dimension)s,
                    %(created_at)s, %(updated_at)s
                )
                ON CONFLICT ON CONSTRAINT uq_entity_embedding DO UPDATE SET
                    content_text = EXCLUDED.content_text,
                    embedding = EXCLUDED.embedding,
                    dimension = EXCLUDED.dimension,
                    updated_at = EXCLUDED.updated_at;
            """
            def _execute():
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)

            if commit:
                with transaction.atomic():
                    _execute()
            else:
                # Participates in the surrounding transaction (or autocommits)
                _execute()
        else:
            # Fallback (SQLite/MySQL): upsert ORM con el vector como texto
            EntityEmbedding.objects.update_or_create(
                entity_type=params['entity_type'],
                entity_id=params['entity_id'],
                model_name=params['model_name'],
                defaults={
                    'content_text': params['content_text'],
                    'embedding': params['embedding'],
                    'dimension': params['dimension'],
                    'created_at': params['created_at'],
                    'updated_at': params['updated_at'],
                },
            )
        return True
    except Exception as e:
        logger.error('Error guardando embedding %s#%s: %s', entity_type, entity_id, e, exc_info=True)
        raise e


def _parse_vector(text):
    try:
        if isinstance(text, (list, tuple)):
            return [float(x) for x in text]
        if not text:
            return None
        s = str(text).strip()
        if s.startswith('[') and s.endswith(']'):
            return json.loads(s)
        return json.loads(s)
    except Exception:
        return None


def _cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search_similar_entities(
    query_text: str,
    entity_type: str = None,
    top_k: int = 5,
    min_similarity: float = 0.0,
    provider: BaseEmbeddingProvider = None,
) -> list:
    """
    Realiza búsqueda vectorial semántica por similitud coseno en public.entity_embeddings.
    Retorna lista ordenada de coincidencias con entidad resuelta, similarity (0 a 1) y metadatos.
    """
    query_clean = str(query_text).strip()
    if not query_clean:
        return []

    prov = provider or get_embedding_provider()
    query_vec = prov.embed_text(query_clean)
    query_vec_sql = _vector_to_sql_str(query_vec)

    rows = []  # tuples: (id, entity_type, entity_id, content_text, model_name, dimension, similarity)

    if _is_postgres() and _pgvector_available():
        try:
            sql = """
                SELECT id, entity_type, entity_id, content_text, model_name, dimension,
                       (1 - (embedding <=> CAST(%(vec)s AS vector))) AS similarity
                FROM public.entity_embeddings
                WHERE (%(entity_type)s IS NULL OR entity_type = %(entity_type)s)
                  AND model_name = %(model_name)s
                  AND (1 - (embedding <=> CAST(%(vec)s AS vector))) >= %(min_similarity)s
                ORDER BY embedding <=> CAST(%(vec)s AS vector) ASC
                LIMIT %(top_k)s;
            """
            params = {
                'vec': query_vec_sql,
                'entity_type': entity_type if entity_type else None,
                'model_name': prov.model_name,
                'min_similarity': float(min_similarity),
                'top_k': int(top_k),
            }
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        except Exception as e:
            logger.warning(
                'Fallo consulta pgvector (%s); usando fallback cosine en Python.', e
            )
            rows = []

    if not rows:
        # ---- Python fallback: same filtering/order semantics ----
        qs = EntityEmbedding.objects.filter(model_name=prov.model_name)
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        scored = []
        for emb in qs.iterator():
            stored = _parse_vector(emb.embedding)
            sim = _cosine_similarity(query_vec, stored)
            if sim >= float(min_similarity):
                scored.append(
                    (emb.id, emb.entity_type, emb.entity_id, emb.content_text,
                     emb.model_name, emb.dimension, sim)
                )
        scored.sort(key=lambda r: r[6], reverse=True)
        rows = scored[: int(top_k)]

    results = []

    # Enriquecer con datos de entidad si es service o asset_type
    service_ids = [r[2] for r in rows if r[1] == 'service']
    asset_ids = [r[2] for r in rows if r[1] == 'asset_type']

    services_map = {}
    if service_ids:
        for s in Service.objects.filter(id__in=service_ids):
            services_map[s.id] = s.to_dict()

    assets_map = {}
    if asset_ids:
        for a in AssetTypeCatalog.objects.filter(id__in=asset_ids):
            assets_map[a.id] = a.to_dict()

    for r in rows:
        r_id, r_type, r_entity_id, r_content, r_model, r_dim, r_sim = r[:7]
        sim_val = float(r_sim) if r_sim is not None else 0.0

        entity_obj = None
        if r_type == 'service':
            entity_obj = services_map.get(r_entity_id)
        elif r_type == 'asset_type':
            entity_obj = assets_map.get(r_entity_id)

        results.append({
            'embedding_id': r_id,
            'entity_type': r_type,
            'entity_id': r_entity_id,
            'similarity': round(sim_val, 4),
            'content_text': r_content,
            'model_name': r_model,
            'entity': entity_obj,
        })

    return results


def sync_catalog_embeddings(commit=True, provider: BaseEmbeddingProvider = None) -> dict:
    """
    Sincroniza embeddings para los servicios y los tipos de activo del catálogo.
    Utiliza embed_batch() para generar todos los vectores en una sola llamada de red.
    """
    prov = provider or get_embedding_provider()

    # 1. Recopilar entidades a sincronizar
    items_to_sync = []

    services = Service.objects.all()
    for s in services:
        text_repr = f'Servicio: {s.name}. Categoría: {s.category}. Descripción: {s.description}.'
        items_to_sync.append({'type': 'service', 'id': s.id, 'text': text_repr})

    assets = AssetTypeCatalog.objects.filter(is_active=True)
    for a in assets:
        text_repr = f'Activo del hogar: {a.name}. Categoría técnica: {a.category}. Código: {a.code}.'
        items_to_sync.append({'type': 'asset_type', 'id': a.id, 'text': text_repr})

    if not items_to_sync:
        return {'services_synced': 0, 'assets_synced': 0, 'total_synced': 0}

    # 2. Generar todos los embeddings en BATCH (1 sola llamada API)
    all_texts = [item['text'] for item in items_to_sync]
    all_vectors = prov.embed_batch(all_texts)

    # 3. Guardar en base de datos
    synced_services = 0
    synced_assets = 0

    def _store_all():
        nonlocal synced_services, synced_assets
        for item, vec in zip(items_to_sync, all_vectors):
            store_entity_embedding(
                item['type'],
                item['id'],
                item['text'],
                provider=prov,
                precomputed_vector=vec,
                commit=False,
            )
            if item['type'] == 'service':
                synced_services += 1
            elif item['type'] == 'asset_type':
                synced_assets += 1

    if commit:
        with transaction.atomic():
            _store_all()
    else:
        _store_all()

    return {
        'provider': prov.model_name,
        'dimension': prov.dimension,
        'services_synced': synced_services,
        'assets_synced': synced_assets,
        'total_synced': synced_services + synced_assets,
    }
