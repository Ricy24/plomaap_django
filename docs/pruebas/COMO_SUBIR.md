# Cómo subir tu entrega (fork + Pull Request)

No tienes permiso de escritura en `Ricy24/plomaap_django`. Por eso se trabaja con
un **fork** y un **Pull Request (PR)**. El PR no se mergea hasta que pasen todos
los checks y el responsable lo apruebe.

## 1. Crea tu fork

1. Abre `https://github.com/Ricy24/plomaap_django`.
2. Pulsa **Fork** (arriba a la derecha).
3. Deja el fork en tu cuenta, por ejemplo:
   `https://github.com/TU-USUARIO/plomaap_django`.

## 2. Clona tu fork

```powershell
git clone https://github.com/TU-USUARIO/plomaap_django.git
cd plomaap_django
```

Si ya lo tenías clonado, actualízalo:

```powershell
git checkout main
git pull origin main
```

## 3. Crea tu rama

Usa tu nombre para no chocar con otros:

```powershell
git checkout -b pruebas/tu-nombre
```

## 4. Crea tu archivo

Tu archivo va en **tu carpeta** de `api/tests/unit/equipo/`:

| Integrante | Carpeta | Archivo base | Archivo avanzado |
|---|---|---|---|
| Andrés Durán | `integrante_1_validaciones` | `test_integrante_1_validaciones.py` (ya existe) | `test_reto_avanzado.py` |
| Sebastián Samacá | `integrante_2_seguridad` | `test_integrante_2_seguridad.py` | `test_reto_avanzado.py` |
| Dairon Salazar | `integrante_3_citas` | `test_integrante_3_citas.py` (ya existe) | `test_reto_avanzado.py` |
| Kevin Pinzón | `integrante_4_datos` | `test_integrante_4_datos.py` | `test_reto_avanzado.py` |

Los nombres exactos de las pruebas están en:

- [`CONTRATO_PRUEBAS_PENDIENTES.md`](CONTRATO_PRUEBAS_PENDIENTES.md) para la ronda base.
- [`RETO_AVANZADO.md`](RETO_AVANZADO.md) para la ronda avanzada.

## 5. Prueba antes de subir

```powershell
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\integrante_X -q
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py --integrante <clave>
.\venv\Scripts\python.exe scripts\mutar_entrega.py --integrante <clave> --ronda <ronda>
```

Cambia `integrante_X` y `<clave>` por los tuyos:

| Integrante | `<clave>` |
|---|---|
| Andrés | `andres` |
| Sebastián | `sebastian` |
| Dairon | `dairon` |
| Kevin | `kevin` |

## 6. Sube solo tu archivo

```powershell
git add api/tests/unit/equipo/integrante_X/tu_archivo.py
git commit -m "test(equipo): entrega de <tu nombre>"
git push origin pruebas/tu-nombre
```

No subas cambios de otros módulos, ni el Excel, ni archivos de configuración.

## 7. Abre el Pull Request

1. Entra a tu fork en GitHub.
2. Pulsa **Compare & pull request**.
3. Base: `Ricy24/plomaap_django` → `main`.
4. Compare: `TU-USUARIO/plomaap_django` → `pruebas/tu-nombre`.
5. Llena la plantilla del PR (checklist).
6. Pulsa **Create pull request**.

## 8. Espera los checks

El PR ejecuta automáticamente:

| Check | Qué valida |
|---|---|
| `calidad` | lint, duplicados y contrato |
| `unit-sqlite` | tus pruebas en SQLite |
| `unit-postgres` | tus pruebas en PostgreSQL |
| `unit-mysql` | tus pruebas en MySQL |
| `integration-postgres` | API e integración |
| `mutacion` | que tus pruebas detecten fallos |
| `required` | que todo lo anterior pase |

Si algo está en rojo:

1. Abre la pestaña **Checks** del PR.
2. Lee el paso que falló.
3. Corrige en tu rama.
4. Vuelve a hacer `git add`, `git commit` y `git push`.
5. El PR se actualiza solo.

## 9. Revisión y merge

El responsable revisa el PR y, si todo está bien, lo mergea. Nadie puede
mergear su propio PR.

## Reglas para no perder tiempo

- Un PR por integrante y por ronda.
- Solo tu archivo.
- Nombres exactos, sin pruebas extra.
- Sin copiar pruebas de otro compañero.
- Sin `mock`, `monkeypatch`, `skip`, `xfail`, `parametrize`, `random` ni `sleep`.
- Si no puedes explicar una prueba sin abrir el archivo, no está lista.

## Si algo no carga

- Verifica que el fork sea tuyo y que la rama esté actualizada con `main`.
- Si GitHub dice que no tienes permiso, estás intentando subir a
  `Ricy24/plomaap_django` en vez de a tu fork.
- Si el PR no muestra checks, espera unos segundos y recarga.
