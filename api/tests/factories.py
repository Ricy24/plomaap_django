# -*- coding: utf-8 -*-
"""Factories used by the PlomApp test suite."""
from datetime import date

import bcrypt
import factory

from api.models import (
    AppEvent,
    Appointment,
    AssetTypeCatalog,
    EntityEmbedding,
    Home,
    HomeAsset,
    HomeMember,
    HomeRoom,
    ProfileAttribute,
    RecommendationEvent,
    RoomTypeCatalog,
    Service,
    TechnicianProfile,
    User,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    name = factory.Sequence(lambda n: f'Usuario Test {n}')
    email = factory.Sequence(lambda n: f'user{n}@plomaap.test')
    role = 'customer'
    status = 'active'
    email_verified = True
    # 4 rounds keep the suite fast; production uses 12.
    password_hash = factory.LazyFunction(
        lambda: bcrypt.hashpw(b'Password123!', bcrypt.gensalt(rounds=4)).decode()
    )


class TechnicianFactory(UserFactory):
    role = 'technician'
    name = factory.Sequence(lambda n: f'Tecnico Test {n}')
    email = factory.Sequence(lambda n: f'tech{n}@plomaap.test')


class TechnicianProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianProfile

    user = factory.SubFactory(TechnicianFactory)
    specialties = factory.LazyFunction(lambda: ['plumbing'])
    rating = 4.8
    available = True
    schedule = factory.LazyFunction(
        lambda: {day: [[8, 18]] for day in ('mon', 'tue', 'wed', 'thu', 'fri', 'sat')}
    )


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service

    name = factory.Sequence(lambda n: f'Servicio Test {n}')
    category = 'General'
    icon = 'fa-wrench'
    color = 'water'
    base_price = 80000
    description = 'Servicio de prueba'
    duration_minutes = 60


class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Appointment

    user = factory.SubFactory(UserFactory)
    technician = factory.SubFactory(TechnicianFactory)
    service = factory.SubFactory(ServiceFactory)
    date = factory.LazyFunction(lambda: date(2026, 11, 2))
    time = '09:00'
    status = 'scheduled'
    address = 'Calle 1 #2-3'
    evidence_photos = factory.LazyFunction(list)


class RoomTypeCatalogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoomTypeCatalog

    code = factory.Sequence(lambda n: f'room{n}')
    name = factory.Sequence(lambda n: f'Room {n}')
    is_active = True


class AssetTypeCatalogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetTypeCatalog

    code = factory.Sequence(lambda n: f'asset{n}')
    name = factory.Sequence(lambda n: f'Asset {n}')
    category = 'plumbing'
    is_active = True


class HomeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Home

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Home {n}')
    type = 'apartment'
    rooms_count = 0


class HomeMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HomeMember

    home = factory.SubFactory(HomeFactory)
    user = factory.SubFactory(UserFactory)
    role = 'member'


class HomeRoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HomeRoom

    home = factory.SubFactory(HomeFactory)
    name = factory.Sequence(lambda n: f'Room {n}')
    type = 'bano'


class HomeAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HomeAsset

    home = factory.SubFactory(HomeFactory)
    room = None
    asset_type = 'ducha'


class ProfileAttributeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProfileAttribute

    entity_type = 'user'
    entity_id = 1
    attribute_key = factory.Sequence(lambda n: f'attr{n}')
    attribute_value = factory.LazyFunction(dict)
    source = 'explicit_user_input'
    confidence = 1.0


class AppEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AppEvent

    user = factory.SubFactory(UserFactory)
    event_type = 'SERVICE_VIEWED'
    entity_type = 'service'
    entity_id = 1
    metadata = factory.LazyFunction(dict)


class RecommendationEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecommendationEvent

    user = factory.SubFactory(UserFactory)
    recommendation_type = 'service'
    entity_id = 1
    score = 0.5
    algorithm_version = 'recommendation_v1'
    position = 1
    metadata = factory.LazyFunction(dict)


class EntityEmbeddingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityEmbedding

    entity_type = 'service'
    entity_id = 1
    content_text = 'Servicio de prueba'
    embedding = '[1.0,0.0,0.0]'
    model_name = 'local-hash-512'
    dimension = 3
