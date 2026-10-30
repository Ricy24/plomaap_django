"""
Rate limiting para endpoints sensibles (login, register, forgot-password).

Implementación ligera basada en la cache de Django. Funciona con LocMemCache
en desarrollo y con Redis/Memcached en producción si se configura CACHES.

Uso:
    from api.utils.rate_limit import rate_limit

    @rate_limit(requests=5, window=60)   # 5 peticiones por minuto por IP
    def login_route(request):
        ...
"""
from __future__ import annotations

import functools
import logging
import time

from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Prefijo para las claves de cache, para no colisionar con otras apps.
_CACHE_PREFIX = "rl:"

# Límites por defecto (peticiones, ventana en segundos).
DEFAULT_REQUESTS = 10
DEFAULT_WINDOW = 60


def _client_ip(request) -> str:
    """Obtiene la IP del cliente, respetando X-Forwarded-For detrás de un proxy."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        # El primer valor es el cliente original.
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(requests: int = DEFAULT_REQUESTS, window: int = DEFAULT_WINDOW):
    """Decorador que limita peticiones por IP y por endpoint.

    Si se excede el límite, responde 429 Too Many Requests con un mensaje
    JSON y registra el evento.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ip = _client_ip(request)
            key = f"{_CACHE_PREFIX}{request.path}:{ip}"

            # Contador atómico: get + set no es atómico, pero es suficiente
            # para un rate limiter básico (LocMemCache).
            now = time.time()
            data = cache.get(key)
            if data is None:
                data = {"count": 0, "start": now}

            # Reiniciar la ventana si ya pasó.
            if now - data["start"] >= window:
                data = {"count": 0, "start": now}

            data["count"] += 1
            cache.set(key, data, timeout=window)

            if data["count"] > requests:
                logger.warning(
                    "Rate limit excedido: %s %s desde %s (%d/%d en %ds)",
                    request.method,
                    request.path,
                    ip,
                    data["count"],
                    requests,
                    window,
                )
                return JsonResponse(
                    {
                        "error": "Too many requests",
                        "message": f"Límite de {requests} peticiones por "
                        f"{window} segundos excedido. Intenta más tarde.",
                    },
                    status=429,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator