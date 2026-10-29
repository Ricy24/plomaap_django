#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Valida la entrega pendiente de los integrantes 2 y 4.

Si el archivo todavía no existe, lo reporta como pendiente y no falla. Cuando
existe, exige el formato definido en
docs/pruebas/ESPECIFICACION_PRUEBAS_PENDIENTES.md:

  - exactamente 10 pruebas;
  - docstring con Caso / Entrada / Esperado / Cubre;
  - Cubre: ruta::simbolo, con la ruta permitida y el símbolo existente;
  - al menos un assert real (no `assert True`);
  - pytestmark = pytest.mark.unit;
  - un mínimo de símbolos distintos cubiertos.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EQUIPO = RAIZ / "api" / "tests" / "unit" / "equipo"

REGLAS = {
    "test_integrante_2_seguridad.py": {
        "responsable": "Sebastián Samacá",
        "modulos": {
            "api/utils/jwt_utils.py",
            "api/utils/decorators.py",
        },
        "min_simbolos": 4,
    },
    "test_integrante_4_datos.py": {
        "responsable": "Kevin Pinzón",
        "modulos": {
            "api/services/profile_service.py",
            "api/services/event_service.py",
            "api/services/recommendation_service.py",
        },
        "min_simbolos": 6,
    },
}

ETIQUETAS = ("Caso:", "Entrada:", "Esperado:", "Cubre:")


def _simbolos_de(ruta: Path) -> set[str]:
    """Nombres definidos a nivel de módulo en un archivo Python."""
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


def _asserts_reales(funcion: ast.FunctionDef) -> bool:
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Assert):
            valor = nodo.test
            if isinstance(valor, ast.Constant) and valor.value in (True, 1):
                continue
            if isinstance(valor, ast.Name) and valor.id in {"True", "False"}:
                continue
            return True
    return False


def _validar_archivo(archivo: Path, regla: dict) -> list[str]:
    errores: list[str] = []
    texto = archivo.read_text(encoding="utf-8")

    if "pytestmark = pytest.mark.unit" not in texto:
        errores.append("falta `pytestmark = pytest.mark.unit`")

    arbol = ast.parse(texto)
    pruebas = [
        nodo
        for nodo in arbol.body
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
        and nodo.name.startswith("test_")
    ]

    if len(pruebas) != 10:
        errores.append(f"debe tener exactamente 10 pruebas, tiene {len(pruebas)}")

    simbolos_cubiertos: set[str] = set()

    for funcion in pruebas:
        doc = ast.get_docstring(funcion) or ""
        faltantes = [e for e in ETIQUETAS if e not in doc]
        if faltantes:
            errores.append(
                f"{funcion.name}: falta en el docstring {', '.join(faltantes)}"
            )
            continue

        linea_cubre = next(
            (l.strip() for l in doc.splitlines() if l.strip().startswith("Cubre:")), ""
        )
        valor = linea_cubre.split("Cubre:", 1)[1].strip()
        if "::" not in valor:
            errores.append(f"{funcion.name}: `Cubre:` debe ser ruta::simbolo")
            continue

        ruta_txt, simbolo = valor.split("::", 1)
        ruta_txt = ruta_txt.strip().replace("\\", "/")
        simbolo = simbolo.strip()

        if ruta_txt not in regla["modulos"]:
            errores.append(
                f"{funcion.name}: `Cubre:` apunta a {ruta_txt}, que no es un "
                f"módulo asignado"
            )
            continue

        ruta = RAIZ / ruta_txt
        if not ruta.exists():
            errores.append(f"{funcion.name}: no existe {ruta_txt}")
            continue

        if simbolo not in _simbolos_de(ruta):
            errores.append(
                f"{funcion.name}: `{simbolo}` no existe en {ruta_txt}"
            )
            continue

        simbolos_cubiertos.add(simbolo)

        if not _asserts_reales(funcion):
            errores.append(f"{funcion.name}: no tiene un assert real")

    if len(simbolos_cubiertos) < regla["min_simbolos"]:
        errores.append(
            f"debe cubrir al menos {regla['min_simbolos']} símbolos distintos, "
            f"cubre {len(simbolos_cubiertos)}"
        )

    return errores


def main() -> int:
    pendientes = 0
    fallos = 0

    for nombre, regla in REGLAS.items():
        archivo = EQUIPO / nombre
        if not archivo.exists():
            pendientes += 1
            print(f"[entrega] PENDIENTE: {nombre} ({regla['responsable']})")
            continue

        print(f"[entrega] Revisando {nombre} ({regla['responsable']})")
        errores = _validar_archivo(archivo, regla)
        if errores:
            fallos += 1
            for error in errores:
                print(f"  - {error}")
        else:
            print("  OK: cumple la especificación")

    if fallos:
        print(
            "\n[entrega] La entrega no cumple. Revisa "
            "docs/pruebas/ESPECIFICACION_PRUEBAS_PENDIENTES.md"
        )
        return 1

    if pendientes == len(REGLAS):
        print("[entrega] Sin entregas nuevas: no hay nada que validar todavía")
    return 0


if __name__ == "__main__":
    sys.exit(main())
