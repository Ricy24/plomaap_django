"""
Normaliza `appointments.evidence_photos` a JSONB en PostgreSQL.

La base original de Flask/SQLAlchemy creó la columna como `json`, mientras
Django (psycopg2) solo registra el decodificador nativo para `jsonb`: al leer
una fila, psycopg2 devuelve una lista de Python y `JSONField` intenta hacer
`json.loads(lista)` -> TypeError -> HTTP 500 en /api/appointments y
/api/admin/dashboard.

Esta migración convierte la columna a `jsonb` conservando los datos. Es
idempotente: si la columna ya es jsonb, el ALTER no cambia nada.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        'ALTER TABLE appointments ALTER COLUMN evidence_photos DROP DEFAULT'
    )
    schema_editor.execute(
        'ALTER TABLE appointments ALTER COLUMN evidence_photos '
        "TYPE jsonb USING evidence_photos::jsonb"
    )
    schema_editor.execute(
        "ALTER TABLE appointments ALTER COLUMN evidence_photos "
        "SET DEFAULT '[]'::jsonb"
    )


def backwards(apps, schema_editor):
    # No se revierte: json y jsonb son compatibles a nivel de datos y volver
    # a `json` reintroduciría el fallo de lectura en Django.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_new_tables_and_appointment_fields'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
