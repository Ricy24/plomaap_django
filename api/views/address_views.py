"""
User saved addresses - port of app/routes/addresses.py (/api/user/addresses).
"""
from django.db.models import Q
from django.http import JsonResponse

from api.models import User, UserAddress, utcnow
from api.utils.decorators import jwt_required_custom
from api.utils.request_utils import json_body


@jwt_required_custom
def list_addresses(request, user):
    """List all addresses for the authenticated user."""
    addresses = UserAddress.objects.filter(user_id=user.id).order_by(
        '-is_default', '-updated_at'
    )
    return JsonResponse({
        'success': True,
        'addresses': [addr.to_dict() for addr in addresses],
    }, status=200)


@jwt_required_custom
def create_address(request, user):
    """Create a new saved address for the authenticated user."""
    data = json_body(request)

    label = (data.get('label') or data.get('name') or 'Casa').strip()
    address_str = (data.get('address') or '').strip()

    if not address_str:
        return JsonResponse({'success': False, 'message': 'La dirección es obligatoria'}, status=400)

    # Check if this should be default (if requested or if it's the first one)
    existing_count = UserAddress.objects.filter(user_id=user.id).count()
    is_default = bool(data.get('is_default', existing_count == 0))

    if is_default:
        UserAddress.objects.filter(user_id=user.id).update(is_default=False)

    new_addr = UserAddress(
        user_id=user.id,
        label=label,
        address=address_str,
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        place_id=data.get('place_id'),
        reference=data.get('reference'),
        is_default=is_default,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    new_addr.save()

    # Also update user's main address in profile if marked default
    if is_default:
        user.address = address_str
        user.updated_at = utcnow()
        user.save()

    return JsonResponse({
        'success': True,
        'message': 'Ubicación guardada con éxito',
        'address': new_addr.to_dict(),
    }, status=201)


@jwt_required_custom
def update_address(request, user, addr_id):
    """Update an existing address of the authenticated user."""
    addr = UserAddress.objects.filter(id=addr_id, user_id=user.id).first()
    if not addr:
        return JsonResponse({'success': False, 'message': 'Ubicación no encontrada'}, status=404)

    data = json_body(request)

    if 'label' in data or 'name' in data:
        addr.label = (data.get('label') or data.get('name') or addr.label).strip()
    if 'address' in data and data['address'].strip():
        addr.address = data['address'].strip()
    if 'latitude' in data:
        addr.latitude = data['latitude']
    if 'longitude' in data:
        addr.longitude = data['longitude']
    if 'place_id' in data:
        addr.place_id = data['place_id']
    if 'reference' in data:
        addr.reference = data['reference']

    if 'is_default' in data and bool(data['is_default']):
        UserAddress.objects.filter(user_id=user.id).update(is_default=False)
        addr.is_default = True
        user.address = addr.address

    addr.updated_at = utcnow()
    addr.save()
    if 'address' in data and addr.is_default:
        user.updated_at = utcnow()
        user.save()

    return JsonResponse({
        'success': True,
        'message': 'Ubicación actualizada',
        'address': addr.to_dict(),
    }, status=200)


@jwt_required_custom
def delete_address(request, user, addr_id):
    """Delete a saved address."""
    addr = UserAddress.objects.filter(id=addr_id, user_id=user.id).first()
    if not addr:
        return JsonResponse({'success': False, 'message': 'Ubicación no encontrada'}, status=404)

    was_default = addr.is_default
    addr.delete()

    # If it was default, make another one default if available
    if was_default:
        next_addr = (
            UserAddress.objects.filter(user_id=user.id)
            .order_by('-updated_at')
            .first()
        )
        if next_addr:
            next_addr.is_default = True
            next_addr.updated_at = utcnow()
            next_addr.save()
            user.address = next_addr.address
            user.updated_at = utcnow()
            user.save()

    return JsonResponse({'success': True, 'message': 'Ubicación eliminada'}, status=200)


@jwt_required_custom
def set_default_address(request, user, addr_id):
    """Set an address as default for the authenticated user."""
    addr = UserAddress.objects.filter(id=addr_id, user_id=user.id).first()
    if not addr:
        return JsonResponse({'success': False, 'message': 'Ubicación no encontrada'}, status=404)

    UserAddress.objects.filter(user_id=user.id).update(is_default=False)
    addr.is_default = True
    addr.updated_at = utcnow()
    addr.save()

    user.address = addr.address
    user.updated_at = utcnow()
    user.save()

    return JsonResponse({
        'success': True,
        'message': 'Ubicación predeterminada establecida',
        'address': addr.to_dict(),
    }, status=200)
