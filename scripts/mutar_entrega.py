#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mide si las pruebas de una entrega detectan fallos inyectados.

Rompe el codigo asignado en puntos que cambian el comportamiento
(comparaciones, condiciones, ``and``/``or``, negaciones, numeros, retornos y
operaciones aritmeticas), ejecuta el archivo de la entrega contra cada rotura y
cuenta cuantas detecto.

Una rotura cuenta como detectada solo si pytest falla con codigo 1 (al menos una
prueba falla). Los errores de coleccion, los timeouts y los archivos que no se
pueden importar se descartan para no inflar el puntaje.

Uso:
    python scripts/mutar_entrega.py --integrante sebastian --ronda base
    python scripts/mutar_entrega.py --integrante kevin --ronda avanzada
    python scripts/mutar_entrega.py --todo
    python scripts/mutar_entrega.py --integrante dairon --detalle

El detalle de las roturas que sobrevivieron es para el responsable, no para el
integrante.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(RAIZ / "scripts"))
from especificaciones_entrega import ENTREGAS, POR_CLAVE, Ronda, iterar_rondas  # noqa: E402

MAX_MUTANTES_POR_SIMBOLO = 6
TIMEOUT_SEGUNDOS = 20


@dataclass
class Mutante:
    ruta: str
    linea: int
    descripcion: str
    fuente: str
    simbolo: str = ""
    pruebas: tuple[str, ...] = ()

    @property
    def huella(self) -> str:
        return hashlib.sha256(self.fuente.encode("utf-8")).hexdigest()


class _Mutador(ast.NodeTransformer):
    """Aplica una sola mutacion al nodo indicado."""

    def __init__(self, objetivo: ast.AST) -> None:
        self.objetivo = objetivo
        self.hecho = False

    def visit_Compare(self, nodo: ast.Compare) -> ast.AST:
        if nodo is not self.objetivo:
            self.generic_visit(nodo)
            return nodo
        inversos = {
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Lt: ast.GtE,
            ast.GtE: ast.Lt,
            ast.Gt: ast.LtE,
            ast.LtE: ast.Gt,
            ast.In: ast.NotIn,
            ast.NotIn: ast.In,
            ast.Is: ast.IsNot,
            ast.IsNot: ast.Is,
        }
        if not nodo.ops or type(nodo.ops[0]) not in inversos:
            return nodo
        nuevo = copy.deepcopy(nodo)
        nuevo.ops = [inversos[type(nodo.ops[0])]() for _ in nodo.ops]
        self.hecho = True
        return nuevo

    def visit_BoolOp(self, nodo: ast.BoolOp) -> ast.AST:
        if nodo is not self.objetivo:
            self.generic_visit(nodo)
            return nodo
        nuevo = copy.deepcopy(nodo)
        nuevo.op = ast.Or() if isinstance(nodo.op, ast.And) else ast.And()
        self.hecho = True
        return nuevo

    def visit_UnaryOp(self, nodo: ast.UnaryOp) -> ast.AST:
        if nodo is self.objetivo:
            self.hecho = True
            return ast.copy_location(nodo.operand, nodo)
        self.generic_visit(nodo)
        return nodo

    def visit_Constant(self, nodo: ast.Constant) -> ast.AST:
        if nodo is not self.objetivo:
            return nodo
        valor = nodo.value
        if isinstance(valor, bool):
            nuevo_valor = not valor
        elif isinstance(valor, int):
            nuevo_valor = valor + 1
        elif isinstance(valor, float):
            nuevo_valor = valor + 0.5
        else:
            return nodo
        self.hecho = True
        return ast.copy_location(ast.Constant(value=nuevo_valor), nodo)

    def visit_BinOp(self, nodo: ast.BinOp) -> ast.AST:
        if nodo is not self.objetivo:
            self.generic_visit(nodo)
            return nodo
        cambios = {
            ast.Add: ast.Sub,
            ast.Sub: ast.Add,
            ast.Mult: ast.Div,
            ast.Div: ast.Mult,
            ast.FloorDiv: ast.Mult,
        }
        if type(nodo.op) not in cambios:
            return nodo
        nuevo = copy.deepcopy(nodo)
        nuevo.op = cambios[type(nodo.op)]()
        self.hecho = True
        return nuevo

    def visit_Return(self, nodo: ast.Return) -> ast.AST:
        if nodo is self.objetivo:
            self.hecho = True
            return ast.copy_location(ast.Return(value=ast.Constant(value=None)), nodo)
        self.generic_visit(nodo)
        return nodo

    def visit_If(self, nodo: ast.If) -> ast.AST:
        if nodo is not self.objetivo:
            self.generic_visit(nodo)
            return nodo
        nuevo = copy.deepcopy(nodo)
        nuevo.test = ast.copy_location(
            ast.UnaryOp(op=ast.Not(), operand=nuevo.test), nodo.test
        )
        self.hecho = True
        return nuevo


