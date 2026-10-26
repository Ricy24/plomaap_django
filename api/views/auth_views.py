"""
Auth routes - port of app/routes/auth.py (/api/auth).
"""
import os

from django.http import JsonResponse

from api.controllers import auth_controller as ctrl
from api.controllers import passkey_controller as passkey
from api.models import User
from api.utils.decorators import jwt_required_custom
from api.utils.jwt_utils import generate_token
from api.utils.request_utils import json_body


def google_login(request):
    """POST /api/auth/google-login"""
    data = json_body(request)
    token = data.get('credential')

    if not token:
        return JsonResponse({'error': 'Token missing'}, status=400)

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        # 1. Leer el Client ID desde el archivo .env
        CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

        # Validación de seguridad por si olvidas ponerlo en el .env
        if not CLIENT_ID:
            return JsonResponse({'error': 'Server configuration error'}, status=500)

        # 2. Usar el CLIENT_ID dinámico
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)

        user_email = idinfo['email']
        user = User.objects.filter(email=user_email).first()

        if not user:
            user = User(
                name=idinfo.get('name') or user_email.split('@')[0],
                email=user_email,
                role='customer',
                phone=None,
                address=None,
                avatar=idinfo.get('picture'),
            )
            user.set_password(os.getenv('GOOGLE_DEFAULT_PASSWORD', 'GoogleAuth123!'))
            user.save()

        if user.status != 'active':
            return JsonResponse({'error': 'User account is not active'}, status=403)

        access_token = generate_token(user.id)

        return JsonResponse({
            'token': access_token,
            'user': user.to_dict(),
        }, status=200)

    except ValueError:
        return JsonResponse({'error': 'Invalid Google token'}, status=401)


def login_route(request):
    """Login endpoint"""
    return ctrl.login(request)


def register_route(request):
    """Register endpoint"""
    return ctrl.register(request)


@jwt_required_custom
def profile_get(request, user):
    """Get user profile"""
    return ctrl.get_profile(user.id)


@jwt_required_custom
def profile_update(request, user):
    """Update user profile"""
    return ctrl.update_profile(request, user.id)


@jwt_required_custom
def logout(request, user):
    """Logout endpoint"""
    return JsonResponse({'message': 'Logged out successfully'}, status=200)


def forgot_password_route(request):
    """Forgot password endpoint"""
    return ctrl.forgot_password(request)


def reset_password_route(request):
    """Reset password with code/token"""
    return ctrl.reset_password(request)


@jwt_required_custom
def refresh_token_route(request, user):
    """Refresh JWT access token"""
    if not user or user.status != 'active':
        return JsonResponse({'error': 'Cuenta inactiva o no encontrada'}, status=403)
    new_token = generate_token(user.id)
    return JsonResponse({'success': True, 'token': new_token, 'user': user.to_dict()}, status=200)


@jwt_required_custom
def passkey_reg_options_route(request, user):
    """Get registration options for WebAuthn/Passkey"""
    return passkey.passkey_register_options(request, user.id)


@jwt_required_custom
def passkey_reg_verify_route(request, user):
    """Verify and save WebAuthn/Passkey"""
    return passkey.passkey_register_verify(request, user.id)


def passkey_auth_options_route(request):
    """Get authentication options for WebAuthn/Passkey"""
    return passkey.passkey_login_options(request)


def passkey_auth_verify_route(request):
    """Verify assertion and login with WebAuthn/Passkey"""
    return passkey.passkey_login_verify(request)


def verify_email_route(request):
    """Verify email address with code or link (GET renders HTML, POST returns JSON)"""
    return ctrl.verify_email(request)


def resend_verification_route(request):
    """Resend email verification code"""
    return ctrl.resend_verification(request)
