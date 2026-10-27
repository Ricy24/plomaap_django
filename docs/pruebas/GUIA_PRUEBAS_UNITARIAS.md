# Guía de la suite de pruebas unitarias de PlomApp

## ¿Qué es una prueba unitaria?

Una prueba unitaria revisa **una sola función** o **una sola regla** del código,
de forma aislada: sin levantar el servidor, sin internet y sin depender de
servicios externos. En PlomApp las dependencias de red (Voyage, Gemini, SMTP) se
simulan con `unittest.mock` y los servicios que usan modelos corren sobre SQLite
en memoria.

## ¿Dónde están?

Están organizadas por módulo, no en un solo archivo:

```text
api/tests/unit/
  utils/
    test_validators_email.py
    test_validators_phone.py
    test_validators_password.py
    test_validators_name.py
    test_validators_date_time.py
    test_validators_catalogs.py
    test_jwt_utils.py
    test_request_utils.py
    test_dispatch.py
    test_decorators.py
    test_email_utils.py
  services/
    test_appointment_service.py
    test_embedding_provider.py
    test_embedding_service.py
    test_event_service.py
    test_hybrid_search_service.py
    test_nlu_service.py
    test_onboarding_service.py
    test_profile_service.py
    test_recommendation_service.py
```

- **`utils/`**: funciones puras y helpers (validaciones, JWT, request, despacho
  por método HTTP, decoradores y correo).
- **`services/`**: reglas de negocio (citas, embeddings, eventos, búsqueda
  híbrida, NLU, onboarding, perfil y recomendaciones).

## ¿Cómo se ejecutan?

```powershell
cd C:\Users\Anrid\backend_plomaap
.\venv\Scripts\python.exe -m pytest -m unit -q
```

Resultado real:

```text
470 passed, 18 deselected
```

### Cobertura

```powershell
.\venv\Scripts\python.exe -m coverage erase
.\venv\Scripts\python.exe -m coverage run --source=api/utils,api/services -m pytest -m unit -q
.\venv\Scripts\python.exe -m coverage report -m
```

Resultado real: **100 %** sobre `api/utils` + `api/services` (1243 sentencias,
0 sin cubrir).

## ¿Cómo está escrita cada prueba?

Todas siguen el patrón **AAA**:

| Parte | Qué significa | Ejemplo |
|---|---|---|
| Arrange | Preparar el dato | `email = "usuario@plomaap.com"` |
| Act | Ejecutar la función | `resultado = validate_email(email)` |
| Assert | Comprobar el resultado | `assert resultado is True` |

Cuando un mismo caso lógico se prueba con varios datos se usa
`@pytest.mark.parametrize`; cada variante se cuenta como un caso ejecutado.

## ¿Qué se prueba en cada grupo?

| Grupo | Qué cubre |
|---|---|
| Validadores | Email, teléfono, contraseña, nombre, fecha/hora, roles y estados |
| JWT | Creación, decodificación, expiración y token alterado |
| Request / dispatch | Lectura de JSON, cabeceras y despacho por método HTTP (incluido `405`) |
| Decoradores | Autenticación, roles y respuestas `401/403` |
| Correo | Envío SMTP, SSL/TLS y manejo de errores sin romper la petición |
| Citas | Horarios, disponibilidad, conflictos, slots inteligentes y transiciones |
| Embeddings | Proveedor Voyage, fallback local, similitud coseno y pgvector |
| Búsqueda híbrida | Sinónimos, activos, síntomas, fusión léxica + vectorial |
| NLU | Gemini, fallback determinista, normalización y prellenado de reserva |
| Onboarding | Preguntas adaptativas, hogar, habitaciones, activos y estado |
| Perfil | Atributos, procedencia, normalización y borrado |
| Recomendaciones | Puntajes, historial, penalización y tracking de clics |

## Evidencia en el Excel

La hoja **Pruebas Unitarias** de
[`Plan_de_Pruebas_PlomApp_SENA.xlsx`](Plan_de_Pruebas_PlomApp_SENA.xlsx) contiene
**470 filas** (`UNIT-001` a `UNIT-470`), una por variante realmente ejecutada.
Cada fila incluye el nodo exacto de pytest en la columna de evidencia.

## Consejos para la entrega

- No inventes resultados: ejecuta el comando y muestra el `470 passed`.
- No uses datos aleatorios; usa datos fijos para saber qué esperar.
- Cada prueba debe tener un nombre claro y revisar una sola cosa.
- Si una prueba falla, revisa primero el dato de entrada y el resultado esperado.
- Separa las pruebas por módulo: así se identifica rápido qué falla.
