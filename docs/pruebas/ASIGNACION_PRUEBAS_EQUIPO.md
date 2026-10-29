# Asignación de pruebas unitarias por integrante

Estado actual: **20 pruebas entregadas** (Andrés Durán y Dairon Salazar) y
**20 pendientes** (Sebastián Samacá y Kevin Pinzón).

Cada integrante tiene su propio archivo, así que pueden trabajar en paralelo sin
pisarse ni generar conflictos en Git.

## Resumen de la división

| Integrante | Archivo | Módulo que prueba | Pruebas | Estado |
|---|---|---|---:|---|
| Andrés Durán | `api/tests/unit/equipo/test_integrante_1_validaciones.py` | `api/utils/validators.py` | 10 | Entregado |
| Sebastián Samacá | `api/tests/unit/equipo/test_integrante_2_seguridad.py` | `api/utils/jwt_utils.py` + `api/utils/decorators.py` | 10 | **Pendiente** |
| Dairon Salazar | `api/tests/unit/equipo/test_integrante_3_citas.py` | `api/services/appointment_service.py` | 10 | Entregado |
| Kevin Pinzón | `api/tests/unit/equipo/test_integrante_4_datos.py` | `profile_service` + `event_service` + `recommendation_service` | 10 | **Pendiente** |
| **Total** | | | **40** | **20 entregadas** |

> La suite histórica de regresión sigue viviendo en `api/tests/unit/utils/` y
> `api/tests/unit/services/` (470 casos). La carpeta `equipo/` es la entrega
> identificable de los integrantes.

## Cómo ejecutar

Desde la raíz del proyecto:

```powershell
# Las pruebas entregadas (20)
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q

# Solo una entrega
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\test_integrante_1_validaciones.py -q
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\test_integrante_3_citas.py -q

# Toda la suite unitaria (entrega + regresión)
.\venv\Scripts\python.exe -m pytest -m unit -q
```

Resultado real del **28/10/2026**:

```text
pytest api\tests\unit\equipo -q      -> 20 passed
pytest -m unit -q                    -> 490 passed, 34 deselected
```

## Reglas para las entregas pendientes

El formato exacto que deben cumplir está en
[`ESPECIFICACION_PRUEBAS_PENDIENTES.md`](ESPECIFICACION_PRUEBAS_PENDIENTES.md).
Resumen:

1. **Archivo propio**: cada integrante crea su archivo en `api/tests/unit/equipo/`.
2. **10 pruebas que pasen**: no se acepta código que rompa la suite.
3. **Docstring obligatorio** con `Caso:`, `Entrada:`, `Esperado:` y `Cubre:`; el
   `Cubre:` debe apuntar a un símbolo real del módulo asignado.
4. **Sin repetidas**: el pipeline falla si detecta nombres de prueba duplicados o
   cuerpos idénticos dentro de `equipo/`.
5. **Sin copiar**: cada prueba debe apuntar a su módulo asignado y usar sus propios
   datos; no se aceptan copias de otra entrega con el nombre cambiado.
6. **Entrega por Pull Request**: se abre un PR hacia `main` y lo revisa el
   responsable del repositorio. Nadie puede mergear su propio PR.

Validación local antes de entregar:

```powershell
.\venv\Scripts\python.exe scripts\check_test_duplicates.py
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
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

## Integrante 2 - Seguridad y sesión (PENDIENTE)

Archivo a crear: `test_integrante_2_seguridad.py`
Módulos asignados: `api/utils/jwt_utils.py` y `api/utils/decorators.py`

Debe entregar 10 pruebas propias sobre, como mínimo:

- Generación y validación de tokens JWT.
- Lectura del encabezado `Authorization: Bearer <token>`.
- Rechazo de tokens alterados o vencidos.
- Comportamiento de los decoradores `jwt_required`, `admin_only` y `jwt_optional`.
- Códigos de respuesta `401` y `403`.

Las pruebas deben usar `RequestFactory` y no levantar el servidor.

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

## Integrante 4 - Perfil, eventos y recomendaciones (PENDIENTE)

Archivo a crear: `test_integrante_4_datos.py`
Módulos asignados: `profile_service`, `event_service` y `recommendation_service`

Debe entregar 10 pruebas propias sobre, como mínimo:

- Registro y actualización de atributos del perfil.
- Validación de fuente y de rango de confianza.
- Borrado de atributos de una entidad.
- Registro de eventos válidos e inválidos (modo normal y estricto).
- Clic en una recomendación.
- Límite de resultados en `generate_recommendations`.

## Evidencia para la entrega

Archivos en `docs/pruebas/`:

| Archivo | Contenido |
|---|---|
| `Plan_de_Pruebas_PlomApp_SENA.xlsx` | Original con los 470 casos de regresión (no se modificó) |
| `Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx` | **Entrega**: las 20 pruebas de Andrés y Dairon (`UNIT-001` a `UNIT-020`) |

En la copia, la hoja **Control y Resumen** tiene los nombres de quienes ya
entregaron en "Aprendices / Equipo de Pruebas". La hoja **Pruebas Unitarias**
incluye la columna **Responsable / Integrante**:

| Integrante | Casos en el Excel | Estado |
|---|---|---|
| Andrés Durán | `UNIT-001` a `UNIT-010` | Entregado |
| Dairon Salazar | `UNIT-011` a `UNIT-020` | Entregado |
| Sebastián Samacá | — | Pendiente |
| Kevin Pinzón | — | Pendiente |

Cada integrante debe adjuntar la salida de su archivo, por ejemplo:

```text
api/tests/unit/equipo/test_integrante_1_validaciones.py .......... [100%]
10 passed
```

Y el consolidado de lo entregado:

```text
api/tests/unit/equipo ............................................ [100%]
20 passed
```

## Reparto sugerido para la exposición

| Integrante | Tema | Pregunta que debe poder responder |
|---|---|---|
| Andrés Durán | Validaciones | ¿Qué datos rechaza el registro y por qué? |
| Sebastián Samacá | Seguridad | ¿Cómo se protege una vista y qué pasa sin token? |
| Dairon Salazar | Citas | ¿Cómo se evita que dos citas ocupen la misma hora? |
| Kevin Pinzón | Datos | ¿Cómo se guarda el perfil y qué pasa con un evento inválido? |
