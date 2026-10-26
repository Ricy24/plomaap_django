"""
Intelligence route - port of app/routes/intelligence.py
(POST /api/intelligence/understand).
FASE 11: Comprensión de Lenguaje Natural.
"""
import logging

from django.http import JsonResponse

from api.services.nlu_service import understand_text
from api.utils.jwt_utils import get_jwt_identity
from api.utils.request_utils import json_body

logger = logging.getLogger('api.intelligence')


def process_text_understanding(request):
    """
    POST /api/intelligence/understand
    Acepta {"text": "..."} y retorna estructura NLU validada con IDs reales.
    """
    data = json_body(request)
    text = (data.get('text') or '').strip()

    if not text:
        return JsonResponse({
            'success': False,
            'error': 'El campo text es obligatorio',
        }, status=400)

    user_id = None
    try:
        jwt_id = get_jwt_identity(request)
        if jwt_id:
            user_id = int(jwt_id)
    except Exception:
        pass

    try:
        result = understand_text(text=text, user_id=user_id)
        status_code = 200 if result.get('success') else 400
        return JsonResponse(result, status=status_code)
    except Exception as e:
        logger.error(f'Error procesando comprensión NLU: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno procesando análisis NLU',
            'details': str(e),
        }, status=500)
