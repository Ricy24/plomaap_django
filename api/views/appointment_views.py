"""
Appointments - port of app/routes/appointments.py (/api/appointments).
"""
from datetime import datetime

from django.db import transaction
from django.http import JsonResponse

from api.models import Appointment, Service, User, UserAddress
from api.services.appointment_service import (
    check_technician_availability,
    find_available_technician,
    get_smart_time_slots,
    validate_appointment_transition,
)
from api.services.event_service import track_event
from api.utils.decorators import jwt_required_custom
from api.utils.email_utils import send_template_email
from api.utils.request_utils import json_body, query_int, query_str
from api.utils.validators import validate_appointment_status, validate_date_time

RELATION = {'user', 'technician', 'service', 'user_address'}


def _enriched(apt):
    return apt.to_dict(enriched=True)


def _base_queryset():
    return Appointment.objects.select_related(*RELATION)


def get_availability(request):
    """Dedicated availability slots endpoint."""
    service_id = query_int(request, 'service_id') or query_int(request, 'serviceId')
    date_str = query_str(request, 'date')
    technician_id = query_int(request, 'technician_id') or query_int(request, 'technicianId')

    if not date_str:
        return JsonResponse({'error': 'date is required'}, status=400)

    result = get_smart_time_slots(
        service_id=service_id, date_str=date_str, technician_id=technician_id
    )
    if isinstance(result, tuple):
        return JsonResponse(result[0], status=result[1])
    return JsonResponse(result, status=200)


@jwt_required_custom
def list_appointments(request, user):
    """List user appointments."""
    date_filter = query_str(request, 'date')
    status_filter = query_str(request, 'status')

    if user.role == 'customer':
        query = _base_queryset().filter(user_id=user.id)
    elif user.role == 'technician':
        query = _base_queryset().filter(technician_id=user.id)
    elif user.role == 'admin':
        query = _base_queryset()
    else:
        return JsonResponse({'error': 'Invalid user role'}, status=403)

    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            parsed_date = None
        if parsed_date:
            query = query.filter(date=parsed_date)

    if status_filter:
        query = query.filter(status=status_filter)

    # Order by date descending, time descending
    appointments = query.order_by('-date', '-time')

    return JsonResponse(
        {'appointments': [_enriched(apt) for apt in appointments]},
        status=200,
    )


@jwt_required_custom
def get_appointment(request, user, appointment_id):
    """Get single appointment details."""
    appointment = _base_queryset().filter(pk=appointment_id).first()

    if not appointment:
        return JsonResponse({'error': 'Appointment not found'}, status=404)

    if user.role == 'customer' and appointment.user_id != int(user.id):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    elif user.role == 'technician' and appointment.technician_id != int(user.id):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    return JsonResponse(_enriched(appointment), status=200)


