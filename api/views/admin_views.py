"""
Admin - port of app/routes/admin.py (/api/admin).
"""
import calendar
from datetime import datetime, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse

from api.models import Appointment, Service, TechnicianProfile, User
from api.services.appointment_service import validate_appointment_transition
from api.utils.decorators import admin_only
from api.utils.request_utils import json_body, query_int, query_str
from api.utils.validators import validate_appointment_status, validate_role, validate_status


def _format_appointment_for_admin(appointment):
    customer = appointment.user
    technician = appointment.technician
    service = appointment.service
    return {
        'id': appointment.id,
        'status': appointment.status,
        'date': appointment.date.isoformat() if appointment.date else None,
        'dateFormatted': appointment.date.strftime('%d/%m/%Y') if appointment.date else None,
        'time': appointment.time,
        'serviceName': service.name if service else 'Servicio',
        'serviceId': service.id if service else None,
        'technicianName': technician.name if technician else 'Por asignar',
        'technicianId': appointment.technician_id,
        'clientName': customer.name if customer else 'Cliente',
        'clientAvatar': customer.avatar if customer else None,
        'technicianAvatar': technician.avatar if technician else None,
        'notes': appointment.notes,
        'createdAt': appointment.created_at.isoformat() if appointment.created_at else None,
    }


def _build_week_calendar():
    today = datetime.utcnow().date()
    calendar_items = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        count = Appointment.objects.filter(date=day).count()
        calendar_items.append({
            'date': day.isoformat(),
            'label': day.strftime('%a').capitalize(),
            'dayNum': day.day,
            'isToday': offset == 0,
            'count': count,
        })
    return calendar_items


def _build_monthly_appointments():
    monthly_map = {}
    for appointment in Appointment.objects.all():
        if not appointment.date:
            continue
        month_key = appointment.date.strftime('%Y-%m')
        if month_key not in monthly_map:
            monthly_map[month_key] = {
                'month': calendar.month_abbr[appointment.date.month],
                'year': appointment.date.year,
                'total': 0,
                'completed': 0,
            }
        monthly_map[month_key]['total'] += 1
        if appointment.status == 'completed':
            monthly_map[month_key]['completed'] += 1

    return [monthly_map[key] for key in sorted(monthly_map.keys())][-6:]


def _build_service_breakdown():
    rows = (
        Service.objects.annotate(cnt=Count('appointments'))
        .order_by('-cnt')
    )
    return [
        {
            'id': s.id,
            'name': s.name,
            'icon': s.icon or 'fa-screwdriver-wrench',
            'count': s.cnt,
        }
        for s in rows
    ]


@admin_only
def dashboard(request, user):
    """Get admin dashboard stats."""
    total_customers = User.objects.filter(role='customer').count()
    total_technicians = User.objects.filter(role='technician').count()
    total_users = User.objects.count()

    total_appointments = Appointment.objects.count()
    completed_appointments = Appointment.objects.filter(status='completed').count()
    pending_appointments = Appointment.objects.filter(status='pending').count()
    scheduled_appointments = Appointment.objects.filter(status='scheduled').count()
    in_progress_appointments = Appointment.objects.filter(status='in_progress').count()
    cancelled_appointments = Appointment.objects.filter(status='cancelled').count()

    revenue_result = Appointment.objects.filter(status='completed').aggregate(
        s=Sum('service__base_price')
    )['s']
    total_revenue = float(revenue_result) if revenue_result else 0.0

    avg_rating_result = TechnicianProfile.objects.aggregate(r=Avg('rating'))['r']
    avg_rating = float(avg_rating_result) if avg_rating_result else 0.0

    today = datetime.utcnow().date()
    today_appointments = list(
        Appointment.objects.filter(date=today)
        .select_related('user', 'technician', 'service')
    )
    today_completed = sum(1 for apt in today_appointments if apt.status == 'completed')
    today_scheduled = sum(1 for apt in today_appointments if apt.status == 'scheduled')
    today_in_progress = sum(1 for apt in today_appointments if apt.status == 'in_progress')

    ordered = Appointment.objects.order_by('-date', '-time').select_related(
        'user', 'technician', 'service'
    )
    recent_appointments = list(ordered[:10])
    all_appointments = list(ordered)

    completion_rate = round(
        (completed_appointments / total_appointments * 100) if total_appointments else 0
    )

    return JsonResponse({
        'stats': {
            'totalClients': total_customers,
            'totalTechnicians': total_technicians,
            'totalAppointments': total_appointments,
            'completionRate': completion_rate,
            'inProgressAppointments': in_progress_appointments,
            'scheduledAppointments': scheduled_appointments,
            'cancelledAppointments': cancelled_appointments,
            'todayTotal': len(today_appointments),
            'todayCompleted': today_completed,
            'todayScheduled': today_scheduled,
            'todayInProgress': today_in_progress,
            'revenueEstimate': total_revenue,
            'totalRevenue': total_revenue,
            'avgRating': avg_rating,
        },
        'weekCalendar': _build_week_calendar(),
        'todaySchedule': [
            {
                'id': apt.id,
                'time': apt.time,
                'endTime': apt.time,
                'title': apt.service.name if apt.service else 'Servicio',
                'clientName': apt.user.name if apt.user else 'Cliente',
                'technicianName': apt.technician.name if apt.technician else 'Por asignar',
                'status': apt.status,
                'isPrimary': apt.status == 'in_progress',
            }
            for apt in today_appointments
        ],
        'recentAppointments': [_format_appointment_for_admin(apt) for apt in recent_appointments],
        'allAppointments': [_format_appointment_for_admin(apt) for apt in all_appointments],
        'monthlyAppointments': _build_monthly_appointments(),
        'composition': {
            'total': total_users,
            'clients': total_customers,
            'technicians': total_technicians,
        },
        'serviceBreakdown': _build_service_breakdown(),
        'users': {
            'total': total_users,
            'customers': total_customers,
            'technicians': total_technicians,
        },
        'appointments': {
            'total': total_appointments,
            'completed': completed_appointments,
            'pending': pending_appointments,
        },
        'revenue': total_revenue,
        'avg_rating': avg_rating,
        'recent_appointments': [
            _format_appointment_for_admin(apt) for apt in recent_appointments
        ],
        'services': [
            s.to_dict() for s in Service.objects.order_by('name')
        ],
    }, status=200)


