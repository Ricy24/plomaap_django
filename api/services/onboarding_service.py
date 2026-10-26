"""
Adaptive Onboarding Service for PlomApp - FASE 8.
Direct port of app/services/onboarding_service.py (Flask version).
"""
import logging
from datetime import datetime

from django.db import transaction

from api.models import (
    AssetTypeCatalog,
    Home,
    HomeAsset,
    HomeMember,
    HomeRoom,
    ProfileAttribute,
    RoomTypeCatalog,
    User,
    utcnow,
)
from api.services.event_service import track_event
from api.services.profile_service import record_attribute

logger = logging.getLogger(__name__)

# Confianza base otorgada a datos recolectados durante onboarding (confidence = 0.90)
ONBOARDING_CONFIDENCE = 0.900

# Catálogo de opciones y preguntas adaptativas
QUESTIONS_CONFIG = {
    1: {
        'id': 'home_type',
        'step': 1,
        'title': '¿Qué tipo de hogar tienes?',
        'subtitle': 'Personalizaremos las sugerencias y servicios según tu vivienda',
        'is_multi_select': False,
        'options': [
            {'code': 'apartment', 'label': 'Apartamento', 'icon': 'apartment'},
            {'code': 'house', 'label': 'Casa', 'icon': 'home'},
            {'code': 'other', 'label': 'Otro tipo de inmueble', 'icon': 'location_city'},
        ],
    },
    2: {
        'id': 'needs_frequency',
        'step': 2,
        'title': '¿Qué sueles necesitar en tu hogar?',
        'subtitle': 'Para priorizar los servicios más relevantes en tu inicio',
        'is_multi_select': False,
        'options': [
            {'code': 'reparaciones', 'label': 'Reparaciones puntuales', 'icon': 'build'},
            {'code': 'mantenimiento', 'label': 'Mantenimiento preventivo', 'icon': 'engineering'},
            {'code': 'remodelacion', 'label': 'Remodelación y mejoras', 'icon': 'format_paint'},
            {'code': 'emergencias', 'label': 'Urgencias / Emergencias', 'icon': 'warning'},
            {'code': 'un_poco_de_todo', 'label': 'Un poco de todo', 'icon': 'apps'},
        ],
    },
    3: {
        'id': 'key_zones',
        'step': 3,
        'is_adaptive': True,
        'is_multi_select': True,
        'variants': {
            'apartment': {
                'title': '¿Qué zonas utilizas más en tu apartamento?',
                'subtitle': 'Selecciona las áreas clave para crear el mapa de tu hogar',
                'options': [
                    {'code': 'cocina', 'label': 'Cocina', 'icon': 'kitchen'},
                    {'code': 'bano', 'label': 'Baños', 'icon': 'bathtub'},
                    {'code': 'sala', 'label': 'Sala', 'icon': 'weekend'},
                    {'code': 'habitacion', 'label': 'Habitaciones', 'icon': 'bed'},
                    {'code': 'balcon', 'label': 'Balcón', 'icon': 'deck'},
                    {'code': 'zona_lavado', 'label': 'Zona de lavado', 'icon': 'local_laundry_service'},
                ],
            },
            'house': {
                'title': '¿Qué espacios de tu casa quieres mantener o mejorar?',
                'subtitle': 'Selecciona las áreas principales para crear el mapa de tu hogar',
                'options': [
                    {'code': 'cocina', 'label': 'Cocina', 'icon': 'kitchen'},
                    {'code': 'bano', 'label': 'Baños', 'icon': 'bathtub'},
                    {'code': 'sala', 'label': 'Sala', 'icon': 'weekend'},
                    {'code': 'habitacion', 'label': 'Habitaciones', 'icon': 'bed'},
                    {'code': 'patio', 'label': 'Patio o Jardín', 'icon': 'yard'},
                    {'code': 'zona_lavado', 'label': 'Zona de lavado', 'icon': 'local_laundry_service'},
                ],
            },
            'default': {
                'title': '¿Qué zonas principales componen tu espacio?',
                'subtitle': 'Selecciona las áreas clave',
                'options': [
                    {'code': 'cocina', 'label': 'Cocina', 'icon': 'kitchen'},
                    {'code': 'bano', 'label': 'Baños', 'icon': 'bathtub'},
                    {'code': 'sala', 'label': 'Sala', 'icon': 'weekend'},
                    {'code': 'habitacion', 'label': 'Habitaciones', 'icon': 'bed'},
                ],
            },
        },
    },
    4: {
        'id': 'assets_present',
        'step': 4,
        'title': '¿Qué equipos o instalaciones tienes en casa?',
        'subtitle': 'Te ayudaremos a llevar el historial y alertas de mantenimiento',
        'is_multi_select': True,
        'options': [
            {'code': 'calentador', 'label': 'Calentador de agua', 'icon': 'water_heater'},
            {'code': 'lavadora', 'label': 'Lavadora', 'icon': 'local_laundry_service'},
            {'code': 'aire_acondicionado', 'label': 'Aire acondicionado', 'icon': 'mode_fan'},
            {'code': 'ducha', 'label': 'Duchas / Griferías', 'icon': 'shower'},
            {'code': 'enchufe', 'label': 'Instalaciones eléctricas / Tomas', 'icon': 'power'},
            {'code': 'iluminacion', 'label': 'Iluminación especializada', 'icon': 'lightbulb'},
            {'code': 'no_estoy_seguro', 'label': 'No estoy seguro por ahora', 'icon': 'help_outline'},
        ],
    },
    5: {
        'id': 'maintenance_philosophy',
        'step': 5,
        'title': '¿Cómo prefieres manejar el mantenimiento de tu hogar?',
        'subtitle': 'Ajustaremos las recomendaciones a tu estilo',
        'is_multi_select': False,
        'options': [
            {'code': 'reactivo', 'label': 'Solo cuando ocurre algo', 'icon': 'schedule'},
            {'code': 'al_dia', 'label': 'Mantener todo al día', 'icon': 'check_circle'},
            {'code': 'preventivo', 'label': 'Prevenir problemas con anticipación', 'icon': 'shield'},
            {'code': 'mixto', 'label': 'Depende del equipo o problema', 'icon': 'tune'},
        ],
    },
}


