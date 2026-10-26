"""
Root URL configuration for PlomApp Django backend.
All API routes are mounted under /api/ exactly like the Flask blueprints.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path, include

from api.views import serve_uploaded_file

urlpatterns = [
    # Legacy uploads directory: /static/uploads/evidence/<filename>
    re_path(
        r'^static/uploads/(?P<path>.*)$',
        serve_uploaded_file,
    ),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = 'api.errors.bad_request'
handler401 = 'api.errors.unauthorized'
handler403 = 'api.errors.forbidden'
handler404 = 'api.errors.not_found'
handler500 = 'api.errors.internal_error'
