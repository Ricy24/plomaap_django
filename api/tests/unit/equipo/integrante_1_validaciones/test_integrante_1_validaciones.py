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
    """Caso: correo con usuario, arroba y dominio.
    Entrada: 'carlos@plomaap.com'.
    Esperado: True, porque cumple el patron de correo.
    Cubre: api/utils/validators.py::validate_email
    """
    # Arrange
    email = 'carlos@plomaap.com'

    # Act
    resultado = validate_email(email)

    # Assert
    assert resultado is True


def test_email_sin_arroba_es_invalido():
    """Caso: correo sin arroba.
    Entrada: 'carlos.plomaap.com'.
    Esperado: False, porque falta el separador obligatorio.
    Cubre: api/utils/validators.py::validate_email
    """
    assert validate_email('carlos.plomaap.com') is False


def test_password_de_ocho_caracteres_es_valida():
    """Caso: contrasena en el limite minimo.
    Entrada: 'PlomApp1' (8 caracteres).
    Esperado: True, porque el minimo es inclusivo.
    Cubre: api/utils/validators.py::validate_password
    """
    assert validate_password('PlomApp1') is True


def test_password_corta_es_invalida():
    """Caso: contrasena por debajo del minimo.
    Entrada: '1234' (4 caracteres).
    Esperado: False, porque no alcanza los 8 caracteres.
    Cubre: api/utils/validators.py::validate_password
    """
    assert validate_password('1234') is False


def test_telefono_valido():
    """Caso: celular colombiano con prefijo internacional.
    Entrada: '+573001234567'.
    Esperado: True, porque cumple el patron de telefono.
    Cubre: api/utils/validators.py::validate_phone
    """
    assert validate_phone('+573001234567') is True


def test_telefono_con_letras_es_invalido():
    """Caso: telefono con caracteres no numericos.
    Entrada: 'abc1234567'.
    Esperado: False, porque solo se admiten digitos y un prefijo opcional.
    Cubre: api/utils/validators.py::validate_phone
    """
    assert validate_phone('abc1234567') is False


def test_nombre_de_un_caracter_es_invalido():
    """Caso: nombre demasiado corto.
    Entrada: 'A'.
    Esperado: False, porque se exigen al menos 2 caracteres tras limpiar.
    Cubre: api/utils/validators.py::validate_name
    """
    assert validate_name('A') is False


def test_fecha_y_hora_validas():
    """Caso: fecha y hora en los formatos de la aplicacion.
    Entrada: '2026-11-02' y '09:30'.
    Esperado: True, porque ambos formatos son validos.
    Cubre: api/utils/validators.py::validate_date_time
    """
    assert validate_date_time('2026-11-02', '09:30') is True


def test_fecha_con_formato_incorrecto_es_invalida():
    """Caso: fecha en formato local no soportado.
    Entrada: '02/11/2026' y '09:30'.
    Esperado: False, porque el formato esperado es YYYY-MM-DD.
    Cubre: api/utils/validators.py::validate_date_time
    """
    assert validate_date_time('02/11/2026', '09:30') is False


def test_rol_valido():
    """Caso: rol permitido por el modelo de usuarios.
    Entrada: 'technician'.
    Esperado: True, porque pertenece a la lista de roles validos.
    Cubre: api/utils/validators.py::validate_role
    """
    assert validate_role('technician') is True
