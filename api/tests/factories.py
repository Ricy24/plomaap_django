# -*- coding: utf-8 -*-
"""Factories used by the PlomApp test suite."""
from datetime import date

import bcrypt
import factory

from api.models import Appointment, Service, TechnicianProfile, User


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
