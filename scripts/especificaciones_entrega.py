#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fuente unica de verdad de las entregas de pruebas del equipo.

Cada integrante tiene una carpeta propia y dos rondas:

* ``base``     : 10 pruebas de dominio, ya sea entregadas o pendientes.
* ``avanzada`` : 5 pruebas de mayor dificultad sobre modulos con mas ramas.

Los nombres de las pruebas son publicos; los resultados esperados no. El
integrante debe deducirlos leyendo el codigo. La solucion de referencia vive
fuera del repositorio, en una carpeta privada local.

Este modulo lo usan:

* ``scripts/check_entrega_equipo.py``
* ``scripts/mutar_entrega.py``
* ``scripts/informe_entrega.py``
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ronda:
    clave: str
    archivo: str
    modulos: tuple[str, ...]
    pruebas: tuple[str, ...]
    estado: str
    max_lineas: int = 25
    min_simbolos: int = 3
    mutacion_minima: float = 0.60
    mutacion_absoluta: int = 6

    @property
    def pendiente(self) -> bool:
        return self.estado == "pendiente"


@dataclass(frozen=True)
class Entrega:
    clave: str
    responsable: str
    carpeta: str
    rondas: tuple[Ronda, ...]

    def ronda(self, clave: str) -> Ronda:
        for ronda in self.rondas:
            if ronda.clave == clave:
                return ronda
        raise KeyError(f"{self.clave} no tiene la ronda {clave}")

    @property
    def ruta_carpeta(self) -> str:
        return f"api/tests/unit/equipo/{self.carpeta}"


