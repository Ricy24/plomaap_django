"""
Event Tracking Service for PlomApp - FASE 6.
Direct port of app/services/event_service.py (Flask version).
"""
import logging

from api.models import AppEvent, utcnow

logger = logging.getLogger(__name__)

# Catálogo oficial de tipos de eventos validados a nivel de aplicación
VALID_EVENT_TYPES = {
    'USER_REGISTERED',
    'ONBOARDING_STARTED',
    'ONBOARDING_COMPLETED',
    'SEARCH_PERFORMED',
    'NLU_QUERY_PROCESSED',
    'SERVICE_VIEWED',
    'SERVICE_RECOMMENDED',
    'SERVICE_CLICKED',
    'SERVICE_BOOKED',
    'BOOKING_CREATED',
    'BOOKING_CANCELLED',
    'BOOKING_COMPLETED',
    'RATING_CREATED',
    'ASSET_CREATED',
    'MAINTENANCE_RECORDED',
    'NOTIFICATION_CREATED',
    'NOTIFICATION_OPENED',
    'NOTIFICATION_ACTIONED',
}


def track_event(
    event_type,
    user_id=None,
    entity_type=None,
    entity_id=None,
    session_id=None,
    metadata=None,
    strict=False,
):
    """
    Registra un evento de aplicación en public.app_events.

    :param event_type: Tipo de evento (debe pertenecer a VALID_EVENT_TYPES)
    :param user_id: ID del usuario (opcional)
    :param entity_type: Tipo de entidad relacionada (ej. 'user', 'appointment')
    :param entity_id: ID de la entidad relacionada
    :param session_id: Identificador de sesión cliente/dispositivo (opcional)
    :param metadata: Diccionario con información contextual (JSON)
    :param strict: Si True, lanza ValueError ante tipo de evento no válido
    :return: Instancia de AppEvent creada, o None en caso de fallo no estricto
    """
    if event_type not in VALID_EVENT_TYPES:
        msg = (
            f"Tipo de evento inválido: '{event_type}'. "
            'Debe pertenecer a VALID_EVENT_TYPES.'
        )
        logger.warning(msg)
        if strict:
            raise ValueError(msg)
        return None

    try:
        event = AppEvent.objects.create(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            created_at=utcnow(),
        )
        return event
    except Exception as e:
        logger.error("Error registrando evento '%s': %s", event_type, e, exc_info=True)
        if strict:
            raise
        return None
