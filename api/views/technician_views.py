"""
Technicians - port of app/routes/technicians.py (/api/technicians).
"""
from datetime import datetime

from django.http import JsonResponse

from api.models import Appointment, User
from api.services.appointment_service import (
    _normalize_schedule,
    get_smart_time_slots,
    validate_appointment_transition,
)
from api.services.event_service import track_event
from api.utils.decorators import jwt_required_custom, technician_only
from api.utils.request_utils import json_body, query_int, query_str
from api.utils.validators import validate_appointment_status


def list_technicians(request):
    """List all active technicians."""
    limit = query_int(request, 'limit', 20) or 20
    offset = query_int(request, 'offset', 0) or 0
    if limit > 100:
        limit = 100

    technicians = (
        User.objects.filter(role='technician', status='active')
        .select_related('technician_profile')[offset:offset + limit]
    )

    result = []
    for tech in technicians:
        tech_dict = tech.to_dict()
        profile = tech.technician_profile
        if profile:
            tech_dict['profile'] = profile.to_dict()
        result.append(tech_dict)

    return JsonResponse({'technicians': result}, status=200)


def available_technicians(request):
    """Get available technicians for date/time/service."""
    date_str = query_str(request, 'date') or None
    time_str = query_str(request, 'time') or None
    service_id = query_int(request, 'service_id') or query_int(request, 'serviceId')

    if not date_str or not service_id:
        return JsonResponse({'error': 'date and service_id are required'}, status=400)

    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    technicians = User.objects.filter(
        role='technician', status='active'
    ).select_related('technician_profile')

    available = []
    for tech in technicians:
        profile = tech.technician_profile
        if not profile or not profile.available:
            continue

        day_name = appointment_date.strftime('%a').lower()
        schedule = _normalize_schedule(profile.schedule or {})
        if day_name not in schedule:
            continue

        if time_str:
            try:
                appointment_time = datetime.strptime(time_str, '%H:%M').time()
            except (ValueError, TypeError):
                continue

            is_within_schedule = any(
                start_hour <= appointment_time.hour < end_hour
                for start_hour, end_hour in schedule[day_name]
            )
            if not is_within_schedule:
                continue

            conflict = Appointment.objects.filter(
                technician_id=tech.id,
                date=appointment_date,
                time=time_str,
                status__in=['pending', 'scheduled', 'in_progress'],
            ).first()
            if conflict:
                continue

        tech_dict = tech.to_dict()
        tech_dict['profile'] = profile.to_dict()
        available.append(tech_dict)

    available.sort(
        key=lambda x: x['profile']['rating'] if x.get('profile') and x['profile'].get('rating') else 0,
        reverse=True,
    )
    return JsonResponse({'technicians': available}, status=200)


def available_slots(request):
    """Get available time slots with detailed status and periods."""
    technician_id = query_int(request, 'technician_id') or query_int(request, 'technicianId')
    service_id = query_int(request, 'service_id') or query_int(request, 'serviceId')
    date_str = query_str(request, 'date')

    if not date_str:
        return JsonResponse({'error': 'date is required'}, status=400)

    # Use smart slot calculation
    result = get_smart_time_slots(
        service_id=service_id, date_str=date_str, technician_id=technician_id
    )
    if isinstance(result, tuple):
        return JsonResponse(result[0], status=result[1])

    return JsonResponse(result, status=200)


@technician_only
def get_technician_profile(request, user):
    """Get authenticated technician's profile."""
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    profile_dict = user.to_dict()
    profile = user.technician_profile
    if profile:
        profile_dict['profile'] = profile.to_dict()
    return JsonResponse(profile_dict, status=200)


@technician_only
def technician_appointments(request, user):
    """Get technician's appointments."""
    date_filter = query_str(request, 'date')
    status_filter = query_str(request, 'status')

    query = Appointment.objects.filter(technician_id=user.id).select_related(
        'user', 'technician', 'service', 'user_address'
    )
    if date_filter:
        query = query.filter(date=date_filter)
    if status_filter:
        query = query.filter(status=status_filter)

    appointments = query.all()
    return JsonResponse(
        {'appointments': [apt.to_dict(enriched=True) for apt in appointments]},
        status=200,
    )


@technician_only
def update_appointment_status(request, user, appointment_id):
    """Update appointment status (technician only)."""
    data = json_body(request)
    appointment = (
        Appointment.objects.filter(pk=appointment_id)
        .select_related('user', 'technician', 'service', 'user_address')
        .first()
    )
    old_status = appointment.status if appointment else None

    if not appointment:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    if appointment.technician_id != int(user.id):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if 'status' in data:
        new_status = data['status']
        if not validate_appointment_status(new_status):
            return JsonResponse({'error': 'Invalid status'}, status=400)
        if new_status != appointment.status and not validate_appointment_transition(
            appointment.status, new_status
        ):
            return JsonResponse(
                {'error': f'Cannot transition from {appointment.status} to {new_status}'},
                status=400,
            )
        appointment.status = new_status

    if 'travel_status' in data:
        appointment.travel_status = data['travel_status']
        if data['travel_status'] == 'on_the_way' and not appointment.started_at:
            appointment.started_at = datetime.utcnow()
        elif data['travel_status'] == 'arrived' and not appointment.arrived_at:
            appointment.arrived_at = datetime.utcnow()
        elif data['travel_status'] == 'completed':
            if not appointment.completed_at:
                appointment.completed_at = datetime.utcnow()
            appointment.status = 'completed'

    if 'evidence_photos' in data:
        appointment.evidence_photos = data['evidence_photos']

    if 'extra_cost' in data:
        try:
            appointment.extra_cost = float(data['extra_cost'])
        except (ValueError, TypeError):
            pass

    if 'completion_notes' in data:
        appointment.completion_notes = data['completion_notes']

    appointment.save()

    # FASE 6: Event Tracking
    if 'status' in data and data['status'] != old_status:
        if data['status'] == 'cancelled':
            track_event(
                event_type='BOOKING_CANCELLED',
                user_id=user.id,
                entity_type='appointment',
                entity_id=appointment.id,
                metadata={
                    'previous_status': old_status,
                    'cancelled_by': 'technician',
                    'reason': data.get('reason'),
                },
            )
        elif data['status'] == 'completed':
            track_event(
                event_type='BOOKING_COMPLETED',
                user_id=user.id,
                entity_type='appointment',
                entity_id=appointment.id,
                metadata={
                    'previous_status': old_status,
                    'completed_by': 'technician',
                },
            )

    return JsonResponse(appointment.to_dict(enriched=True), status=200)
