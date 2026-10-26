"""
Seed services - direct port of seed.py (Flask).

Usage: python manage.py seed_services
"""
from django.core.management.base import BaseCommand

from api.models import Service


class Command(BaseCommand):
    help = 'Seed the services catalog (same data as the Flask seed.py)'

    def handle(self, *args, **options):
        if Service.objects.first():
            self.stdout.write('⚠️ Los servicios ya existen en la base de datos.')
            return

        self.stdout.write('🚀 Inyectando servicios a la base de datos...')

        servicios = [
            Service(
                name='Fugas de agua',
                description='Goteras, tuberías, llaves',
                icon='fa-droplet',
                color='water',
                base_price=80000,
            ),
            Service(
                name='Destapes',
                description='Baños, cocinas, cañerías',
                icon='fa-toilet',
                color='drain',
                base_price=60000,
            ),
            Service(
                name='Duchas y baños',
                description='Grifería, sanitarios, mamparas',
                icon='fa-shower',
                color='shower',
                base_price=90000,
            ),
            Service(
                name='Instalaciones',
                description='Lavaplatos, calentadores, tubería',
                icon='fa-wrench',
                color='pipe',
                base_price=120000,
            ),
        ]
        Service.objects.bulk_create(servicios)

        self.stdout.write(self.style.SUCCESS('✅ ¡Servicios agregados con éxito!'))
