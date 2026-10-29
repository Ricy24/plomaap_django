# Asignación de pruebas por integrante

Cada integrante tiene una carpeta propia. Así trabajan en paralelo sin pisarse
y el pipeline identifica la entrega por ruta.

```text
api/tests/unit/equipo/
  integrante_1_validaciones/   Andrés Durán
    test_integrante_1_validaciones.py   (base, entregada)
    test_reto_avanzado.py               (avanzada, pendiente)
  integrante_2_seguridad/      Sebastián Samacá
    test_integrante_2_seguridad.py      (base, pendiente)
    test_reto_avanzado.py               (avanzada, pendiente)
  integrante_3_citas/          Dairon Salazar
    test_integrante_3_citas.py          (base, entregada)
    test_reto_avanzado.py               (avanzada, pendiente)
  integrante_4_datos/          Kevin Pinzón
    test_integrante_4_datos.py          (base, pendiente)
    test_reto_avanzado.py               (avanzada, pendiente)
```

## Estado

| Integrante | Base | Avanzada | Total |
|---|---|---|---:|
| Andrés Durán | Entregada (10) | Pendiente (5) | 15 |
| Sebastián Samacá | Pendiente (10) | Pendiente (5) | 15 |
| Dairon Salazar | Entregada (10) | Pendiente (5) | 15 |
| Kevin Pinzón | Pendiente (10) | Pendiente (5) | 15 |

- Ronda base: [`CONTRATO_PRUEBAS_PENDIENTES.md`](CONTRATO_PRUEBAS_PENDIENTES.md)
- Ronda avanzada: [`RETO_AVANZADO.md`](RETO_AVANZADO.md)

## Cómo ejecutar

```powershell
# Solo las entregas del equipo
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q

# Una carpeta
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\integrante_2_seguridad -q

# Suite unitaria completa (regresión + equipo)
.\venv\Scripts\python.exe -m pytest -m unit -q
```

## Reglas de oro

1. **Archivo y nombres fijos**: no cambies rutas ni nombres de pruebas.
2. **Sin copias**: el pipeline rechaza nombres repetidos dentro de una carpeta y
   cuerpos idénticos en cualquier carpeta.
3. **Sin atajos**: no se permiten mocks, `skip`, `xfail`, `parametrize`, `random`
   ni leer el código fuente en tiempo de ejecución.
4. **Dos motores, tres bases**: SQLite, PostgreSQL y MySQL. GitHub levanta cada
   base; el integrante no instala nada.
5. **Roturas**: la entrega debe detectar fallos inyectados (60 % base, 70 %
   avanzada). Una prueba que solo verifica que "no explota" no detecta nada.
6. **Evidencia automática**: el Excel no se llena a mano. El job `informe` genera
   `informe_entrega.xlsx` con las filas aprobadas.

## Evidencia

| Archivo | Contenido | Visibilidad |
|---|---|---|
| `docs/pruebas/Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx` | Base con las 20 pruebas base entregadas (`UNIT-001` a `UNIT-020`) | Repositorio |
| `docs/.interno/Plan_de_Pruebas_PlomApp_SENA.xlsx` | Original con los 470 casos de regresión | Local, ignorado por Git |
| `informe_entrega.xlsx` | Informe generado por el pipeline | Artefacto de GitHub Actions |

El original de 470 casos **no se publica** y no se edita. El informe se regenera
desde la base de entrega y las pruebas que hayan cumplido todo.

## Reparto para la exposición

| Integrante | Tema | Pregunta que debe responder |
|---|---|---|
| Andrés Durán | Búsqueda y validaciones | ¿Cómo se normaliza una consulta y cómo se detecta un activo? |
| Sebastián Samacá | Seguridad y embeddings | ¿Qué pasa con un token vencido y con un vector de otra dimensión? |
| Dairon Salazar | Citas y recomendaciones | ¿Cómo se evita una doble reserva y cómo se penaliza un servicio reciente? |
| Kevin Pinzón | Perfil y eventos | ¿Cómo se guarda un atributo y qué pasa con un evento inválido? |