def get_adaptive_questions(home_type_context=None):
    """
    Retorna el árbol de las 5 preguntas adaptativas, resolviendo la variante de la
    pregunta 3 según el tipo de hogar si se conoce.
    """
    questions = []

    # Pregunta 1 y 2
    questions.append(QUESTIONS_CONFIG[1])
    questions.append(QUESTIONS_CONFIG[2])

    # Pregunta 3 adaptativa
    q3_base = QUESTIONS_CONFIG[3]
    ht_key = str(home_type_context).lower() if home_type_context else None
    if ht_key in ('apartment', 'apartamento'):
        variant = q3_base['variants']['apartment']
    elif ht_key in ('house', 'casa'):
        variant = q3_base['variants']['house']
    else:
        variant = q3_base['variants']['default']

    questions.append({
        'id': q3_base['id'],
        'step': q3_base['step'],
        'title': variant['title'],
        'subtitle': variant['subtitle'],
        'is_multi_select': q3_base['is_multi_select'],
        'options': variant['options'],
        'all_variants': q3_base['variants'],
    })

    # Pregunta 4 y 5
    questions.append(QUESTIONS_CONFIG[4])
    questions.append(QUESTIONS_CONFIG[5])

    return {
        'total_steps': 5,
        'estimated_time_seconds': '30-60',
        'questions': questions,
    }


def get_user_onboarding_status(user_id):
    """
    Consulta si el usuario ya completó o postergó el onboarding.
    Utiliza profile_attributes para no modificar la tabla users.
    """
    attr = ProfileAttribute.objects.filter(
        entity_type='user',
        entity_id=int(user_id),
        attribute_key='onboarding_status',
    ).first()

    has_home = Home.objects.filter(owner_id=int(user_id)).exists()

    if not attr:
        return {
            'completed': False,
            'skipped': False,
            'completed_at': None,
            'has_home': has_home,
        }

    val = attr.attribute_value or {}
    return {
        'completed': bool(val.get('completed', False)),
        'skipped': bool(val.get('skipped', False)),
        'completed_at': val.get('completed_at'),
        'skipped_at': val.get('skipped_at'),
        'has_home': has_home,
    }


