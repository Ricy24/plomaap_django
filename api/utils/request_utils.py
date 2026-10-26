"""
Shared request helpers (Flask request.* equivalents).
"""
import json


def json_body(request):
    """Flask's request.get_json(silent=True) equivalent -> dict."""
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode('utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def query_int(request, name, default=None):
    """request.args.get(name, type=int) equivalent."""
    raw = request.GET.get(name)
    if raw is None or raw == '':
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def query_str(request, name, default=''):
    """request.args.get(name, default=str) equivalent."""
    val = request.GET.get(name, default)
    return default if val is None else val
