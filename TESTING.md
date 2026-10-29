# Pruebas del backend PlomApp

El backend usa **pytest + pytest-django**. La suite unitaria está organizada por
módulos y corre sobre **SQLite en memoria** por defecto, sin Docker ni servicios
externos: las llamadas a Voyage, Gemini y SMTP se simulan.

El pipeline prueba además en **PostgreSQL 17 + pgvector** y en **MySQL 8.4**.
Ninguna rama entra a `main` si esos checks fallan.

## Instalación

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Suite unitaria

```powershell
.\venv\Scripts\python.exe -m pytest -m unit -q
```

Estado actual: **490 casos aprobados** (363 funciones; varias están
parametrizadas) y **34 casos de integración** deseleccionados. Incluye las 20
pruebas base ya entregadas por el equipo. Las 20 pruebas de la **ronda avanzada**
todavía no están en el repositorio; cuando se entreguen, la suite sube a 510.

### Cobertura

```powershell
.\venv\Scripts\python.exe -m coverage erase
.\venv\Scripts\python.exe -m coverage run --source=api/utils,api/services -m pytest -m unit -q
.\venv\Scripts\python.exe -m coverage report -m
```

Resultado real: **100 %** sobre `api/utils` + `api/services` (1243 sentencias,
0 sin cubrir). El pipeline falla si baja de 100 %.

La cobertura se mide sobre la **capa unitaria**. Las vistas y controladores
(`api/views`, `api/controllers`) se cubren con integración/API.

### Estructura

```text
api/tests/
  conftest.py                     fixtures compartidas
  factories.py                    fábricas de usuarios, técnicos, servicios, citas,
                                  hogares, catálogos, eventos y embeddings
  unit/
    equipo/                       entregas identificables del equipo
      integrante_1_validaciones/  Andrés Durán
      integrante_2_seguridad/     Sebastián Samacá
      integrante_3_citas/         Dairon Salazar
      integrante_4_datos/         Kevin Pinzón
    utils/                        una función/helper por archivo (regresión)
    services/                     un servicio por archivo (regresión)
  integration/                    INT-01 .. INT-04 + contrato de API
pytest.ini                        configuración y marcadores (unit/integration/e2e)
config/settings_test.py           SQLite por defecto; Postgres/MySQL con TEST_USE_CONFIGURED_DB=1
```

Cada carpeta de `equipo/` tiene su `LEEME.md` y su contrato:

- [`docs/pruebas/ASIGNACION_PRUEBAS_EQUIPO.md`](docs/pruebas/ASIGNACION_PRUEBAS_EQUIPO.md)
- [`docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md`](docs/pruebas/CONTRATO_PRUEBAS_PENDIENTES.md)
- [`docs/pruebas/RETO_AVANZADO.md`](docs/pruebas/RETO_AVANZADO.md)

### Entregas del equipo

```powershell
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
```

Estado actual: **20 passed** (las 20 pruebas base entregadas). Cada archivo
contiene exactamente 10 pruebas y se puede ejecutar por separado.

El pipeline verifica además:

```powershell
.\venv\Scripts\python.exe scripts\check_test_duplicates.py
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py
.\venv\Scripts\python.exe scripts\mutar_entrega.py --todo
```

- **Duplicados**: falla si dos pruebas de la misma carpeta tienen el mismo nombre
  o si dos cuerpos son idénticos en cualquier carpeta.
- **Contrato**: nombres exactos, docstring `Caso/Entrada/Esperado/Cubre`, símbolo
  real, llamada al símbolo, assert con comparación y sin atajos.
- **Roturas**: inyecta fallos en los símbolos que cada prueba declara en
  `Cubre:` y exige detectar 60 % (base) o 70 % (avanzada).

### Evidencia

| Archivo | Contenido | Visibilidad |
|---|---|---|
| `docs/pruebas/Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx` | 20 pruebas base (`UNIT-001` a `UNIT-020`) | Repositorio |
| `docs/.interno/Plan_de_Pruebas_PlomApp_SENA.xlsx` | 470 casos de regresión | Local, ignorado por Git |
| `informe_entrega.xlsx` | Informe generado por el pipeline | Artefacto de GitHub Actions |

El original de 470 casos **no se publica** y no se edita. El informe se regenera
desde la base de entrega y las rondas aprobadas.

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

### Contenedor desechable

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

Casos:

- `INT-01`: registro, login, perfil y rechazo de contraseña incorrecta.
- `INT-02`: disponibilidad, creación de cita y doble reserva (`409`).
- `INT-03`: sincronización de embeddings, columna `vector(512)`, índice HNSW y
  búsqueda semántica.
- `INT-04`: upload de evidencias (PNG válido, contenido falso, tamaño máximo) y
  persistencia de `evidence_photos`.

## CI en GitHub

El pipeline está en [`.github/workflows/pruebas.yml`](.github/workflows/pruebas.yml)
y se ejecuta en cada `pull_request` hacia `main`, en cada push a `dev_Andres` y de
forma manual (`workflow_dispatch`).

| Job | Qué ejecuta |
|---|---|
| `calidad` | compilación, `ruff`, duplicados, contrato y `bandit` |
| `unit-sqlite` | suite unitaria, entregas y cobertura 100 % (SQLite en memoria) |
| `unit-postgres` | suite unitaria y entregas contra PostgreSQL 17 + pgvector |
| `unit-mysql` | suite unitaria y entregas contra MySQL 8.4 |
| `integration-postgres` | integración y contrato contra PostgreSQL 17 + pgvector |
| `mutacion` | roturas de todas las entregas presentes |
| `informe` | genera `informe_entrega.xlsx` y lo publica como artefacto |
| `required` | agregador: falla si cualquier check anterior falló |

`main` está protegida con estos ajustes, así que **no se puede mergear nada sin
que el pipeline pase**:

- Checks obligatorios: `calidad`, `unit-sqlite`, `unit-postgres`, `unit-mysql`,
  `integration-postgres`, `mutacion` y `required`.
- La rama del PR debe estar actualizada con `main` antes de mergear.
- Prohibido el push directo, el force push y el borrado de la rama.
- Se exige resolver las conversaciones antes de mergear.
- **Se exige la aprobación del responsable** (`.github/CODEOWNERS`): nadie puede
  mergear su propio trabajo.
- `enforce_admins` activo: ni siquiera el administrador mergea con checks en rojo.
  Para una emergencia real hay que desactivar la protección explícitamente.

Para revisar o cambiar la configuración:

```powershell
gh api repos/Ricy24/plomaap_django/branches/main/protection
```

Si GitHub muestra `The job was not started because your account is locked due to a
billing issue`, los jobs no arrancan y el PR queda en `BLOCKED`. Hay que resolver la
facturación en **Settings → Billing and plans** de la cuenta; mientras tanto las
pruebas se pueden ejecutar en local con los comandos de este documento.

## Verificación local completa

```powershell
.\venv\Scripts\python.exe scripts\verificar_todo.py
```

Ejecuta duplicados, contrato, suite unitaria, cobertura, integración, roturas,
lint y seguridad. Con `--rapido` omite integración y mutación.

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
