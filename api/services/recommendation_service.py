"""
Recommendation Service for PlomApp - FASE 12.
Direct port of app/services/recommendation_service.py (Flask version).

NOTE: The Flask version contained raw SQL referencing columns that don't exist
(`ha.asset_type = ac.id` and `h.is_active`), which always fell back to the
generic list. This port keeps the same API contract but fixes the queries so
the feature actually works (assets resolved by code, homes by ownership or
membership), while preserving the fallback behavior on error.
"""
import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Count, Q

from api.models import (
    AppEvent,
    Appointment,
    AssetTypeCatalog,
    Home,
    HomeAsset,
    HomeMember,
    RecommendationEvent,
    Service,
    utcnow,
)

logger = logging.getLogger(__name__)

RECOMMENDATION_WEIGHTS = {
    'asset_match': 0.35,
    'preference_match': 0.25,
    'history_match': 0.15,
    'popularity': 0.05,
    'repetition_penalty': 0.20,
}


def _user_asset_codes(user_id):
    """Codes of asset types the user has in their Digital Home(s)."""
    homes = Home.objects.filter(
        Q(owner_id=user_id) | Q(members__user_id=user_id)
    ).distinct()
    asset_ids = HomeAsset.objects.filter(home__in=homes).values_list('asset_type', flat=True)
    if not asset_ids:
        return []
    codes = set(
        AssetTypeCatalog.objects.filter(code__in=asset_ids).values_list('code', flat=True)
    )
    # Also include raw codes not present in the catalog
    codes.update(set(asset_ids))
    return list(codes)


def _popularity_map():
    rows = (
        AppEvent.objects.filter(
            event_type__in=['SERVICE_BOOKED', 'BOOKING_CREATED'],
            entity_type='service',
        )
        .values('entity_id')
        .annotate(cnt=Count('id'))
    )
    return {r['entity_id']: r['cnt'] for r in rows}


def generate_recommendations(user_id=None, limit=5):
    try:
        services = list(Service.objects.all())

        user_assets = []
        user_events = []
        user_appointments = []

        if user_id:
            user_assets = _user_asset_codes(user_id)

            user_events = list(
                AppEvent.objects.filter(user_id=user_id)
                .order_by('-created_at')[:20]
            )

            user_appointments = list(
                Appointment.objects.filter(user_id=user_id)
                .order_by('-created_at')[:10]
            )

        pop_map = _popularity_map()
        max_pop = max(pop_map.values()) if pop_map else 1

        candidates = []
        for svc in services:
            score = 0.0
            factors = {}
            reasons = []

            s_pop = pop_map.get(svc.id, 0) / max_pop
            score += RECOMMENDATION_WEIGHTS['popularity'] * s_pop
            factors['popularity'] = round(s_pop, 4)

            if user_id:
                s_asset = 0.0
                if svc.id == 1:
                    if any(a in ['ducha', 'lavamanos', 'sanitario', 'calentador', 'lavadora'] for a in user_assets):
                        s_asset = 1.0
                        reasons.append('Recomendado porque tienes equipos de plomería en tu Hogar Digital.')
                elif svc.id == 2:
                    if any(a in ['sanitario', 'lavamanos', 'ducha'] for a in user_assets):
                        s_asset = 1.0
                        reasons.append('Servicio esencial para el mantenimiento preventivo de tus baños.')
                elif svc.id == 3:
                    if any(a in ['ducha', 'sanitario', 'lavamanos'] for a in user_assets):
                        s_asset = 1.0
                        reasons.append('Ideal para el cuidado de los baños registrados en tu hogar.')
                elif svc.id == 4:
                    if any(a in ['calentador', 'lavadora', 'aire_acondicionado'] for a in user_assets):
                        s_asset = 1.0
                        reasons.append('Recomendado por los electrodomésticos y equipos de gas en tu hogar.')

                score += RECOMMENDATION_WEIGHTS['asset_match'] * s_asset
                factors['asset_match'] = round(s_asset, 4)

                s_hist = 0.0
                views = sum(
                    1 for e in user_events
                    if e.event_type in ('SERVICE_VIEWED', 'SERVICE_CLICKED') and e.entity_id == svc.id
                )
                if views > 0:
                    s_hist = min(views / 5.0, 1.0)
                    reasons.append('Basado en tus búsquedas e intereses recientes.')

                score += RECOMMENDATION_WEIGHTS['history_match'] * s_hist
                factors['history_match'] = round(s_hist, 4)

                penalty = 0.0
                cutoff = datetime.utcnow() - timedelta(days=30)
                recent_booking = next(
                    (
                        a for a in user_appointments
                        if a.service_id == svc.id and a.created_at and a.created_at > cutoff
                    ),
                    None,
                )
                if recent_booking:
                    penalty = 1.0
                    reasons.append('Agendaste este servicio recientemente.')

                score -= RECOMMENDATION_WEIGHTS['repetition_penalty'] * penalty
                factors['repetition_penalty'] = round(penalty, 4)

            if not reasons:
                reasons.append('Servicio destacado y altamente calificado por la comunidad.')

            candidates.append({
                'service': svc,
                'score': round(score, 4),
                'factors': factors,
                'reason': reasons[0] if reasons else '',
            })

        candidates.sort(key=lambda x: x['score'], reverse=True)
        final_recommendations = candidates[:limit]

        result_items = []
        rec_ids = []

        with transaction.atomic():
            for idx, rec in enumerate(final_recommendations):
                svc = rec['service']

                rec_id = None
                if user_id:
                    rec_event = RecommendationEvent(
                        user_id=user_id,
                        recommendation_type='service',
                        entity_id=svc.id,
                        score=rec['score'],
                        algorithm_version='recommendation_v1',
                        position=idx + 1,
                        shown_at=utcnow(),
                        metadata={'reason': rec['reason'], 'factors': rec['factors']},
                    )
                    rec_event.save()
                    rec_id = rec_event.id
                    rec_ids.append(rec_id)

                item = svc.to_dict()
                item['recommendation_id'] = rec_id
                item['recommendation_score'] = rec['score']
                item['recommendation_reason'] = rec['reason']
                result_items.append(item)

        return result_items

    except Exception as e:
        logger.error('Error generating recommendations: %s', e, exc_info=True)
        services = list(Service.objects.all()[:limit])
        return [{
            **svc.to_dict(),
            'recommendation_id': None,
            'recommendation_score': 0.0,
            'recommendation_reason': 'Recomendación general.',
        } for svc in services]


def track_recommendation_click(rec_id, user_id):
    try:
        rec = RecommendationEvent.objects.filter(id=rec_id, user_id=user_id).first()
        if rec and not rec.clicked_at:
            rec.clicked_at = utcnow()
            rec.save()

            AppEvent.objects.create(
                user_id=user_id,
                event_type='SERVICE_CLICKED',
                entity_type='service',
                entity_id=rec.entity_id,
                metadata={'recommendation_id': rec_id, 'source': 'ai_recommendation'},
                created_at=utcnow(),
            )
            return True
        return False
    except Exception as e:
        logger.error('Error tracking click: %s', e)
        return False


def track_recommendation_conversion(rec_id, user_id):
    try:
        rec = RecommendationEvent.objects.filter(id=rec_id, user_id=user_id).first()
        if rec and not rec.converted_at:
            rec.converted_at = utcnow()
            rec.save()
            return True
        return False
    except Exception as e:
        logger.error('Error tracking conversion: %s', e)
        return False
