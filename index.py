"""Punto de entrada WSGI para desplegar el backend Django en Vercel.

Vercel ejecuta este archivo como funcion serverless. El objeto `app` es la
aplicacion WSGI de Django, exactamente la misma que usa Gunicorn en AWS.

Notas:
- Este archivo debe estar en la raiz del repositorio.
- `vercel.json` enruta todas las peticiones a este entrypoint.
- `.vercelignore` excluye `pyproject.toml` para que Vercel instale las
  dependencias desde `requirements.txt` (el pyproject solo tiene config de Ruff).
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