def _pruebas_por_simbolo(archivo_rel: str) -> dict[str, tuple[str, ...]]:
    """Mapa ``simbolo -> pruebas que lo declaran en Cubre:``."""
    archivo = RAIZ / archivo_rel
    try:
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return {}
    mapa: dict[str, list[str]] = {}
    for nodo in arbol.body:
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not nodo.name.startswith("test_"):
            continue
        doc = ast.get_docstring(nodo) or ""
        for linea in doc.splitlines():
            if not linea.strip().startswith("Cubre:"):
                continue
            cubre = linea.split("Cubre:", 1)[1].strip()
            if "::" not in cubre:
                continue
            simbolo = cubre.split("::", 1)[1].strip()
            if simbolo:
                mapa.setdefault(simbolo, []).append(nodo.name)
    return {simbolo: tuple(pruebas) for simbolo, pruebas in mapa.items()}


def _nodos_cubiertos(arbol: ast.AST, simbolos: set[str]) -> list[int]:
    """Indices de ast.walk que pertenecen a los simbolos declarados."""
    if not simbolos:
        return list(range(len(list(ast.walk(arbol)))))

    permitidos: set[int] = set()
    for nodo in arbol.body:
        nombre = None
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombre = nodo.name
        elif isinstance(nodo, ast.Assign):
            for objetivo in nodo.targets:
                if isinstance(objetivo, ast.Name):
                    nombre = objetivo.id
                    break
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            nombre = nodo.target.id
        if nombre not in simbolos:
            continue
        for hijo in ast.walk(nodo):
            permitidos.add(id(hijo))

    return [i for i, nodo in enumerate(ast.walk(arbol)) if id(nodo) in permitidos]


def _objetivos(arbol: ast.AST, indices: list[int] | None = None) -> list[tuple[int, str]]:
    indices_permitidos = set(indices) if indices is not None else None
    objetivos: list[tuple[int, str]] = []
    for indice, nodo in enumerate(ast.walk(arbol)):
        if indices_permitidos is not None and indice not in indices_permitidos:
            continue
        if isinstance(nodo, ast.Compare):
            objetivos.append((indice, "comparacion invertida"))
        elif isinstance(nodo, ast.BoolOp):
            objetivos.append((indice, "and/or invertido"))
        elif isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, ast.Not):
            objetivos.append((indice, "negacion eliminada"))
        elif isinstance(nodo, ast.Constant) and isinstance(
            nodo.value, (bool, int, float)
        ):
            objetivos.append((indice, "constante alterada"))
        elif isinstance(nodo, ast.BinOp) and isinstance(
            nodo.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)
        ):
            objetivos.append((indice, "operacion aritmetica alterada"))
        elif isinstance(nodo, ast.Return) and nodo.value is not None:
            objetivos.append((indice, "return cambiado a None"))
        elif isinstance(nodo, ast.If):
            objetivos.append((indice, "condicion negada"))
    return objetivos


