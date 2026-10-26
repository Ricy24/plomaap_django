"""
PlomApp models - direct port of app/database/models.py (Flask-SQLAlchemy).

Table names, column names, types, defaults and constraints are kept identical
so this backend can point at the same PostgreSQL `plomapp` database used by the
Flask version (or create an equivalent schema from scratch).
"""
from datetime import datetime

import bcrypt
from django.db import models
from django.db.models import Q


def utcnow():
    """Naive UTC timestamp (same as datetime.utcnow used in the Flask app)."""
    return datetime.utcnow()


# --------------------------------------------------------------------------- #
# Helpers for JSON-like columns (Flask used db.JSON)
# --------------------------------------------------------------------------- #
try:
    from django.contrib.postgres.fields import ArrayField  # noqa: F401
except Exception:  # pragma: no cover - postgres app not required
    ArrayField = None


# --------------------------------------------------------------------------- #
# User
# --------------------------------------------------------------------------- #
class User(models.Model):
    """User model for customers, technicians, and admins."""

    ROLE_CHOICES = [
        ('customer', 'customer'),
        ('technician', 'technician'),
        ('admin', 'admin'),
    ]
    STATUS_CHOICES = [
        ('active', 'active'),
        ('inactive', 'inactive'),
        ('suspended', 'suspended'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    email = models.CharField(max_length=120, unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    email_verified = models.BooleanField(default=False)
    reset_token = models.CharField(max_length=255, null=True, blank=True)
    reset_token_expiry = models.DateTimeField(null=True, blank=True)
    verification_token = models.CharField(max_length=255, null=True, blank=True)
    verification_token_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=utcnow)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'users'

    # ---- password helpers (bcrypt, same as Flask version) ----
    def set_password(self, password):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password):
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                self.password_hash.encode('utf-8'),
            )
        except (ValueError, TypeError):
            return False

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'avatar': self.avatar,
            'role': self.role,
            'status': self.status,
            'email_verified': bool(self.email_verified),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def has_role(self, role):
        return self.role == role

    def is_active(self):
        return self.status == 'active'

    def __str__(self):
        return f'{self.name} <{self.email}>'


class TechnicianProfile(models.Model):
    """Technician profile details."""

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, db_column='user_id',
        related_name='technician_profile',
    )
    specialties = models.JSONField(default=list)  # ['plumbing', 'gas', 'heating']
    rating = models.FloatField(default=0.0)  # 0-5
    bio = models.TextField(null=True, blank=True)
    schedule = models.JSONField(default=dict)  # {'mon': [[9,17]], ...}
    available = models.BooleanField(default=True)

    class Meta:
        db_table = 'technician_profiles'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'specialties': self.specialties or [],
            'rating': self.rating,
            'bio': self.bio,
            'schedule': self.schedule or {},
            'available': self.available,
        }

    def __str__(self):
        return f'TechnicianProfile#{self.id} (user {self.user_id})'


