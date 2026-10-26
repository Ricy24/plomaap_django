"""
Events - port of app/routes/events.py (POST /api/events).
"""
from django.http import JsonResponse

from api.services.event_service import VALID_EVENT_TYPES, track_event
from api.utils.jwt_utils import get_jwt_identity
from api.utils.request_utils import json_body


def create_event(request):
    """
    POST /api/events
    Endpoint genérico para registro de eventos desde clientes (Android/Web).
    """
    data = json_body(request)
    event_type = data.get('event_type')

    if not event_type:
        return JsonResponse({'success': False, 'message': 'El campo event_type es obligatorio'}, status=400)

    if event_type not in VALID_EVENT_TYPES:
        return JsonResponse({
            'success': False,
            'message': f'Tipo de evento inválido: {event_type}. Consulte el catálogo permitido.',
        }, status=400)

    # Resolver user_id desde JWT si está presente, o del payload
    resolved_user_id = None
    try:
        identity = get_jwt_identity(request)
        if identity:
            resolved_user_id = int(identity)
    except Exception:
        pass

    if resolved_user_id is None and data.get('user_id'):
        try:
            resolved_user_id = int(data.get('user_id'))
        except (ValueError, TypeError):
            pass

    entity_type = data.get('entity_type')
    entity_id = data.get('entity_id')
    if entity_id is not None:
        try:
            entity_id = int(entity_id)
        except (ValueError, TypeError):
            entity_id = None

    session_id = data.get('session_id') or request.headers.get('X-Session-ID')
    metadata = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}

    event = track_event(
        event_type=event_type,
        user_id=resolved_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        session_id=session_id,
        metadata=metadata,
        strict=True,
    )

    return JsonResponse({
        'success': True,
        'message': 'Evento registrado exitosamente',
        'event': event.to_dict(),
    }, status=201)
