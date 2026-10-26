"""
Services - port of app/routes/services.py (/api/services).
"""
from django.db.models import Q
from django.http import JsonResponse

from api.models import Service
from api.utils.request_utils import query_int, query_str


def list_services(request):
    """List all services with pagination, category filter and hybrid search."""
    limit = query_int(request, 'limit', 50) or 50
    offset = query_int(request, 'offset', 0) or 0
    search = (query_str(request, 'search', '') or '').strip()
    category = (query_str(request, 'category', '') or '').strip()

    if limit > 100:
        limit = 100

    # Búsqueda híbrida inteligente si se proporciona texto de búsqueda
    if search:
        try:
            from api.services.hybrid_search_service import perform_hybrid_search
            cat_filter = category if category.lower() not in ['todo', 'todos', ''] else None
            hybrid_res = perform_hybrid_search(
                query=search,
                category_filter=cat_filter,
                top_k=limit,
            )
            services_data = []
            for item in hybrid_res.get('results', []):
                s_dict = dict(item.get('service', {}) or {})
                s_dict['hybrid_score'] = item.get('hybrid_score')
                s_dict['vector_score'] = item.get('vector_score')
                s_dict['lexical_score'] = item.get('lexical_score')
                s_dict['match_reasons'] = item.get('match_reasons')
                services_data.append(s_dict)

            return JsonResponse({
                'services': services_data,
                'total': len(services_data),
                'limit': limit,
                'offset': offset,
                'hybrid_search': True,
                'detected_assets': hybrid_res.get('detected_assets', []),
                'detected_symptoms': hybrid_res.get('detected_symptoms', []),
            }, status=200)
        except Exception:
            # En caso de excepción imprevista, continuar con fallback léxico SQL
            pass

    query = Service.objects.all()

    if search:
        query = query.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    if category and category.lower() not in ('todo', 'todos'):
        query = query.filter(category__icontains=category)

    total = query.count()
    services = list(query.order_by('id')[offset:offset + limit])

    return JsonResponse({
        'services': [service.to_dict() for service in services],
        'total': total,
        'limit': limit,
        'offset': offset,
        'hybrid_search': False,
    }, status=200)


def list_categories(request):
    """List distinct categories available in services."""
    cats = list(
        Service.objects.exclude(category__isnull=True)
        .exclude(category__exact='')
        .values_list('category', flat=True)
        .distinct()
    )
    if 'Todo' not in cats:
        cats.insert(0, 'Todo')
    return JsonResponse({'success': True, 'categories': cats}, status=200)


def get_service(request, service_id):
    """Get single service by ID."""
    service = Service.objects.filter(pk=service_id).first()
    if not service:
        return JsonResponse({'error': 'Service not found'}, status=404)
    return JsonResponse(service.to_dict(), status=200)