class Service(models.Model):
    """Service catalog."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    icon = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)  # Hex color
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)

    class Meta:
        db_table = 'services'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category or 'General',
            'icon': self.icon,
            'color': self.color,
            'base_price': float(self.base_price),
            'description': self.description,
            'duration_minutes': self.duration_minutes or 60,
        }

    def __str__(self):
        return self.name


class UserAddress(models.Model):
    """User saved addresses."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='addresses')
    label = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=7, null=True, blank=True)
    place_id = models.CharField(max_length=255, null=True, blank=True)
    reference = models.CharField(max_length=255, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=utcnow)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'user_addresses'
        indexes = [models.Index(fields=['user'], name='idx_user_addresses_user')]
        ordering = ['-is_default', '-updated_at']

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'label': self.label,
            'address': self.address,
            'latitude': float(self.latitude) if self.latitude is not None else None,
            'longitude': float(self.longitude) if self.longitude is not None else None,
            'place_id': self.place_id,
            'reference': self.reference,
            'is_default': bool(self.is_default),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Appointment(models.Model):
    """Appointment schedule."""

    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('scheduled', 'scheduled'),
        ('in_progress', 'in_progress'),
        ('completed', 'completed'),
        ('cancelled', 'cancelled'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='appointments_as_customer')
    technician = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='technician_id', related_name='appointments_as_technician',
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, db_column='service_id', related_name='appointments')
    date = models.DateField()
    time = models.CharField(max_length=5)  # HH:MM format
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    address = models.CharField(max_length=255, null=True, blank=True)
    address_reference = models.CharField(max_length=255, null=True, blank=True)
    user_address = models.ForeignKey(
        UserAddress, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='user_address_id', related_name='appointments',
    )
    notes = models.TextField(null=True, blank=True)
    travel_status = models.CharField(max_length=50, default='assigned')
    security_pin = models.CharField(max_length=10, default='1234')
    evidence_photos = models.JSONField(default=list)
    extra_cost = models.FloatField(default=0.0)
    completion_notes = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=utcnow)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'appointments'
        indexes = [
            models.Index(fields=['user', 'date'], name='idx_user_date'),
            models.Index(fields=['technician', 'date'], name='idx_technician_date'),
        ]

    # Backwards-compatible accessors used across the codebase
    @property
    def customer(self):
        return self.user

    @property
    def technician_name(self):
        return self.technician.name if self.technician else None

    @property
    def service_name(self):
        return self.service.name if self.service else None

    # NOTE: user_address_id is provided automatically by the FK attname

    def enrich(self):
        """Return appointment with related data (same shape as Flask version)."""
        service = self.service
        technician = self.technician
        customer = self.user
        price = float(service.base_price) if service and service.base_price else 0.0
        return {
            'id': self.id,
            'user_id': self.user_id,
            'customer': customer.to_dict() if customer else None,
            'technician_id': self.technician_id,
            'technician': technician.to_dict() if technician else None,
            'technician_name': technician.name if technician else None,
            'service_id': self.service_id,
            'service': service.to_dict() if service else None,
            'service_name': service.name if service else None,
            'price': price,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time,
            'status': self.status,
            'address': self.address,
            'address_reference': self.address_reference,
            'user_address_id': self.user_address_id,
            'notes': self.notes,
            'travel_status': self.travel_status or 'assigned',
            'security_pin': self.security_pin or '1234',
            'evidence_photos': self.evidence_photos or [],
            'extra_cost': float(self.extra_cost or 0.0),
            'total_price': price + float(self.extra_cost or 0.0),
            'completion_notes': self.completion_notes,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'arrived_at': self.arrived_at.isoformat() if self.arrived_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict(self, enriched=False):
        if enriched:
            return self.enrich()
        return {
            'id': self.id,
            'user_id': self.user_id,
            'technician_id': self.technician_id,
            'service_id': self.service_id,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Device(models.Model):
    """User device tracking for multi-device support."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='devices')
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    registered_at = models.DateTimeField(default=utcnow)
    last_access = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'devices'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_agent': self.user_agent,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'last_access': self.last_access.isoformat() if self.last_access else None,
        }


class WebAuthnCredential(models.Model):
    """Passkey / WebAuthn credential."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='passkeys')
    credential_id = models.CharField(max_length=500, unique=True, db_index=True)
    public_key = models.TextField()
    sign_count = models.IntegerField(default=0)
    transports = models.JSONField(default=list)
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'webauthn_credentials'

    def to_dict(self):
        return {
            'id': self.id,
            'credential_id': self.credential_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserFavorite(models.Model):
    """User favorite services."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='favorites')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, db_column='service_id', related_name='favorited_by')
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'user_favorites'
        constraints = [
            models.UniqueConstraint(fields=['user', 'service'], name='uq_user_service'),
        ]
        indexes = [models.Index(fields=['user'], name='idx_user_favorites_user')]

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'service_id': self.service_id,
            'service': self.service.to_dict() if self.service else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AppEvent(models.Model):
    """Application Event Log for User Actions and System Events."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='user_id', related_name='app_events',
    )
    session_id = models.CharField(max_length=100, null=True, blank=True)
    event_type = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, db_column='metadata')
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'app_events'
        indexes = [
            models.Index(fields=['user'], name='idx_app_events_user'),
            models.Index(fields=['event_type'], name='idx_app_events_type'),
            models.Index(fields=['entity_type', 'entity_id'], name='idx_app_events_entity'),
            models.Index(fields=['created_at'], name='idx_app_events_created'),
        ]

    # SQLAlchemy attribute was metadata_ mapped to column "metadata"
    @property
    def metadata_(self):
        return self.metadata

    @metadata_.setter
    def metadata_(self, value):
        self.metadata = value

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'event_type': self.event_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'metadata': self.metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RecommendationEvent(models.Model):
    """Recommendation Engine Event Log."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='recommendation_events')
    recommendation_type = models.CharField(max_length=50)
    entity_id = models.IntegerField()
    score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    algorithm_version = models.CharField(max_length=30)
    position = models.IntegerField(null=True, blank=True)
    shown_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, db_column='metadata')

    class Meta:
        db_table = 'recommendation_events'
        indexes = [
            models.Index(fields=['user'], name='idx_recommendation_events_user'),
            models.Index(fields=['recommendation_type'], name='idx_recommendation_events_type'),
        ]

    @property
    def metadata_(self):
        return self.metadata

    @metadata_.setter
    def metadata_(self, value):
        self.metadata = value

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'recommendation_type': self.recommendation_type,
            'entity_id': self.entity_id,
            'score': float(self.score) if self.score is not None else None,
            'algorithm_version': self.algorithm_version,
            'position': self.position,
            'shown_at': self.shown_at.isoformat() if self.shown_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'converted_at': self.converted_at.isoformat() if self.converted_at else None,
            'metadata': self.metadata or {},
        }


class RoomTypeCatalog(models.Model):
    """Catalog of Room Types (FASE 5)."""

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'room_type_catalog'

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'display_order': self.display_order,
            'is_active': self.is_active,
        }

    def __str__(self):
        return f'{self.code} - {self.name}'


class AssetTypeCatalog(models.Model):
    """Catalog of Asset Types (FASE 5)."""

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, null=True, blank=True)
    default_maintenance_months = models.IntegerField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'asset_type_catalog'

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'category': self.category,
            'icon': self.icon,
            'default_maintenance_months': self.default_maintenance_months,
            'display_order': self.display_order,
            'is_active': self.is_active,
        }

    def __str__(self):
        return f'{self.code} - {self.name}'


class Home(models.Model):
    """Digital Home Entity (FASE 5)."""

    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_column='owner_id', related_name='owned_homes')
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=30, default='apartment')
    approximate_area = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    rooms_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=utcnow)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'homes'
        indexes = [models.Index(fields=['owner'], name='idx_homes_owner')]

    def to_dict(self, enriched=False):
        data = {
            'id': self.id,
            'owner_id': self.owner_id,
            'name': self.name,
            'type': self.type,
            'approximate_area': float(self.approximate_area) if self.approximate_area is not None else None,
            'rooms_count': self.rooms_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if enriched:
            data['members_count'] = self.members.count()
            data['actual_rooms_count'] = self.rooms.count()
            data['assets_count'] = self.assets.count()
        return data

    def __str__(self):
        return f'Home#{self.id} {self.name}'


class HomeMember(models.Model):
    """Membership and Role in a Digital Home (FASE 5)."""

    id = models.AutoField(primary_key=True)
    home = models.ForeignKey(Home, on_delete=models.CASCADE, db_column='home_id', related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='home_memberships')
    role = models.CharField(max_length=30, default='member')
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'home_members'
        constraints = [
            models.UniqueConstraint(fields=['home', 'user'], name='uq_home_member'),
        ]
        indexes = [
            models.Index(fields=['home'], name='idx_home_members_home'),
            models.Index(fields=['user'], name='idx_home_members_user'),
        ]

    def to_dict(self):
        return {
            'id': self.id,
            'home_id': self.home_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'user_email': self.user.email if self.user else None,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class HomeRoom(models.Model):
    """Room in a Digital Home (FASE 5)."""

    id = models.AutoField(primary_key=True)
    home = models.ForeignKey(Home, on_delete=models.CASCADE, db_column='home_id', related_name='rooms')
    name = models.CharField(max_length=100)
    # NOTE: in the Flask version this was an FK to room_type_catalog.code;
    # we keep a plain char column plus catalog validation in services/views.
    type = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'home_rooms'
        indexes = [
            models.Index(fields=['home'], name='idx_home_rooms_home'),
            models.Index(fields=['type'], name='idx_home_rooms_type'),
        ]

    @property
    def room_type(self):
        """Resolve RoomTypeCatalog by code (matches Flask relationship)."""
        if not hasattr(self, '_room_type_cache'):
            self._room_type_cache = RoomTypeCatalog.objects.filter(code=self.type).first()
        return self._room_type_cache

    # self.assets is provided by HomeAsset.room related_name='assets'

    def to_dict(self):
        rt = self.room_type
        return {
            'id': self.id,
            'home_id': self.home_id,
            'name': self.name,
            'type': self.type,
            'type_name': rt.name if rt else self.type,
            'icon': rt.icon if rt else None,
            'assets_count': self.assets.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f'HomeRoom#{self.id} {self.name}'


class HomeAsset(models.Model):
    """Asset / Appliance in a Digital Home (FASE 5)."""

    id = models.AutoField(primary_key=True)
    home = models.ForeignKey(Home, on_delete=models.CASCADE, db_column='home_id', related_name='assets')
    room = models.ForeignKey(
        HomeRoom, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='room_id', related_name='assets',
    )
    # NOTE: plain char column + catalog validation (see HomeRoom.type note)
    asset_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    last_maintenance = models.DateField(null=True, blank=True)
    warranty_until = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, db_column='metadata')
    created_at = models.DateTimeField(default=utcnow)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'home_assets'
        indexes = [
            models.Index(fields=['home'], name='idx_home_assets_home'),
            models.Index(fields=['room'], name='idx_home_assets_room'),
            models.Index(fields=['asset_type'], name='idx_home_assets_type'),
        ]

    @property
    def metadata_(self):
        return self.metadata

    @metadata_.setter
    def metadata_(self, value):
        self.metadata = value

    @property
    def asset_type_obj(self):
        """Resolve AssetTypeCatalog by code (matches Flask relationship)."""
        if not hasattr(self, '_asset_type_cache'):
            self._asset_type_cache = AssetTypeCatalog.objects.filter(code=self.asset_type).first()
        return self._asset_type_cache

    @property
    def room_name(self):
        return self.room.name if self.room else None

    def to_dict(self):
        at = self.asset_type_obj
        return {
            'id': self.id,
            'home_id': self.home_id,
            'room_id': self.room_id,
            'room_name': self.room.name if self.room else None,
            'asset_type': self.asset_type,
            'asset_type_name': at.name if at else self.asset_type,
            'category': at.category if at else None,
            'brand': self.brand,
            'model': self.model,
            'installation_date': self.installation_date.isoformat() if self.installation_date else None,
            'last_maintenance': self.last_maintenance.isoformat() if self.last_maintenance else None,
            'warranty_until': self.warranty_until.isoformat() if self.warranty_until else None,
            'metadata': self.metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f'HomeAsset#{self.id} {self.asset_type}'


class ProfileAttribute(models.Model):
    """Profile Attributes with Source Provenance and Confidence (FASE 7)."""

    id = models.BigAutoField(primary_key=True)
    entity_type = models.CharField(max_length=30)
    entity_id = models.IntegerField()
    attribute_key = models.CharField(max_length=100)
    attribute_value = models.JSONField()
    source = models.CharField(max_length=30)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=1.000)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'profile_attributes'
        constraints = [
            models.UniqueConstraint(
                fields=['entity_type', 'entity_id', 'attribute_key'],
                name='uq_profile_attribute',
            ),
        ]
        indexes = [
            models.Index(fields=['entity_type', 'entity_id'], name='idx_profile_attributes_entity'),
            models.Index(fields=['source'], name='idx_profile_attributes_source'),
        ]

    def to_dict(self):
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'attribute_key': self.attribute_key,
            'attribute_value': self.attribute_value,
            'source': self.source,
            'confidence': float(self.confidence) if self.confidence is not None else 1.0,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EntityEmbedding(models.Model):
    """Vector Embeddings Storage for Semantic Search (FASE 9)."""

    id = models.AutoField(primary_key=True)
    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField()
    content_text = models.TextField()
    # Stored as text and cast to vector(512) in PostgreSQL queries
    embedding = models.TextField(null=True, blank=True)
    model_name = models.CharField(max_length=100)
    dimension = models.IntegerField()
    created_at = models.DateTimeField(default=utcnow)
    updated_at = models.DateTimeField(default=utcnow)

    class Meta:
        db_table = 'entity_embeddings'
        constraints = [
            models.UniqueConstraint(
                fields=['entity_type', 'entity_id', 'model_name'],
                name='uq_entity_embedding',
            ),
        ]
        indexes = [
            models.Index(fields=['entity_type', 'entity_id'], name='idx_entity_embeddings_lookup'),
        ]

    def to_dict(self, include_vector=False):
        data = {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'content_text': self.content_text,
            'model_name': self.model_name,
            'dimension': self.dimension,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_vector and self.embedding:
            data['embedding'] = self.embedding
        return data
