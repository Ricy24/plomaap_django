# Guía de la suite de pruebas unitarias

## Qué es una prueba unitaria

Revisa **una sola función o una sola regla** del código, de forma aislada: sin
levantar el servidor, sin internet y sin depender de servicios externos. Las
dependencias de red (Voyage, Gemini, SMTP) se simulan; los servicios que usan
modelos corren sobre SQLite en memoria.

## Dónde están

```text
api/tests/
  conftest.py                 fixtures compartidas
  factories.py                fábricas de usuarios, técnicos, servicios, citas,
                              hogares, catálogos, eventos y embeddings
  unit/
    equipo/                   entregas identificables del equipo
      integrante_1_validaciones/
      integrante_2_seguridad/
      integrante_3_citas/
      integrante_4_datos/
    utils/                    una función/helper por archivo (regresión)
      test_validators_*.py
      test_jwt_utils.py
      test_request_utils.py
      test_dispatch.py
      test_decorators.py
      test_email_utils.py
    services/                 un servicio por archivo (regresión)
      test_appointment_service.py
      test_embedding_provider.py
      test_embedding_service.py
      test_event_service.py
      test_hybrid_search_service.py
      test_nlu_service.py
      test_onboarding_service.py
      test_profile_service.py
      test_recommendation_service.py
  integration/                INT-01 .. INT-04 + contrato de API
```

- **`equipo/`**: la entrega de los 4 integrantes. Cada carpeta tiene su `LEEME.md`
  y sus archivos. Estado y contratos en
  [`ASIGNACION_PRUEBAS_EQUIPO.md`](ASIGNACION_PRUEBAS_EQUIPO.md).
- **`utils/` y `services/`**: suite histórica de regresión. No se entrega; sirve
  para detectar si un cambio rompe el comportamiento existente.
- **`integration/`**: API real, PostgreSQL/pgvector y uploads.

## Cómo se ejecutan

```powershell
# Suite unitaria completa
.\venv\Scripts\python.exe -m pytest -m unit -q

# Solo las entregas del equipo
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q

# Una entrega
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\integrante_2_seguridad -q
```

## Cobertura

```powershell
.\venv\Scripts\python.exe -m coverage erase
.\venv\Scripts\python.exe -m coverage run --source=api/utils,api/services -m pytest -m unit -q
.\venv\Scripts\python.exe -m coverage report -m
```

La cobertura se mide sobre `api/utils` + `api/services`. Las vistas y
controladores se cubren con integración/API y no forman parte de este porcentaje.

## Cómo se escribe una prueba

Patrón **AAA**:

| Parte | Qué significa | Ejemplo |
|---|---|---|
| Arrange | Preparar el dato | `email = "usuario@plomaap.com"` |
| Act | Ejecutar la función | `resultado = validate_email(email)` |
| Assert | Comprobar el resultado | `assert resultado is True` |

Cada prueba de la entrega debe incluir un docstring con cuatro etiquetas:

```python
def test_email_valido():
    """Caso: correo con usuario, arroba y dominio.
    Entrada: 'carlos@plomaap.com'.
    Esperado: True, porque cumple el patrón.
    Cubre: api/utils/validators.py::validate_email
    """
    assert validate_email('carlos@plomaap.com') is True
```

## Qué se prueba en cada grupo

| Grupo | Qué cubre |
|---|---|
| Validadores | Email, teléfono, contraseña, nombre, fecha/hora, roles y estados |
| JWT | Creación, decodificación, expiración, firma alterada y cabeceras |
| Request / dispatch | Lectura de JSON, query params y despacho por método HTTP (incluido `405`) |
| Decoradores | Autenticación, roles y respuestas `401/403` |
| Correo | Envío SMTP, SSL/TLS y manejo de errores sin romper la petición |
| Citas | Horarios, disponibilidad, conflictos, slots inteligentes y transiciones |
| Embeddings | Proveedor Voyage, fallback local, similitud coseno y pgvector |
| Búsqueda híbrida | Sinónimos, activos, síntomas y fusión léxica + vectorial |
| NLU | Gemini, fallback determinista, normalización y prellenado de reserva |
| Onboarding | Preguntas adaptativas, hogar, habitaciones, activos y estado |
| Perfil | Atributos, procedencia, normalización y borrado |
| Recomendaciones | Puntajes, historial, penalización y tracking de clics |

## Evidencia

- `docs/pruebas/Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx`: base con las
  20 pruebas base entregadas (`UNIT-001` a `UNIT-020`).
- `docs/.interno/Plan_de_Pruebas_PlomApp_SENA.xlsx`: original con los 470 casos
  de regresión. **No se publica** y no se edita.
- `informe_entrega.xlsx`: lo genera el pipeline con las rondas aprobadas.

Cada fila incluye el nodo exacto de pytest en la columna de evidencia.

## Consejos

- No inventes resultados: ejecuta el comando y muestra el `passed`.
- No copies pruebas: el pipeline rechaza nombres repetidos y cuerpos idénticos.
- No uses datos aleatorios; usa datos fijos para saber qué esperar.
- Cada prueba debe revisar una sola cosa y llamar al símbolo que declara cubrir.
- Si una prueba falla, revisa primero el dato de entrada y el resultado esperado.
- Separa las pruebas por módulo: así se identifica rápido qué falla.
- Si no sabes qué esperar de una función, no la pruebes todavía: ábrela, léela y
  ejecútala en la consola hasta entenderla.
