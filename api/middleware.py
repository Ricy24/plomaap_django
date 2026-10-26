"""
JSON error middleware - equivalent of app/middlewares/error_handler.py in Flask.
Guarantees that every error response is JSON (never an HTML debug page),
matching the Flask API contract consumed by the React frontend.
"""
import json
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _body(error, message):
    return {'error': error, 'message': message}


class JSONErrorMiddleware:
    """Convert uncaught exceptions and common errors to JSON responses."""

    ERROR_STATUSES = (400, 401, 403, 404, 500)
    LABELS = {
        400: ('Bad request', 'Bad request'),
        401: ('Unauthorized', 'Authentication required'),
        403: ('Forbidden', 'Access denied'),
        404: ('Not found', 'Resource not found'),
        500: ('Server error', 'Internal server error'),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # In DEBUG, 404/500 come back as HTML debug pages; the frontend
        # contract requires JSON. Views can opt out by setting
        # response.intentional_html = True (e.g. the verify-email HTML page).
        if (
            response.status_code in self.ERROR_STATUSES
            and not getattr(response, 'intentional_html', False)
            and 'json' not in (response.headers.get('Content-Type') or '')
        ):
            error, message = self.LABELS[response.status_code]
            response = JsonResponse(_body(error, message), status=response.status_code)
        return response

    def process_exception(self, request, exception):
        # Let Django's handler500 flow produce the canonical body
        return None


# ---------------------------------------------------------------------------
# Exception handlers used as Django error handlers (config/urls.py)
# ---------------------------------------------------------------------------
def bad_request(request, exception=None):
    message = str(exception) if exception else 'Bad request'
    return JsonResponse(_body('Bad request', message), status=400)


def unauthorized(request, exception=None):
    return JsonResponse(_body('Unauthorized', 'Authentication required'), status=401)


def forbidden(request, exception=None):
    return JsonResponse(_body('Forbidden', 'Access denied'), status=403)


def not_found(request, exception=None):
    return JsonResponse(_body('Not found', 'Resource not found'), status=404)


def internal_error(request):
    logger.exception('Unhandled server error on %s %s', request.method, request.path)
    return JsonResponse(_body('Server error', 'Internal server error'), status=500)
