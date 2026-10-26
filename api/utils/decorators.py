"""
Auth decorators - direct port of app/utils/decorators.py (Flask version).

Behavior parity:
- jwt_required_custom : valid JWT + user exists + status == 'active' (401 otherwise)
- admin_only          : + role == 'admin' (403 otherwise)
- technician_only     : + role == 'technician' (403 otherwise)
- customer_only       : + role == 'customer' (403 otherwise)
- jwt_optional        : resolves user when a token is present, never fails

Decorated views receive the authenticated user as the FIRST argument after
`request` (like Flask's get_jwt_identity() usage inside the view body).
"""
from functools import wraps

from django.http import JsonResponse

from api.models import User
from api.utils.jwt_utils import get_jwt_identity


def _identity_or_none(request):
    return get_jwt_identity(request)


def _load_user(request):
    """Return (user_or_None, error_response_or_None)."""
    identity = _identity_or_none(request)
    if identity is None:
        return None, JsonResponse(
            {'error': 'Unauthorized', 'message': 'Authentication required'},
            status=401,
        )
    try:
        user = User.objects.get(pk=int(identity))
    except (User.DoesNotExist, TypeError, ValueError):
        return None, JsonResponse(
            {'error': 'Unauthorized', 'message': 'Authentication required'},
            status=401,
        )
    return user, None


def jwt_required_custom(fn):
    """Custom JWT requirement decorator that checks user status"""

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user, error = _load_user(request)
        if error is not None:
            return error
        if user.status != 'active':
            return JsonResponse(
                {'error': 'Unauthorized', 'message': 'User account is not active'},
                status=401,
            )
        return fn(request, user, *args, **kwargs)

    return wrapper


def jwt_required(fn):
    """Plain JWT requirement (like flask_jwt_extended.jwt_required)."""

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user, error = _load_user(request)
        if error is not None:
            return error
        return fn(request, user, *args, **kwargs)

    return wrapper


def jwt_optional(fn):
    """Like jwt_required(optional=True): user resolved when a valid token exists."""

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user, _error = _load_user(request)
        request.jwt_user = user  # may be None
        return fn(request, *args, **kwargs)

    return wrapper


def admin_only(fn):
    """Restrict access to active admin users."""

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user, error = _load_user(request)
        if error is not None:
            return error
        if user.role != 'admin' or user.status != 'active':
            return JsonResponse(
                {'error': 'Forbidden', 'message': 'Admin access required'},
                status=403,
            )
        return fn(request, user, *args, **kwargs)

    return wrapper


def technician_only(fn):
    """Restrict access to active technician users."""

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user, error = _load_user(request)
        if error is not None:
            return error
        if user.role != 'technician' or user.status != 'active':
            return JsonResponse(
                {'error': 'Forbidden', 'message': 'Technician access required'},
                status=403,
            )
        return fn(request, user, *args, **kwargs)

    return wrapper


def customer_only(fn):
    """Restrict access to active customer users."""

    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user, error = _load_user(request)
        if error is not None:
            return error
        if user.role != 'customer' or user.status != 'active':
            return JsonResponse(
                {'error': 'Forbidden', 'message': 'Customer access required'},
                status=403,
            )
        return fn(request, user, *args, **kwargs)

    return wrapper
