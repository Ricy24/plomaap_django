"""
Digital Home routes - port of app/routes/homes.py (/api/homes).
FASE 7: Perfil de Hogar (Infraestructura de Fuente/Confianza + CRUD basico).
"""
import logging
from datetime import datetime

from django.db import transaction
from django.http import JsonResponse

from api.models import (
    AssetTypeCatalog,
    Home,
    HomeAsset,
    HomeMember,
    HomeRoom,
    RoomTypeCatalog,
)
from api.services.event_service import track_event
from api.services.profile_service import record_attribute
from api.utils.decorators import jwt_required
from api.utils.request_utils import json_body, query_int

logger = logging.getLogger('api.homes')

# Mapeo y validacion de tipos de hogar
VALID_HOME_TYPES = {
    'apartment': 'apartment',
    'apartamento': 'apartment',
    'house': 'house',
    'casa': 'house',
    'studio': 'studio',
    'estudio': 'studio',
    'office': 'office',
    'oficina': 'office',
    'other': 'other',
    'otro': 'other',
}


def _get_membership(home_id, user_id):
    """
    Obtiene la autorizacion y rol del usuario para un hogar dado.
    Retorna (has_access, role, home); role: 'owner', 'admin', 'member' o None.
    """
    home = Home.objects.filter(pk=home_id).first()
    if not home:
        return False, None, None

    if home.owner_id == int(user_id):
        return True, 'owner', home

    member = HomeMember.objects.filter(home_id=home_id, user_id=user_id).first()
    if member:
        return True, member.role, home

    return False, None, home


# =====================================================================
# 1. HOMES ENDPOINTS
# =====================================================================

@jwt_required
def create_home(request, user):
    """
    POST /api/homes
    Crea un nuevo hogar asignando owner_id al usuario autenticado.
    Auto-crea fila en home_members con role='owner'.
    Registra en profile_attributes cada campo provisto.
    """
    user_id = int(user.id)
    data = json_body(request)

    name = data.get('name')
    if not name or not str(name).strip():
        return JsonResponse({'error': 'El campo name es obligatorio'}, status=400)
    name = str(name).strip()

    raw_type = data.get('type', 'apartment')
    home_type = VALID_HOME_TYPES.get(str(raw_type).lower())
    if not home_type:
        return JsonResponse(
            {'error': f"Tipo de hogar invalido: '{raw_type}'. Debe ser: apartment, house, studio, office, other"},
            status=400,
        )

    approximate_area = data.get('approximate_area')
    if approximate_area is not None:
        try:
            approximate_area = float(approximate_area)
            if approximate_area < 0:
                return JsonResponse({'error': 'approximate_area debe ser un numero positivo'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'approximate_area debe ser numerico'}, status=400)

    rooms_count = data.get('rooms_count', 0)
    if rooms_count is not None:
        try:
            rooms_count = int(rooms_count)
            if rooms_count < 0:
                return JsonResponse({'error': 'rooms_count debe ser un entero no negativo'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'rooms_count debe ser un entero'}, status=400)

    try:
        with transaction.atomic():
            home = Home(
                owner_id=user_id,
                name=name,
                type=home_type,
                approximate_area=approximate_area,
                rooms_count=rooms_count,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            home.save()

            # (a) Auto-crear membresia como owner
            HomeMember.objects.create(
                home_id=home.id,
                user_id=user_id,
                role='owner',
                created_at=datetime.utcnow(),
            )

            # (b) Registrar procedencia en profile_attributes (dentro de la transaccion)
            if 'type' in data and data['type'] is not None:
                record_attribute('home', home.id, 'type', home.type, source='explicit_user_input', confidence=1.000, commit=False)
            if 'approximate_area' in data and data['approximate_area'] is not None:
                record_attribute('home', home.id, 'approximate_area', float(home.approximate_area), source='explicit_user_input', confidence=1.000, commit=False)
            if 'rooms_count' in data and data['rooms_count'] is not None:
                record_attribute('home', home.id, 'rooms_count', home.rooms_count, source='explicit_user_input', confidence=1.000, commit=False)

        return JsonResponse({
            'success': True,
            'message': 'Hogar creado exitosamente',
            'home': home.to_dict(enriched=True),
        }, status=201)

    except Exception as e:
        logger.error(f'Error creando hogar: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al crear el hogar'}, status=500)


