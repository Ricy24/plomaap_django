# Reto avanzado · ronda 2

Cada integrante entrega **5 pruebas adicionales** en su propia carpeta. Esta
ronda es más difícil: los módulos tienen más ramas, estados y efectos en base de
datos. **No se publican resultados esperados**; hay que leer el código.

## Archivo por integrante

| Integrante | Archivo | Módulos |
|---|---|---|
| Andrés Durán | `api/tests/unit/equipo/integrante_1_validaciones/test_reto_avanzado.py` | `hybrid_search_service.py`, `request_utils.py` |
| Sebastián Samacá | `api/tests/unit/equipo/integrante_2_seguridad/test_reto_avanzado.py` | `embedding_service.py`, `decorators.py` |
| Dairon Salazar | `api/tests/unit/equipo/integrante_3_citas/test_reto_avanzado.py` | `appointment_service.py`, `recommendation_service.py` |
| Kevin Pinzón | `api/tests/unit/equipo/integrante_4_datos/test_reto_avanzado.py` | `profile_service.py`, `event_service.py` |

## Nombres exactos

### Andrés

```text
test_normalizacion_quita_tildes_y_signos
test_sinonimo_de_activo_lo_detecta
test_sintoma_suma_afinidad_al_puntaje_lexico
test_busqueda_sin_texto_lista_todos_los_servicios
test_filtro_categoria_ignora_mayusculas
```

### Sebastián

```text
test_coseno_es_cero_si_cambia_la_dimension
test_coseno_es_cero_con_vector_nulo
test_parse_vector_acepta_texto_json
test_admin_inactivo_recibe_403
test_jwt_optional_con_token_vencido_no_lanza
```

### Dairon

```text
test_slots_inteligentes_aplican_buffer_de_treinta_minutos
test_slots_inteligentes_ajustan_fin_a_la_duracion
test_slots_inteligentes_clasifican_tarde_y_noche
test_recomendacion_penaliza_servicio_reciente
test_recomendacion_no_penaliza_reserva_antigua
```

### Kevin

```text
test_normalizacion_decimal_negativo_conserva_signo
test_normalizacion_recorre_listas_y_diccionarios
test_upsert_no_duplica_filas
test_borrado_solo_afecta_la_entidad_indicada
test_evento_valido_guarda_sesion_y_metadata
```

## Reglas

Se aplican las mismas reglas de la ronda base, con estos cambios:

| Regla | Valor |
|---|---|
| Pruebas por archivo | Exactamente 5 |
| `pytestmark = pytest.mark.unit` | Obligatorio |
| Docstring | `Caso:`, `Entrada:`, `Esperado:`, `Cubre:` |
| `Cubre:` | Módulo asignado + símbolo real |
| Uso real | La prueba debe llamar al símbolo |
| Assert | Comparación real o `pytest.raises` específico |
| Tamaño | Máximo 32 líneas por prueba |
| Símbolos distintos | 4 (Dairon: 2, porque los módulos solo exponen 2 funciones objetivo) |
| Prohibido | Mocks, `monkeypatch`, `parametrize`, `skip`, `xfail`, `random`, `sleep`, leer el código fuente en tiempo de ejecución |
| Roturas | Al menos **70 %** y **8** absolutas sobre los símbolos declarados en `Cubre:` |
| Bases de datos | SQLite, PostgreSQL y MySQL |

### Herramientas permitidas

- `pytest.mark.django_db` y las fábricas de `api/tests/factories.py`.
- `freezegun.freeze_time` cuando el caso dependa de la hora (Dairon).
- `RequestFactory` para simular peticiones (Sebastián).
- `json.loads(respuesta.content)` para leer un `JsonResponse`.

## Aprobación

1. Formato y contrato.
2. Las 5 pruebas pasan en SQLite.
3. Las 5 pruebas pasan en PostgreSQL y MySQL.
4. Detecta al menos el 70 % de las roturas (mínimo 8).

La solución de referencia **no está en el repositorio**. Si el reto no se puede
resolver con el código actual, el responsable lo corrige antes de publicarlo.

## Recursos

[`RECURSOS.md`](RECURSOS.md) tiene enlaces de pytest, Django, factory_boy,
freezegun, PyJWT, pgvector y pruebas de mutación. No contiene respuestas.
