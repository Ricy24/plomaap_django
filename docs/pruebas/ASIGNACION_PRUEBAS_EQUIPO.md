# Asignación de pruebas unitarias por integrante

Entrega del equipo: **10 pruebas unitarias por integrante**, **40 en total**.
Cada integrante tiene su propio archivo, así que pueden trabajar en paralelo sin
pisarse ni generar conflictos en Git.

## Resumen de la división

| Integrante | Archivo | Módulo que prueba | Pruebas |
|---|---|---|---:|
| Integrante 1: ______________________ | `api/tests/unit/equipo/test_integrante_1_validaciones.py` | `api/utils/validators.py` | 10 |
| Integrante 2: ______________________ | `api/tests/unit/equipo/test_integrante_2_seguridad.py` | `api/utils/jwt_utils.py` + `api/utils/decorators.py` | 10 |
| Integrante 3: ______________________ | `api/tests/unit/equipo/test_integrante_3_citas.py` | `api/services/appointment_service.py` | 10 |
| Integrante 4: ______________________ | `api/tests/unit/equipo/test_integrante_4_datos.py` | `profile_service` + `event_service` + `recommendation_service` | 10 |
| **Total** | | | **40** |

> La suite histórica de regresión sigue viviendo en `api/tests/unit/utils/` y
> `api/tests/unit/services/` (470 casos). La carpeta `equipo/` es la entrega
> identificable de los 4 integrantes.

## Cómo ejecutar

Desde la raíz del proyecto:

```powershell
# Las 40 pruebas de la entrega
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q

# Solo las pruebas de un integrante
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\test_integrante_1_validaciones.py -q
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\test_integrante_2_seguridad.py -q
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\test_integrante_3_citas.py -q
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\test_integrante_4_datos.py -q

# Toda la suite unitaria (entrega + regresión)
.\venv\Scripts\python.exe -m pytest -m unit -q
```

Resultado real del **27/10/2026**:

```text
pytest api\tests\unit\equipo -q      -> 40 passed
pytest -m unit -q                    -> 510 passed, 18 deselected
```

## Integrante 1 - Validaciones de entrada

Archivo: `test_integrante_1_validaciones.py`
Funciones puras: no usan base de datos ni red.

| # | Prueba | Qué verifica |
|---|---|---|
| 1 | `test_email_valido` | Acepta `carlos@plomaap.com` |
| 2 | `test_email_sin_arroba_es_invalido` | Rechaza un correo sin `@` |
| 3 | `test_password_de_ocho_caracteres_es_valida` | Acepta exactamente 8 caracteres |
| 4 | `test_password_corta_es_invalida` | Rechaza una contraseña de 4 caracteres |
| 5 | `test_telefono_valido` | Acepta `+573001234567` |
| 6 | `test_telefono_con_letras_es_invalido` | Rechaza letras en el teléfono |
| 7 | `test_nombre_de_un_caracter_es_invalido` | Exige mínimo 2 caracteres |
| 8 | `test_fecha_y_hora_validas` | Acepta `2026-11-02` y `09:30` |
| 9 | `test_fecha_con_formato_incorrecto_es_invalida` | Rechaza `02/11/2026` |
| 10 | `test_rol_valido` | Acepta el rol `technician` |

## Integrante 2 - Seguridad y sesión

Archivo: `test_integrante_2_seguridad.py`
Simula peticiones con `RequestFactory`; no levanta el servidor.

| # | Prueba | Qué verifica |
|---|---|---|
| 1 | `test_generar_token_devuelve_texto` | El JWT es texto con 3 partes |
| 2 | `test_token_contiene_id_del_usuario` | El claim `sub` guarda el id |
| 3 | `test_token_alterado_es_rechazado` | Una firma alterada no es válida |
| 4 | `test_token_expirado_es_rechazado` | Un token vencido devuelve `None` |
| 5 | `test_extraer_token_con_bearer` | Lee `Bearer <token>` |
| 6 | `test_extraer_token_sin_encabezado_retorna_none` | Sin cabecera no hay token |
| 7 | `test_get_current_user_id_devuelve_entero` | Convierte el id a entero |
| 8 | `test_decorador_sin_token_responde_401` | Vista protegida sin token -> 401 |
| 9 | `test_admin_only_rechaza_a_un_cliente` | Cliente en vista admin -> 403 |
| 10 | `test_jwt_optional_permite_peticion_sin_token` | Token opcional deja `jwt_user = None` |

## Integrante 3 - Citas y disponibilidad

Archivo: `test_integrante_3_citas.py`
Usa SQLite en memoria y las fábricas de `api/tests/factories.py`.