@jwt_required
def list_homes(request, user):
    """
    GET /api/homes
    Lista los hogares donde el usuario autenticado es owner o member.
    """
    user_id = int(user.id)

    homes = Home.objects.filter(
        owner_id=user_id
    ) | Home.objects.filter(members__user_id=user_id)
    homes = homes.distinct().order_by('id')

    return JsonResponse({
        'success': True,
        'count': homes.count(),
        'homes': [h.to_dict(enriched=True) for h in homes],
    }, status=200)


@jwt_required
def get_home(request, user, id):
    """
    GET /api/homes/<id>
    Detalle de un hogar. Solo si el usuario es owner o member.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{id} no encontrado'}, status=404)
    if not has_access:
        return JsonResponse({'error': 'No tienes autorizacion para acceder a este hogar'}, status=403)

    data = home.to_dict(enriched=True)
    data['current_user_role'] = role
    data['members'] = [m.to_dict() for m in home.members.all()]
    data['rooms'] = [r.to_dict() for r in home.rooms.all()]
    return JsonResponse({'success': True, 'home': data}, status=200)


@jwt_required
def update_home(request, user, id):
    """
    PATCH /api/homes/<id>
    Actualiza datos del hogar. Solo owner o admin.
    Registra provenance de los campos cambiados.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para modificar el hogar'},
            status=403,
        )

    data = json_body(request)
    updated_fields = []

    if 'name' in data:
        new_name = str(data['name']).strip()
        if not new_name:
            return JsonResponse({'error': 'El nombre no puede estar vacio'}, status=400)
        home.name = new_name
        updated_fields.append('name')

    if 'type' in data:
        raw_type = data['type']
        home_type = VALID_HOME_TYPES.get(str(raw_type).lower())
        if not home_type:
            return JsonResponse({'error': f"Tipo de hogar invalido: '{raw_type}'"}, status=400)
        home.type = home_type
        updated_fields.append('type')

    if 'approximate_area' in data:
        val = data['approximate_area']
        if val is not None:
            try:
                val = float(val)
                if val < 0:
                    return JsonResponse({'error': 'approximate_area debe ser positivo'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'approximate_area debe ser numerico'}, status=400)
        home.approximate_area = val
        updated_fields.append('approximate_area')

    if 'rooms_count' in data:
        val = data['rooms_count']
        if val is not None:
            try:
                val = int(val)
                if val < 0:
                    return JsonResponse({'error': 'rooms_count debe ser no negativo'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'rooms_count debe ser entero'}, status=400)
        home.rooms_count = val
        updated_fields.append('rooms_count')

    if not updated_fields:
        return JsonResponse(
            {'message': 'No se proporcionaron campos para actualizar', 'home': home.to_dict()},
            status=200,
        )

    try:
        home.updated_at = datetime.utcnow()

        # Registrar provenance de campos actualizados
        for field in updated_fields:
            if field == 'type':
                record_attribute('home', home.id, 'type', home.type, source='explicit_user_input', confidence=1.000, commit=False)
            elif field == 'approximate_area' and home.approximate_area is not None:
                record_attribute('home', home.id, 'approximate_area', float(home.approximate_area), source='explicit_user_input', confidence=1.000, commit=False)
            elif field == 'rooms_count' and home.rooms_count is not None:
                record_attribute('home', home.id, 'rooms_count', home.rooms_count, source='explicit_user_input', confidence=1.000, commit=False)
            elif field == 'name':
                record_attribute('home', home.id, 'name', home.name, source='explicit_user_input', confidence=1.000, commit=False)

        home.save()

        return JsonResponse({
            'success': True,
            'message': 'Hogar actualizado exitosamente',
            'home': home.to_dict(enriched=True),
        }, status=200)

    except Exception as e:
        logger.error(f'Error actualizando hogar #{id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al actualizar el hogar'}, status=500)


