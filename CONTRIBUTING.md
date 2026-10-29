# Cómo contribuir

## Si eres integrante del equipo y entregas pruebas

Empieza por tu carpeta:

| Integrante | Carpeta | Documento |
|---|---|---|
| Andrés Durán | `api/tests/unit/equipo/integrante_1_validaciones/` | [`LEEME.md`](api/tests/unit/equipo/integrante_1_validaciones/LEEME.md) |
| Sebastián Samacá | `api/tests/unit/equipo/integrante_2_seguridad/` | [`LEEME.md`](api/tests/unit/equipo/integrante_2_seguridad/LEEME.md) |
| Dairon Salazar | `api/tests/unit/equipo/integrante_3_citas/` | [`LEEME.md`](api/tests/unit/equipo/integrante_3_citas/LEEME.md) |
| Kevin Pinzón | `api/tests/unit/equipo/integrante_4_datos/` | [`LEEME.md`](api/tests/unit/equipo/integrante_4_datos/LEEME.md) |

Resumen del flujo:

1. Haz **fork** de `Ricy24/plomaap_django`.
2. Crea una rama `pruebas/tu-nombre`.
3. Crea **solo tu archivo** en tu carpeta.
4. Ejecuta `python -m pytest api/tests/unit/equipo/integrante_X -q`.
5. Ejecuta `python scripts/check_entrega_equipo.py --integrante <clave>`.
6. Ejecuta `python scripts/mutar_entrega.py --integrante <clave> --ronda <ronda>`.
7. Sube la rama a tu fork y abre un **Pull Request** hacia `main`.
8. Espera los checks y la revisión del responsable.

El paso a paso con comandos está en
[`docs/pruebas/COMO_SUBIR.md`](docs/pruebas/COMO_SUBIR.md).

## Antes de abrir el PR

- [ ] Solo cambié mi carpeta.
- [ ] Los nombres de archivo y de prueba son los del contrato.
- [ ] Las pruebas pasan en local.
- [ ] No copié pruebas de otro integrante.
- [ ] No usé `mock`, `monkeypatch`, `skip`, `xfail`, `parametrize`, `random` ni `sleep`.
- [ ] Puedo explicar cada prueba sin abrir el archivo.

## Reglas del repositorio

- `main` está protegida: requiere checks en verde y aprobación del responsable.
- No se permite push directo, force push ni borrar la rama.
- La entrega se valida en SQLite, PostgreSQL y MySQL.
- El pipeline mide si tus pruebas detectan fallos inyectados.
- La solución de referencia no está en el repositorio.