@admin_only
def list_users(request, user):
    """List all users with filters."""
    role_filter = query_str(request, 'role')
    status_filter = query_str(request, 'status')
    search = query_str(request, 'search', '')
    limit = query_int(request, 'limit', 20) or 20
    offset = query_int(request, 'offset', 0) or 0

    if limit > 100:
        limit = 100

    query = User.objects.all()

    if role_filter and validate_role(role_filter):
        query = query.filter(role=role_filter)

    if status_filter and validate_status(status_filter):
        query = query.filter(status=status_filter)

    if search:
        query = query.filter(Q(name__icontains=search) | Q(email__icontains=search))

    total = query.count()
    users = list(query[offset:offset + limit])

    return JsonResponse({
        'users': [u.to_dict() for u in users],
        'total': total,
        'limit': limit,
        'offset': offset,
    }, status=200)


@admin_only
def create_user(request, user):
    """Create new user (admin only)."""
    data = json_body(request)

    if not data or not data.get('email') or not data.get('password'):
        return JsonResponse({'error': 'email and password are required'}, status=400)

    # Check if user exists
    if User.objects.filter(email=data['email']).first():
        return JsonResponse({'error': 'Email already exists'}, status=409)

    new_user = User(
        name=data.get('name', 'New User'),
        email=data['email'],
        role=data.get('role', 'customer'),
        phone=data.get('phone'),
        address=data.get('address'),
        status=data.get('status', 'active'),
    )
    new_user.set_password(data['password'])
    new_user.save()

    return JsonResponse(new_user.to_dict(), status=201)


@admin_only
def update_user(request, user, user_id):
    """Update user."""
    target = User.objects.filter(pk=user_id).first()

    if not target:
        return JsonResponse({'error': 'User not found'}, status=404)

    data = json_body(request)

    if 'name' in data:
        target.name = data['name']
    if 'phone' in data:
        target.phone = data['phone']
    if 'address' in data:
        target.address = data['address']
    if 'avatar' in data:
        target.avatar = data['avatar']
    if 'role' in data and validate_role(data['role']):
        target.role = data['role']
    if 'status' in data and validate_status(data['status']):
        target.status = data['status']

    target.save()

    return JsonResponse(target.to_dict(), status=200)


@admin_only
def update_appointment(request, user, appointment_id):
    """Update appointment (admin only)."""
    appointment = (
        Appointment.objects.select_related('user', 'technician', 'service')
        .filter(pk=appointment_id)
        .first()
    )

    if not appointment:
        return JsonResponse({'error': 'Appointment not found'}, status=404)

    data = json_body(request)

    if 'status' in data:
        if not validate_appointment_status(data['status']):
            return JsonResponse({'error': 'Invalid status'}, status=400)
        if not validate_appointment_transition(appointment.status, data['status']):
            return JsonResponse(
                {'error': f'Cannot transition from {appointment.status} to {data["status"]}'},
                status=400,
            )
        appointment.status = data['status']

    if 'technician_id' in data:
        appointment.technician_id = data['technician_id']
    if 'date' in data:
        appointment.date = data['date']
    if 'time' in data:
        appointment.time = data['time']
    if 'notes' in data:
        appointment.notes = data['notes']

    appointment.save()

    return JsonResponse(appointment.enrich(), status=200)


@admin_only
def delete_user(request, user, user_id):
    """Delete user (admin only)."""
    target = User.objects.filter(pk=user_id).first()
    if not target:
        return JsonResponse({'error': 'User not found'}, status=404)
    try:
        from api.models import TechnicianProfile

        tech = TechnicianProfile.objects.filter(user_id=user_id).first()
        if tech:
            tech.delete()
        target.delete()
        return JsonResponse(
            {'success': True, 'message': 'Usuario eliminado exitosamente'},
            status=200,
        )
    except Exception:
        # If foreign keys prevent delete, deactivate instead
        target.status = 'inactive'
        target.save()
        return JsonResponse(
            {'success': True, 'message': 'Usuario desactivado debido a registros asociados'},
            status=200,
        )
