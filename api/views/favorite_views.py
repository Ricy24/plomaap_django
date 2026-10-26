"""
User favorites - port of app/routes/favorites.py (/api/user/favorites).
"""
from django.http import JsonResponse

from api.models import Service, UserFavorite, utcnow
from api.utils.decorators import jwt_required_custom


@jwt_required_custom
def list_favorites(request, user):
    """List all favorite services for the authenticated user."""
    favs = UserFavorite.objects.filter(user_id=user.id).select_related('service')
    service_ids = [f.service_id for f in favs]
    services = [f.service.to_dict() for f in favs if f.service]

    return JsonResponse({
        'success': True,
        'favorite_ids': service_ids,
        'favorites': services,
    }, status=200)


@jwt_required_custom
def toggle_favorite(request, user, service_id):
    """Toggle favorite status for a service."""
    service = Service.objects.filter(pk=service_id).first()
    if not service:
        return JsonResponse({'success': False, 'message': 'Servicio no encontrado'}, status=404)

    existing = UserFavorite.objects.filter(user_id=user.id, service_id=service_id).first()
    if existing:
        existing.delete()
        return JsonResponse({
            'success': True,
            'is_favorite': False,
            'message': 'Eliminado de favoritos',
            'service_id': service_id,
        }, status=200)

    UserFavorite.objects.create(
        user_id=user.id,
        service_id=service_id,
        created_at=utcnow(),
    )
    return JsonResponse({
        'success': True,
        'is_favorite': True,
        'message': 'Agregado a favoritos',
        'service_id': service_id,
    }, status=201)


@jwt_required_custom
def remove_favorite(request, user, service_id):
    """Remove service from favorites."""
    existing = UserFavorite.objects.filter(user_id=user.id, service_id=service_id).first()
    if existing:
        existing.delete()

    return JsonResponse({
        'success': True,
        'is_favorite': False,
        'message': 'Eliminado de favoritos',
    }, status=200)
