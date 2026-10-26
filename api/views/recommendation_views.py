"""
Recommendations routes - port of app/routes/recommendations.py.
"""
import logging

from django.http import JsonResponse

from api.services.recommendation_service import (
    generate_recommendations,
    track_recommendation_click,
    track_recommendation_conversion,
)
from api.utils.decorators import jwt_required
from api.utils.request_utils import query_int

logger = logging.getLogger('api.recommendations')


@jwt_required
def get_recommendations(request, user):
    """
    GET /api/recommendations
    Servicios recomendados según Hogar Digital, Preferencias e Historial.
    """
    try:
        user_id = int(user.id)
        limit = query_int(request, 'limit', 5) or 5
        recommendations = generate_recommendations(user_id=user_id, limit=limit)

        return JsonResponse({'status': 'success', 'data': recommendations}, status=200)
    except Exception as e:
        logger.error(f'Error fetching recommendations: {e}', exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


@jwt_required
def track_click(request, user, rec_id):
    """
    POST /api/recommendations/<rec_id>/click
    Registra que el usuario interactuó con la recomendación.
    """
    success = track_recommendation_click(rec_id, user.id)
    if success:
        return JsonResponse({'status': 'success', 'message': 'Click tracked successfully'}, status=200)
    return JsonResponse(
        {'status': 'error', 'message': 'Could not track click or recommendation not found'},
        status=400,
    )


@jwt_required
def track_conversion(request, user, rec_id):
    """
    POST /api/recommendations/<rec_id>/convert
    Registra que el usuario reservó el servicio a partir de la recomendación.
    """
    success = track_recommendation_conversion(rec_id, user.id)
    if success:
        return JsonResponse({'status': 'success', 'message': 'Conversion tracked successfully'}, status=200)
    return JsonResponse(
        {'status': 'error', 'message': 'Could not track conversion or recommendation not found'},
        status=400,
    )
