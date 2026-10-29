#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera una defensa oral aleatoria para una entrega.

El objetivo es que el integrante explique sus propias pruebas sin leerlas. El
script elige pruebas al azar y arma preguntas sobre el caso, el dato de entrada,
el resultado esperado y el simbolo cubierto. No conoce ni muestra la respuesta:
solo la pregunta.

Uso:
    python scripts/defensa_entrega.py --integrante sebastian
    python scripts/defensa_entrega.py --integrante kevin --ronda avanzada --preguntas 5
    python scripts/defensa_entrega.py --todo --salida defensa.md
"""
from __future__ import annotations

import argparse
import ast
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(RAIZ / "scripts"))
from especificaciones_entrega import ENTREGAS, POR_CLAVE  # noqa: E402

PREGUNTAS = (
    "¿Qué comportamiento del codigo demuestra `{test}` y por que ese dato de entrada?",
    "En `{test}`, ¿que pasaria si el valor de entrada cambiara a un caso limite?",
    "¿Que simbolo cubre `{test}` ({cubre}) y que rama del codigo ejercita?",
    "Si `{test}` fallara en PostgreSQL pero pasara en SQLite, ¿que revisarias primero?",
    "¿Por que `{test}` no es una copia de otra prueba del equipo?",
    "Explica el assert de `{test}` sin mirar el archivo.",
)


def _campo(doc: str, etiqueta: str) -> str:
    for linea in doc.splitlines():
        if linea.strip().startswith(etiqueta):
            return linea.split(etiqueta, 1)[1].strip()
    return ""


def _pruebas(archivo: Path) -> list[dict]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    datos = []
    for nodo in arbol.body:
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not nodo.name.startswith("test_"):
            continue
        doc = ast.get_docstring(nodo) or ""
        datos.append(
            {
                "nombre": nodo.name,
                "caso": _campo(doc, "Caso:"),
                "cubre": _campo(doc, "Cubre:"),
            }
        )
    return datos


def _seleccion(integrante: str | None, ronda: str | None):
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
            yield entrega, item


def generar(integrante: str | None, ronda: str | None, cantidad: int, semilla: int) -> str:
    azar = random.Random(semilla)
    lineas: list[str] = ["# Defensa oral de la entrega", ""]
    encontrado = False

    for entrega, item in _seleccion(integrante, ronda):
        archivo = RAIZ / entrega.ruta_carpeta / item.archivo
        if not archivo.exists():
            continue
        encontrado = True
        pruebas = _pruebas(archivo)
        if not pruebas:
            continue
        elegidas = azar.sample(pruebas, min(cantidad, len(pruebas)))
        plantillas = azar.sample(PREGUNTAS, min(len(elegidas), len(PREGUNTAS)))
        lineas.append(f"## {entrega.responsable} · ronda {item.clave}")
        lineas.append("")
        lineas.append(f"Archivo: `{entrega.ruta_carpeta}/{item.archivo}`")
        lineas.append("")
        for indice, prueba in enumerate(elegidas, start=1):
            plantilla = plantillas[(indice - 1) % len(plantillas)]
            pregunta = plantilla.format(
                test=prueba["nombre"],
                cubre=prueba["cubre"] or "sin Cubre",
            )
            lineas.append(f"{indice}. {pregunta}")
            if prueba["caso"]:
                lineas.append(f"   - Caso declarado: {prueba['caso']}")
            lineas.append("")

    if not encontrado:
        return "# Defensa oral\n\nNo hay archivos de entrega para evaluar.\n"

    lineas.append("## Criterio")
    lineas.append("")
    lineas.append(
        "Se aprueba solo si responde sin abrir el archivo, justifica los datos "
        "elegidos y explica que rama del codigo cubre cada prueba."
    )
    return "\n".join(lineas) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrante", choices=sorted(POR_CLAVE))
    parser.add_argument("--ronda", choices=("base", "avanzada"))
    parser.add_argument("--preguntas", type=int, default=3)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--salida", type=Path)
    parser.add_argument("--todo", action="store_true")
    args = parser.parse_args()

    if not args.integrante and not args.todo:
        parser.error("indica --integrante o --todo")

    texto = generar(args.integrante, args.ronda, args.preguntas, args.semilla)
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto, encoding="utf-8")
        print(f"[defensa] Generado: {args.salida}")
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