def _generar_mutantes(
    ruta_rel: str,
    simbolo: str,
    pruebas: tuple[str, ...],
) -> list[Mutante]:
    original = (RAIZ / ruta_rel).read_text(encoding="utf-8")
    arbol = ast.parse(original)
    indices = _nodos_cubiertos(arbol, {simbolo})

    mutantes: list[Mutante] = []
    vistos: set[str] = set()

    for indice, descripcion in _objetivos(arbol, indices):
        fresco = ast.parse(original)
        nodos = list(ast.walk(fresco))
        if indice >= len(nodos):
            continue
        objetivo = nodos[indice]
        linea = getattr(objetivo, "lineno", 0)

        mutador = _Mutador(objetivo)
        nuevo_arbol = mutador.visit(fresco)
        if not mutador.hecho:
            continue
        if ast.dump(nuevo_arbol) == ast.dump(arbol):
            continue
        try:
            fuente = ast.unparse(nuevo_arbol)
        except Exception:  # pragma: no cover - defensivo
            continue
        mutante = Mutante(
            ruta=ruta_rel,
            linea=linea,
            descripcion=descripcion,
            fuente=fuente,
            simbolo=simbolo,
            pruebas=pruebas,
        )
        if mutante.huella in vistos:
            continue
        vistos.add(mutante.huella)
        mutantes.append(mutante)

    return mutantes


def _muestrear(mutantes: list[Mutante], maximo: int) -> list[Mutante]:
    if len(mutantes) <= maximo:
        return mutantes
    paso = len(mutantes) / maximo
    return [mutantes[int(i * paso)] for i in range(maximo)]