@jwt_required_custom
def create_appointment(request, user):
    """
    Create a new appointment with atomic transaction and double-booking prevention.
    Supports automatic technician assignment or explicit selection.
    Associates location snapshot (address, address_reference, user_address_id).
    """
    if user.role != 'customer':
        return JsonResponse(
            {'success': False, 'message': 'Solo los clientes pueden agendar citas'},
            status=403,
        )

    data = json_body(request)

    service_id = data.get('service_id') or data.get('serviceId')
    date_value = data.get('date')
    time_value = data.get('time')
    address_str = data.get('address')
    address_ref = data.get('address_reference') or data.get('addressReference')
    user_addr_id = data.get('user_address_id') or data.get('userAddressId')
    notes_val = data.get('notes', '')

    # Validation of required parameters
    if not service_id or not date_value or not time_value:
        return JsonResponse(
            {'success': False, 'message': 'service_id, date y time son requeridos'},
            status=400,
        )

    if not validate_date_time(date_value, time_value):
        return JsonResponse(
            {'success': False, 'message': 'Formato de fecha u hora invalido'},
            status=400,
        )

    try:
        appointment_date = datetime.strptime(date_value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse(
            {'success': False, 'message': 'Formato de fecha invalido'},
            status=400,
        )

    # Ensure date is not in the past
    now = datetime.now()
    if appointment_date < now.date():
        return JsonResponse(
            {'success': False, 'message': 'No puedes agendar citas en fechas pasadas'},
            status=400,
        )

    # Validate service exists
    service = Service.objects.filter(pk=int(service_id)).first() if str(service_id).isdigit() else None
    if not service:
        return JsonResponse({'success': False, 'message': 'Servicio no encontrado'}, status=404)

    # Resolve address from user_address_id if provided
    resolved_address = address_str
    resolved_ref = address_ref
    if user_addr_id:
        user_addr = UserAddress.objects.filter(id=user_addr_id, user_id=user.id).first()
        if user_addr:
            if not resolved_address:
                resolved_address = f'{user_addr.label}: {user_addr.address}'
            if not resolved_ref and user_addr.reference:
                resolved_ref = user_addr.reference
        else:
            user_addr_id = None

    if not resolved_address and user.address:
        resolved_address = user.address

    # Handle Technician Assignment: Manual or Auto-assign
    supplied_technician_id = data.get('technician_id') or data.get('technicianId')
    technician = None

    try:
        # Atomic Transaction start (row locks require an atomic block)
        with transaction.atomic():
            if supplied_technician_id and str(supplied_technician_id) not in ('0', 'null', 'None', ''):
                tech_id = int(supplied_technician_id)
                is_avail, err_msg, technician = check_technician_availability(
                    tech_id, date_value, time_value
                )
                if not is_avail:
                    return JsonResponse({
                        'success': False,
                        'code': 'SLOT_UNAVAILABLE',
                        'message': err_msg or (
                            'El plomero seleccionado ya no esta disponible para ese horario. '
                            'Por favor elige otro horario o plomero.'
                        ),
                    }, status=409)
            else:
                # Auto-assign best available technician
                technician = find_available_technician(date_value, time_value, service.id)
                if not technician:
                    return JsonResponse({
                        'success': False,
                        'code': 'SLOT_UNAVAILABLE',
                        'message': (
                            'No hay ningun profesional disponible en ese horario. '
                            'Por favor selecciona otro horario.'
                        ),
                    }, status=409)

            # Double-booking check with row-lock to prevent race conditions
            conflict = (
                Appointment.objects.select_for_update()
                .filter(
                    technician_id=technician.id,
                    date=appointment_date,
                    time=time_value,
                    status__in=['pending', 'scheduled', 'in_progress'],
                )
                .first()
            )

            if conflict:
                return JsonResponse({
                    'success': False,
                    'code': 'SLOT_UNAVAILABLE',
                    'message': 'Este horario acaba de ser ocupado. Por favor selecciona otro horario.',
                }, status=409)

            appointment = Appointment(
                user_id=int(user.id),
                technician_id=technician.id,
                service_id=service.id,
                date=appointment_date,
                time=time_value,
                status='scheduled',
                address=resolved_address,
                address_reference=resolved_ref,
                user_address_id=user_addr_id,
                notes=notes_val,
            )
            appointment.save()

        # Send rich notification emails
        customer = User.objects.filter(pk=user.id).first()
        if customer and customer.email:
            send_template_email(
                customer.email,
                f'¡Servicio Confirmado! Cita #{appointment.id} - PlomApp',
                'appointment_customer',
                {
                    'name': customer.name,
                    'booking_id': f'PLM-{appointment.id:05d}',
                    'service_name': service.name,
                    'service_price': f'${float(service.base_price):,.0f} COP'.replace(',', '.'),
                    'duration': f'{service.duration_minutes or 60} minutos',
                    'appointment_date': appointment_date.strftime('%d/%m/%Y'),
                    'appointment_time': time_value,
                    'technician_name': technician.name,
                    'technician_rating': str(
                        technician.technician_profile.rating if technician.technician_profile else 4.8
                    ),
                    'address': resolved_address or 'Por coordinar',
                    'address_reference': resolved_ref or '',
                    'notes': notes_val or 'Ninguna observacion adicional.',
                    'text_body': (
                        f'Tu cita para {service.name} ha sido confirmada para el '
                        f'{appointment_date} a las {time_value}.'
                    ),
                },
            )

        if technician and technician.email:
            send_template_email(
                technician.email,
                f'Nueva cita asignada #{appointment.id} - PlomApp',
                'appointment_technician',
                {
                    'name': technician.name,
                    'booking_id': f'PLM-{appointment.id:05d}',
                    'service_name': service.name,
                    'appointment_date': appointment_date.strftime('%d/%m/%Y'),
                    'appointment_time': time_value,
                    'customer_name': customer.name if customer else 'Cliente',
                    'customer_phone': customer.phone if customer and customer.phone else 'No especificado',
                    'customer_address': resolved_address or 'Por coordinar',
                    'customer_reference': resolved_ref or '',
                    'notes': notes_val or '',
                    'text_body': (
                        f'Se te ha asignado una nueva cita para {service.name} el '
                        f'{appointment_date} a las {time_value}.'
                    ),
                },
            )

        # FASE 6: Event Tracking
        track_event(
            event_type='BOOKING_CREATED',
            user_id=user.id,
            entity_type='appointment',
            entity_id=appointment.id,
            metadata={
                'service_id': service.id,
                'service_name': service.name,
                'technician_id': appointment.technician_id,
                'date': str(appointment.date),
                'time': str(appointment.time),
                'total_price': float(service.base_price) if service.base_price else 0.0,
            },
        )

        return JsonResponse({
            'success': True,
            'message': 'Cita agendada exitosamente',
            'appointment': _enriched(appointment),
        }, status=201)

    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': f'Error agendando la cita: {str(e)}'},
            status=500,
        )


