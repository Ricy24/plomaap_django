#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera el Excel de entrega con las pruebas que ya cumplieron todo.

Para cada ronda con archivo:

  1. valida el contrato (scripts/check_entrega_equipo.py);
  2. ejecuta sus pruebas;
  3. mide si detecta las roturas (scripts/mutar_entrega.py);
  4. solo si todo pasa, agrega sus filas al Excel.

El Excel de entrada nunca se modifica: el resultado se escribe en ``--salida``.

Uso:
    python scripts/informe_entrega.py --salida informe.xlsx
    python scripts/informe_entrega.py --integrante sebastian --ronda base --salida informe.xlsx
    python scripts/informe_entrega.py --todo --salida informe.xlsx
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / "docs" / "pruebas" / "Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx"

sys.path.insert(0, str(RAIZ / "scripts"))
from check_entrega_equipo import validar_ronda  # noqa: E402
from especificaciones_entrega import ENTREGAS, POR_CLAVE, Ronda  # noqa: E402
from mutar_entrega import _evaluar_archivo  # noqa: E402


def _campo(doc: str, etiqueta: str) -> str:
    for linea in doc.splitlines():
        if linea.strip().startswith(etiqueta):
            return linea.split(etiqueta, 1)[1].strip()
    return ""


def _pruebas_del_archivo(archivo: Path) -> list[dict]:
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
                "entrada": _campo(doc, "Entrada:"),
                "esperado": _campo(doc, "Esperado:"),
                "cubre": _campo(doc, "Cubre:"),
            }
        )
    return datos


