"""
Appointment service - direct port of app/services/appointment_service.py.
"""
from datetime import datetime, time as dtime, timedelta

from django.db import transaction

from api.models import Appointment, Service, User


def _normalize_schedule(schedule):
    if not schedule:
        return {}
    normalized = {}
    for day, ranges in schedule.items():
        if not ranges:
            continue
        normalized[day.lower()] = []
        for item in ranges:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                start, end = item
                try:
                    normalized[day.lower()].append([int(start), int(end)])
                except (TypeError, ValueError):
                    continue
    return normalized


def find_available_technician(date_str, time_str, service_id=None, exclude_technician_id=None):
    """Find available technician for given date/time/service with highest rating."""
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return None

    technicians = User.objects.filter(role='technician', status='active').select_related(
        'technician_profile'
    )

    available = []

    for tech in technicians:
        if exclude_technician_id and tech.id == exclude_technician_id:
            continue

        profile = tech.technician_profile
        if not profile or not profile.available:
            continue

        day_name = appointment_date.strftime('%a').lower()
        schedule = _normalize_schedule(profile.schedule or {})
        if day_name not in schedule:
            continue

        is_within_schedule = False
        for start_hour, end_hour in schedule[day_name]:
            if start_hour <= appointment_time.hour < end_hour:
                is_within_schedule = True
                break

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

        available.append({
            'technician': tech,
            'rating': float(profile.rating or 0.0),
        })

    available.sort(key=lambda x: x['rating'], reverse=True)
    return available[0]['technician'] if available else None


def get_available_time_slots(technician_id, date_str):
    """Get available time slots for technician on specific date (backward compatibility)."""
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return []

    tech = User.objects.filter(pk=technician_id).first()
    if not tech or tech.role != 'technician':
        return []

    profile = tech.technician_profile
    if not profile:
        return []

    day_name = appointment_date.strftime('%a').lower()
    schedule = _normalize_schedule(profile.schedule or {})

    if day_name not in schedule:
        return []

    slots = []
    for start_hour, end_hour in schedule[day_name]:
        current_hour = start_hour
        while current_hour < end_hour:
            slot_time = f'{int(current_hour):02d}:00'
            conflict = Appointment.objects.filter(
                technician_id=technician_id,
                date=appointment_date,
                time=slot_time,
                status__in=['pending', 'scheduled', 'in_progress'],
            ).first()

            if not conflict:
                slots.append(slot_time)

            current_hour += 1

    return slots


def get_smart_time_slots(service_id, date_str, technician_id=None):
    """
    Generate intelligent availability time slots for a service on a given date.
    Respects:
    - Service duration (e.g. 60 or 90 min)
    - Operating schedule of technicians
    - Existing appointments
    - Past time on current day
    - Grouping by period: morning, afternoon, evening
    """
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return {'error': 'Invalid date format'}, 400

    service = Service.objects.filter(pk=service_id).first() if service_id else None
    duration_minutes = (
        service.duration_minutes
        if service and service.duration_minutes
        else 60
    )

    # Determine candidate technicians
    if technician_id:
        tech = User.objects.filter(pk=technician_id).first()
        candidate_techs = (
            [tech]
            if tech and tech.role == 'technician' and tech.status == 'active'
            else []
        )
    else:
        candidate_techs = list(
            User.objects.filter(role='technician', status='active').select_related(
                'technician_profile'
            )
        )

    day_name = appointment_date.strftime('%a').lower()
    now = datetime.now()
    is_today = (appointment_date == now.date())

    # Standard working hours in PlomApp: 08:00 to 18:00
    candidate_hours = [
        (8, 0), (9, 0), (10, 0), (11, 0),
        (12, 0), (13, 0), (14, 0), (15, 0), (16, 0), (17, 0),
    ]

    # Preload conflicting appointments for the day (single query)
    day_conflicts = set(
        Appointment.objects.filter(
            date=appointment_date,
            status__in=['pending', 'scheduled', 'in_progress'],
        ).values_list('technician_id', 'time')
    )

    slots = []
    for hour, minute in candidate_hours:
        slot_start_str = f'{hour:02d}:{minute:02d}'
        slot_start_time = dtime(hour, minute)
        slot_end_dt = datetime.combine(appointment_date, slot_start_time) + timedelta(
            minutes=duration_minutes
        )
        slot_end_str = slot_end_dt.strftime('%H:%M')

        # Check if slot is already in the past today (buffer of 30 mins)
        if is_today and datetime.combine(appointment_date, slot_start_time) < (
            now + timedelta(minutes=30)
        ):
            is_available = False
            available_techs_count = 0
        else:
            available_techs_count = 0
            for tech in candidate_techs:
                profile = tech.technician_profile
                if not profile or not profile.available:
                    continue

                schedule = _normalize_schedule(profile.schedule or {})
                if day_name not in schedule:
                    continue

                # Must be within schedule
                within_schedule = any(
                    start_h <= hour < end_h for start_h, end_h in schedule[day_name]
                )
                if not within_schedule:
                    continue

                # Check conflict (preloaded set)
                if (tech.id, slot_start_str) in day_conflicts:
                    continue

                available_techs_count += 1

            is_available = (available_techs_count > 0)

        # Categorize period
        if hour < 12:
            period = 'morning'
        elif hour < 17:
            period = 'afternoon'
        else:
            period = 'evening'

        slots.append({
            'start': slot_start_str,
            'end': slot_end_str,
            'time': slot_start_str,
            'available': is_available,
            'period': period,
            'available_technicians_count': available_techs_count,
        })

    return {
        'date': date_str,
        'service_id': service_id,
        'duration_minutes': duration_minutes,
        'slots': slots,
    }


def validate_appointment_transition(current_status, new_status):
    """Validate appointment status transitions"""
    valid_transitions = {
        'pending': ['scheduled', 'cancelled'],
        'scheduled': ['in_progress', 'cancelled'],
        'in_progress': ['completed', 'cancelled'],
        'completed': [],
        'cancelled': [],
    }
    return new_status in valid_transitions.get(current_status, [])


def check_technician_availability(technician_id, date_str, time_str):
    """Check specific technician availability for booking with row lock."""
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return False, 'Formato de fecha u hora invalido', None

    tech = User.objects.filter(pk=technician_id).select_related('technician_profile').first()
    if not tech:
        return False, 'El plomero seleccionado no existe', None
    if tech.role != 'technician':
        return False, 'El usuario seleccionado no es un tecnico plomero', None
    if tech.status != 'active':
        return False, 'El plomero seleccionado no se encuentra activo', None

    profile = tech.technician_profile
    if not profile or not profile.available:
        return False, 'El plomero seleccionado no esta disponible para servicios', None

    day_name = appointment_date.strftime('%a').lower()
    schedule = _normalize_schedule(profile.schedule or {})
    if day_name not in schedule:
        return False, f'El plomero no atiende en el dia solicitado ({day_name})', None

    is_within_schedule = False
    for start_hour, end_hour in schedule[day_name]:
        if start_hour <= appointment_time.hour < end_hour:
            is_within_schedule = True
            break

    if not is_within_schedule:
        return False, 'La hora seleccionada esta fuera del horario de atencion del plomero', None

    conflict = Appointment.objects.filter(
        technician_id=tech.id,
        date=appointment_date,
        time=time_str,
        status__in=['pending', 'scheduled', 'in_progress'],
    ).first()

    if conflict:
        return (
            False,
            'El plomero seleccionado ya no esta disponible para ese horario. '
            'Por favor elige otro horario o plomero.',
            None,
        )

    return True, None, tech
