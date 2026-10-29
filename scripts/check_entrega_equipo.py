#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Valida las entregas del equipo contra el contrato cerrado.

Fuente de verdad: ``scripts/especificaciones_entrega.py``.
Contratos publicos: ``docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md`` y
``docs/pruebas/RETO_AVANZADO.md``.

Si un archivo todavia no existe, lo reporta como pendiente y no falla. Cuando
existe, exige:

  - exactamente las pruebas del contrato, con esos nombres y sin extras;
  - docstring con Caso / Entrada / Esperado / Cubre;
  - ``Cubre:`` = ruta::simbolo, con un modulo asignado y un simbolo real;
  - que la prueba **llame** al simbolo (o use la constante) en su codigo;
  - al menos un assert con comparacion real o ``pytest.raises`` especifico;
  - sin mocks, monkeypatch, skip/xfail, parametrize, random, sleep ni lectura
    del codigo fuente en tiempo de ejecucion;
  - maximo de lineas por prueba y minimo de simbolos distintos;
  - ``pytestmark = pytest.mark.unit``.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EQUIPO = RAIZ / "api" / "tests" / "unit" / "equipo"

sys.path.insert(0, str(RAIZ / "scripts"))
from especificaciones_entrega import ENTREGAS, POR_CLAVE, Ronda, iterar_rondas  # noqa: E402

ETIQUETAS = ("Caso:", "Entrada:", "Esperado:", "Cubre:")

PROHIBIDO = (
    "monkeypatch",
    "unittest.mock",
    "from mock",
    "import mock",
    "MagicMock",
    "pytest.skip",
    "pytest.mark.skip",
    "pytest.mark.xfail",
    "parametrize",
    "random.",
    "time.sleep",
    "inspect.getsource",
    "read_text(",
    "open(",
)

EXCEPCIONES_GENERICAS = {"Exception", "BaseException", "object"}


