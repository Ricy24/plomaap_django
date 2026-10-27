# Pruebas del backend PlomApp

El backend usa **pytest + pytest-django** para las pruebas unitarias y de
integración. Los nombres de archivo y de prueba conservan el ID del plan SENA
(`UNIT-01`, `INT-01`, etc.) para que la evidencia sea rastreable.

## Instalación

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Pruebas unitarias

```powershell
.\venv\Scripts\python.exe -m pytest -m unit -q
```

Corren en SQLite en memoria y no requieren Docker. La suite completa incluye
las pruebas de validadores, JWT, disponibilidad de citas y embeddings.

Para la entrega del aprendiz hay un archivo aparte con **10 pruebas unitarias
básicas** sobre `api/utils/validators.py`:

```powershell
.\venv\Scripts\python.exe -m pytest api\tests\unit\test_unit_10_basicas.py -v
```

El Excel documenta esas 10 pruebas en la hoja **Pruebas Unitarias** como
`UNIT-01` a `UNIT-10`. La suite completa del repositorio conserva además las
demás pruebas unitarias y de integración.

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

## Estructura

```
api/tests/
  conftest.py                 fixtures compartidas
  factories.py                factorías de usuarios, técnicos, servicios y citas
  unit/                       UNIT-01 .. UNIT-04
  integration/                INT-01 .. INT-04 + contrato existente
pytest.ini                    configuración de pytest
config/settings_test.py       SQLite por defecto; Postgres con TEST_USE_CONFIGURED_DB=1
```

## Frontend

Las pruebas del frontend viven en el repositorio React:

```powershell
npm run test:unit      # Vitest (UNIT-05)
npm run test:e2e       # Playwright (E2E-01 .. E2E-03)
```

Para E2E se deben levantar backend y frontend y definir las credenciales
`E2E_CLIENT_*`, `E2E_TECHNICIAN_*` y `E2E_ADMIN_*`; si faltan, los casos se
omiten y no se reportan como exitosos.
