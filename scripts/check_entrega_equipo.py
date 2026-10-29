#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Valida la entrega de los integrantes 2 y 4 contra el contrato del proyecto.

Contrato: docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md

Si el archivo todavía no existe, lo reporta como pendiente y no falla. Cuando
existe, exige:

  - exactamente las 10 pruebas del contrato, con esos nombres;
  - que cada prueba cubra el símbolo indicado en el contrato;
  - docstring con Caso / Entrada / Esperado / Cubre;
  - al menos un assert con comparación real (no `assert True`);
  - pytestmark = pytest.mark.unit.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EQUIPO = RAIZ / "api" / "tests" / "unit" / "equipo"

# Contrato cerrado: nombres de prueba y símbolo que deben cubrir.
SPEC = {
    "test_integrante_2_seguridad.py": {
        "responsable": "Sebastián Samacá",
        "precondiciones": (
            "Sin base de datos ni servidor. Se usa RequestFactory para simular "
            "la petición cuando la prueba lo requiera."
        ),
        "severidad": "Alta",
        "modulos": {
            "api/utils/jwt_utils.py",
            "api/utils/decorators.py",
        },
        "tests": {
            "test_generar_token_devuelve_texto": "api/utils/jwt_utils.py::generate_token",
            "test_token_contiene_identidad_del_usuario": "api/utils/jwt_utils.py::decode_token",
            "test_token_alterado_es_rechazado": "api/utils/jwt_utils.py::decode_token",
            "test_token_expirado_es_rechazado": "api/utils/jwt_utils.py::decode_token",
            "test_extraer_token_con_bearer": "api/utils/jwt_utils.py::get_token_from_request",
            "test_extraer_token_sin_encabezado": "api/utils/jwt_utils.py::get_token_from_request",
            "test_identidad_del_token_es_entero": "api/utils/jwt_utils.py::get_current_user_id",
            "test_vista_protegida_sin_token_responde_401": "api/utils/decorators.py::jwt_required",
            "test_vista_de_admin_rechaza_a_un_cliente": "api/utils/decorators.py::admin_only",
            "test_jwt_optional_permite_peticion_sin_token": "api/utils/decorators.py::jwt_optional",
        },
    },
    "test_integrante_4_datos.py": {
        "responsable": "Kevin Pinzón",
        "precondiciones": (
            "SQLite en memoria (pytest-django) y factories de "
            "api/tests/factories.py."
        ),
        "severidad": "Media",
        "modulos": {
            "api/services/profile_service.py",
            "api/services/event_service.py",
            "api/services/recommendation_service.py",
        },
        "tests": {
            "test_registrar_atributo_nuevo": "api/services/profile_service.py::record_attribute",
            "test_actualizar_atributo_existente": "api/services/profile_service.py::record_attribute",
            "test_rechazar_fuente_desconocida": "api/services/profile_service.py::record_attribute",
            "test_rechazar_confianza_fuera_de_rango": "api/services/profile_service.py::record_attribute",
            "test_consultar_atributos_de_entidad": "api/services/profile_service.py::get_entity_attributes",
            "test_eliminar_atributos_de_entidad": "api/services/profile_service.py::delete_entity_attributes",
            "test_registrar_evento_valido": "api/services/event_service.py::track_event",
            "test_evento_desconocido_no_rompe": "api/services/event_service.py::track_event",
            "test_registrar_clic_en_recomendacion": "api/services/recommendation_service.py::track_recommendation_click",
            "test_respetar_limite_de_recomendaciones": "api/services/recommendation_service.py::generate_recommendations",
        },
    },
}

ETIQUETAS = ("Caso:", "Entrada:", "Esperado:", "Cubre:")
OPERADORES_VALIDOS = (
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
)


def _simbolos_de(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombres.add(nodo.name)
        elif isinstance(nodo, ast.Assign):
            for objetivo in nodo.targets:
                if isinstance(objetivo, ast.Name):
                    nombres.add(objetivo.id)
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nombres.add(nodo.target.id)
    return nombres


def _assert_valido(funcion: ast.FunctionDef) -> bool:
    """Exige un assert con comparación real."""
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Assert):
            valor = nodo.test
            if isinstance(valor, ast.Compare):
                if any(isinstance(op, OPERADORES_VALIDOS) for op in valor.ops):
                    return True
            if isinstance(valor, ast.Call):
                # pytest.raises(...) como sentencia/contexto se valida aparte.
                return True
    return False


