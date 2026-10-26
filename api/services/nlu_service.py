"""
NLU (Natural Language Understanding) Service for PlomApp - FASE 11.
Direct port of app/services/nlu_service.py (Flask version).

Characteristics:
1. Structured extraction: Intent, Category, Asset, Symptom, Urgency, Confidence.
2. Gemini API inference (gemini-3.6-flash / gemini-3.5-flash-lite) with strict JSON.
3. Deterministic Local Fallback: 100% uptime guarantee on network/quota failures.
4. Zero Hallucinations: maps directly to real IDs from services/asset_type_catalog.
5. Transparency and pre-filled booking action.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from api.models import AssetTypeCatalog, Service
from api.services.event_service import track_event

logger = logging.getLogger(__name__)

# Catálogo canónico de intenciones
VALID_INTENTS = ["repair", "installation", "maintenance", "unblock", "emergency", "inspection", "inquiry"]

# Catálogo canónico de urgencias
VALID_URGENCIES = ["low", "medium", "high", "emergency"]

# Catálogo canónico de problemas
VALID_ISSUES = [
    "water_leak", "blockage", "gas_smell", "faulty_installation",
    "electrical_issue", "low_pressure", "noise", "broken_fixture", "routine_check",
]

# Diccionario local de contingencia (Fallback NLU)
KEYWORD_INTENT_MAP = {
    "fuga": ("repair", "water_leak", "medium", 1),
    "gotera": ("repair", "water_leak", "medium", 1),
    "gotea": ("repair", "water_leak", "medium", 1),
    "salidero": ("repair", "water_leak", "medium", 1),
    "filtracion": ("repair", "water_leak", "medium", 1),
    "saliendo agua": ("repair", "water_leak", "medium", 1),
    "tubo roto": ("emergency", "water_leak", "emergency", 1),
    "inundacion": ("emergency", "water_leak", "emergency", 1),
    "inundando": ("emergency", "water_leak", "emergency", 1),
    "tapado": ("unblock", "blockage", "high", 2),
    "tapo": ("unblock", "blockage", "high", 2),
    "atasco": ("unblock", "blockage", "high", 2),
    "atascado": ("unblock", "blockage", "high", 2),
    "rebosa": ("emergency", "blockage", "emergency", 2),
    "rebosando": ("emergency", "blockage", "emergency", 2),
    "desborda": ("emergency", "blockage", "emergency", 2),
    "no baja": ("unblock", "blockage", "medium", 2),
    "calentador": ("repair", "faulty_installation", "medium", 4),
    "gas": ("emergency", "gas_smell", "emergency", 4),
    "olor a gas": ("emergency", "gas_smell", "emergency", 4),
    "huele a gas": ("emergency", "gas_smell", "emergency", 4),
    "instalar": ("installation", "faulty_installation", "low", 4),
    "instalacion": ("installation", "faulty_installation", "low", 4),
    "montar": ("installation", "faulty_installation", "low", 4),
    "conectar": ("installation", "faulty_installation", "low", 4),
    "ducha": ("repair", "broken_fixture", "medium", 3),
    "regadera": ("repair", "broken_fixture", "medium", 3),
    "grifo": ("repair", "water_leak", "medium", 1),
    "mantenimiento": ("maintenance", "routine_check", "low", 4),
    "revision": ("inspection", "routine_check", "low", 4),
    "presion": ("repair", "low_pressure", "medium", 1),
}


def _get_gemini_api_key() -> Optional[str]:
    """Obtiene la clave de API de Gemini desde settings/.env."""
    k = settings.GEMINI_API_KEY or os.environ.get('GEMINI_API_KEY')
    if k:
        return k
    try:
        from dotenv import load_dotenv
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        load_dotenv(os.path.join(base_dir, '.env'))
        return os.environ.get('GEMINI_API_KEY')
    except Exception:
        return None


def _call_gemini_nlu(
    text: str,
    services_context: List[Dict[str, Any]],
    assets_context: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Ejecuta el análisis de lenguaje natural mediante Gemini API.
    Prueba primero gemini-3.6-flash y luego gemini-3.5-flash-lite con timeout optimizado.
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        logger.warning('GEMINI_API_KEY no configurada. Utilizando fallback local determinista.')
        return None

    candidate_models = ['gemini-3.6-flash', 'gemini-3.5-flash-lite']

    services_desc = '\n'.join(
        [f"- ID {s['id']}: {s['name']} (Cat: {s['category']}) - {s['description']}" for s in services_context]
    )
    assets_desc = '\n'.join(
        [f"- ID {a['id']} [code: {a['code']}]: {a['name']}" for a in assets_context]
    )

    system_instruction = (
        "Eres el motor NLU especializado de PlomApp, una plataforma de plomería y mantenimiento del hogar.\n"
        "Tu tarea es analizar el texto del usuario y extraer con precisión la intención, los activos involucrados, la urgencia y recomendar el servicio real más adecuado.\n\n"
        f"SERVICIOS DISPONIBLES EN BASE DE DATOS (Usa SOLO estos IDs):\n{services_desc}\n\n"
        f"ACTIVOS DISPONIBLES EN BASE DE DATOS (Usa SOLO estos códigos/IDs):\n{assets_desc}\n\n"
        "REGLAS ESTRICTAS:\n"
        "1. NO inventes IDs ni servicios. La fuente de verdad es la lista provista.\n"
        "2. recommended_service_ids debe contener los IDs numéricos exactos de los servicios que resuelven el problema.\n"
        "3. Si el usuario menciona riesgo de inundación, fuga masiva, rebose o gas, la urgencia DEBE ser 'emergency' o 'high'.\n"
        "4. asset_id debe ser el ID del activo detectado o null si no aplica.\n"
        "5. Devuelve EXCLUSIVAMENTE el objeto JSON conforme al esquema solicitado. Sin markdown, sin bloques de código, solo el JSON puro."
    )

    clean_q = text.replace('"', '\\"')
    prompt = (
        'Analiza la siguiente solicitud del usuario:\n"' + clean_q + '"\n\n'
        "Responde en JSON con esta estructura exacta:\n"
        "{\n"
        '  "intent": "repair | installation | maintenance | unblock | emergency | inspection | inquiry",\n'
        '  "category": "plumbing | gas | electricity",\n'
        '  "asset_code": "código_del_activo_o_null",\n'
        '  "asset_id": 4,\n'
        '  "issue": "water_leak | blockage | gas_smell | faulty_installation | electrical_issue | low_pressure | noise | broken_fixture | routine_check",\n'
        '  "urgency": "low | medium | high | emergency",\n'
        '  "confidence": 0.95,\n'
        '  "symptoms": ["síntoma_1", "síntoma_2"],\n'
        '  "recommended_service_ids": [1],\n'
        '  "reasoning": "Explicación clara y concisa en español",\n'
        '  "suggested_action": {\n'
        '    "action_type": "book_service",\n'
        '    "target_service_id": 1,\n'
        '    "prefill_notes": "Resumen técnico para la reserva"\n'
        '  }\n'
        "}"
    )

    payload = {
        'contents': [
            {'parts': [{'text': system_instruction + '\n\n' + prompt}]},
        ],
        'generationConfig': {
            'temperature': 0.1,
            'responseMimeType': 'application/json',
        },
    }

    for model_name in candidate_models:
        url = (
            'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{model_name}:generateContent?key={api_key}'
        )
        try:
            resp = requests.post(url, json=payload, timeout=18)
            if resp.status_code == 200:
                candidates = resp.json().get('candidates', [])
                if candidates:
                    raw_json = candidates[0]['content']['parts'][0]['text'].strip()
                    if raw_json.startswith('```json'):
                        raw_json = raw_json[7:]
                    if raw_json.endswith('```'):
                        raw_json = raw_json[:-3]
                    parsed = json.loads(raw_json.strip())
                    parsed['_model_used'] = model_name
                    return parsed
            else:
                logger.warning('Gemini model %s error %s: %s', model_name, resp.status_code, resp.text[:150])
        except Exception as e:
            logger.warning('Excepción llamando a Gemini %s: %s', model_name, e)

    return None


def _fallback_local_nlu(
    text: str,
    services_context: List[Dict[str, Any]],
    assets_context: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Motor determinista local de reglas y expresiones regulares.
    Se activa si Gemini no está disponible, garantizando 100% de disponibilidad sin errores 500.
    """
    t_clean = text.lower()
    t_norm = re.sub(r'[^a-z0-9\s]', ' ', t_clean)

    detected_intent = 'repair'
    detected_issue = 'water_leak'
    detected_urgency = 'medium'
    detected_asset_id = None
    detected_asset_code = None
    target_service_id = 1
    confidence = 0.88
    detected_symptoms = []

    # 1. Detección de activos del catálogo
    for asset in assets_context:
        code = asset['code'].lower()
        name = asset['name'].lower()
        if code in t_norm or any(part in t_norm for part in code.split('_')) or name in t_norm:
            detected_asset_id = asset['id']
            detected_asset_code = asset['code']
            break

    # Sinónimos manuales comunes
    if not detected_asset_code:
        if any(w in t_norm for w in ['inodoro', 'wc', 'retrete', 'taza']):
            for a in assets_context:
                if a['code'] == 'sanitario':
                    detected_asset_id = a['id']
                    detected_asset_code = 'sanitario'
                    break
        elif any(w in t_norm for w in ['boiler', 'calefon', 'terma']):
            for a in assets_context:
                if a['code'] == 'calentador':
                    detected_asset_id = a['id']
                    detected_asset_code = 'calentador'
                    break

    # 2. Detección de síntomas, urgencia e intención
    for kw, (intent_val, issue_val, urgency_val, s_id) in KEYWORD_INTENT_MAP.items():
        if kw in t_norm or kw in t_clean:
            detected_intent = intent_val
            detected_issue = issue_val
            detected_urgency = urgency_val
            target_service_id = s_id
            detected_symptoms.append(kw)

    # Revisar agravantes de urgencia
    if any(w in t_norm for w in [
        'urgente', 'emergencia', 'ya', 'inundando', 'inundacion', 'auxilio',
        'rebosa', 'rebosando', 'olor a gas', 'huele a gas',
    ]):
        detected_urgency = 'emergency'
        detected_intent = 'emergency'
        confidence = 0.95

    # Afinidades según activo detectado
    if detected_asset_code == 'sanitario' and target_service_id == 1:
        target_service_id = 2  # Destapes

    if detected_asset_code == 'calentador' and detected_intent == 'installation':
        target_service_id = 4  # Instalaciones

    return {
        'intent': detected_intent,
        'category': 'plumbing',
        'asset_code': detected_asset_code,
        'asset_id': detected_asset_id,
        'issue': detected_issue,
        'urgency': detected_urgency,
        'confidence': confidence,
        'symptoms': list(set(detected_symptoms)),
        'recommended_service_ids': [target_service_id],
        'reasoning': (
            f"Diagnóstico inteligente: detectado problema '{detected_issue}' "
            f"con urgencia '{detected_urgency}'"
        ),
        'suggested_action': {
            'action_type': 'book_service',
            'target_service_id': target_service_id,
            'prefill_notes': f'Solicitud asistida: {text.strip()}',
        },
    }


