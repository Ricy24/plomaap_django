"""
Hybrid Search Service for PlomApp - FASE 10.
Direct port of app/services/hybrid_search_service.py (Flask version).
Combines lexical understanding (synonyms, symptoms, assets), pgvector semantic
similarity and weighted RRF-style fusion with strict no-hallucination guarantee
(only real database entities are returned).
"""
import logging
import re
from typing import Any, Dict, List, Optional

from api.models import AssetTypeCatalog, Service
from api.services.embedding_service import search_similar_entities

logger = logging.getLogger(__name__)

# Sinónimos y variaciones para activos del catálogo
ASSET_SYNONYMS = {
    'sanitario': ['sanitario', 'sanitarios', 'inodoro', 'inodoros', 'wc', 'retrete', 'taza'],
    'calentador': ['calentador', 'calentadores', 'boiler', 'calefon', 'terma'],
    'ducha': ['ducha', 'duchas', 'regadera', 'regaderas', 'mampara', 'mamparas'],
    'lavamanos': ['lavamanos', 'lavabo', 'lavabos'],
    'lavadora': ['lavadora', 'lavadoras'],
    'iluminacion': ['iluminacion', 'lampara', 'lamparas', 'bombillo', 'bombillos', 'foco', 'focos'],
    'enchufe': ['enchufe', 'enchufes', 'tomacorriente', 'tomacorrientes', 'toma'],
    'aire_acondicionado': ['aire acondicionado', 'aire_acondicionado', 'clima', 'minisplit', 'split'],
}

# Mapeo de síntomas comunes hacia conceptos clave
SYMPTOM_MAP = {
    'fuga': ['fuga', 'fugas', 'gotera', 'goteras', 'filtracion', 'filtraciones', 'salidero', 'goteando', 'gotea', 'salida de agua'],
    'destape': ['destape', 'destapes', 'tapado', 'tapada', 'tapo', 'tapa', 'tapar', 'taparon', 'atasco', 'atascos', 'atascado', 'atascada', 'atascar', 'obstruido', 'obstruida', 'obstruccion', 'atorado', 'atorada', 'tapon'],
    'reparacion': ['roto', 'rota', 'rotos', 'rotas', 'quebrado', 'danado', 'danada', 'partido', 'descompuesto', 'averiado'],
    'instalacion': ['instalar', 'instalacion', 'instalaciones', 'instalarlo', 'instalarla', 'conectar', 'conexion', 'montaje', 'montar', 'colocar'],
    'mantenimiento': ['mantenimiento', 'revision', 'chequeo', 'inspeccion', 'limpieza'],
    'presion': ['presion', 'bomba', 'fuerza', 'caudal', 'poca agua', 'baja presion'],
}

# Afinidad directa síntoma -> Servicio ID
# ID 1: Fugas de agua / ID 2: Destapes / ID 3: Duchas y baños / ID 4: Instalaciones
SYMPTOM_SERVICE_AFFINITY = {
    'fuga': [1],
    'destape': [2],
    'instalacion': [4],
    'reparacion': [1, 3],
    'mantenimiento': [4, 1],
    'presion': [1],
}

# Mapeo de activos a servicios estándar de PlomApp
ASSET_SERVICE_AFFINITY = {
    'calentador': [4, 1],       # Instalaciones, Fugas
    'lavadora': [4, 1],         # Instalaciones, Fugas
    'ducha': [3, 1],            # Duchas y baños, Fugas
    'lavamanos': [3, 1],        # Duchas y baños, Fugas
    'sanitario': [2, 3],        # Destapes, Duchas y baños
    'iluminacion': [4],         # Instalaciones
    'enchufe': [4],             # Instalaciones
    'aire_acondicionado': [4],  # Instalaciones
}


def _normalize_text(text: str) -> str:
    """Elimina acentos y caracteres especiales para búsqueda léxica robusta."""
    t = str(text).lower().strip()
    replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n'}
    for orig, rep in replacements.items():
        t = t.replace(orig, rep)
    return re.sub(r'[^a-z0-9\s]', ' ', t)


def detect_assets_and_symptoms(query_text: str) -> Dict[str, Any]:
    """
    Detecta menciones explícitas de activos del catálogo y síntomas en la consulta,
    usando diccionarios de sinónimos ampliados.
    """
    norm_query = _normalize_text(query_text)
    tokens = set(norm_query.split())

    detected_assets = []
    active_assets = AssetTypeCatalog.objects.filter(is_active=True)

    for a in active_assets:
        code_norm = _normalize_text(a.code)
        name_norm = _normalize_text(a.name)
        synonyms = ASSET_SYNONYMS.get(a.code, [])

        matched = False
        if code_norm in norm_query or name_norm in norm_query:
            matched = True
        elif any(syn in norm_query for syn in synonyms):
            matched = True

        if matched:
            detected_assets.append({
                'id': a.id,
                'code': a.code,
                'name': a.name,
                'category': a.category,
            })

    detected_symptoms = []
    for symptom_key, terms in SYMPTOM_MAP.items():
        if symptom_key in tokens or any(term in norm_query for term in terms):
            detected_symptoms.append(symptom_key)

    return {
        'normalized_query': norm_query,
        'tokens': list(tokens),
        'detected_assets': detected_assets,
        'detected_symptoms': detected_symptoms,
    }


