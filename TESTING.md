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

Resultado real: **490 casos aprobados** (363 funciones de prueba; varias están
parametrizadas), **34 casos de integración deseleccionados**. Incluye los 470
casos de regresión y las **20 pruebas entregadas por los integrantes**.

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
    equipo/                       entrega: 20 pruebas (10 por integrante)
      test_integrante_1_validaciones.py
      test_integrante_3_citas.py
                                  pendientes: test_integrante_2_seguridad.py
                                              test_integrante_4_datos.py
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
`UNIT-470`). Las 20 pruebas de `unit/equipo/` son la entrega identificable de
los integrantes que ya entregaron y están detalladas en
[`docs/pruebas/ASIGNACION_PRUEBAS_EQUIPO.md`](docs/pruebas/ASIGNACION_PRUEBAS_EQUIPO.md).
La copia con esas 20 pruebas (`UNIT-001` a `UNIT-020`) es
`docs/pruebas/Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx`; contiene
solo lo entregado, mientras que el archivo original conserva los 470
casos de regresión sin cambios. Las 20 pruebas restantes quedan pendientes y se
registran con `scripts/registrar_entrega.py` cuando la entrega cumple el
[contrato](docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md).

### Entrega por integrantes

```powershell
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
```

Resultado real: **20 passed**. Cada archivo contiene exactamente 10 pruebas y
se puede ejecutar por separado para la evidencia individual.

El pipeline verifica además que no haya pruebas repetidas:

```powershell
.\venv\Scripts\python.exe scripts\check_test_duplicates.py
```

Falla si dos pruebas tienen el mismo nombre o el mismo cuerpo, aunque se
renombren las variables.

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

### Contenedor desechable (prueba satisfactoria)

Para demostrar la integración sin tocar el contenedor real se puede levantar un
PostgreSQL 17 + pgvector temporal, ejecutar la suite y destruirlo al final:

```powershell
docker run -d --name plomapp-test-pgvector `
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=plomaap_test_pw `
  -e POSTGRES_DB=plomapp_test -p 5435:5432 pgvector/pgvector:pg17

$env:TEST_USE_CONFIGURED_DB = '1'
$env:POSTGRES_DB = 'plomapp_test'
$env:POSTGRES_USER = 'postgres'
$env:POSTGRES_PASSWORD = 'plomaap_test_pw'
$env:POSTGRES_HOST = 'localhost'
$env:POSTGRES_PORT = '5435'
.\venv\Scripts\python.exe -m pytest api\tests\integration -q --create-db
Remove-Item Env:TEST_USE_CONFIGURED_DB,Env:POSTGRES_DB,Env:POSTGRES_USER,Env:POSTGRES_PASSWORD,Env:POSTGRES_HOST,Env:POSTGRES_PORT

docker rm -fv plomapp-test-pgvector
```

Resultado real del **27/10/2026**:

- `pytest -m integration -q --create-db`: **8 passed** (incluye `INT-02` con
  `select_for_update` e `INT-03` con `vector(512)` e índice HNSW).
- `pytest api\tests\integration -q --create-db`: **18 passed** (integración +
  contrato de API).
- Django creó y destruyó `test_plomapp_test`; la base real `plomapp`
  (`localhost:5434`) no se modificó. El contenedor temporal se eliminó con
  `docker rm -fv` al finalizar.

Casos:

- `INT-01`: registro, login, perfil y rechazo de contraseña incorrecta.
- `INT-02`: disponibilidad, creación de cita y doble reserva (`409`).
- `INT-03`: sincronización de embeddings, columna `vector(512)`, índice HNSW y
  búsqueda semántica.
- `INT-04`: upload de evidencias (PNG válido, contenido falso, tamaño máximo) y
  persistencia de `evidence_photos`.

## CI en GitHub y protección de `main`

El pipeline está en [`.github/workflows/pruebas.yml`](.github/workflows/pruebas.yml) y se
ejecuta en cada `pull_request` hacia `main`, en cada push a `dev_Andres` y de forma
manual (`workflow_dispatch`). Tiene dos jobs:

| Job | Qué ejecuta |
|---|---|
| `unit-tests` | `scripts/check_test_duplicates.py`, `scripts/check_entrega_equipo.py`, `pytest api/tests/unit/equipo -q` (20) y `pytest -m unit -q` (490) con SQLite en memoria |
| `integration-tests` | `pytest api/tests/integration -q --create-db` contra PostgreSQL 17 + pgvector |

`main` está protegida con estos ajustes, así que **no se puede mergear nada sin que
el pipeline pase**:

- Checks obligatorios: `unit-tests` e `integration-tests`.
- La rama del PR debe estar actualizada con `main` antes de mergear.
- Prohibido el push directo, el force push y el borrado de la rama.
- Se exige resolver las conversaciones antes de mergear.
- **Se exige la aprobación del responsable** (`.github/CODEOWNERS`): nadie puede
  mergear su propio trabajo.
- El administrador conserva la posibilidad de saltarse la regla en una emergencia.

Para revisar o cambiar la configuración:

```powershell
gh api repos/Ricy24/plomaap_django/branches/main/protection
```

Si GitHub muestra `The job was not started because your account is locked due to a
billing issue`, los jobs no arrancan y el PR queda en `BLOCKED`. Hay que resolver la
facturación en **Settings → Billing and plans** de la cuenta; mientras tanto las
pruebas se pueden ejecutar en local con los comandos de este documento.

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
