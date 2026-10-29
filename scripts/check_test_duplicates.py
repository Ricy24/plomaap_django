#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Impide que se entreguen pruebas repetidas en api/tests/unit/equipo.

Falla (exit code 1) si encuentra:

  - dos funciones de prueba con el mismo nombre dentro de la misma carpeta de
    integrante;
  - dos funciones de prueba con el mismo cuerpo en cualquier carpeta, aunque se
    renombren las variables.

El cuerpo se compara ignorando el docstring, los comentarios y los nombres de
las variables locales. Los nombres pueden repetirse entre integrantes porque
pytest los identifica por ruta, pero no dentro de la misma entrega.
"""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "api" / "tests" / "unit" / "equipo"


def _cuerpo(funcion: ast.FunctionDef) -> list[ast.stmt]:
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
    """Huella del cuerpo, ignorando solo los nombres de variables locales."""
    cuerpo = _cuerpo(funcion)
    modulo = ast.Module(body=cuerpo, type_ignores=[])

    locales: set[str] = set()
    for argumento in (
        funcion.args.posonlyargs + funcion.args.args + funcion.args.kwonlyargs
    ):
        locales.add(argumento.arg)
    if funcion.args.vararg:
        locales.add(funcion.args.vararg.arg)
    if funcion.args.kwarg:
        locales.add(funcion.args.kwarg.arg)
    for nodo in ast.walk(modulo):
        if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store):
            locales.add(nodo.id)

    for nodo in ast.walk(modulo):
        if isinstance(nodo, ast.Name) and nodo.id in locales:
            nodo.id = "_v"
        elif isinstance(nodo, ast.arg) and nodo.arg in locales:
            nodo.arg = "_v"

    texto = ast.dump(modulo, annotate_fields=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _archivos() -> list[Path]:
    return sorted(
        archivo
        for archivo in BASE.rglob("test_*.py")
        if "__pycache__" not in archivo.parts
    )


def main() -> int:
    archivos = _archivos()
    if not archivos:
        print(f"[duplicados] No hay archivos en {BASE}")
        return 0

    nombres: dict[tuple[str, str], str] = {}
    firmas: dict[str, tuple[str, str]] = {}
    errores: list[str] = []
    total = 0

    for archivo in archivos:
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errores.append(f"{archivo.relative_to(BASE)}: error de sintaxis ({exc})")
            continue

        carpeta = archivo.parent.name

        for nodo in arbol.body:
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not nodo.name.startswith("test_"):
                continue

            total += 1
            clave_nombre = (carpeta, nodo.name)

            if clave_nombre in nombres:
                errores.append(
                    f"Nombre repetido en {carpeta}: {nodo.name} aparece en "
                    f"{nombres[clave_nombre]} y en {archivo.name}"
                )
            else:
                nombres[clave_nombre] = archivo.name

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