def compute_lexical_score(service: Service, analysis: Dict[str, Any]) -> float:
    """
    Calcula puntuación léxica normalizada (0.0 a 1.0) comparando tokens,
    categoría, nombre y descripción del servicio contra los síntomas y activos detectados.
    """
    s_name_norm = _normalize_text(service.name or '')
    s_desc_norm = _normalize_text(service.description or '')
    s_cat_norm = _normalize_text(service.category or '')
    service_full_text = f'{s_name_norm} {s_desc_norm} {s_cat_norm}'

    tokens = analysis['tokens']
    if not tokens:
        return 0.0

    score = 0.0

    # 1. Coincidencias de tokens individuales
    for tok in tokens:
        if len(tok) <= 2:
            continue
        if tok in s_name_norm:
            score += 0.35
        elif tok in s_desc_norm:
            score += 0.20
        elif tok in s_cat_norm:
            score += 0.25

    # 2. Afinidad directa de síntomas
    for symptom in analysis['detected_symptoms']:
        affinities = SYMPTOM_SERVICE_AFFINITY.get(symptom, [])
        if service.id in affinities:
            score += 0.45
        terms = SYMPTOM_MAP.get(symptom, [])
        if any(term in service_full_text for term in terms):
            score += 0.20

    # 3. Afinidad de activos detectados
    for asset in analysis['detected_assets']:
        affinities = ASSET_SERVICE_AFFINITY.get(asset['code'], [])
        if service.id in affinities:
            idx = affinities.index(service.id)
            score += 0.35 if idx == 0 else 0.20

    return min(round(score, 4), 1.0)


def perform_hybrid_search(query: str, category_filter: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
    """
    Ejecuta el pipeline de búsqueda híbrida:
      1. Análisis léxico de la consulta
      2. Búsqueda vectorial semántica con pgvector
      3. Ponderación híbrida equilibrada y combinación de candidatos
      4. Re-ranking y generación de explicaciones
    """
    clean_query = str(query).strip()
    if not clean_query:
        all_services = list(Service.objects.all())
        return {
            'query': '',
            'total_results': len(all_services),
            'detected_assets': [],
            'detected_symptoms': [],
            'results': [{
                'service_id': s.id,
                'name': s.name,
                'category': s.category,
                'base_price': float(s.base_price),
                'hybrid_score': 1.0,
                'vector_score': 0.0,
                'lexical_score': 0.0,
                'match_reasons': ['Listado predeterminado'],
                'service': s.to_dict(),
            } for s in all_services],
        }

    # 1. Análisis de lenguaje, sinónimos, activos y síntomas
    analysis = detect_assets_and_symptoms(clean_query)

    # 2. Búsqueda vectorial semántica (pgvector)
    vector_results = {}
    try:
        raw_vec_matches = search_similar_entities(
            query_text=clean_query,
            entity_type='service',
            top_k=10,
            min_similarity=0.0,
        )
        for rank, match in enumerate(raw_vec_matches, 1):
            s_id = match['entity_id']
            vector_results[s_id] = {
                'similarity': match['similarity'],
                'rank': rank,
            }
    except Exception as e:
        logger.warning('Error en consulta vectorial (fallback a léxico): %s', e)

    # 3. Evaluación de todos los servicios reales disponibles
    all_services = list(Service.objects.all())
    if category_filter and category_filter.lower() not in ['todo', 'todos', '']:
        all_services = [
            s for s in all_services
            if (s.category or '').lower() == category_filter.lower()
        ]

    candidates = []

    # Pesos de fusión híbrida
    w_vec = 0.50
    w_lex = 0.35
    w_direct_boost = 0.15

    for s in all_services:
        vec_info = vector_results.get(s.id, {'similarity': 0.0, 'rank': 99})
        s_vec = vec_info['similarity']
        s_lex = compute_lexical_score(s, analysis)

        # Boost si hay activo o síntoma directamente emparejado
        direct_boost = 0.0
        matched_asset_names = []
        for asset in analysis['detected_assets']:
            affinities = ASSET_SERVICE_AFFINITY.get(asset['code'], [])
            if s.id in affinities:
                matched_asset_names.append(asset['name'])
                if affinities.index(s.id) == 0:
                    direct_boost = max(direct_boost, w_direct_boost)

        for sym in analysis['detected_symptoms']:
            affinities = SYMPTOM_SERVICE_AFFINITY.get(sym, [])
            if s.id in affinities:
                direct_boost = max(direct_boost, w_direct_boost)

        hybrid_score = (w_vec * s_vec) + (w_lex * s_lex) + direct_boost

        reasons = []
        if s_vec >= 0.50:
            reasons.append(f'Alta coincidencia semántica ({int(s_vec * 100)}%)')
        elif s_vec >= 0.25:
            reasons.append(f'Coincidencia contextual ({int(s_vec * 100)}%)')

        if matched_asset_names:
            reasons.append(f"Afinidad con equipo: {', '.join(matched_asset_names)}")

        if analysis['detected_symptoms']:
            matched_symps = [
                sym for sym in analysis['detected_symptoms']
                if s.id in SYMPTOM_SERVICE_AFFINITY.get(sym, [])
            ]
            if matched_symps:
                reasons.append(f"Síntoma clave: {', '.join(matched_symps)}")

        if not reasons:
            reasons.append('Sugerencia por especialidad')

        candidates.append({
            'service_id': s.id,
            'name': s.name,
            'category': s.category,
            'base_price': float(s.base_price),
            'duration_minutes': s.duration_minutes,
            'icon': s.icon,
            'color': s.color,
            'description': s.description,
            'hybrid_score': round(float(hybrid_score), 4),
            'vector_score': round(float(s_vec), 4),
            'lexical_score': round(float(s_lex), 4),
            'match_reasons': reasons,
            'service': s.to_dict(),
        })

    # 4. Ordenar candidatos por hybrid_score descendente
    candidates.sort(key=lambda x: x['hybrid_score'], reverse=True)
    top_candidates = candidates[:top_k]

    return {
        'query': clean_query,
        'total_results': len(top_candidates),
        'detected_assets': [a['name'] for a in analysis['detected_assets']],
        'detected_symptoms': analysis['detected_symptoms'],
        'results': top_candidates,
    }
