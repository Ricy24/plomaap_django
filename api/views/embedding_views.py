"""
Embedding and Vector Search routes - port of app/routes/embeddings.py.
FASE 9: Embedding Provider.
"""
import logging

from django.http import JsonResponse

from api.services.embedding_provider import get_embedding_provider
from api.services.embedding_service import (
    search_similar_entities,
    sync_catalog_embeddings,
)
from api.utils.request_utils import json_body

logger = logging.getLogger('api.embeddings')


def get_provider_info(request):
    """
    GET /api/embeddings/provider-info
    Retorna el proveedor activo, modelo y dimensión vectorial.
    """
    prov = get_embedding_provider()
    return JsonResponse({
        'success': True,
        'provider_class': prov.__class__.__name__,
        'model_name': prov.model_name,
        'dimension': prov.dimension,
    }, status=200)


def generate_embedding(request):
    """
    POST /api/embeddings/embed
    Genera embedding para un texto provisto.
    """
    data = json_body(request)
    text_input = data.get('text')
    if not text_input or not str(text_input).strip():
        return JsonResponse({'error': 'El campo text es obligatorio'}, status=400)

    prov = get_embedding_provider()
    try:
        vec = prov.embed_text(str(text_input).strip())
        return JsonResponse({
            'success': True,
            'model_name': prov.model_name,
            'dimension': len(vec),
            'embedding_sample': vec[:8],  # Muestra inicial para inspección
            'embedding': vec if data.get('include_full_vector') else None,
        }, status=200)
    except Exception as e:
        logger.error(f'Error generando embedding: {e}', exc_info=True)
        return JsonResponse({'error': f'Error generando embedding: {str(e)}'}, status=500)


def sync_embeddings(request):
    """
    POST /api/embeddings/sync
    Genera y almacena en pgvector los embeddings de servicios y activos.
    """
    try:
        result = sync_catalog_embeddings(commit=True)
        return JsonResponse({
            'success': True,
            'message': 'Catálogo sincronizado exitosamente en pgvector',
            'data': result,
        }, status=200)
    except Exception as e:
        logger.error(f'Error sincronizando catálogo: {e}', exc_info=True)
        return JsonResponse({'error': f'Error sincronizando catálogo: {str(e)}'}, status=500)


def search_embeddings(request):
    """
    POST /api/embeddings/search
    Realiza búsqueda vectorial por similitud semántica.
    """
    data = json_body(request)
    query_text = data.get('query')
    if not query_text or not str(query_text).strip():
        return JsonResponse({'error': 'El campo query es obligatorio'}, status=400)

    entity_type = data.get('entity_type')  # 'service' | 'asset_type' | None
    try:
        top_k = int(data.get('top_k', 5))
        min_similarity = float(data.get('min_similarity', 0.0))
    except (TypeError, ValueError):
        top_k, min_similarity = 5, 0.0

    try:
        results = search_similar_entities(
            query_text=query_text,
            entity_type=entity_type,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        return JsonResponse({
            'success': True,
            'query': query_text,
            'count': len(results),
            'results': results,
        }, status=200)
    except Exception as e:
        logger.error(f'Error en búsqueda semántica: {e}', exc_info=True)
        return JsonResponse({'error': f'Error en búsqueda semántica: {str(e)}'}, status=500)