| # | Prueba | Qué verifica |
|---|---|---|
| 1 | `test_pendiente_puede_pasar_a_agendada` | `pending -> scheduled` es válido |
| 2 | `test_agendada_puede_pasar_a_en_progreso` | `scheduled -> in_progress` es válido |
| 3 | `test_cita_completada_no_puede_cancelarse` | `completed` es estado final |
| 4 | `test_cita_cancelada_no_puede_reabrirse` | `cancelled` es estado final |
| 5 | `test_fecha_invalida_no_genera_horarios` | Fecha mal formada -> lista vacía |
| 6 | `test_usuario_que_no_es_tecnico_no_tiene_horarios` | Un cliente no tiene agenda |
| 7 | `test_jornada_laboral_genera_diez_franjas` | De 8:00 a 18:00 hay 10 franjas |
| 8 | `test_hora_ocupada_no_se_ofrece` | Una cita activa bloquea su hora |
| 9 | `test_tecnico_libre_esta_disponible` | Técnico libre -> disponible |
| 10 | `test_tecnico_fuera_de_horario_no_esta_disponible` | A las 7:00 no atiende |

## Integrante 4 - Perfil, eventos y recomendaciones

Archivo: `test_integrante_4_datos.py`
Servicios de negocio que escriben en la base de datos de pruebas.

| # | Prueba | Qué verifica |
|---|---|---|
| 1 | `test_record_attribute_guarda_el_valor` | Guarda un atributo del perfil |
| 2 | `test_record_attribute_actualiza_si_ya_existe` | Actualiza sin duplicar filas |
| 3 | `test_record_attribute_rechaza_fuente_invalida` | Fuente fuera del catálogo -> `ValueError` |
| 4 | `test_record_attribute_rechaza_confianza_fuera_de_rango` | Confianza > 1.0 -> `ValueError` |
| 5 | `test_delete_entity_attributes_elimina_los_atributos` | Borra y retorna cuántos eliminó |
| 6 | `test_track_event_crea_el_evento` | Registra un evento válido |
| 7 | `test_track_event_invalido_retorna_none` | Evento desconocido no rompe la petición |
| 8 | `test_track_event_invalido_en_modo_estricto_lanza_error` | Modo estricto sí falla |
| 9 | `test_click_en_recomendacion_se_registra` | Marca el clic y crea el evento |
| 10 | `test_generate_recommendations_respeta_el_limite` | Devuelve como máximo `limit` |

## Reglas que sigue cada prueba

1. **Un archivo por integrante**: identifica rápido quién escribió qué.
2. **Nombre descriptivo en español**: el nombre dice qué se espera, no cómo se
   implementa (`test_password_corta_es_invalida`, no `test_password_2`).
3. **Patrón AAA**: Arrange (preparar), Act (ejecutar), Assert (comprobar).
4. **Datos fijos**: nada de valores aleatorios; así el resultado es reproducible.
5. **Sin red ni servidor**: JWT y base de datos se manejan localmente; las
   pruebas que usan modelos corren sobre SQLite en memoria.
6. **Marcadas como `unit`**: `pytestmark = pytest.mark.unit` en cada archivo.

## Evidencia para la entrega

El equipo tiene dos archivos en `docs/pruebas/`:

| Archivo | Contenido |
|---|---|
| `Plan_de_Pruebas_PlomApp_SENA.xlsx` | Original con los 470 casos de regresión (no se modificó) |
| `Plan_de_Pruebas_PlomApp_SENA_40_pruebas_equipo.xlsx` | **Entrega**: solo las 40 pruebas del equipo (`UNIT-001` a `UNIT-040`) |

En la copia, la hoja **Control y Resumen** ya tiene los nombres del equipo en
"Aprendices / Equipo de Pruebas". La hoja **Pruebas Unitarias** agrega la columna
**Responsable / Integrante**, con 10 filas asignadas a cada uno:

| Integrante | Casos en el Excel |
|---|---|
| Andrés Durán | `UNIT-001` a `UNIT-010` |
| Sebastián Samacá | `UNIT-011` a `UNIT-020` |
| Dairon Salazar | `UNIT-021` a `UNIT-030` |
| Kevin Pinzón | `UNIT-031` a `UNIT-040` |

Cada integrante debe adjuntar la salida de su archivo, por ejemplo:

```text
api/tests/unit/equipo/test_integrante_1_validaciones.py .......... [100%]
10 passed
```

Y el consolidado del equipo:

```text
api/tests/unit/equipo ............................................ [100%]
40 passed
```

## Reparto sugerido para la exposición

| Integrante | Tema | Pregunta que debe poder responder |
|---|---|---|
| 1 | Validaciones | ¿Qué datos rechaza el registro y por qué? |
| 2 | Seguridad | ¿Cómo se protege una vista y qué pasa sin token? |
| 3 | Citas | ¿Cómo se evita que dos citas ocupen la misma hora? |
| 4 | Datos | ¿Cómo se guarda el perfil y qué pasa con un evento inválido? |
