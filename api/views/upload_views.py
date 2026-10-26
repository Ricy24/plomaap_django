"""
Uploads - port of app/routes/upload.py (/api/upload).
"""
import os
import uuid

from django.conf import settings
from django.http import JsonResponse

from api.utils.request_utils import json_body

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

# Tamaño máximo de una foto de evidencia (10 MB)
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024

# Firmas reales de los formatos permitidos (evita subir un .exe/.html
# renombrado como .png). Se comprueban los primeros bytes del archivo.
_IMAGE_SIGNATURES = {
    'png': (b'\x89PNG\r\n\x1a\n',),
    'jpg': (b'\xff\xd8\xff',),
    'jpeg': (b'\xff\xd8\xff',),
    'gif': (b'GIF87a', b'GIF89a'),
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _is_real_image(file, ext):
    """Valida la firma binaria del archivo, no solo la extensión."""
    head = file.read(12)
    file.seek(0)
    if ext == 'webp':
        return head[:4] == b'RIFF' and head[8:12] == b'WEBP'
    return any(head.startswith(sig) for sig in _IMAGE_SIGNATURES.get(ext, ()))


def upload_evidence(request):
    files = request.FILES
    if 'image' not in files and 'file' not in files and 'photo' not in files:
        data = json_body(request)
        if data.get('url'):
            return JsonResponse({'success': True, 'url': data['url']}, status=200)
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    file = files.get('image') or files.get('file') or files.get('photo')
    if not file or file.name == '':
        return JsonResponse({'error': 'Empty filename'}, status=400)

    if allowed_file(file.name):
        ext = file.name.rsplit('.', 1)[1].lower()

        if file.size and file.size > MAX_EVIDENCE_BYTES:
            return JsonResponse(
                {'error': 'File too large (max 10 MB)'}, status=400
            )
        if not _is_real_image(file, ext):
            return JsonResponse(
                {'error': 'Invalid image content'}, status=400
            )

        unique_name = uuid.uuid4().hex + '.' + ext

        upload_dir = settings.UPLOADS_STATIC_DIR
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(str(upload_dir), unique_name)
        with open(file_path, 'wb') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        scheme = 'https' if request.is_secure() else 'http'
        photo_url = f'{scheme}://{request.get_host()}/static/uploads/evidence/{unique_name}'

        return JsonResponse({
            'success': True,
            'filename': unique_name,
            'url': photo_url,
        }, status=201)

    return JsonResponse(
        {'error': 'Invalid file extension. Allowed: png, jpg, jpeg, webp'},
        status=400,
    )


def get_evidence_presets(request):
    presets = [
        {
            'title': 'Tuberia con fuga (Antes)',
            'type': 'before',
            'url': 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80',
        },
        {
            'title': 'Desague obstruido (Antes)',
            'type': 'before',
            'url': 'https://images.unsplash.com/photo-1585771724684-38269d6639fd?auto=format&fit=crop&w=800&q=80',
        },
        {
            'title': 'Tuberia PVC reparada (Despues)',
            'type': 'after',
            'url': 'https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?auto=format&fit=crop&w=800&q=80',
        },
        {
            'title': 'Grifo nuevo instalado (Despues)',
            'type': 'after',
            'url': 'https://images.unsplash.com/photo-1542013936693-884638332954?auto=format&fit=crop&w=800&q=80',
        },
    ]
    return JsonResponse({'presets': presets}, status=200)
