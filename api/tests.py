"""
Contract tests - port of backend_flask/tests/test_api_contract.py.

They run on in-memory SQLite (see config/settings.py) so they work without a
live PostgreSQL/MySQL:

    python manage.py test api
"""
from django.test import TestCase


class ApiContractTests(TestCase):
    """Same assertions as the original Flask unittest suite."""

    def test_login_returns_frontend_compatible_payload(self):
        from api.models import User

        user = User(name='Test User', email='test@example.com', role='customer')
        user.set_password('Password123!')
        user.save()

        response = self.client.post(
            '/api/auth/login',
            data='{"email": "test@example.com", "password": "Password123!"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('token', payload)
        self.assertIn('user', payload)
        self.assertEqual(payload['user']['email'], 'test@example.com')

    def test_register_returns_frontend_compatible_payload(self):
        response = self.client.post(
            '/api/auth/register',
            data='{"name": "New User", "email": "new@example.com", "password": "Password123!"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('token', payload)
        self.assertIn('user', payload)
        self.assertEqual(payload['user']['email'], 'new@example.com')

    def test_profile_requires_auth(self):
        response = self.client.get('/api/auth/profile')
        self.assertIn(response.status_code, (401, 403))

    def test_health_endpoint_reports_database(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'healthy')
        self.assertIn('database', payload)

    def test_services_listing_matches_contract(self):
        from api.models import Service

        Service.objects.create(
            name='Fugas de agua',
            description='Goteras, tuberías, llaves',
            icon='fa-droplet',
            color='water',
            base_price=80000,
        )

        response = self.client.get('/api/services')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('services', payload)
        self.assertIn('total', payload)
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['services'][0]['name'], 'Fugas de agua')

    def test_login_with_wrong_password_returns_401(self):
        from api.models import User

        user = User(name='Test User', email='fail@example.com', role='customer')
        user.set_password('Password123!')
        user.save()

        response = self.client.post(
            '/api/auth/login',
            data='{"email": "fail@example.com", "password": "WrongPass999!"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()['success'])

    def test_method_not_allowed_returns_405(self):
        response = self.client.get('/api/auth/login')
        self.assertEqual(response.status_code, 405)


class UploadValidationTests(TestCase):
    """La subida de evidencias valida extensión, firma binaria y tamaño."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        self._tmp = tempfile.mkdtemp()
        self._override = override_settings(UPLOADS_STATIC_DIR=Path(self._tmp))
        self._override.enable()

    def tearDown(self):
        self._override.disable()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _upload(self, name, content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return self.client.post(
            '/api/upload/evidence',
            data={'image': SimpleUploadedFile(name, content, content_type='image/png')},
        )

    def test_accepts_real_png(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
        response = self._upload('evidence.png', png)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])

    def test_rejects_fake_image_content(self):
        response = self._upload('evidence.png', b'<html>no soy una imagen</html>')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid image content', response.json()['error'])

    def test_rejects_oversized_file(self):
        from unittest.mock import patch

        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 200
        with patch('api.views.upload_views.MAX_EVIDENCE_BYTES', 100):
            response = self._upload('evidence.png', png)
        self.assertEqual(response.status_code, 400)
        self.assertIn('too large', response.json()['error'])


class DomainUnitTests(TestCase):
    def test_validators_cover_format_and_boundary_cases(self):
        from api.utils.validators import (
            validate_email,
            validate_name,
            validate_password,
            validate_phone,
        )

        self.assertTrue(validate_email('ana+plomapp@example.co'))
        self.assertFalse(validate_email('ana@localhost'))
        self.assertTrue(validate_password('12345678'))
        self.assertFalse(validate_password('1234567'))
        self.assertTrue(validate_phone('+573001234567'))
        self.assertFalse(validate_phone('300-123-4567'))
        self.assertFalse(validate_name('  '))
        self.assertTrue(validate_name(' Ana '))

    def test_appointment_transitions_allow_only_forward_progress(self):
        from api.services.appointment_service import validate_appointment_transition

        allowed = {
            'pending': ('scheduled', 'cancelled'),
            'scheduled': ('in_progress', 'cancelled'),
            'in_progress': ('completed', 'cancelled'),
        }
        for current, destinations in allowed.items():
            for destination in destinations:
                with self.subTest(current=current, destination=destination):
                    self.assertTrue(validate_appointment_transition(current, destination))

        for current in ('pending', 'scheduled', 'in_progress', 'completed', 'cancelled'):
            with self.subTest(current=current, destination=current):
                self.assertFalse(validate_appointment_transition(current, current))
        self.assertFalse(validate_appointment_transition('completed', 'scheduled'))
        self.assertFalse(validate_appointment_transition('unknown', 'pending'))

    def test_password_hash_verifies_without_storing_plaintext(self):
        from api.models import User

        user = User(name='Ana', email='ana@example.com', password_hash='')
        user.set_password('SecretPass123!')

        self.assertNotEqual(user.password_hash, 'SecretPass123!')
        self.assertTrue(user.verify_password('SecretPass123!'))
        self.assertFalse(user.verify_password('WrongPass123!'))

    def test_user_serialization_omits_password_and_auth_tokens(self):
        from api.models import User

        user = User(
            name='Ana',
            email='ana@example.com',
            password_hash='hashed-password',
            reset_token='reset-secret',
            verification_token='verification-secret',
        )

        payload = user.to_dict()

        self.assertEqual(payload['email'], 'ana@example.com')
        self.assertNotIn('password_hash', payload)
        self.assertNotIn('reset_token', payload)
        self.assertNotIn('verification_token', payload)


class AppointmentServiceUnitTests(TestCase):
    appointment_date = '2032-01-05'  # Monday

    def _create_user(self, name, email, role='customer', status='active'):
        from api.models import User

        return User.objects.create(
            name=name,
            email=email,
            role=role,
            status=status,
            password_hash='test-hash',
        )

    def _create_technician(
        self,
        name,
        email,
        rating,
        schedule=None,
        available=True,
        status='active',
    ):
        from api.models import TechnicianProfile

        user = self._create_user(name, email, role='technician', status=status)
        TechnicianProfile.objects.create(
            user=user,
            specialties=['plumbing'],
            rating=rating,
            schedule=schedule if schedule is not None else {'mon': [[8, 18]]},
            available=available,
        )
        return user

    def _create_service(self, duration_minutes=60):
        from api.models import Service

        return Service.objects.create(
            name=f'Plomeria {duration_minutes}',
            duration_minutes=duration_minutes,
            base_price=80000,
        )

    def test_assignment_selects_highest_rated_eligible_technician(self):
        from api.services.appointment_service import find_available_technician

        self._create_technician('Offline', 'offline@example.com', 5.0, available=False)
        self._create_technician(
            'Wrong day', 'wrong-day@example.com', 4.9, schedule={'tue': [[8, 18]]}
        )
        self._create_technician('Inactive', 'inactive@example.com', 4.8, status='inactive')
        self._create_technician('Lower rating', 'lower@example.com', 3.5)
        best = self._create_technician('Best rating', 'best@example.com', 4.9)

        selected = find_available_technician(self.appointment_date, '09:00')

        self.assertEqual(selected, best)

    def test_assignment_skips_technician_with_active_booking(self):
        from api.models import Appointment
        from api.services.appointment_service import find_available_technician

        customer = self._create_user('Customer', 'customer@example.com')
        service = self._create_service()
        highest = self._create_technician('Highest', 'highest@example.com', 5.0)
        alternate = self._create_technician('Alternate', 'alternate@example.com', 4.0)
        Appointment.objects.create(
            user=customer,
            technician=highest,
            service=service,
            date=self.appointment_date,
            time='09:00',
            status='scheduled',
        )

        selected = find_available_technician(self.appointment_date, '09:00')

        self.assertEqual(selected, alternate)

    def test_assignment_respects_excluded_technician_and_invalid_date(self):
        from api.services.appointment_service import find_available_technician

        technician = self._create_technician('Only tech', 'only@example.com', 5.0)

        self.assertIsNone(find_available_technician(
            self.appointment_date,
            '09:00',
            exclude_technician_id=technician.id,
        ))
        self.assertIsNone(find_available_technician('2032-02-31', '09:00'))

    def test_specific_availability_checks_date_schedule_and_conflicts(self):
        from api.models import Appointment
        from api.services.appointment_service import check_technician_availability

        technician = self._create_technician('Available', 'available@example.com', 4.5)
        customer = self._create_user('Customer', 'customer@example.com')
        service = self._create_service()

        available, error, selected = check_technician_availability(
            technician.id, self.appointment_date, '09:00'
        )
        self.assertTrue(available)
        self.assertIsNone(error)
        self.assertEqual(selected, technician)

        outside_hours, _, _ = check_technician_availability(
            technician.id, self.appointment_date, '19:00'
        )
        invalid_date, _, _ = check_technician_availability(
            technician.id, 'not-a-date', '09:00'
        )
        self.assertFalse(outside_hours)
        self.assertFalse(invalid_date)

        Appointment.objects.create(
            user=customer,
            technician=technician,
            service=service,
            date=self.appointment_date,
            time='09:00',
            status='in_progress',
        )
        booked, _, _ = check_technician_availability(
            technician.id, self.appointment_date, '09:00'
        )
        self.assertFalse(booked)

    def test_time_slots_hide_active_bookings_but_keep_completed_ones(self):
        from api.models import Appointment
        from api.services.appointment_service import get_available_time_slots

        technician = self._create_technician(
            'Schedule', 'schedule@example.com', 4.0, schedule={'mon': [[8, 11]]}
        )
        customer = self._create_user('Customer', 'customer@example.com')
        service = self._create_service()
        for time, status in (('09:00', 'pending'), ('10:00', 'completed')):
            Appointment.objects.create(
                user=customer,
                technician=technician,
                service=service,
                date=self.appointment_date,
                time=time,
                status=status,
            )

        slots = get_available_time_slots(technician.id, self.appointment_date)

        self.assertEqual(slots, ['08:00', '10:00'])

    def test_smart_slots_apply_service_duration_schedule_and_conflicts(self):
        from api.models import Appointment
        from api.services.appointment_service import get_smart_time_slots

        technician = self._create_technician(
            'Smart slots', 'smart@example.com', 4.0, schedule={'mon': [[8, 11]]}
        )
        customer = self._create_user('Customer', 'customer@example.com')
        service = self._create_service(duration_minutes=90)
        Appointment.objects.create(
            user=customer,
            technician=technician,
            service=service,
            date=self.appointment_date,
            time='09:00',
            status='pending',
        )

        result = get_smart_time_slots(service.id, self.appointment_date, technician.id)
        slots = {slot['start']: slot for slot in result['slots']}

        self.assertEqual(result['duration_minutes'], 90)
        self.assertEqual(len(result['slots']), 10)
        self.assertEqual(slots['08:00']['end'], '09:30')
        self.assertTrue(slots['08:00']['available'])
        self.assertFalse(slots['09:00']['available'])
        self.assertEqual(slots['09:00']['available_technicians_count'], 0)
        self.assertFalse(slots['12:00']['available'])
        self.assertEqual(slots['17:00']['period'], 'evening')