@jwt_required_custom
def update_appointment(request, user, appointment_id):
    """Update appointment status / cancellation."""
    appointment = _base_queryset().filter(pk=appointment_id).first()

    if not appointment:
        return JsonResponse({'error': 'Cita no encontrada'}, status=404)

    old_status = appointment.status
    if user.role == 'customer' and appointment.user_id != int(user.id):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    data = json_body(request)

    if user.role == 'customer':
        if 'status' in data:
            if data['status'] == 'cancelled':
                if appointment.status in ['completed', 'cancelled']:
                    return JsonResponse({
                        'success': False,
                        'message': 'No se puede cancelar una cita completada o previamente cancelada',
                    }, status=400)
                appointment.status = 'cancelled'
            else:
                return JsonResponse(
                    {'success': False, 'message': 'Solo puedes cancelar citas'},
                    status=400,
                )
    else:
        if 'status' in data:
            if not validate_appointment_status(data['status']):
                return JsonResponse({'success': False, 'message': 'Estado invalido'}, status=400)
            if not validate_appointment_transition(appointment.status, data['status']):
                return JsonResponse({
                    'success': False,
                    'message': (
                        f'Transicion no permitida de {appointment.status} '
                        f'a {data["status"]}'
                    ),
                }, status=400)
            appointment.status = data['status']
        if 'technician_id' in data:
            appointment.technician_id = data['technician_id']
        if 'notes' in data:
            appointment.notes = data['notes']

    appointment.save()

    # FASE 6: Event Tracking
    if appointment.status != old_status:
        if appointment.status == 'cancelled':
            track_event(
                event_type='BOOKING_CANCELLED',
                user_id=user.id,
                entity_type='appointment',
                entity_id=appointment.id,
                metadata={
                    'previous_status': old_status,
                    'cancelled_by': user.role if user else 'unknown',
                    'reason': data.get('reason') or data.get('cancellation_reason'),
                },
            )
        elif appointment.status == 'completed':
            track_event(
                event_type='BOOKING_COMPLETED',
                user_id=user.id,
                entity_type='appointment',
                entity_id=appointment.id,
                metadata={
                    'previous_status': old_status,
                    'completed_by': user.role if user else 'unknown',
                },
            )

    return JsonResponse({
        'success': True,
        'message': 'Cita actualizada',
        'appointment': _enriched(appointment),
    }, status=200)
