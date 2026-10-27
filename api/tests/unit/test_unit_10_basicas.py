# -*- coding: utf-8 -*-
"""
10 pruebas unitarias básicas de PlomApp.

Cada prueba revisa una sola cosa y sigue el patrón:
1. Arrange: preparar el dato.
2. Act: ejecutar la función.
3. Assert: comprobar el resultado esperado.
"""
import pytest

from api.utils.validators import (
    validate_date_time,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
)

pytestmark = pytest.mark.unit


def test_01_email_valido():
    # Arrange: un correo que sí cumple el formato.
    email = "usuario@plomaap.com"

    # Act: ejecutar la función que queremos probar.
    resultado = validate_email(email)

    # Assert: el resultado debe ser True.
    assert resultado is True


def test_02_email_invalido():
    # Este correo no tiene dominio después del arroba.
    email = "usuario@"

    resultado = validate_email(email)

    assert resultado is False


def test_03_telefono_valido():
    # Un celular colombiano de 10 dígitos.
    telefono = "3229874810"

    resultado = validate_phone(telefono)

    assert resultado is True


def test_04_telefono_invalido():
    # Es demasiado corto para ser un teléfono válido.
    telefono = "123"

    resultado = validate_phone(telefono)

    assert resultado is False


def test_05_password_valido():
    # La contraseña tiene 8 caracteres o más.
    password = "PlomApp2026*"

    resultado = validate_password(password)

    assert resultado is True


def test_06_password_corto():
    # Solo tiene 7 caracteres, por eso debe fallar.
    password = "1234567"

    resultado = validate_password(password)

    assert resultado is False


def test_07_nombre_valido():
    # Un nombre normal, con dos letras o más.
    nombre = "Andrés"

    resultado = validate_name(nombre)

    assert resultado is True


def test_08_nombre_corto():
    # Una sola letra no es un nombre válido.
    nombre = "A"

    resultado = validate_name(nombre)

    assert resultado is False


def test_09_fecha_y_hora_validas():
    # Fecha en formato AAAA-MM-DD y hora en formato HH:MM.
    fecha = "2026-11-02"
    hora = "09:00"

    resultado = validate_date_time(fecha, hora)

    assert resultado is True


def test_10_fecha_y_hora_invalidas():
    # El mes 13 no existe, así que la fecha es inválida.
    fecha = "2026-13-01"
    hora = "09:00"

    resultado = validate_date_time(fecha, hora)

    assert resultado is False