def _ejecutar_pruebas(archivo_rel: str) -> bool:
    comando = [
        sys.executable,
        "-m",
        "pytest",
        archivo_rel,
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    return subprocess.run(comando, cwd=RAIZ).returncode == 0


def _ultimo_numero(ws) -> int:
    for fila in range(ws.max_row, 7, -1):
        valor = ws.cell(fila, 1).value
        if isinstance(valor, str):
            coincidencia = re.match(r"UNIT-(\d+)", valor)
            if coincidencia:
                return int(coincidencia.group(1))
    return 0


def _actualizar_formulas(ws, control, total: int) -> None:
    ultima = 7 + total
    for fila in ws.iter_rows():
        for celda in fila:
            if isinstance(celda.value, str) and celda.value.startswith("="):
                celda.value = re.sub(r"A8:A\d+", f"A8:A{ultima}", celda.value)
                celda.value = re.sub(r"I8:I\d+", f"I8:I{ultima}", celda.value)
                celda.value = re.sub(r"J8:J\d+", f"J8:J{ultima}", celda.value)

    for fila in control.iter_rows():
        for celda in fila:
            if isinstance(celda.value, str) and celda.value.startswith("="):
                celda.value = re.sub(
                    r"'Pruebas Unitarias'!A8:A\d+",
                    f"'Pruebas Unitarias'!A8:A{ultima}",
                    celda.value,
                )
                celda.value = re.sub(
                    r"'Pruebas Unitarias'!I8:I\d+",
                    f"'Pruebas Unitarias'!I8:I{ultima}",
                    celda.value,
                )


def _rehacer_validaciones(ws, total: int) -> None:
    ultima = 7 + total

    ws.data_validations.dataValidation = []
    ws.conditional_formatting = ConditionalFormattingList()

    dv_estado = DataValidation(
        type="list",
        formula1='"Exitoso,Falló,Bloqueado,Pendiente"',
        allow_blank=True,
    )
    dv_estado.add(f"I8:I{ultima}")
    ws.add_data_validation(dv_estado)

    dv_sev = DataValidation(type="list", formula1='"Alta,Media,Baja"', allow_blank=True)
    dv_sev.add(f"J8:J{ultima}")
    ws.add_data_validation(dv_sev)

    ws.conditional_formatting.add(
        f"I8:I{ultima}",
        CellIsRule(
            operator="equal",
            formula=['"Exitoso"'],
            fill=PatternFill("solid", fgColor="FFC6EFCE"),
            font=Font(color="FF006100"),
        ),
    )


def _precondicion(ronda: Ronda) -> str:
    solo_utils = all(modulo.startswith("api/utils/") for modulo in ronda.modulos)
    if solo_utils:
        return "Sin base de datos ni servidor."
    return "SQLite en memoria o PostgreSQL/MySQL de pruebas."


def _registrar(ws, archivo: Path, archivo_rel: str, responsable: str, ronda: Ronda) -> int:
    pruebas = _pruebas_del_archivo(archivo)
    ultima_actual = ws.max_row
    numero = _ultimo_numero(ws)

    for indice, prueba in enumerate(pruebas, start=1):
        fila = ultima_actual + indice
        numero += 1
        valores = {
            1: f"UNIT-{numero:03d}",
            2: prueba["caso"] or prueba["nombre"],
            3: _precondicion(ronda),
            4: prueba["entrada"],
            5: (
                f"1. Ejecutar: pytest {archivo_rel}::{prueba['nombre']}\n"
                "2. Verificar el resultado esperado."
            ),
            6: prueba["esperado"],
            7: "Aprobado: passed en la suite del equipo.",
            8: "Caja Blanca (unitaria)",
            9: "Exitoso",
            10: "Alta" if "seguridad" in archivo.name or ronda.clave == "avanzada" else "Media",
            11: f"{archivo_rel}::{prueba['nombre']} -> 1 passed",
            12: (
                f"Sin defectos. Entrega de {responsable} "
                f"(ronda {ronda.clave})."
            ),
            13: responsable,
        }

        for columna, valor in valores.items():
            celda = ws.cell(fila, columna, valor)
            celda._style = copy(ws.cell(ultima_actual, columna)._style)

        ws.row_dimensions[fila].height = 78

    return numero


def _ya_registrado(ws, archivo_rel: str) -> bool:
    objetivo = archivo_rel.replace("\\", "/")
    for fila in range(8, ws.max_row + 1):
        evidencia = ws.cell(fila, 11).value
        if evidencia and objetivo in str(evidencia).replace("\\", "/"):
            return True
    return False


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


def generar(integrante: str | None, ronda: str | None, salida: Path) -> int:
    wb = load_workbook(BASE)
    ws = wb["Pruebas Unitarias"]
    control = wb["Control y Resumen"]

    registrados: list[str] = []

    for entrega, item in _seleccion(integrante, ronda):
        archivo_rel = f"{entrega.ruta_carpeta}/{item.archivo}"
        archivo = RAIZ / archivo_rel
        etiqueta = f"{entrega.clave}:{item.clave}"

        if not archivo.exists():
            print(f"[informe] {etiqueta}: sin entrega.")
            continue

        if _ya_registrado(ws, archivo_rel):
            print(f"[informe] {etiqueta}: ya estaba registrado.")
            continue

        print(f"[informe] {etiqueta}: validando contrato ...")
        errores = validar_ronda(entrega.clave, item.clave)
        if errores:
            print(f"[informe] {etiqueta}: no cumple el contrato.")
            for error in errores:
                print(f"  - {error}")
            continue

        print(f"[informe] {etiqueta}: ejecutando pruebas ...")
        if not _ejecutar_pruebas(archivo_rel):
            print(f"[informe] {etiqueta}: las pruebas no pasan.")
            continue

        print(f"[informe] {etiqueta}: midiendo deteccion de fallos ...")
        aprobado, _ = _evaluar_archivo(entrega.clave, item, False)
        if not aprobado:
            print(f"[informe] {etiqueta}: no detecta suficientes fallos.")
            continue

        _registrar(ws, archivo, archivo_rel, entrega.responsable, item)
        registrados.append(entrega.responsable)

    total = _ultimo_numero(ws)
    _actualizar_formulas(ws, control, total)
    _rehacer_validaciones(ws, total)

    ws["A6"] = (
        f"ENTREGA ACTUAL: {total} PRUEBAS UNITARIAS registradas "
        f"(UNIT-001 a UNIT-{total:03d}). Cada fila indica el integrante responsable."
    )

    if registrados:
        equipo = control["C6"].value or ""
        for responsable in registrados:
            if responsable not in equipo:
                equipo = f"{equipo}, {responsable}"
        control["C6"] = equipo.strip(", ")

    wb.calculation.fullCalcOnLoad = True
    salida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(salida)

    print(f"[informe] Excel generado: {salida} ({total} filas de prueba).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrante", choices=sorted(POR_CLAVE))
    parser.add_argument("--ronda", choices=("base", "avanzada"))
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "informe_entrega.xlsx"),
        help="Ruta del Excel de salida.",
    )
    parser.add_argument(
        "--copiar-base",
        action="store_true",
        help="Copia el Excel base sin validar entregas.",
    )
    args = parser.parse_args()

    salida = Path(args.salida)
    if args.copiar_base:
        salida.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE, salida)
        print(f"[informe] Copia del Excel base: {salida}")
        return 0

    return generar(args.integrante, args.ronda, salida)


if __name__ == "__main__":
    sys.exit(main())
