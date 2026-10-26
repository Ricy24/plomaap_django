"""
Seed technicians - direct port of seed_technicians.py (Flask).

Usage: python manage.py seed_technicians
"""
from django.core.management.base import BaseCommand

from api.models import TechnicianProfile, User

HORARIO_BASE = {
    'mon': [[9, 17]],
    'tue': [[9, 17]],
    'wed': [[9, 17]],
    'thu': [[9, 17]],
    'fri': [[9, 17]],
}


class Command(BaseCommand):
    help = 'Seed the default technicians and their profiles'

    def handle(self, *args, **options):
        if User.objects.filter(role='technician').first():
            self.stdout.write('⚠️ Los técnicos ya existen en la base de datos.')
            return

        self.stdout.write('🚀 Inyectando técnicos a la base de datos...')

        # --- PASO 1: Crear los Usuarios (Técnicos) ---
        tech1 = User(
            name='Carlos Plomero',
            email='carlos@plomaap.com',
            phone='3001234567',
            address='Bogotá, Zona Norte',
            role='technician',
            status='active',
        )
        tech1.set_password('123456')  # Contraseña por defecto para pruebas

        tech2 = User(
            name='Roberto Destapes',
            email='roberto@plomaap.com',
            phone='3109876543',
            address='Bogotá, Zona Sur',
            role='technician',
            status='active',
        )
        tech2.set_password('123456')

        tech1.save()
        tech2.save()

        self.stdout.write('👤 Usuarios de técnicos creados. Generando perfiles...')

        # --- PASO 2: Crear sus Perfiles de Técnico ---
        profile1 = TechnicianProfile(
            user_id=tech1.id,
            specialties=['Fugas de agua', 'Duchas y baños'],
            rating=4.8,
            bio='Especialista en fugas y grifería fina con más de 10 años de experiencia.',
            schedule=HORARIO_BASE,
            available=True,
        )

        profile2 = TechnicianProfile(
            user_id=tech2.id,
            specialties=['Destapes', 'Instalaciones'],
            rating=4.9,
            bio='Experto en tuberías complejas y destapes con maquinaria especializada.',
            schedule=HORARIO_BASE,
            available=True,
        )

        TechnicianProfile.objects.bulk_create([profile1, profile2])

        self.stdout.write(self.style.SUCCESS('✅ ¡Técnicos y sus perfiles agregados con éxito!'))
