"""
Hybrid Search route - port of app/routes/search.py (POST /api/search/hybrid).
FASE 10: Búsqueda Híbrida Inteligente.
"""
import logging

from django.http import JsonResponse

from api.services.hybrid_search_service import perform_hybrid_search
from api.utils.request_utils import json_body

logger = logging.getLogger('api.search')


def search_hybrid(request):
    """
    POST /api/search/hybrid
    Acepta:
      {
        "query": "se me está saliendo agua debajo del lavamanos",
        "top_k": 5,
        "category": "Fugas" (opcional)
      }
    Retorna lista de servicios reales clasificados por hybrid_score.
    """
    data = json_body(request)
    query = (data.get('query') or '').strip()
    try:
        top_k = int(data.get('top_k', 5))
    except (TypeError, ValueError):
        top_k = 5
    category = data.get('category')

    if top_k > 20:
        top_k = 20
    if top_k < 1:
        top_k = 5

    try:
        results = perform_hybrid_search(
            query=query,
            category_filter=category,
            top_k=top_k,
        )
        return JsonResponse({'success': True, **results}, status=200)
    except Exception as e:
        logger.error(f'Error ejecutando búsqueda híbrida: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error procesando búsqueda híbrida',
            'details': str(e),
        }, status=500)
