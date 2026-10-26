"""
HTTP method dispatcher - replicates Flask's method-specific routing.

Usage in urls.py:
    path('auth/profile', methods(GET=profile_get, PATCH=profile_update))

Any method not listed returns 405 (Flask behavior), and HEAD falls back to GET.
"""
from django.http import JsonResponse


def methods(**handlers):
    allowed = ', '.join(sorted(handlers.keys()))
    allowed_header = ', '.join(sorted(set(list(handlers.keys()) + ['HEAD', 'OPTIONS'])))

    def dispatcher(request, *args, **kwargs):
        handler = handlers.get(request.method)
        if handler is None and request.method == 'HEAD':
            handler = handlers.get('GET')
        if handler is None:
            return JsonResponse(
                {
                    'error': 'Method not allowed',
                    'message': f'{request.method} method is not allowed for this endpoint.',
                },
                status=405,
                headers={'Allow': allowed_header},
            )
        return handler(request, *args, **kwargs)

    dispatcher.__name__ = f"dispatch_{allowed.replace(', ', '_').lower()}"
    return dispatcher
