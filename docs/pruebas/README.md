# Pruebas del equipo

Índice de la parte de pruebas. Empieza por el documento de tu ronda.

| Documento | Para qué sirve |
|---|---|
| [`ASIGNACION_PRUEBAS_EQUIPO.md`](ASIGNACION_PRUEBAS_EQUIPO.md) | Estructura por integrante, estado y comandos |
| [`CONTRATO_PRUEBAS_PENDIENTES.md`](CONTRATO_PRUEBAS_PENDIENTES.md) | Ronda base: archivos y nombres pendientes |
| [`RETO_AVANZADO.md`](RETO_AVANZADO.md) | Ronda avanzada: 5 pruebas extra por integrante |
| [`GUIA_PRUEBAS_UNITARIAS.md`](GUIA_PRUEBAS_UNITARIAS.md) | Cómo está organizada la suite y cómo se escribe una prueba |
| [`RECURSOS.md`](RECURSOS.md) | Documentación y videos por tema |
| [`PASO_A_PASO.md`](PASO_A_PASO.md) | Guía corta para el responsable y para cada integrante |
| [`COMO_SUBIR.md`](COMO_SUBIR.md) | Fork, rama, commit y Pull Request paso a paso |
| [`../../TESTING.md`](../../TESTING.md) | Pipeline completo, cobertura, integración y CI |

## Regla general

El repositorio **no contiene las respuestas**. Los nombres de las pruebas son
públicos; el comportamiento esperado se deduce leyendo el código. La solución de
referencia vive fuera del repositorio y solo la usa el responsable para calibrar
el reto.

## Comandos rápidos

```powershell
# Ver qué falta
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py

# Ejecutar solo la entrega del equipo
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q

# Verificar todo antes de subir
.\venv\Scripts\python.exe scripts\verificar_todo.py --rapido
```
