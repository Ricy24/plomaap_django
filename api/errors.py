"""
Error handler functions referenced by config.urls (handler400..handler500).
They mirror app/middlewares/error_handler.py from the Flask version.
"""
from django.http import JsonResponse

from api.middleware import bad_request, forbidden, internal_error, not_found, unauthorized

__all__ = ['bad_request', 'unauthorized', 'forbidden', 'not_found', 'internal_error']
