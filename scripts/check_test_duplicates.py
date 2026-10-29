#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Impide que se entreguen pruebas repetidas en api/tests/unit/equipo.

Falla (exit code 1) si encuentra:
  - Dos funciones de prueba con el mismo nombre en archivos distintos.
  - Dos funciones de prueba con el mismo cuerpo (aunque cambie el nombre).

El cuerpo se compara ignorando el docstring, los comentarios y los nombres de
los decoradores, para detectar copias aunque se renombren las variables.
"""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "api" / "tests" / "unit" / "equipo"


def _cuerpo(funcion: ast.FunctionDef) -> list[ast.stmt]:
    """Devuelve las sentencias de la función sin su docstring."""
    cuerpo = list(funcion.body)
    if (
        cuerpo
        and isinstance(cuerpo[0], ast.Expr)
        and isinstance(cuerpo[0].value, ast.Constant)
        and isinstance(cuerpo[0].value.value, str)
    ):
        cuerpo = cuerpo[1:]
    return cuerpo


def _firma(funcion: ast.FunctionDef) -> str:
    """Huella del cuerpo, ignorando nombres de variables locales."""
    cuerpo = _cuerpo(funcion)
    # Se normalizan los nombres de variables/atributos a un marcador para que
    # una copia con variables renombradas siga siendo detectada.
    for nodo in ast.walk(ast.Module(body=cuerpo, type_ignores=[])):
        if isinstance(nodo, ast.Name):
            nodo.id = "_v"
        elif isinstance(nodo, ast.Attribute):
            nodo.attr = "_a"
        elif isinstance(nodo, ast.arg):
            nodo.arg = "_v"
    texto = ast.dump(ast.Module(body=cuerpo, type_ignores=[]), annotate_fields=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def main() -> int:
    archivos = sorted(BASE.glob("test_*.py"))
    if not archivos:
        print(f"[duplicados] No hay archivos en {BASE}")
        return 0

    nombres: dict[str, str] = {}
    firmas: dict[str, tuple[str, str]] = {}
    errores: list[str] = []
    total = 0

    for archivo in archivos:
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errores.append(f"{archivo.name}: error de sintaxis ({exc})")
            continue

        for nodo in arbol.body:
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not nodo.name.startswith("test_"):
                continue

            total += 1

            if nodo.name in nombres:
                errores.append(
                    f"Nombre repetido: {nodo.name} aparece en "
                    f"{nombres[nodo.name]} y en {archivo.name}"
                )
            else:
                nombres[nodo.name] = archivo.name

            firma = _firma(nodo)
            if firma in firmas:
                otro, archivo_otro = firmas[firma]
                errores.append(
                    f"Cuerpo repetido: {nodo.name} ({archivo.name}) es igual a "
                    f"{otro} ({archivo_otro})"
                )
            else:
                firmas[firma] = (nodo.name, archivo.name)

    print(f"[duplicados] {total} pruebas revisadas en {len(archivos)} archivos")

    if errores:
        print("\n[duplicados] Se encontraron pruebas repetidas:\n")
        for error in errores:
            print(f"  - {error}")
        print("\nCada integrante debe entregar pruebas propias y diferentes.")
        return 1

    print("[duplicados] OK: no hay nombres ni cuerpos repetidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
