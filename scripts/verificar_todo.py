#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ejecuta localmente todo lo que el pipeline exige antes de subir.

Pasos:

  1. pruebas duplicadas;
  2. contrato de las entregas existentes;
  3. suite unitaria;
  4. cobertura de api/utils + api/services;
  5. pruebas de integracion (se omiten si no hay PostgreSQL configurado);
  6. roturas de todas las entregas presentes;
  7. lint y formato (ruff) y seguridad (bandit), si estan instalados.

Uso:
    python scripts/verificar_todo.py
    python scripts/verificar_todo.py --rapido        # sin integracion ni mutacion
    python scripts/verificar_todo.py --sin-mutacion
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable


def _run(nombre: str, comando: list[str], obligatorio: bool = True) -> bool:
    print(f"\n=== {nombre} ===")
    print(" ".join(comando))
    inicio = time.time()
    resultado = subprocess.run(comando, cwd=RAIZ)
    duracion = time.time() - inicio
    if resultado.returncode == 0:
        print(f"[ok] {nombre} ({duracion:.1f}s)")
        return True
    print(f"[fallo] {nombre} ({duracion:.1f}s)")
    return not obligatorio


def _existe(nombre: str) -> bool:
    if shutil.which(nombre):
        return True
    sufijo = ".exe" if sys.platform == "win32" else ""
    return (Path(PY).parent / f"{nombre}{sufijo}").exists()


def _comando_herramienta(nombre: str, *args: str) -> list[str]:
    if shutil.which(nombre):
        return [nombre, *args]
    sufijo = ".exe" if sys.platform == "win32" else ""
    return [str(Path(PY).parent / f"{nombre}{sufijo}"), *args]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rapido", action="store_true")
    parser.add_argument("--sin-mutacion", action="store_true")
    args = parser.parse_args()

    pasos: list[tuple[str, list[str], bool]] = [
        (
            "duplicados",
            [PY, "scripts/check_test_duplicates.py"],
            True,
        ),
        (
            "contrato de entregas",
            [PY, "scripts/check_entrega_equipo.py"],
            True,
        ),
        (
            "suite unitaria",
            [PY, "-m", "pytest", "-m", "unit", "-q"],
            True,
        ),
        (
            "cobertura",
            [
                PY,
                "-m",
                "coverage",
                "run",
                "--source=api/utils,api/services",
                "-m",
                "pytest",
                "-m",
                "unit",
                "-q",
            ],
            True,
        ),
        (
            "cobertura minima",
            [PY, "-m", "coverage", "report", "--fail-under=100", "-m"],
            True,
        ),
    ]

    if not args.rapido:
        pasos.append(
            (
                "integracion",
                [PY, "-m", "pytest", "-m", "integration", "-q"],
                False,
            )
        )
        if not args.sin_mutacion:
            pasos.append(
                (
                    "roturas",
                    [PY, "scripts/mutar_entrega.py", "--todo"],
                    True,
                )
            )

    if _existe("ruff"):
        pasos.append(("ruff check", _comando_herramienta("ruff", "check", "."), True))

    if _existe("bandit"):
        pasos.append(
            (
                "bandit",
                _comando_herramienta(
                    "bandit", "-q", "-r", "api", "-x", "api/tests,api/migrations", "-lll"
                ),
                False,
            )
        )

    fallos = 0
    for nombre, comando, obligatorio in pasos:
        if not _run(nombre, comando, obligatorio):
            fallos += 1

    print("\n=== resumen ===")
    if fallos:
        print(f"{fallos} paso(s) fallaron.")
        return 1
    print("Todo en verde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