@jwt_required
def delete_home(request, user, id):
    """
    DELETE /api/homes/<id>
    Elimina el hogar. Solo el owner legitimo.
    Cascada cubierta por FKs (rooms, assets, members se borran en cascada).
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{id} no encontrado'}, status=404)
    if home.owner_id != user_id:
        return JsonResponse(
            {'error': 'Solo el propietario original puede eliminar el hogar'},
            status=403,
        )

    try:
        home.delete()
        return JsonResponse({
            'success': True,
            'message': f'Hogar #{id} eliminado exitosamente',
        }, status=200)
    except Exception as e:
        logger.error(f'Error eliminando hogar #{id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al eliminar el hogar'}, status=500)


# =====================================================================
# 2. HOME ROOMS ENDPOINTS (/api/homes/<home_id>/rooms)
# =====================================================================

@jwt_required
def create_room(request, user, home_id):
    """
    POST /api/homes/<home_id>/rooms
    Crea una habitacion en el hogar. Solo owner o admin.
    Valida type contra room_type_catalog y registra provenance.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para agregar habitaciones'},
            status=403,
        )

    data = json_body(request)
    name = data.get('name')
    if not name or not str(name).strip():
        return JsonResponse({'error': 'El campo name es obligatorio'}, status=400)
    name = str(name).strip()

    raw_type = data.get('type')
    if not raw_type:
        return JsonResponse({'error': 'El campo type es obligatorio'}, status=400)
    raw_type_str = str(raw_type).strip()

    # Validacion contra room_type_catalog (por code o name)
    catalog_item = RoomTypeCatalog.objects.filter(
        code=raw_type_str.lower()
    ).first() or RoomTypeCatalog.objects.filter(name__iexact=raw_type_str).first()
    if not catalog_item:
        return JsonResponse(
            {'error': f"Tipo de habitacion '{raw_type_str}' no valido en catalogo"},
            status=400,
        )
    room_code = catalog_item.code

    try:
        with transaction.atomic():
            room = HomeRoom(
                home_id=home_id,
                name=name,
                type=room_code,
                created_at=datetime.utcnow(),
            )
            room.save()

            # Registrar provenance de type
            record_attribute('home_room', room.id, 'type', room.type, source='explicit_user_input', confidence=1.000, commit=False)

        return JsonResponse({
            'success': True,
            'message': 'Habitacion creada exitosamente',
            'room': room.to_dict(),
        }, status=201)

    except Exception as e:
        logger.error(f'Error creando habitacion en hogar #{home_id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al crear la habitacion'}, status=500)


@jwt_required
def list_rooms(request, user, home_id):
    """
    GET /api/homes/<home_id>/rooms
    Lista habitaciones del hogar. Cualquier miembro/owner puede ver.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access:
        return JsonResponse({'error': 'No tienes autorizacion para acceder a este hogar'}, status=403)

    rooms = HomeRoom.objects.filter(home_id=home_id).order_by('id')
    return JsonResponse({
        'success': True,
        'home_id': home_id,
        'count': len(rooms),
        'rooms': [r.to_dict() for r in rooms],
    }, status=200)


@jwt_required
def update_room(request, user, home_id, room_id):
    """
    PATCH /api/homes/<home_id>/rooms/<room_id>
    Actualiza una habitacion. Solo owner o admin.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para modificar habitaciones'},
            status=403,
        )

    room = HomeRoom.objects.filter(id=room_id, home_id=home_id).first()
    if not room:
        return JsonResponse(
            {'error': f'Habitacion #{room_id} no encontrada en este hogar'},
            status=404,
        )

    data = json_body(request)
    updated_fields = []

    if 'name' in data:
        new_name = str(data['name']).strip()
        if not new_name:
            return JsonResponse({'error': 'El nombre no puede estar vacio'}, status=400)
        room.name = new_name
        updated_fields.append('name')

    if 'type' in data:
        raw_type_str = str(data['type']).strip()
        catalog_item = RoomTypeCatalog.objects.filter(
            code=raw_type_str.lower()
        ).first() or RoomTypeCatalog.objects.filter(name__iexact=raw_type_str).first()
        if not catalog_item:
            return JsonResponse(
                {'error': f"Tipo de habitacion '{raw_type_str}' no valido en catalogo"},
                status=400,
            )
        room.type = catalog_item.code
        updated_fields.append('type')

    try:
        with transaction.atomic():
            if 'type' in updated_fields:
                record_attribute('home_room', room.id, 'type', room.type, source='explicit_user_input', confidence=1.000, commit=False)
            room.save()

        return JsonResponse({
            'success': True,
            'message': 'Habitacion actualizada exitosamente',
            'room': room.to_dict(),
        }, status=200)
    except Exception as e:
        logger.error(f'Error actualizando habitacion #{room_id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al actualizar habitacion'}, status=500)