def understand_text(text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Punto de entrada principal para NLU.
    1. Carga contexto canónico de servicios y catálogo de activos.
    2. Ejecuta Gemini API con prompt estructurado.
    3. Si Gemini no responde a tiempo, ejecuta el motor local de reglas deterministas.
    4. Valida y enriquece la respuesta con objetos completos de la base de datos.
    5. Registra el evento en app_events para el motor de recomendaciones.
    """
    clean_text = str(text or '').strip()
    if not clean_text:
        return {
            'success': False,
            'error': 'El texto a analizar no puede estar vacío',
        }

    # 1. Obtener contexto canónico real de la base de datos
    all_services = list(Service.objects.all())
    services_context = [{
        'id': s.id,
        'name': s.name,
        'category': s.category,
        'description': s.description,
        'base_price': float(s.base_price),
    } for s in all_services]
    service_map = {s['id']: s for s in services_context}

    all_assets = list(AssetTypeCatalog.objects.filter(is_active=True))
    assets_context = [{
        'id': a.id,
        'code': a.code,
        'name': a.name,
        'category': a.category,
    } for a in all_assets]
    asset_id_map = {a['id']: a for a in assets_context}
    asset_code_map = {a['code']: a for a in assets_context}

    # 2. Intento con Gemini NLU
    nlu_data = _call_gemini_nlu(clean_text, services_context, assets_context)
    provider_used = 'local-deterministic-rules'

    if nlu_data and isinstance(nlu_data, dict) and 'intent' in nlu_data:
        provider_used = nlu_data.get('_model_used', 'gemini-api')
    else:
        # 3. Fallback si Gemini no respondió o devolvió datos incompletos
        nlu_data = _fallback_local_nlu(clean_text, services_context, assets_context)
        provider_used = 'local-deterministic-rules'

    # 4. Normalización y validación estricta contra base de datos
    intent = nlu_data.get('intent', 'repair')
    if intent not in VALID_INTENTS:
        intent = 'repair'

    urgency = nlu_data.get('urgency', 'medium')
    if urgency not in VALID_URGENCIES:
        urgency = 'medium'

    # Validar asset_id y asset_code contra catálogo real
    asset_id = nlu_data.get('asset_id')
    asset_code = nlu_data.get('asset_code')

    resolved_asset = None
    if asset_id and asset_id in asset_id_map:
        resolved_asset = asset_id_map[asset_id]
    elif asset_code and asset_code in asset_code_map:
        resolved_asset = asset_code_map[asset_code]

    if resolved_asset:
        asset_id = resolved_asset['id']
        asset_code = resolved_asset['code']
        asset_name = resolved_asset['name']
    else:
        asset_id = None
        asset_code = None
        asset_name = None

    # Validar recommended_service_ids contra tabla services real
    raw_rec_ids = nlu_data.get('recommended_service_ids', [])
    if isinstance(raw_rec_ids, int):
        raw_rec_ids = [raw_rec_ids]
    elif not isinstance(raw_rec_ids, list):
        raw_rec_ids = []

    valid_service_ids = [
        sid for sid in raw_rec_ids
        if isinstance(sid, int) and sid in service_map
    ]
    if not valid_service_ids and services_context:
        valid_service_ids = [1]

    recommended_services = []
    for sid in valid_service_ids:
        s_info = service_map[sid]
        recommended_services.append({
            'id': s_info['id'],
            'name': s_info['name'],
            'category': s_info['category'],
            'base_price': s_info['base_price'],
            'reason': nlu_data.get(
                'reasoning',
                f"Servicio especializado para atender la incidencia en {s_info['category']}",
            ),
        })

    primary_service_id = valid_service_ids[0] if valid_service_ids else 1
    suggested_action = nlu_data.get('suggested_action') or {}
    prefill_notes = suggested_action.get('prefill_notes') or f'Diagnóstico PlomApp: {clean_text}'
    if asset_name and asset_name not in prefill_notes:
        prefill_notes += f' | Activo: {asset_name}'
    if urgency not in prefill_notes:
        prefill_notes += f' | Urgencia: {urgency}'

    final_action = {
        'action_type': 'book_service',
        'target_service_id': primary_service_id,
        'prefill_notes': prefill_notes,
        'urgency_level': urgency,
    }

    # 5. Registrar evento en app_events
    try:
        track_event(
            user_id=user_id,
            event_type='NLU_QUERY_PROCESSED',
            entity_type='service',
            entity_id=primary_service_id,
            metadata={
                'query': clean_text,
                'provider': provider_used,
                'intent': intent,
                'urgency': urgency,
                'asset_code': asset_code,
                'recommended_ids': valid_service_ids,
            },
        )
    except Exception as e:
        logger.debug('No se pudo registrar app_event para NLU: %s', e)

    return {
        'success': True,
        'original_text': clean_text,
        'provider': provider_used,
        'intent': intent,
        'category': nlu_data.get('category', 'plumbing'),
        'asset': asset_code,
        'asset_id': asset_id,
        'asset_name': asset_name,
        'issue': nlu_data.get('issue', 'water_leak'),
        'urgency': urgency,
        'confidence': float(nlu_data.get('confidence', 0.90)),
        'symptoms': nlu_data.get('symptoms', []),
        'entities': [
            {'type': 'asset', 'value': asset_name or asset_code, 'entity_id': asset_id} if asset_id else None,
            {'type': 'urgency', 'value': urgency},
            {'type': 'issue', 'value': nlu_data.get('issue', 'water_leak')},
        ],
        'recommended_service_ids': valid_service_ids,
        'recommended_services': recommended_services,
        'suggested_action': final_action,
    }
