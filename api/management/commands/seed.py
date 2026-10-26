"""
Seed everything (catalogs + services + admin + technicians).

Usage: python manage.py seed
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run seed_catalogs, seed_services, seed_admin and seed_technicians'

    def handle(self, *args, **options):
        call_command('seed_catalogs')
        call_command('seed_services')
        call_command('seed_admin')
        call_command('seed_technicians')
        self.stdout.write(self.style.SUCCESS('✅ Seed completo finalizado.'))
