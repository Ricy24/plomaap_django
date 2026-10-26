"""
PlomApp API views - one module per Flask blueprint.
"""
import os

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse


def serve_uploaded_file(request, path):
    """Serve /static/uploads/<path> (evidence photos) with path traversal protection."""
    base = os.path.abspath(str(settings.BASE_DIR / 'static' / 'uploads'))
    full = os.path.abspath(os.path.join(base, path))
    if not full.startswith(base + os.sep) or not os.path.isfile(full):
        raise Http404()
    return FileResponse(open(full, 'rb'))