def _usa_pytest_raises(funcion: ast.FunctionDef) -> bool:
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Call):
            nombre = ""
            if isinstance(nodo.func, ast.Attribute):
                nombre = nodo.func.attr
            elif isinstance(nodo.func, ast.Name):
                nombre = nodo.func.id
            if nombre == "raises":
                return True
        if isinstance(nodo, ast.With):
            for item in nodo.items:
                expr = item.context_expr
                if isinstance(expr, ast.Call):
                    nombre = ""
                    if isinstance(expr.func, ast.Attribute):
                        nombre = expr.func.attr
                    elif isinstance(expr.func, ast.Name):
                        nombre = expr.func.id
                    if nombre == "raises":
                        return True
    return False


def _docstring_valido(funcion: ast.FunctionDef) -> tuple[bool, str]:
    doc = ast.get_docstring(funcion) or ""
    for etiqueta in ETIQUETAS:
        if etiqueta not in doc:
            return False, f"falta `{etiqueta}` en el docstring"
    return True, ""


def _cubre(funcion: ast.FunctionDef) -> str:
    doc = ast.get_docstring(funcion) or ""
    for linea in doc.splitlines():
        if linea.strip().startswith("Cubre:"):
            return linea.split("Cubre:", 1)[1].strip()
    return ""


def _usa_simbolo(funcion: ast.FunctionDef, simbolo: str) -> bool:
    """La prueba debe usar de verdad el símbolo que dice cubrir."""
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Name) and nodo.id == simbolo:
            return True
        if isinstance(nodo, ast.Attribute) and nodo.attr == simbolo:
            return True
    return False


def validar(nombre: str) -> list[str]:
    """Devuelve la lista de errores de un archivo. Vacía = cumple."""
    regla = SPEC[nombre]
    archivo = EQUIPO / nombre
    errores: list[str] = []

    if not archivo.exists():
        return [f"no existe {archivo}"]

    texto = archivo.read_text(encoding="utf-8")
    if "pytestmark = pytest.mark.unit" not in texto:
        errores.append("falta `pytestmark = pytest.mark.unit`")

    try:
        arbol = ast.parse(texto)
    except SyntaxError as exc:
        return [f"error de sintaxis: {exc}"]

    pruebas = {
        nodo.name: nodo
        for nodo in arbol.body
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
        and nodo.name.startswith("test_")
    }

    esperadas = list(regla["tests"])
    faltan = [n for n in esperadas if n not in pruebas]
    sobran = [n for n in pruebas if n not in regla["tests"]]

    if faltan:
        errores.append("faltan pruebas del contrato: " + ", ".join(faltan))
    if sobran:
        errores.append("pruebas que no están en el contrato: " + ", ".join(sobran))

    for nombre_test, destino in regla["tests"].items():
        funcion = pruebas.get(nombre_test)
        if funcion is None:
            continue

        ok, motivo = _docstring_valido(funcion)
        if not ok:
            errores.append(f"{nombre_test}: {motivo}")
            continue

        cubre = _cubre(funcion)
        if cubre != destino:
            errores.append(
                f"{nombre_test}: `Cubre:` debe ser {destino!r}, está {cubre!r}"
            )

        ruta_txt = cubre.split("::")[0] if "::" in cubre else cubre
        if ruta_txt and ruta_txt not in regla["modulos"]:
            errores.append(
                f"{nombre_test}: {ruta_txt} no es un módulo asignado"
            )

        if not (_assert_valido(funcion) or _usa_pytest_raises(funcion)):
            errores.append(
                f"{nombre_test}: falta un assert con comparación real o pytest.raises"
            )

        simbolo = destino.split("::")[1] if "::" in destino else ""
        if simbolo and not _usa_simbolo(funcion, simbolo):
            errores.append(
                f"{nombre_test}: la prueba no usa `{simbolo}` en su código"
            )

    return errores


def main() -> int:
    pendientes = 0
    fallos = 0

    for nombre, regla in SPEC.items():
        archivo = EQUIPO / nombre
        if not archivo.exists():
            pendientes += 1
            print(f"[entrega] PENDIENTE: {nombre} ({regla['responsable']})")
            continue

        print(f"[entrega] Revisando {nombre} ({regla['responsable']})")
        errores = validar(nombre)
        if errores:
            fallos += 1
            for error in errores:
                print(f"  - {error}")
        else:
            print("  OK: cumple el contrato")

    if fallos:
        print(
            "\n[entrega] La entrega no cumple. Revisa "
            "docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md"
        )
        return 1

    if pendientes == len(SPEC):
        print("[entrega] Sin entregas nuevas: no hay nada que validar todavía")
    return 0


if __name__ == "__main__":
    sys.exit(main())
