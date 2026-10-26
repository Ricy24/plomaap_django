"""
Profile Attribute and Provenance Tracking Service for PlomApp - FASE 7.
Direct port of app/services/profile_service.py (Flask version).

The Flask version used a PostgreSQL-specific INSERT ... ON CONFLICT DO UPDATE
(upsert on uq_profile_attribute). Here we use update_or_create() against the
same unique constraint (entity_type, entity_id, attribute_key), which behaves
identically and also works on SQLite/MySQL.
"""
import logging
from datetime import date, datetime
from decimal import Decimal

from api.models import ProfileAttribute, utcnow

logger = logging.getLogger(__name__)

VALID_SOURCES = {
    'onboarding',
    'explicit_user_input',
    'search',
    'booking',
    'rating',
    'home_asset',
    'inferred',
    'system',
}


def _normalize_json_value(val):
    """Convierte tipos no serializables nativamente (Decimal, date, datetime) a tipos JSON compatibles."""
    if isinstance(val, Decimal):
        f = float(val)
        return int(f) if f.is_integer() else f
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): _normalize_json_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_normalize_json_value(x) for x in val]
    return val


def record_attribute(
    entity_type,
    entity_id,
    attribute_key,
    attribute_value,
    source='explicit_user_input',
    confidence=1.0,
    commit=True,
):
    """
    Registra o actualiza (upsert) un atributo de perfil con fuente y confianza.

    :param entity_type: Tipo de entidad ('home', 'home_room', 'home_asset', 'user')
    :param entity_id: ID entero de la entidad
    :param attribute_key: Clave del atributo ('type', 'brand', 'approximate_area', etc.)
    :param attribute_value: Valor del atributo (serializable a JSON)
    :param source: Fuente del dato (debe pertenecer a VALID_SOURCES)
    :param confidence: Nivel de confianza numerico entre 0.0 y 1.0
    :param commit: Si False, la escritura se hará dentro de la transacción circundante
    :return: True o lanza excepcion
    """
    if source not in VALID_SOURCES:
        raise ValueError(
            f"Fuente '{source}' no valida. Debe ser una de: {sorted(list(VALID_SOURCES))}"
        )

    conf_num = Decimal(str(confidence))
    if conf_num < Decimal('0.0') or conf_num > Decimal('1.0'):
        raise ValueError(f'Confianza {confidence} fuera de rango [0.0, 1.0]')

    normalized_value = _normalize_json_value(attribute_value)
    now = utcnow()

    try:
        ProfileAttribute.objects.update_or_create(
            entity_type=str(entity_type),
            entity_id=int(entity_id),
            attribute_key=str(attribute_key),
            defaults={
                'attribute_value': normalized_value,
                'source': str(source),
                'confidence': conf_num,
                'updated_at': now,
            },
        )
        return True
    except Exception as e:
        logger.error(
            'Error registrando atributo %s:%s:%s: %s',
            entity_type, entity_id, attribute_key, e, exc_info=True,
        )
        raise e


def get_entity_attributes(entity_type, entity_id):
    """
    Obtiene todos los atributos registrados para una entidad en formato de diccionario clave -> dict.
    """
    rows = ProfileAttribute.objects.filter(
        entity_type=str(entity_type),
        entity_id=int(entity_id),
    )
    return {row.attribute_key: row.to_dict() for row in rows}


def delete_entity_attributes(entity_type, entity_id, commit=True):
    """
    Elimina atributos de una entidad eliminada.
    """
    try:
        count, _ = ProfileAttribute.objects.filter(
            entity_type=str(entity_type),
            entity_id=int(entity_id),
        ).delete()
        return count
    except Exception as e:
        logger.error(
            'Error eliminando atributos para %s:%s: %s',
            entity_type, entity_id, e, exc_info=True,
        )
        raise e
