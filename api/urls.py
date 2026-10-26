"""
API URL routing - exact replica of every Flask blueprint route (paths AND methods).

Flask blueprints mounted:
  /api/auth/*            auth_bp
  /api/services*         services_bp
  /api/technicians/*     technicians_bp
  /api/appointments/*    appointments_bp
  /api/admin/*           admin_bp
  /api/health            health_bp
  /api/user/addresses*   addresses_bp
  /api/user/favorites*   favorites_bp
  /api/events            events_bp
  /api/homes/*           homes_bp
  /api/onboarding/*      onboarding_bp
  /api/embeddings/*      embeddings_bp
  /api/search/*          search_bp
  /api/intelligence/*    intelligence_bp
  /api/recommendations*  recommendations_bp
  /api/upload/*          upload_bp

Every entry uses methods(...) so HTTP-method routing matches Flask exactly
(unsupported methods return 405 JSON instead of Django's HTML page).
"""
from django.urls import path

from api.utils.dispatch import methods
from api.views import (
    address_views,
    admin_views,
    appointment_views,
    auth_views,
    embedding_views,
    event_views,
    favorite_views,
    health_views,
    home_views,
    intelligence_views,
    onboarding_views,
    recommendation_views,
    search_views,
    service_views,
    technician_views,
    upload_views,
)