@jwt_required
def delete_room(request, user, home_id, room_id):
    """
    DELETE /api/homes/<home_id>/rooms/<room_id>
    Elimina una habitacion. Solo owner o admin.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para eliminar habitaciones'},
            status=403,
        )

    room = HomeRoom.objects.filter(id=room_id, home_id=home_id).first()
    if not room:
        return JsonResponse(
            {'error': f'Habitacion #{room_id} no encontrada en este hogar'},
            status=404,
        )

    try:
        room.delete()
        return JsonResponse({
            'success': True,
            'message': f'Habitacion #{room_id} eliminada exitosamente',
        }, status=200)
    except Exception as e:
        logger.error(f'Error eliminando habitacion #{room_id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al eliminar habitacion'}, status=500)


# =====================================================================
# 3. HOME ASSETS ENDPOINTS (/api/homes/<home_id>/assets)
# =====================================================================

def _parse_date(date_str, field_name):
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'Formato invalido para {field_name}. Use YYYY-MM-DD')


@jwt_required
def create_asset(request, user, home_id):
    """
    POST /api/homes/<home_id>/assets
    Crea un activo dentro de un hogar. Solo owner o admin.
    Valida asset_type contra asset_type_catalog, registra provenance y
    dispara evento ASSET_CREATED.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para agregar activos'},
            status=403,
        )

    data = json_body(request)

    raw_asset_type = data.get('asset_type')
    if not raw_asset_type:
        return JsonResponse({'error': 'El campo asset_type es obligatorio'}, status=400)
    raw_asset_str = str(raw_asset_type).strip()

    # Validacion contra asset_type_catalog
    catalog_item = AssetTypeCatalog.objects.filter(
        code=raw_asset_str.lower()
    ).first() or AssetTypeCatalog.objects.filter(name__iexact=raw_asset_str).first()
    if not catalog_item:
        return JsonResponse(
            {'error': f"Tipo de activo '{raw_asset_str}' no valido en catalogo"},
            status=400,
        )
    asset_code = catalog_item.code

    # Validar room_id si viene provisto
    room_id = data.get('room_id')
    if room_id is not None:
        try:
            room_id = int(room_id)
            room = HomeRoom.objects.filter(id=room_id, home_id=home_id).first()
            if not room:
                return JsonResponse(
                    {'error': f'Habitacion #{room_id} no pertenece a este hogar'},
                    status=400,
                )
        except (ValueError, TypeError):
            return JsonResponse({'error': 'room_id debe ser un entero valido'}, status=400)

    brand = data.get('brand')
    brand = str(brand).strip() if brand else None

    model = data.get('model')
    model = str(model).strip() if model else None

    try:
        installation_date = _parse_date(data.get('installation_date'), 'installation_date')
        last_maintenance = _parse_date(data.get('last_maintenance'), 'last_maintenance')
        warranty_until = _parse_date(data.get('warranty_until'), 'warranty_until')
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)

    metadata = data.get('metadata')
    if metadata is not None and not isinstance(metadata, dict):
        return JsonResponse({'error': 'metadata debe ser un objeto JSON'}, status=400)
    metadata = metadata or {}

    try:
        with transaction.atomic():
            asset = HomeAsset(
                home_id=home_id,
                room_id=room_id,
                asset_type=asset_code,
                brand=brand,
                model=model,
                installation_date=installation_date,
                last_maintenance=last_maintenance,
                warranty_until=warranty_until,
                metadata=metadata,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            asset.save()

            # Registrar provenance de campos provistos
            record_attribute('home_asset', asset.id, 'asset_type', asset.asset_type, source='explicit_user_input', confidence=1.000, commit=False)
            if brand:
                record_attribute('home_asset', asset.id, 'brand', brand, source='explicit_user_input', confidence=1.000, commit=False)
            if model:
                record_attribute('home_asset', asset.id, 'model', model, source='explicit_user_input', confidence=1.000, commit=False)

        # Disparar evento ASSET_CREATED (FASE 6 event tracking)
        try:
            track_event(
                event_type='ASSET_CREATED',
                user_id=user_id,
                entity_type='home_asset',
                entity_id=asset.id,
                metadata={
                    'home_id': home_id,
                    'room_id': asset.room_id,
                    'asset_type': asset.asset_type,
                    'brand': asset.brand,
                    'model': asset.model,
                },
            )
        except Exception as ev_err:
            logger.warning(f'No se pudo disparar evento ASSET_CREATED: {ev_err}')

        return JsonResponse({
            'success': True,
            'message': 'Activo creado exitosamente',
            'asset': asset.to_dict(),
        }, status=201)

    except Exception as e:
        logger.error(f'Error creando activo en hogar #{home_id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al crear el activo'}, status=500)


