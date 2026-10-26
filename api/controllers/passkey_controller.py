"""
Passkey (WebAuthn) controller - direct port of app/controllers/passkey_controller.py.
Requires the `webauthn` package (py-webauthn), same as the Flask version.
"""
import base64
import json
from datetime import datetime, timedelta

from django.http import HttpResponse, JsonResponse

from api.models import User, WebAuthnCredential, utcnow
from api.utils.jwt_utils import generate_token

import webauthn
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

# In-memory challenge store: { challenge_str: { 'user_id': id, 'created_at': datetime } }
CHALLENGES = {}

RP_ID = None
RP_NAME = 'PlomApp'
ORIGIN = None


def _settings():
    from django.conf import settings
    return settings


def _rp_id():
    return _settings().WEBAUTHN_RP_ID


def _rp_name():
    return _settings().WEBAUTHN_RP_NAME


def _origin():
    return _settings().WEBAUTHN_ORIGIN


def _parse_json(request):
    from api.controllers.auth_controller import parse_json
    return parse_json(request)


def _clean_expired_challenges():
    now = datetime.utcnow()
    expired = [k for k, v in CHALLENGES.items() if now - v['created_at'] > timedelta(minutes=5)]
    for k in expired:
        CHALLENGES.pop(k, None)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _b64url_decode(value: str) -> bytes:
    """Decode base64url (tolerating missing padding)."""
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def _challenge_key(challenge) -> str:
    """Normalize a registration/authentication challenge to the base64url string
    the browser echoes back inside clientDataJSON.challenge."""
    if isinstance(challenge, (bytes, bytearray)):
        return bytes_to_base64url(bytes(challenge))
    return str(challenge)


def _find_credential(credential_id: str):
    """Find a stored credential matching the raw ID or its b64url-normalized form."""
    cred = WebAuthnCredential.objects.filter(credential_id=credential_id).first()
    if cred:
        return cred
    try:
        normalized = _b64url(_b64url_decode(credential_id))
        return WebAuthnCredential.objects.filter(credential_id=normalized).first()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def passkey_register_options(request, user_id):
    """POST /api/auth/passkey/register/options"""
    _clean_expired_challenges()
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name=_rp_name(),
        user_id=str(user.id).encode('utf-8'),  # webauthn>=2 exige bytes
        user_name=user.email,
        user_display_name=user.name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=[
            webauthn.helpers.structs.PublicKeyCredentialDescriptor(
                id=webauthn.helpers.base64url_to_bytes(cred.credential_id),
            )
            for cred in WebAuthnCredential.objects.filter(user_id=user.id)
        ],
    )

    CHALLENGES[_challenge_key(options.challenge)] = {
        'user_id': user.id,
        'created_at': datetime.utcnow(),
    }

    return HttpResponse(options_to_json(options), content_type='application/json')


def passkey_register_verify(request, user_id):
    """POST /api/auth/passkey/register/verify"""
    data = _parse_json(request)
    body = data.get('credential') or data

    credential_id = body.get('id') or body.get('rawId')
    client_data_json = body.get('response', {}).get('clientDataJSON')
    attestation_object = body.get('response', {}).get('attestationObject')

    if not credential_id or not client_data_json or not attestation_object:
        return JsonResponse({'success': False, 'message': 'Payload de passkey incompleto'}, status=400)

    client_data_bytes = base64.urlsafe_b64decode(client_data_json + '=' * (-len(client_data_json) % 4))
    try:
        parsed_client = json.loads(client_data_bytes.decode('utf-8'))
    except Exception:
        parsed_client = {}
    challenge = parsed_client.get('challenge', '')

    stored = CHALLENGES.pop(challenge, None)
    if not stored:
        return JsonResponse({'success': False, 'message': 'Challenge inválido o expirado'}, status=400)

    try:
        verification = verify_registration_response(
            response={
                'id': credential_id,
                'rawId': credential_id,
                'type': 'public-key',
                'response': {
                    'clientDataJSON': client_data_json,
                    'attestationObject': attestation_object,
                    'transports': body.get('response', {}).get('transports', []),
                },
            },
            expected_challenge=_b64url_decode(challenge) if challenge else b'',
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
        )
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Verificación fallida: {e}'}, status=400)

    WebAuthnCredential.objects.update_or_create(
        credential_id=_b64url(verification.credential_id),
        defaults={
            'user_id': stored['user_id'],
            'public_key': _b64url(verification.credential_public_key),
            'sign_count': verification.new_sign_count,
            'transports': body.get('response', {}).get('transports', []),
        },
    )

    return JsonResponse({'success': True, 'message': 'Passkey registrada correctamente'}, status=201)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def passkey_login_options(request):
    """POST /api/auth/passkey/login/options"""
    _clean_expired_challenges()
    options = generate_authentication_options(
        rp_id=_rp_id(),
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    CHALLENGES[_challenge_key(options.challenge)] = {
        'user_id': None,
        'created_at': datetime.utcnow(),
    }
    return HttpResponse(options_to_json(options), content_type='application/json')


def passkey_login_verify(request):
    """POST /api/auth/passkey/login/verify"""
    data = _parse_json(request)
    body = data.get('credential') or data

    credential_id = body.get('id') or body.get('rawId')
    client_data_json = body.get('response', {}).get('clientDataJSON')
    authenticator_data = body.get('response', {}).get('authenticatorData')
    signature = body.get('response', {}).get('signature')

    if not credential_id or not client_data_json or not authenticator_data or not signature:
        return JsonResponse({'success': False, 'message': 'Payload de passkey incompleto'}, status=400)

    client_data_bytes = base64.urlsafe_b64decode(client_data_json + '=' * (-len(client_data_json) % 4))
    try:
        parsed_client = json.loads(client_data_bytes.decode('utf-8'))
    except Exception:
        parsed_client = {}
    challenge = parsed_client.get('challenge', '')

    stored = CHALLENGES.pop(challenge, None)
    if not stored:
        return JsonResponse({'success': False, 'message': 'Challenge inválido o expirado'}, status=400)

    cred = _find_credential(credential_id)

    if not cred:
        return JsonResponse({'success': False, 'message': 'Passkey no registrada'}, status=401)

    try:
        verification = verify_authentication_response(
            credential={
                'id': credential_id,
                'rawId': credential_id,
                'type': 'public-key',
                'response': {
                    'clientDataJSON': client_data_json,
                    'authenticatorData': authenticator_data,
                    'signature': signature,
                },
            },
            expected_challenge=_b64url_decode(challenge) if challenge else b'',
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
            credential_public_key=base64.urlsafe_b64decode(
                cred.public_key + '=' * (-len(cred.public_key) % 4)
            ),
            credential_current_sign_count=cred.sign_count,
        )
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Verificación fallida: {e}'}, status=401)

    cred.sign_count = verification.new_sign_count
    cred.save()

    user = User.objects.filter(pk=cred.user_id).first()
    if not user or user.status != 'active':
        return JsonResponse({'success': False, 'message': 'Cuenta inactiva'}, status=401)

    token = generate_token(user.id)
    user_dict = user.to_dict()
    if user.role == 'technician' and user.technician_profile:
        user_dict['technicianProfile'] = user.technician_profile.to_dict()

    return JsonResponse({
        'success': True,
        'message': 'Inicio de sesión con passkey correcto',
        'token': token,
        'user': user_dict,
    }, status=200)