urlpatterns = [
    # ------------------------------------------------------------------
    # health_bp: /api/health
    # ------------------------------------------------------------------
    path('health', methods(GET=health_views.health_check)),

    # ------------------------------------------------------------------
    # auth_bp: /api/auth
    # ------------------------------------------------------------------
    path('auth/google-login', methods(POST=auth_views.google_login)),
    path('auth/login', methods(POST=auth_views.login_route)),
    path('auth/register', methods(POST=auth_views.register_route)),
    path('auth/profile', methods(GET=auth_views.profile_get, PATCH=auth_views.profile_update)),
    path('auth/logout', methods(POST=auth_views.logout)),
    path('auth/forgot-password', methods(POST=auth_views.forgot_password_route)),
    path('auth/reset-password', methods(POST=auth_views.reset_password_route)),
    path('auth/refresh', methods(POST=auth_views.refresh_token_route)),
    path('auth/passkey/register/options', methods(POST=auth_views.passkey_reg_options_route)),
    path('auth/passkey/register/verify', methods(POST=auth_views.passkey_reg_verify_route)),
    path('auth/passkey/login/options', methods(POST=auth_views.passkey_auth_options_route)),
    path('auth/passkey/login/verify', methods(POST=auth_views.passkey_auth_verify_route)),
    path('auth/verify-email', methods(GET=auth_views.verify_email_route, POST=auth_views.verify_email_route)),
    path('auth/resend-verification', methods(POST=auth_views.resend_verification_route)),

    # ------------------------------------------------------------------
    # services_bp: /api/services
    # ------------------------------------------------------------------
    path('services', methods(GET=service_views.list_services)),
    path('services/', methods(GET=service_views.list_services)),
    path('services/categories', methods(GET=service_views.list_categories)),
    path('services/<int:service_id>', methods(GET=service_views.get_service)),

    # ------------------------------------------------------------------
    # technicians_bp: /api/technicians
    # ------------------------------------------------------------------
    path('technicians', methods(GET=technician_views.list_technicians)),
    path('technicians/', methods(GET=technician_views.list_technicians)),
    path('technicians/available', methods(GET=technician_views.available_technicians)),
    path('technicians/slots', methods(GET=technician_views.available_slots)),
    path('technicians/profile', methods(GET=technician_views.get_technician_profile)),
    path('technicians/appointments', methods(GET=technician_views.technician_appointments)),
    path(
        'technicians/appointments/<int:appointment_id>',
        methods(PATCH=technician_views.update_appointment_status),
    ),

    # ------------------------------------------------------------------
    # appointments_bp: /api/appointments
    # ------------------------------------------------------------------
    path('appointments/availability', methods(GET=appointment_views.get_availability)),
    path('appointments', methods(GET=appointment_views.list_appointments, POST=appointment_views.create_appointment)),
    path('appointments/', methods(GET=appointment_views.list_appointments, POST=appointment_views.create_appointment)),
    path(
        'appointments/<int:appointment_id>',
        methods(GET=appointment_views.get_appointment, PATCH=appointment_views.update_appointment),
    ),

    # ------------------------------------------------------------------
    # admin_bp: /api/admin
    # ------------------------------------------------------------------
    path('admin/dashboard', methods(GET=admin_views.dashboard)),
    path('admin/users', methods(GET=admin_views.list_users, POST=admin_views.create_user)),
    path(
        'admin/users/<int:user_id>',
        methods(PATCH=admin_views.update_user, DELETE=admin_views.delete_user),
    ),
    path(
        'admin/appointments/<int:appointment_id>',
        methods(PATCH=admin_views.update_appointment),
    ),

    # ------------------------------------------------------------------
    # addresses_bp: /api/user/addresses
    # ------------------------------------------------------------------
    path('user/addresses', methods(GET=address_views.list_addresses, POST=address_views.create_address)),
    path(
        'user/addresses/<int:addr_id>',
        methods(
            PATCH=address_views.update_address,
            PUT=address_views.update_address,
            DELETE=address_views.delete_address,
        ),
    ),
    path(
        'user/addresses/<int:addr_id>/set-default',
        methods(POST=address_views.set_default_address),
    ),

    # ------------------------------------------------------------------
    # favorites_bp: /api/user/favorites
    # ------------------------------------------------------------------
    path('user/favorites', methods(GET=favorite_views.list_favorites)),
    path(
        'user/favorites/<int:service_id>',
        methods(POST=favorite_views.toggle_favorite, DELETE=favorite_views.remove_favorite),
    ),

    # ------------------------------------------------------------------
    # events_bp: /api/events
    # ------------------------------------------------------------------
    path('events', methods(POST=event_views.create_event)),
    path('events/', methods(POST=event_views.create_event)),

    # ------------------------------------------------------------------
    # homes_bp: /api/homes
    # ------------------------------------------------------------------
    path('homes', methods(POST=home_views.create_home, GET=home_views.list_homes)),
    path(
        'homes/<int:id>',
        methods(GET=home_views.get_home, PATCH=home_views.update_home, DELETE=home_views.delete_home),
    ),
    path(
        'homes/<int:home_id>/rooms',
        methods(POST=home_views.create_room, GET=home_views.list_rooms),
    ),
    path(
        'homes/<int:home_id>/rooms/<int:room_id>',
        methods(PATCH=home_views.update_room, DELETE=home_views.delete_room),
    ),
    path(
        'homes/<int:home_id>/assets',
        methods(POST=home_views.create_asset, GET=home_views.list_assets),
    ),
    path(
        'homes/<int:home_id>/assets/<int:asset_id>',
        methods(PATCH=home_views.update_asset, DELETE=home_views.delete_asset),
    ),

    # ------------------------------------------------------------------
    # onboarding_bp: /api/onboarding
    # ------------------------------------------------------------------
    path('onboarding/status', methods(GET=onboarding_views.get_status)),
    path('onboarding/questions', methods(GET=onboarding_views.get_questions)),
    path('onboarding/start', methods(POST=onboarding_views.start)),
    path('onboarding/complete', methods(POST=onboarding_views.complete)),
    path('onboarding/skip', methods(POST=onboarding_views.skip)),

    # ------------------------------------------------------------------
    # embeddings_bp: /api/embeddings
    # ------------------------------------------------------------------
    path('embeddings/provider-info', methods(GET=embedding_views.get_provider_info)),
    path('embeddings/embed', methods(POST=embedding_views.generate_embedding)),
    path('embeddings/sync', methods(POST=embedding_views.sync_embeddings)),
    path('embeddings/search', methods(POST=embedding_views.search_embeddings)),

    # ------------------------------------------------------------------
    # search_bp: /api/search
    # ------------------------------------------------------------------
    path('search/hybrid', methods(POST=search_views.search_hybrid)),

    # ------------------------------------------------------------------
    # intelligence_bp: /api/intelligence
    # ------------------------------------------------------------------
    path('intelligence/understand', methods(POST=intelligence_views.process_text_understanding)),

    # ------------------------------------------------------------------
    # recommendations_bp: /api/recommendations (Flask rule was '/')
    # ------------------------------------------------------------------
    path('recommendations', methods(GET=recommendation_views.get_recommendations)),
    path('recommendations/', methods(GET=recommendation_views.get_recommendations)),
    path('recommendations/<int:rec_id>/click', methods(POST=recommendation_views.track_click)),
    path('recommendations/<int:rec_id>/convert', methods(POST=recommendation_views.track_conversion)),

    # ------------------------------------------------------------------
    # upload_bp: /api/upload
    # ------------------------------------------------------------------
    path('upload/evidence', methods(POST=upload_views.upload_evidence)),
    path('upload/presets', methods(GET=upload_views.get_evidence_presets)),
]
