"""
Seed admin user - direct port of seed_admin.py (Flask).

Usage: python manage.py seed_admin
Env:   ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME
"""
import os

from django.core.management.base import BaseCommand

from api.models import User

DEFAULT_ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@plomapp.com')
DEFAULT_ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin123!')
DEFAULT_ADMIN_NAME = os.getenv('ADMIN_NAME', 'Administrador Principal')


class Command(BaseCommand):
    help = 'Create/update the default admin user'

    def handle(self, *args, **options):
        admin = User.objects.filter(email=DEFAULT_ADMIN_EMAIL).first()
        if not admin:
            admin = User.objects.filter(role='admin').first()

        if admin:
            admin.name = DEFAULT_ADMIN_NAME
            admin.email = DEFAULT_ADMIN_EMAIL
            admin.role = 'admin'
            admin.status = 'active'
            admin.set_password(DEFAULT_ADMIN_PASSWORD)
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Administrador listo: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}')
            )
            return

        self.stdout.write('🚀 Creando usuario administrador...')

        admin = User(
            name=DEFAULT_ADMIN_NAME,
            email=DEFAULT_ADMIN_EMAIL,
            phone='3000000000',
            address='Oficina Central',
            role='admin',
            status='active',
        )
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        admin.save()

        self.stdout.write(
            self.style.SUCCESS(f'✅ Administrador creado: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}')
        )