def _simbolos_de(ruta: Path) -> dict[str, str]:
    """Devuelve ``{nombre: tipo}`` de los simbolos de nivel superior."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: dict[str, str] = {}
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nombres[nodo.name] = "funcion"
        elif isinstance(nodo, ast.ClassDef):
            nombres[nodo.name] = "clase"
        elif isinstance(nodo, ast.Assign):
            for objetivo in nodo.targets:
                if isinstance(objetivo, ast.Name):
                    nombres[objetivo.id] = "constante"
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nombres[nodo.target.id] = "constante"
    return nombres


def _llamadas(funcion: ast.AST) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Call):
            if isinstance(nodo.func, ast.Name):
                nombres.add(nodo.func.id)
            elif isinstance(nodo.func, ast.Attribute):
                nombres.add(nodo.func.attr)
        elif isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorador in nodo.decorator_list:
                if isinstance(decorador, ast.Name):
                    nombres.add(decorador.id)
                elif isinstance(decorador, ast.Attribute):
                    nombres.add(decorador.attr)
    return nombres


def _nombres_usados(funcion: ast.AST) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Name):
            nombres.add(nodo.id)
        elif isinstance(nodo, ast.Attribute):
            nombres.add(nodo.attr)
    return nombres


def _usa_simbolo(funcion: ast.AST, simbolo: str, tipo: str) -> bool:
    if tipo in {"funcion", "clase"}:
        return simbolo in _llamadas(funcion)
    return simbolo in _nombres_usados(funcion)


def _assert_valido(funcion: ast.AST) -> tuple[bool, str]:
    for nodo in ast.walk(funcion):
        if not isinstance(nodo, ast.Assert):
            continue
        prueba = nodo.test
        if isinstance(prueba, ast.Constant):
            return False, "no se permite `assert` con una constante"
        if isinstance(prueba, ast.Compare):
            return True, ""
        if isinstance(prueba, ast.Name):
            return False, "el assert debe comparar, no solo nombrar una variable"
    return False, "falta un assert con comparacion real"


def _raises_especifico(funcion: ast.AST) -> bool:
    for nodo in ast.walk(funcion):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = ""
        if isinstance(nodo.func, ast.Attribute):
            nombre = nodo.func.attr
        elif isinstance(nodo.func, ast.Name):
            nombre = nodo.func.id
        if nombre != "raises" or not nodo.args:
            continue
        excepcion = nodo.args[0]
        if isinstance(excepcion, ast.Name) and excepcion.id in EXCEPCIONES_GENERICAS:
            continue
        if isinstance(excepcion, ast.Attribute) and excepcion.attr in EXCEPCIONES_GENERICAS:
            continue
        return True
    return False


def _docstring_valido(funcion: ast.AST) -> tuple[bool, str]:
    doc = ast.get_docstring(funcion) or ""
    for etiqueta in ETIQUETAS:
        if etiqueta not in doc:
            return False, f"falta `{etiqueta}` en el docstring"
    if len(doc.strip()) < 40:
        return False, "el docstring es demasiado corto para explicar el caso"
    return True, ""


def _cubre(funcion: ast.AST) -> str:
    doc = ast.get_docstring(funcion) or ""
    for linea in doc.splitlines():
        if linea.strip().startswith("Cubre:"):
            return linea.split("Cubre:", 1)[1].strip()
    return ""


def _modulo_del_simbolo(cubre: str, modulos: tuple[str, ...]) -> str | None:
    if "::" not in cubre:
        return None
    ruta = cubre.split("::")[0].strip().replace("\\", "/")
    return ruta if ruta in modulos else None


def _validar_funcion(
    nombre_test: str,
    funcion: ast.AST,
    ronda: Ronda,
    simbolos_modulo: dict[str, dict[str, str]],
) -> tuple[list[str], str | None]:
    errores: list[str] = []
    simbolo_usado: str | None = None

    ok, motivo = _docstring_valido(funcion)
    if not ok:
        errores.append(f"{nombre_test}: {motivo}")
        return errores, None

    cubre = _cubre(funcion)
    modulo = _modulo_del_simbolo(cubre, ronda.modulos)
    if modulo is None:
        errores.append(
            f"{nombre_test}: `Cubre:` debe apuntar a uno de estos modulos: "
            + ", ".join(ronda.modulos)
        )
        return errores, None

    simbolo = cubre.split("::", 1)[1].strip()
    if not simbolo:
        errores.append(f"{nombre_test}: `Cubre:` no indica el simbolo")
        return errores, None

    tipo = simbolos_modulo[modulo].get(simbolo)
    if tipo is None:
        errores.append(f"{nombre_test}: `{simbolo}` no existe en {modulo}")
        return errores, None

    if not _usa_simbolo(funcion, simbolo, tipo):
        accion = "llamar" if tipo in {"funcion", "clase"} else "usar"
        errores.append(
            f"{nombre_test}: la prueba debe {accion} `{simbolo}` en su propio codigo"
        )

    if not (_assert_valido(funcion)[0] or _raises_especifico(funcion)):
        errores.append(
            f"{nombre_test}: falta un assert con comparacion o un "
            "`pytest.raises` con una excepcion especifica"
        )

    lineas = funcion.end_lineno - funcion.lineno + 1
    if lineas > ronda.max_lineas:
        errores.append(
            f"{nombre_test}: tiene {lineas} lineas (maximo {ronda.max_lineas})"
        )

    if not errores:
        simbolo_usado = simbolo
    return errores, simbolo_usado


def validar_ronda(entrega_clave: str, ronda_clave: str) -> list[str]:
    """Devuelve la lista de errores de una ronda. Vacia = cumple."""
    entrega = POR_CLAVE[entrega_clave]
    ronda = entrega.ronda(ronda_clave)
    archivo = RAIZ / entrega.ruta_carpeta / ronda.archivo
    errores: list[str] = []

    if not archivo.exists():
        return [f"no existe {archivo.relative_to(RAIZ)}"]

    texto = archivo.read_text(encoding="utf-8")

    if "pytestmark = pytest.mark.unit" not in texto:
        errores.append("falta `pytestmark = pytest.mark.unit`")

    for palabra in PROHIBIDO:
        if palabra in texto:
            errores.append(f"no se permite `{palabra}` en la entrega")

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

    faltan = [n for n in ronda.pruebas if n not in pruebas]
    sobran = [n for n in pruebas if n not in ronda.pruebas]
    if faltan:
        errores.append("faltan pruebas del contrato: " + ", ".join(faltan))
    if sobran:
        errores.append("pruebas que no estan en el contrato: " + ", ".join(sobran))

    simbolos_modulo = {
        modulo: _simbolos_de(RAIZ / modulo) for modulo in ronda.modulos
    }

    simbolos: set[str] = set()

    for nombre_test in ronda.pruebas:
        funcion = pruebas.get(nombre_test)
        if funcion is None:
            continue
        errores_funcion, simbolo = _validar_funcion(
            nombre_test, funcion, ronda, simbolos_modulo
        )
        errores.extend(errores_funcion)
        if simbolo:
            simbolos.add(simbolo)

    if len(simbolos) < ronda.min_simbolos:
        errores.append(
            f"debe usar al menos {ronda.min_simbolos} simbolos distintos, "
            f"usa {len(simbolos)}"
        )

    return errores


def _seleccion(integrante: str | None, ronda: str | None, solo_pendientes: bool):
    if integrante:
        if integrante not in POR_CLAVE:
            raise SystemExit(f"Integrante desconocido: {integrante}")
        entregas = (POR_CLAVE[integrante],)
    else:
        entregas = ENTREGAS

    for entrega in entregas:
        for item in entrega.rondas:
            if ronda and item.clave != ronda:
                continue
            if solo_pendientes and not item.pendiente:
                continue
            yield entrega, item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrante", choices=sorted(POR_CLAVE))
    parser.add_argument("--ronda", choices=("base", "avanzada"))
    parser.add_argument(
        "--solo-pendientes",
        action="store_true",
        help="Ignora las rondas marcadas como entregadas.",
    )
    args = parser.parse_args()

    pendientes = 0
    fallos = 0
    revisadas = 0

    for entrega, ronda in _seleccion(args.integrante, args.ronda, args.solo_pendientes):
        archivo = RAIZ / entrega.ruta_carpeta / ronda.archivo
        etiqueta = f"{entrega.clave}:{ronda.clave}"
        if not archivo.exists():
            pendientes += 1
            print(f"[entrega] PENDIENTE {etiqueta} -> {ronda.archivo} ({entrega.responsable})")
            continue

        revisadas += 1
        print(f"[entrega] Revisando {etiqueta} -> {ronda.archivo} ({entrega.responsable})")
        errores = validar_ronda(entrega.clave, ronda.clave)
        if errores:
            fallos += 1
            for error in errores:
                print(f"  - {error}")
        else:
            print("  OK: cumple el contrato")

    if fallos:
        print(
            "\n[entrega] La entrega no cumple. Revisa "
            "docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md y docs/pruebas/RETO_AVANZADO.md"
        )
        return 1

    if revisadas == 0:
        print("[entrega] Sin entregas nuevas: no hay nada que validar todavia")
    elif pendientes:
        print(f"[entrega] {pendientes} ronda(s) pendiente(s); las existentes cumplen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