ENTREGAS: tuple[Entrega, ...] = (
    Entrega(
        clave="andres",
        responsable="Andrés Durán",
        carpeta="integrante_1_validaciones",
        rondas=(
            Ronda(
                clave="base",
                archivo="test_integrante_1_validaciones.py",
                modulos=("api/utils/validators.py",),
                pruebas=(
                    "test_email_valido",
                    "test_email_sin_arroba_es_invalido",
                    "test_password_de_ocho_caracteres_es_valida",
                    "test_password_corta_es_invalida",
                    "test_telefono_valido",
                    "test_telefono_con_letras_es_invalido",
                    "test_nombre_de_un_caracter_es_invalido",
                    "test_fecha_y_hora_validas",
                    "test_fecha_con_formato_incorrecto_es_invalida",
                    "test_rol_valido",
                ),
                estado="entregado",
            ),
            Ronda(
                clave="avanzada",
                archivo="test_reto_avanzado.py",
                modulos=(
                    "api/services/hybrid_search_service.py",
                    "api/utils/request_utils.py",
                ),
                pruebas=(
                    "test_normalizacion_quita_tildes_y_signos",
                    "test_sinonimo_de_activo_lo_detecta",
                    "test_sintoma_suma_afinidad_al_puntaje_lexico",
                    "test_busqueda_sin_texto_lista_todos_los_servicios",
                    "test_filtro_categoria_ignora_mayusculas",
                ),
                estado="pendiente",
                max_lineas=32,
                min_simbolos=4,
                mutacion_minima=0.70,
                mutacion_absoluta=8,
            ),
        ),
    ),
    Entrega(
        clave="sebastian",
        responsable="Sebastián Samacá",
        carpeta="integrante_2_seguridad",
        rondas=(
            Ronda(
                clave="base",
                archivo="test_integrante_2_seguridad.py",
                modulos=(
                    "api/utils/jwt_utils.py",
                    "api/utils/decorators.py",
                ),
                pruebas=(
                    "test_token_lleva_el_id_como_texto",
                    "test_token_con_firma_alterada_se_descarta",
                    "test_token_vencido_se_descarta",
                    "test_esquema_bearer_ignora_mayusculas",
                    "test_token_sin_esquema_se_acepta",
                    "test_identidad_no_numerica_devuelve_none",
                    "test_token_de_usuario_inexistente_responde_401",
                    "test_usuario_inactivo_responde_401",
                    "test_tecnico_no_entra_a_vista_de_admin",
                    "test_cliente_no_entra_a_vista_de_tecnico",
                ),
                estado="pendiente",
            ),
            Ronda(
                clave="avanzada",
                archivo="test_reto_avanzado.py",
                modulos=(
                    "api/services/embedding_service.py",
                    "api/utils/decorators.py",
                ),
                pruebas=(
                    "test_coseno_es_cero_si_cambia_la_dimension",
                    "test_coseno_es_cero_con_vector_nulo",
                    "test_parse_vector_acepta_texto_json",
                    "test_admin_inactivo_recibe_403",
                    "test_jwt_optional_con_token_vencido_no_lanza",
                ),
                estado="pendiente",
                max_lineas=32,
                min_simbolos=4,
                mutacion_minima=0.70,
                mutacion_absoluta=8,
            ),
        ),
    ),
    Entrega(
        clave="dairon",
        responsable="Dairon Salazar",
        carpeta="integrante_3_citas",
        rondas=(
            Ronda(
                clave="base",
                archivo="test_integrante_3_citas.py",
                modulos=("api/services/appointment_service.py",),
                pruebas=(
                    "test_pendiente_puede_pasar_a_agendada",
                    "test_agendada_puede_pasar_a_en_progreso",
                    "test_cita_completada_no_puede_cancelarse",
                    "test_cita_cancelada_no_puede_reabrirse",
                    "test_fecha_invalida_no_genera_horarios",
                    "test_usuario_que_no_es_tecnico_no_tiene_horarios",
                    "test_jornada_laboral_genera_diez_franjas",
                    "test_hora_ocupada_no_se_ofrece",
                    "test_tecnico_libre_esta_disponible",
                    "test_tecnico_fuera_de_horario_no_esta_disponible",
                ),
                estado="entregado",
            ),
            Ronda(
                clave="avanzada",
                archivo="test_reto_avanzado.py",
                modulos=(
                    "api/services/appointment_service.py",
                    "api/services/recommendation_service.py",
                ),
                pruebas=(
                    "test_slots_inteligentes_aplican_buffer_de_treinta_minutos",
                    "test_slots_inteligentes_ajustan_fin_a_la_duracion",
                    "test_slots_inteligentes_clasifican_tarde_y_noche",
                    "test_recomendacion_penaliza_servicio_reciente",
                    "test_recomendacion_no_penaliza_reserva_antigua",
                ),
                estado="pendiente",
                max_lineas=32,
                min_simbolos=2,
                mutacion_minima=0.70,
                mutacion_absoluta=8,
            ),
        ),
    ),
    Entrega(
        clave="kevin",
        responsable="Kevin Pinzón",
        carpeta="integrante_4_datos",
        rondas=(
            Ronda(
                clave="base",
                archivo="test_integrante_4_datos.py",
                modulos=(
                    "api/services/profile_service.py",
                    "api/services/event_service.py",
                ),
                pruebas=(
                    "test_decimal_entero_se_guarda_como_entero",
                    "test_decimal_con_fraccion_conserva_decimales",
                    "test_fecha_se_guarda_en_iso",
                    "test_segundo_registro_actualiza_sin_duplicar",
                    "test_fuente_fuera_del_catalogo_es_rechazada",
                    "test_confianza_fuera_de_rango_es_rechazada",
                    "test_eliminar_atributos_devuelve_la_cantidad",
                    "test_evento_invalido_no_lanza_sin_strict",
                    "test_evento_invalido_lanza_en_strict",
                    "test_metadata_vacia_se_guarda_como_dict",
                ),
                estado="pendiente",
            ),
            Ronda(
                clave="avanzada",
                archivo="test_reto_avanzado.py",
                modulos=(
                    "api/services/profile_service.py",
                    "api/services/event_service.py",
                ),
                pruebas=(
                    "test_normalizacion_decimal_negativo_conserva_signo",
                    "test_normalizacion_recorre_listas_y_diccionarios",
                    "test_upsert_no_duplica_filas",
                    "test_borrado_solo_afecta_la_entidad_indicada",
                    "test_evento_valido_guarda_sesion_y_metadata",
                ),
                estado="pendiente",
                max_lineas=32,
                min_simbolos=4,
                mutacion_minima=0.70,
                mutacion_absoluta=8,
            ),
        ),
    ),
)


POR_CLAVE = {entrega.clave: entrega for entrega in ENTREGAS}


def ruta_archivo(entrega: Entrega, ronda: Ronda) -> str:
    return f"{entrega.ruta_carpeta}/{ronda.archivo}"


def iterar_rondas(estado: str | None = None):
    for entrega in ENTREGAS:
        for ronda in entrega.rondas:
            if estado is None or ronda.estado == estado:
                yield entrega, ronda
