# -*- coding: utf-8 -*-
"""
Integrante 1 - Validaciones de entrada.

Cubre las funciones puras de ``api/utils/validators.py``. Ninguna prueba
necesita base de datos, red ni servicios externos: solo se entrega un dato y
se compara el resultado con lo esperado.
"""
import pytest

from api.utils.validators import (
    validate_date_time,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
    validate_role,
)

pytestmark = pytest.mark.unit


def test_email_valido():
    """Un correo con usuario, arroba y dominio debe ser aceptado."""
    # Arrange
    email = 'carlos@plomaap.com'

    # Act
    resultado = validate_email(email)

    # Assert
    assert resultado is True


def test_email_sin_arroba_es_invalido():
    """Un correo sin arroba debe ser rechazado."""
    assert validate_email('carlos.plomaap.com') is False


def test_password_de_ocho_caracteres_es_valida():
    """La contraseña mínima aceptada tiene exactamente 8 caracteres."""
    assert validate_password('PlomApp1') is True


def test_password_corta_es_invalida():
    """Una contraseña de 4 caracteres no cumple el mínimo."""
    assert validate_password('1234') is False


def test_telefono_valido():
    """Un celular colombiano con prefijo +57 debe ser aceptado."""
    assert validate_phone('+573001234567') is True


def test_telefono_con_letras_es_invalido():
    """El teléfono solo admite dígitos y un posible prefijo."""
    assert validate_phone('abc1234567') is False


def test_nombre_de_un_caracter_es_invalido():
    """El nombre debe tener al menos 2 caracteres después de quitar espacios."""
    assert validate_name('A') is False


def test_fecha_y_hora_validas():
    """El formato esperado es YYYY-MM-DD para la fecha y HH:MM para la hora."""
    assert validate_date_time('2026-11-02', '09:30') is True


def test_fecha_con_formato_incorrecto_es_invalida():
    """El formato DD/MM/YYYY no es el que usa la aplicación."""
    assert validate_date_time('02/11/2026', '09:30') is False


def test_rol_valido():
    """Los roles permitidos son customer, technician y admin."""
    assert validate_role('technician') is True
