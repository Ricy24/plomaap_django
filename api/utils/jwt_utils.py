"""
JWT helpers - drop-in replacement for app/utils/jwt_utils.py (Flask-JWT-Extended).

Tokens are HS256-signed with JWT_SECRET_KEY and store the user id as the
string "sub" claim, exactly like create_access_token(identity=str(user_id)).
Any token issued by the Flask backend keeps working here (same secret).
"""
from datetime import datetime, timedelta

import jwt
from django.conf import settings


def generate_token(user_id):
    """Generate JWT token for user (identity as string, Flask-compatible)."""
    now = datetime.utcnow()
    payload = {
        'sub': str(user_id),
        'iat': now,
        'exp': now + settings.JWT_ACCESS_TOKEN_EXPIRES,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token):
    """Decode and validate a JWT. Returns the payload dict or None."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_request(request):
    """
    Extract the raw token from the Authorization header.
    Supports: 'Bearer <token>' (also tolerates a bare token).
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return None
    parts = auth_header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1].strip()
    return auth_header.strip() or None


def get_jwt_identity(request):
    """Return the JWT identity (string user id) or None if missing/invalid."""
    token = get_token_from_request(request)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return payload.get('sub')


def get_current_user_id(request):
    """Get current user ID (int) from JWT or None."""
    identity = get_jwt_identity(request)
    if identity is None:
        return None
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None