def _ejecutar(archivo_rel: str, pruebas: tuple[str, ...]) -> int | str:
    nodos = [f"{archivo_rel}::{prueba}" for prueba in pruebas]
    comando = [
        sys.executable,
        "-m",
        "pytest",
        *nodos,
        "-q",
        "-x",
        "--tb=no",
        "--disable-warnings",
        "-p",
        "no:cacheprovider",
    ]
    try:
        resultado = subprocess.run(
            comando,
            cwd=RAIZ,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    return resultado.returncode


def _evaluar_archivo(
    entrega_clave: str,
    ronda: Ronda,
    detalle: bool,
) -> tuple[bool, dict]:
    entrega = POR_CLAVE[entrega_clave]
    archivo_rel = f"{entrega.ruta_carpeta}/{ronda.archivo}"
    archivo = RAIZ / archivo_rel

    if not archivo.exists():
        print(f"[mutacion] {entrega_clave}:{ronda.clave}: no existe {archivo_rel}")
        return False, {"integrante": entrega_clave, "ronda": ronda.clave, "error": "sin archivo"}

    mutantes: list[Mutante] = []
    pruebas_por_simbolo = _pruebas_por_simbolo(archivo_rel)
    for modulo in ronda.modulos:
        for simbolo, pruebas in pruebas_por_simbolo.items():
            generados = _generar_mutantes(modulo, simbolo, pruebas)
            mutantes.extend(_muestrear(generados, MAX_MUTANTES_POR_SIMBOLO))

    if not mutantes:
        print(f"[mutacion] {entrega_clave}:{ronda.clave}: no se generaron roturas")
        return False, {"integrante": entrega_clave, "ronda": ronda.clave, "error": "sin roturas"}

    print(
        f"[mutacion] {entrega_clave}:{ronda.clave}: {len(mutantes)} roturas "
        f"en {len(pruebas_por_simbolo)} simbolo(s)"
    )

    detectados = 0
    invalidos = 0
    sobrevivientes: list[Mutante] = []

    for indice, mutante in enumerate(mutantes, start=1):
        ruta_abs = RAIZ / mutante.ruta
        respaldo = ruta_abs.read_bytes()
        respaldo_hash = hashlib.sha256(respaldo).hexdigest()
        try:
            ruta_abs.write_text(mutante.fuente + "\n", encoding="utf-8")
            codigo = _ejecutar(archivo_rel, mutante.pruebas)
        finally:
            ruta_abs.write_bytes(respaldo)
            if hashlib.sha256(ruta_abs.read_bytes()).hexdigest() != respaldo_hash:
                raise RuntimeError(f"No se pudo restaurar {mutante.ruta}")

        print(f"  rotura {indice}/{len(mutantes)}", end="\r")

        if codigo == "TIMEOUT":
            invalidos += 1
        elif codigo == 0:
            sobrevivientes.append(mutante)
        elif codigo == 1:
            detectados += 1
        else:
            invalidos += 1

    print(" " * 48, end="\r")
    validos = len(mutantes) - invalidos
    if validos == 0:
        print(f"[mutacion] {entrega_clave}:{ronda.clave}: no hubo roturas validas")
        return False, {
            "integrante": entrega_clave,
            "ronda": ronda.clave,
            "error": "sin roturas validas",
        }

    proporcion = detectados / validos
    aprobado = (
        detectados >= ronda.mutacion_absoluta
        and proporcion >= ronda.mutacion_minima
    )

    print(
        f"[mutacion] {entrega_clave}:{ronda.clave}: detecto {detectados} de "
        f"{validos} roturas ({proporcion:.0%}); minimo "
        f"{ronda.mutacion_minima:.0%} y {ronda.mutacion_absoluta} absolutas"
    )

    if detalle:
        for mutante in sobrevivientes:
            print(
                f"  - sin detectar: {mutante.ruta}:{mutante.linea} "
                f"({mutante.descripcion})"
            )

    if not aprobado:
        print(f"[mutacion] {entrega_clave}:{ronda.clave}: NO CUMPLE")
    else:
        print(f"[mutacion] {entrega_clave}:{ronda.clave}: OK")

    resultado = {
        "integrante": entrega_clave,
        "ronda": ronda.clave,
        "archivo": archivo_rel,
        "roturas": len(mutantes),
        "validas": validos,
        "detectadas": detectados,
        "proporcion": round(proporcion, 4),
        "minimo": ronda.mutacion_minima,
        "minimo_absoluto": ronda.mutacion_absoluta,
        "aprobado": aprobado,
        "sobrevivientes": [asdict(m) | {"fuente": ""} for m in sobrevivientes],
    }

    return aprobado, resultado


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrante", choices=sorted(POR_CLAVE))
    parser.add_argument("--ronda", choices=("base", "avanzada"))
    parser.add_argument(
        "--todo",
        action="store_true",
        help="Evalua todas las rondas cuyo archivo exista.",
    )
    parser.add_argument("--detalle", action="store_true")
    parser.add_argument("--json-salida", type=Path)
    args = parser.parse_args()

    if not args.integrante and not args.todo:
        parser.error("indica --integrante o --todo")

    resultados = []
    for entrega, ronda in _seleccion(args.integrante, args.ronda):
        archivo = RAIZ / entrega.ruta_carpeta / ronda.archivo
        if args.todo and not archivo.exists():
            continue
        aprobado, resultado = _evaluar_archivo(
            entrega.clave, ronda, args.detalle
        )
        resultados.append((aprobado, resultado))

    if not resultados:
        print("[mutacion] No hay archivos para evaluar.")
        return 1

    if args.json_salida:
        args.json_salida.parent.mkdir(parents=True, exist_ok=True)
        args.json_salida.write_text(
            json.dumps(
                [resultado for _aprobado, resultado in resultados],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    fallos = [r for ok, r in resultados if not ok]
    print(
        f"[mutacion] Resumen: {len(resultados) - len(fallos)}/{len(resultados)} "
        "rondas cumplen."
    )
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
