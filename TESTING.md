# Pruebas del backend PlomApp

El backend usa **pytest + pytest-django**. La suite unitaria está organizada por
módulos (una función de utilidad o un servicio por archivo) y corre sobre
**SQLite en memoria**, sin Docker ni servicios externos: las llamadas a Voyage,
Gemini y SMTP se simulan con `unittest.mock`.

## Instalación

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Pruebas unitarias

```powershell
.\venv\Scripts\python.exe -m pytest -m unit -q
```

Resultado real: **470 casos aprobados** (323 funciones de prueba; varias están
parametrizadas), **18 casos de integración deseleccionados**.

### Cobertura

```powershell
.\venv\Scripts\python.exe -m coverage erase
.\venv\Scripts\python.exe -m coverage run --source=api/utils,api/services -m pytest -m unit -q
.\venv\Scripts\python.exe -m coverage report -m
```

Resultado real: **100 %** sobre `api/utils` + `api/services` (1243 sentencias,
0 sin cubrir).

La cobertura se mide sobre la **capa unitaria** (`api/utils` y `api/services`).
Las vistas y controladores (`api/views`, `api/controllers`) requieren pruebas de
integración/API y no forman parte de este porcentaje.

### Estructura

```
api/tests/
  conftest.py                     fixtures compartidas
  factories.py                    fábricas de usuarios, técnicos, servicios, citas,
                                  hogares, catálogos, eventos y embeddings
  unit/
    utils/                        una función/helper por archivo
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
    services/                     un servicio por archivo
      test_appointment_service.py
      test_embedding_provider.py
      test_embedding_service.py
      test_event_service.py
      test_hybrid_search_service.py
      test_nlu_service.py
      test_onboarding_service.py
      test_profile_service.py
      test_recommendation_service.py
  integration/                    INT-01 .. INT-04 + contrato existente
pytest.ini                        configuración y marcadores (unit/integration/e2e)
config/settings_test.py           SQLite por defecto; Postgres con TEST_USE_CONFIGURED_DB=1
```

Cada fila de la hoja **Pruebas Unitarias** del Excel
(`docs/pruebas/Plan_de_Pruebas_PlomApp_SENA.xlsx`) corresponde a una variante
realmente ejecutada, con el nodo de pytest como evidencia (`UNIT-001` a
`UNIT-470`).

## Pruebas de integración

Por defecto las pruebas de integración que requieren PostgreSQL se marcan como
`skipped`. Para ejecutarlas contra el PostgreSQL/pgvector configurado en `.env`
(el contenedor de desarrollo escucha en `localhost:5434`):

```powershell
$env:TEST_USE_CONFIGURED_DB = '1'
.\venv\Scripts\python.exe -m pytest -m integration -q --create-db
Remove-Item Env:TEST_USE_CONFIGURED_DB
```

Django crea y destruye `test_plomapp`; **no** usa la base `plomapp` real. La
prueba `INT-03` crea la extensión `vector`, convierte la columna de embeddings a
`vector(512)` y crea el índice HNSW dentro de la base de pruebas.

Casos:

- `INT-01`: registro, login, perfil y rechazo de contraseña incorrecta.
- `INT-02`: disponibilidad, creación de cita y doble reserva (`409`).
- `INT-03`: sincronización de embeddings, columna `vector(512)`, índice HNSW y
  búsqueda semántica.
- `INT-04`: upload de evidencias (PNG válido, contenido falso, tamaño máximo) y
  persistencia de `evidence_photos`.

## Suite completa

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

## Frontend

Las pruebas del frontend viven en el repositorio React:

```powershell
npm run test:unit      # Vitest
npm run test:e2e       # Playwright (E2E-01 .. E2E-03)
```

Para E2E se deben levantar backend y frontend y definir las credenciales
`E2E_CLIENT_*`, `E2E_TECHNICIAN_*` y `E2E_ADMIN_*`; si faltan, los casos se
omiten y no se reportan como exitosos.
