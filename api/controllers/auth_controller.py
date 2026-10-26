"""
Auth controller - direct port of app/controllers/auth_controller.py (Flask).
All functions receive the Django HttpRequest and return JsonResponse, keeping
the exact response bodies/status codes of the original API.
"""
import json as _json_lib
import secrets
from datetime import datetime, timedelta

from django.http import JsonResponse

from api.models import TechnicianProfile, User, utcnow
from api.services.event_service import track_event
from api.utils.email_utils import send_template_email
from api.utils.jwt_utils import generate_token
from api.utils.validators import validate_email, validate_name, validate_password


def parse_json(request):
    """Parse JSON body (Flask's request.get_json() equivalent)."""
    if not request.body:
        return {}
    try:
        data = _json_lib.loads(request.body.decode('utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def login(request):
    """Handle user login"""
    data = parse_json(request)

    if not data.get('email') or not data.get('password'):
        return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

    user = User.objects.filter(email=data['email']).first()

    if not user or not user.verify_password(data['password']):
        return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=401)

    if user.status != 'active':
        return JsonResponse({'success': False, 'message': 'Account is not active'}, status=401)

    requested_role = data.get('role')
    if requested_role:
        normalized_requested = 'customer' if requested_role == 'user' else requested_role
        normalized_user_role = 'customer' if user.role == 'user' else user.role
        if normalized_requested != normalized_user_role:
            role_labels = {'customer': 'Cliente', 'technician': 'Técnico', 'admin': 'Administrador'}
            actual_label = role_labels.get(user.role, user.role)
            return JsonResponse({
                'success': False,
                'message': f'Esta cuenta tiene rol de {actual_label}. Por favor ingresa por el portal correspondiente.',
            }, status=403)

    token = generate_token(user.id)
    send_template_email(
        user.email,
        'Inicio de sesión en PlomApp',
        'login_alert',
        {
            'name': user.name,
            'login_time': datetime.utcnow().strftime('%d/%m/%Y %H:%M'),
            'text_body': 'Se ha iniciado sesión en tu cuenta de PlomApp.',
        },
    )
    user_dict = user.to_dict()
    tech_profile = None
    if user.role == 'technician':
        tech_profile = user.technician_profile
    tech_profile_dict = tech_profile.to_dict() if tech_profile else None
    if tech_profile_dict:
        user_dict['technicianProfile'] = tech_profile_dict

    res_data = {
        'success': True,
        'message': 'Inicio de sesión correcto',
        'token': token,
        'user': user_dict,
    }
    if tech_profile_dict:
        res_data['technicianProfile'] = tech_profile_dict

    return JsonResponse(res_data, status=200)


def register(request):
    """Handle user registration"""
    data = parse_json(request)

    if not data:
        return JsonResponse({'success': False, 'message': 'No data provided'}, status=400)

    # Validation
    if not validate_email(data.get('email')):
        return JsonResponse({'success': False, 'message': 'Invalid email format'}, status=400)

    if not validate_password(data.get('password')):
        return JsonResponse({'success': False, 'message': 'Password must be at least 8 characters'}, status=400)

    if not validate_name(data.get('name')):
        return JsonResponse({'success': False, 'message': 'Name must be at least 2 characters'}, status=400)

    # Check if user exists
    if User.objects.filter(email=data['email']).exists():
        return JsonResponse({'success': False, 'message': 'Email already registered'}, status=409)

    # Create user
    user = User(
        name=data['name'],
        email=data['email'],
        role=data.get('role', 'customer'),
        phone=data.get('phone'),
        address=data.get('address'),
    )
    user.set_password(data['password'])
    user.save()

    # Create technician profile if role is technician
    if user.role == 'technician':
        TechnicianProfile.objects.create(
            user_id=user.id,
            specialties=data.get('specialties', []),
        )

    # Generar token de verificacion de 6 digitos
    verification_code = f'{secrets.randbelow(900000) + 100000}'
    user.verification_token = verification_code
    user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
    user.email_verified = False
    user.save()

    token = generate_token(user.id)
    send_template_email(
        user.email,
        'Verifica tu cuenta en PlomApp',
        'welcome',
        {
            'name': user.name,
            'role': user.role,
            'role_label': (
                'Cliente' if user.role == 'customer'
                else 'Técnico' if user.role == 'technician'
                else 'Administrador'
            ),
            'text_body': 'Gracias por registrarte en PlomApp.',
        },
    )
    # FASE 6: Event Tracking
    track_event(
        event_type='USER_REGISTERED',
        user_id=user.id,
        entity_type='user',
        entity_id=user.id,
        metadata={
            'email': user.email,
            'role': user.role,
            'name': user.name,
        },
    )
    return JsonResponse({
        'success': True,
        'message': 'Registro exitoso',
        'token': token,
        'user': user.to_dict(),
    }, status=201)


def get_profile(user_id):
    """Get user profile"""
    user = User.objects.filter(pk=user_id).first()

    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    user_dict = user.to_dict()
    if user.role == 'technician' and user.technician_profile:
        user_dict['technicianProfile'] = user.technician_profile.to_dict()
    return JsonResponse(user_dict, status=200)


def update_profile(request, user_id):
    """Update user profile"""
    user = User.objects.filter(pk=user_id).first()

    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    data = parse_json(request)

    if 'name' in data and validate_name(data['name']):
        user.name = data['name']

    if 'phone' in data:
        user.phone = data['phone']

    if 'address' in data:
        user.address = data['address']

    if 'avatar' in data:
        user.avatar = data['avatar']

    user.updated_at = utcnow()
    user.save()

    user_dict = user.to_dict()
    tech_profile_dict = (
        user.technician_profile.to_dict()
        if user.role == 'technician' and user.technician_profile
        else None
    )
    if tech_profile_dict:
        user_dict['technicianProfile'] = tech_profile_dict

    return JsonResponse({
        'success': True,
        'message': 'Perfil actualizado correctamente',
        'user': user_dict,
        'technicianProfile': tech_profile_dict,
    }, status=200)


def forgot_password(request):
    """Send a password reset code to the user's email."""
    data = parse_json(request)
    email = data.get('email')

    if not email:
        return JsonResponse({'success': False, 'message': 'Email es requerido'}, status=400)

    user = User.objects.filter(email=email).first()
    # Respondemos siempre igual para no filtrar existencia de cuentas
    if not user:
        return JsonResponse({
            'success': True,
            'message': 'Si el correo existe, recibirás instrucciones de recuperación.',
        }, status=200)

    reset_code = f'{secrets.randbelow(900000) + 100000}'
    user.reset_token = reset_code
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    user.save()

    send_template_email(
        user.email,
        'Recuperación de contraseña - PlomApp',
        'reset_password',
        {
            'name': user.name,
            'code': reset_code,
            'text_body': 'Usa este código para restablecer tu contraseña.',
        },
    )
    return JsonResponse({
        'success': True,
        'message': 'Si el correo existe, recibirás instrucciones de recuperación.',
    }, status=200)


def reset_password(request):
    """Reset password using email + token (code) + new password."""
    data = parse_json(request)
    email = data.get('email')
    token = str(data.get('token') or data.get('code') or '').strip()
    new_password = data.get('password') or data.get('new_password')

    if not email or not token or not new_password:
        return JsonResponse({'success': False, 'message': 'Campos incompletos'}, status=400)

    if not validate_password(new_password):
        return JsonResponse({'success': False, 'message': 'Password must be at least 8 characters'}, status=400)

    user = User.objects.filter(email=email).first()
    if not user or not user.reset_token or user.reset_token != token:
        return JsonResponse({'success': False, 'message': 'Código de recuperación inválido'}, status=400)

    if user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow():
        return JsonResponse({'success': False, 'message': 'El código de recuperación ha expirado'}, status=400)

    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    user.updated_at = utcnow()
    user.save()

    return JsonResponse({'success': True, 'message': 'Contraseña actualizada correctamente'}, status=200)


def verify_email(request):
    """Verify email with token. GET returns HTML (Flask parity), POST returns JSON."""
    email = request.GET.get('email') or (parse_json(request).get('email'))
    token = request.GET.get('token') or str(
        (parse_json(request).get('token') if request.method == 'POST' else '') or ''
    ).strip()

    if not email or not token:
        if request.method == 'GET':
            return HttpResponseVerify('Faltan parámetros de verificación', ok=False)
        return JsonResponse({'success': False, 'message': 'Faltan parámetros de verificación'}, status=400)

    user = User.objects.filter(email=email).first()
    valid = (
        user
        and user.verification_token
        and user.verification_token == token
        and (
            not user.verification_token_expiry
            or user.verification_token_expiry >= datetime.utcnow()
        )
    )

    if not valid:
        if request.method == 'GET':
            return HttpResponseVerify('El código de verificación es inválido o ha expirado', ok=False)
        return JsonResponse({'success': False, 'message': 'Token inválido o expirado'}, status=400)

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    user.updated_at = utcnow()
    user.save()

    if request.method == 'GET':
        return HttpResponseVerify('Cuenta verificada correctamente', ok=True)
    return JsonResponse({'success': True, 'message': 'Cuenta verificada correctamente'}, status=200)


def HttpResponseVerify(message, ok):
    """HTML response for GET /api/auth/verify-email (Flask rendered inline HTML)."""
    from django.http import HttpResponse

    color = '#0F52BA' if ok else '#C62828'
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Verificación de cuenta - PlomApp</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F7F9FC;color:#1C2B41;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#fff;border-radius:20px;padding:36px 28px;box-shadow:0 4px 20px rgba(15,82,186,.08);border:1px solid #E2E8F0;text-align:center;max-width:420px}}
h1{{color:{color};font-size:22px;margin:0 0 8px 0}}</style></head>
<body><div class="card"><h1>PlomApp</h1><p>{message}</p></div></body></html>"""
    resp = HttpResponse(html, content_type='text/html; charset=utf-8', status=200 if ok else 400)
    # Exención: el HTML de verificación es una respuesta intencional del endpoint
    # (el JSONErrorMiddleware no debe convertirla a JSON).
    resp.intentional_html = True
    return resp


def resend_verification(request):
    """Resend verification code to the user's email."""
    data = parse_json(request)
    email = data.get('email')

    if not email:
        return JsonResponse({'success': False, 'message': 'Email es requerido'}, status=400)

    user = User.objects.filter(email=email).first()
    if not user:
        return JsonResponse({'success': False, 'message': 'Usuario no encontrado'}, status=404)

    if user.email_verified:
        return JsonResponse({'success': False, 'message': 'La cuenta ya está verificada'}, status=400)

    verification_code = f'{secrets.randbelow(900000) + 100000}'
    user.verification_token = verification_code
    user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
    user.save()

    send_template_email(
        user.email,
        'Verifica tu cuenta en PlomApp',
        'welcome',
        {
            'name': user.name,
            'code': verification_code,
            'text_body': 'Usa este código para verificar tu cuenta.',
        },
    )
    return JsonResponse({'success': True, 'message': 'Código de verificación reenviado'}, status=200)
