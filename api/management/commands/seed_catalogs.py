"""
Seed room/asset catalogs - the codes consumed by onboarding (FASE 8),
Digital Homes (FASE 7), hybrid search (FASE 10) and NLU (FASE 11).

Usage: python manage.py seed_catalogs
"""
from django.core.management.base import BaseCommand

from api.models import AssetTypeCatalog, RoomTypeCatalog

# Codes used by onboarding QUESTIONS_CONFIG key_zones options
ROOM_TYPES = [
    # code, name, icon, order
    ('cocina', 'Cocina', 'kitchen', 1),
    ('bano', 'Baños', 'bathtub', 2),
    ('sala', 'Sala', 'weekend', 3),
    ('habitacion', 'Habitaciones', 'bed', 4),
    ('patio', 'Patio o Jardín', 'yard', 5),
    ('balcon', 'Balcón', 'deck', 6),
    ('zona_lavado', 'Zona de lavado', 'local_laundry_service', 7),
]

# Codes used by onboarding assets_present options + ASSET_SYNONYMS/NLU
ASSET_TYPES = [
    # code, name, category, icon, maintenance months, order
    ('sanitario', 'Sanitario', 'plumbing', 'wc', 6, 1),
    ('calentador', 'Calentador de agua', 'gas', 'water_heater', 6, 2),
    ('ducha', 'Ducha / Grifería', 'plumbing', 'shower', 12, 3),
    ('lavamanos', 'Lavamanos', 'plumbing', 'basin', 6, 4),
    ('lavadora', 'Lavadora', 'appliance', 'local_laundry_service', 12, 5),
    ('aire_acondicionado', 'Aire acondicionado', 'appliance', 'mode_fan', 6, 6),
    ('enchufe', 'Instalaciones eléctricas / Tomas', 'electricity', 'power', 12, 7),
    ('iluminacion', 'Iluminación especializada', 'electricity', 'lightbulb', 12, 8),
]


class Command(BaseCommand):
    help = 'Seed room_type_catalog and asset_type_catalog'

    def handle(self, *args, **options):
        rooms_created = 0
        for code, name, icon, order in ROOM_TYPES:
            _, created = RoomTypeCatalog.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'icon': icon,
                    'display_order': order,
                    'is_active': True,
                },
            )
            rooms_created += 1 if created else 0

        assets_created = 0
        for code, name, category, icon, months, order in ASSET_TYPES:
            _, created = AssetTypeCatalog.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'category': category,
                    'icon': icon,
                    'default_maintenance_months': months,
                    'display_order': order,
                    'is_active': True,
                },
            )
            assets_created += 1 if created else 0

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Catálogos listos: {rooms_created} habitaciones nuevas, '
                f'{assets_created} activos nuevos.'
            )
        )
