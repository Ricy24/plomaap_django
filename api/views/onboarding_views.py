"""
Adaptive Onboarding routes - port of app/routes/onboarding.py (/api/onboarding).
FASE 8: Onboarding Inteligente.
"""
import logging

from django.http import JsonResponse

from api.services.onboarding_service import (
    complete_onboarding,
    get_adaptive_questions,
    get_user_onboarding_status,
    skip_onboarding,
    start_onboarding,
)
from api.utils.decorators import jwt_optional, jwt_required
from api.utils.request_utils import json_body, query_str

logger = logging.getLogger('api.onboarding')


@jwt_required
def get_status(request, user):
    """
    GET /api/onboarding/status
    Devuelve el estado de onboarding del usuario autenticado.
    """
    user_id = int(user.id)
    status = get_user_onboarding_status(user_id)
    return JsonResponse({
        'success': True,
        'user_id': user_id,
        'status': status,
    }, status=200)


@jwt_optional
def get_questions(request):
    """
    GET /api/onboarding/questions
    Retorna el árbol de preguntas adaptativas.
    Parámetro opcional: ?home_type=apartment|house|other
    """
    home_type = query_str(request, 'home_type') or None
    questions_data = get_adaptive_questions(home_type)
    return JsonResponse({'success': True, 'data': questions_data}, status=200)


@jwt_required
def start(request, user):
    """
    POST /api/onboarding/start
    Inicia la sesión de onboarding y registra ONBOARDING_STARTED.
    """
    user_id = int(user.id)
    data = json_body(request)
    session_id = data.get('session_id')

    questions_data = start_onboarding(user_id, session_id=session_id)
    return JsonResponse({
        'success': True,
        'message': 'Sesión de onboarding iniciada',
        'data': questions_data,
    }, status=200)


@jwt_required
def complete(request, user):
    """
    POST /api/onboarding/complete
    Procesa las 5 respuestas adaptativas, aprovisiona hogar, habitaciones y activos,
    registra procedencia (source=onboarding) y evento ONBOARDING_COMPLETED.
    """
    user_id = int(user.id)
    data = json_body(request)

    # Soportar payload anidado {"answers": {...}} o plano {home_type: ..., ...}
    answers = data.get('answers') if 'answers' in data else data
    session_id = data.get('session_id')

    try:
        result = complete_onboarding(user_id, answers, session_id=session_id)
        return JsonResponse(result, status=200)
    except Exception as e:
        logger.error(f'Error completando onboarding para usuario #{user_id}: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno al procesar respuestas de onboarding',
        }, status=500)


@jwt_required
def skip(request, user):
    """
    POST /api/onboarding/skip
    Registra la acción 'Ahora no' para posponer el onboarding.
    """
    user_id = int(user.id)
    data = json_body(request)
    session_id = data.get('session_id')

    result = skip_onboarding(user_id, session_id=session_id)
    return JsonResponse(result, status=200)
