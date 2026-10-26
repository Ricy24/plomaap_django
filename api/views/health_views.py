"""
Health check - port of app/routes/health.py (GET /api/health).
"""
from datetime import datetime

from django.db import connection
from django.http import JsonResponse


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        db_status = 'connected'
    except Exception as e:
        db_status = f'disconnected: {e}'

    return JsonResponse(
        {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status,
        },
        status=200,
    )