@jwt_required
def list_assets(request, user, home_id):
    """
    GET /api/homes/<home_id>/assets
    Lista activos de un hogar. Filtro opcional ?room_id=X.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access:
        return JsonResponse({'error': 'No tienes autorizacion para acceder a este hogar'}, status=403)

    query = HomeAsset.objects.filter(home_id=home_id)
    room_id = query_int(request, 'room_id')
    if room_id is not None:
        query = query.filter(room_id=room_id)

    assets = list(query.order_by('id'))
    return JsonResponse({
        'success': True,
        'home_id': home_id,
        'count': len(assets),
        'assets': [a.to_dict() for a in assets],
    }, status=200)


@jwt_required
def update_asset(request, user, home_id, asset_id):
    """
    PATCH /api/homes/<home_id>/assets/<asset_id>
    Actualiza un activo. Solo owner o admin.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para modificar activos'},
            status=403,
        )

    asset = HomeAsset.objects.filter(id=asset_id, home_id=home_id).first()
    if not asset:
        return JsonResponse(
            {'error': f'Activo #{asset_id} no encontrado en este hogar'},
            status=404,
        )

    data = json_body(request)
    updated_provenance = []

    if 'asset_type' in data:
        raw_asset_str = str(data['asset_type']).strip()
        catalog_item = AssetTypeCatalog.objects.filter(
            code=raw_asset_str.lower()
        ).first() or AssetTypeCatalog.objects.filter(name__iexact=raw_asset_str).first()
        if not catalog_item:
            return JsonResponse(
                {'error': f"Tipo de activo '{raw_asset_str}' no valido en catalogo"},
                status=400,
            )
        asset.asset_type = catalog_item.code
        updated_provenance.append(('asset_type', asset.asset_type))

    if 'room_id' in data:
        room_id = data['room_id']
        if room_id is not None:
            try:
                room_id = int(room_id)
                room = HomeRoom.objects.filter(id=room_id, home_id=home_id).first()
                if not room:
                    return JsonResponse(
                        {'error': f'Habitacion #{room_id} no pertenece a este hogar'},
                        status=400,
                    )
            except (ValueError, TypeError):
                return JsonResponse({'error': 'room_id debe ser un entero valido'}, status=400)
        asset.room_id = room_id

    if 'brand' in data:
        asset.brand = str(data['brand']).strip() if data['brand'] else None
        updated_provenance.append(('brand', asset.brand))

    if 'model' in data:
        asset.model = str(data['model']).strip() if data['model'] else None
        updated_provenance.append(('model', asset.model))

    try:
        if 'installation_date' in data:
            asset.installation_date = _parse_date(data['installation_date'], 'installation_date')
        if 'last_maintenance' in data:
            asset.last_maintenance = _parse_date(data['last_maintenance'], 'last_maintenance')
        if 'warranty_until' in data:
            asset.warranty_until = _parse_date(data['warranty_until'], 'warranty_until')
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)

    if 'metadata' in data:
        meta = data['metadata']
        if meta is not None and not isinstance(meta, dict):
            return JsonResponse({'error': 'metadata debe ser un objeto JSON'}, status=400)
        asset.metadata = meta or {}

    try:
        asset.updated_at = datetime.utcnow()

        # Registrar provenance de campos actualizados
        with transaction.atomic():
            for key, val in updated_provenance:
                if val is not None:
                    record_attribute('home_asset', asset.id, key, val, source='explicit_user_input', confidence=1.000, commit=False)
            asset.save()

        return JsonResponse({
            'success': True,
            'message': 'Activo actualizado exitosamente',
            'asset': asset.to_dict(),
        }, status=200)

    except Exception as e:
        logger.error(f'Error actualizando activo #{asset_id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al actualizar el activo'}, status=500)


@jwt_required
def delete_asset(request, user, home_id, asset_id):
    """
    DELETE /api/homes/<home_id>/assets/<asset_id>
    Elimina un activo. Solo owner o admin.
    """
    user_id = int(user.id)
    has_access, role, home = _get_membership(home_id, user_id)

    if not home:
        return JsonResponse({'error': f'Hogar #{home_id} no encontrado'}, status=404)
    if not has_access or role not in ('owner', 'admin'):
        return JsonResponse(
            {'error': 'Se requieren privilegios de propietario o administrador para eliminar activos'},
            status=403,
        )

    asset = HomeAsset.objects.filter(id=asset_id, home_id=home_id).first()
    if not asset:
        return JsonResponse(
            {'error': f'Activo #{asset_id} no encontrado en este hogar'},
            status=404,
        )

    try:
        asset.delete()
        return JsonResponse({
            'success': True,
            'message': f'Activo #{asset_id} eliminado exitosamente',
        }, status=200)
    except Exception as e:
        logger.error(f'Error eliminando activo #{asset_id}: {e}', exc_info=True)
        return JsonResponse({'error': 'Error interno al eliminar activo'}, status=500)
