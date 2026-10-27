"""
Contract tests - port of backend_flask/tests/test_api_contract.py.

They run on in-memory SQLite (see config/settings.py) so they work without a
live PostgreSQL/MySQL:

    python manage.py test api
"""
from unittest import TestCase as UnitTestCase

from django.test import TestCase


class ValidatorUnitTests(UnitTestCase):
    """Pruebas unitarias de validadores puros, sin base de datos."""

    def test_validate_email_accepts_valid_address(self):
        from api.utils.validators import validate_email

        self.assertTrue(validate_email('persona@example.com'))

    def test_validate_email_rejects_invalid_address(self):
        from api.utils.validators import validate_email

        self.assertFalse(validate_email('persona@'))

    def test_validate_password_accepts_minimum_length(self):
        from api.utils.validators import validate_password

        self.assertTrue(validate_password('12345678'))

    def test_validate_password_rejects_short_password(self):
        from api.utils.validators import validate_password

        self.assertFalse(validate_password('1234567'))

    def test_validate_date_time_accepts_valid_values(self):
        from api.utils.validators import validate_date_time

        self.assertTrue(validate_date_time('2026-10-27', '14:30'))

    def test_validate_date_time_rejects_invalid_values(self):
        from api.utils.validators import validate_date_time

        self.assertFalse(validate_date_time('2026-02-30', '14:30'))


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