def start_onboarding(user_id, session_id=None):
    """
    Registra el inicio del flujo de onboarding emitiendo el evento ONBOARDING_STARTED.
    """
    user_id = int(user_id)
    try:
        track_event(
            event_type='ONBOARDING_STARTED',
            user_id=user_id,
            session_id=session_id,
            metadata={'timestamp': datetime.utcnow().isoformat()},
        )
    except Exception as e:
        logger.warning('Error emitiendo evento ONBOARDING_STARTED: %s', e)

    return get_adaptive_questions()


def skip_onboarding(user_id, session_id=None):
    """
    Registra la opción 'Ahora no' (Skip) sin bloquear el uso de la aplicación.
    """
    user_id = int(user_id)
    now_iso = datetime.utcnow().isoformat()

    record_attribute(
        entity_type='user',
        entity_id=user_id,
        attribute_key='onboarding_status',
        attribute_value={'completed': False, 'skipped': True, 'skipped_at': now_iso},
        source='onboarding',
        confidence=1.000,
        commit=True,
    )

    return {
        'success': True,
        'message': 'Onboarding postergado exitosamente',
        'skipped': True,
    }


def complete_onboarding(user_id, answers, session_id=None):
    """
    Procesa las respuestas de onboarding, convirtiéndolas en entidades estructuradas:
      1. Hogar principal (Home) + Membresía (HomeMember role='owner').
      2. Habitaciones (HomeRoom) validadas contra room_type_catalog.
      3. Activos (HomeAsset) validados contra asset_type_catalog y enlazados a habitaciones.
      4. Atributos en profile_attributes con source='onboarding' y confidence=0.900.
      5. Emisión del evento ONBOARDING_COMPLETED en app_events.
    """
    user_id = int(user_id)
    answers = answers or {}

    # 1. Extraer y normalizar respuestas
    raw_home_type = answers.get('home_type', 'apartment')
    home_type_map = {
        'apartamento': 'apartment', 'apartment': 'apartment',
        'casa': 'house', 'house': 'house',
        'otro': 'other', 'other': 'other',
    }
    home_type = home_type_map.get(str(raw_home_type).lower(), 'apartment')

    needs_frequency = answers.get('needs_frequency', 'un_poco_de_todo')

    raw_zones = answers.get('key_zones', [])
    if isinstance(raw_zones, str):
        raw_zones = [raw_zones]
    zones = [str(z).strip().lower() for z in raw_zones if str(z).strip()]

    raw_assets = answers.get('assets_present', [])
    if isinstance(raw_assets, str):
        raw_assets = [raw_assets]
    assets = [
        str(a).strip().lower() for a in raw_assets
        if str(a).strip() and str(a).strip().lower() != 'no_estoy_seguro'
    ]

    maintenance_philosophy = answers.get('maintenance_philosophy', 'al_dia')

    created_rooms = []
    created_assets = []

    try:
        with transaction.atomic():
            # 2. Gestionar Hogar Principal
            home = Home.objects.filter(owner_id=user_id).first()
            if not home:
                home_name = (
                    'Mi Apartamento' if home_type == 'apartment'
                    else ('Mi Casa' if home_type == 'house' else 'Mi Hogar')
                )
                home = Home(
                    owner_id=user_id,
                    name=home_name,
                    type=home_type,
                    rooms_count=max(len(zones), 1),
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                home.save()

                HomeMember.objects.create(
                    home_id=home.id,
                    user_id=user_id,
                    role='owner',
                    created_at=utcnow(),
                )
            else:
                # Si ya tenía hogar, actualizamos su tipo y cuartos si es pertinente
                home.type = home_type
                if len(zones) > home.rooms_count:
                    home.rooms_count = len(zones)
                home.updated_at = utcnow()
                home.save()

            # 3. Aprovisionar Habitaciones (HomeRoom)
            room_catalog = {
                r.code: r for r in RoomTypeCatalog.objects.filter(is_active=True)
            }
            existing_room_types = {
                r.type: r for r in HomeRoom.objects.filter(home_id=home.id)
            }
            room_instances_by_code = dict(existing_room_types)

            for z_code in zones:
                catalog_item = room_catalog.get(z_code)
                if catalog_item and z_code not in existing_room_types:
                    new_room = HomeRoom(
                        home_id=home.id,
                        name=catalog_item.name,
                        type=catalog_item.code,
                        created_at=utcnow(),
                    )
                    new_room.save()
                    room_instances_by_code[z_code] = new_room
                    created_rooms.append(new_room.to_dict())

                    # Provenance de habitacion
                    record_attribute(
                        'home_room', new_room.id, 'type', new_room.type,
                        source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False,
                    )

            # 4. Aprovisionar Activos (HomeAsset)
            asset_catalog = {
                a.code: a for a in AssetTypeCatalog.objects.filter(is_active=True)
            }
            existing_asset_types = set(
                HomeAsset.objects.filter(home_id=home.id).values_list('asset_type', flat=True)
            )

            # Mapeo logico preferente de activo a habitacion
            ROOM_AFFINITY = {
                'calentador': ['zona_lavado', 'cocina', 'bano'],
                'lavadora': ['zona_lavado', 'patio', 'cocina'],
                'aire_acondicionado': ['habitacion', 'sala'],
                'ducha': ['bano'],
                'lavamanos': ['bano'],
                'sanitario': ['bano'],
                'enchufe': ['sala', 'habitacion', 'cocina'],
                'iluminacion': ['sala', 'habitacion', 'cocina'],
            }

            for a_code in assets:
                cat_asset = asset_catalog.get(a_code)
                if cat_asset and a_code not in existing_asset_types:
                    # Buscar habitacion asociada
                    assigned_room_id = None
                    preferred_rooms = ROOM_AFFINITY.get(a_code, [])
                    for pref in preferred_rooms:
                        if pref in room_instances_by_code:
                            assigned_room_id = room_instances_by_code[pref].id
                            break

                    new_asset = HomeAsset(
                        home_id=home.id,
                        room_id=assigned_room_id,
                        asset_type=cat_asset.code,
                        created_at=utcnow(),
                        updated_at=utcnow(),
                    )
                    new_asset.save()
                    created_assets.append(new_asset.to_dict())

                    # Provenance de activo
                    record_attribute(
                        'home_asset', new_asset.id, 'asset_type', new_asset.asset_type,
                        source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False,
                    )

            # 5. Registrar Atributos Polimórficos de Perfil (profile_attributes)
            now_iso = datetime.utcnow().isoformat()

            # Atributos del Hogar
            record_attribute('home', home.id, 'type', home.type, source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False)
            record_attribute('home', home.id, 'key_zones', zones, source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False)
            record_attribute('home', home.id, 'declared_assets', assets, source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False)

            # Atributos del Usuario
            record_attribute('user', user_id, 'needs_preference', needs_frequency, source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False)
            record_attribute('user', user_id, 'maintenance_philosophy', maintenance_philosophy, source='onboarding', confidence=ONBOARDING_CONFIDENCE, commit=False)
            record_attribute('user', user_id, 'onboarding_status', {'completed': True, 'completed_at': now_iso, 'skipped': False}, source='onboarding', confidence=1.000, commit=False)

            home_id = home.id

        # 6. Event Tracking: ONBOARDING_COMPLETED
        try:
            track_event(
                event_type='ONBOARDING_COMPLETED',
                user_id=user_id,
                entity_type='home',
                entity_id=home_id,
                session_id=session_id,
                metadata={
                    'home_type': home_type,
                    'needs_frequency': needs_frequency,
                    'zones_selected': zones,
                    'assets_selected': assets,
                    'rooms_created_count': len(created_rooms),
                    'assets_created_count': len(created_assets),
                    'maintenance_philosophy': maintenance_philosophy,
                },
            )
        except Exception as ev_err:
            logger.warning('Error emitiendo evento ONBOARDING_COMPLETED: %s', ev_err)

        home = Home.objects.get(pk=home_id)

        return {
            'success': True,
            'message': 'Onboarding completado exitosamente. Hogar y perfil aprovisionados.',
            'onboarding_completed': True,
            'home': home.to_dict(enriched=True),
            'created_rooms_count': len(created_rooms),
            'created_assets_count': len(created_assets),
            'created_rooms': created_rooms,
            'created_assets': created_assets,
            'profile_summary': {
                'home_type': home_type,
                'needs_preference': needs_frequency,
                'maintenance_philosophy': maintenance_philosophy,
                'zones': zones,
                'assets': assets,
            },
        }

    except Exception as e:
        logger.error('Error completando onboarding para usuario #%s: %s', user_id, e, exc_info=True)
        raise e
