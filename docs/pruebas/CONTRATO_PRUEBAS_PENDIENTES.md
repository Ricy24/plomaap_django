# Contrato · ronda base

Esta ronda ya está cerrada. Solo se entregan los archivos que faltan. **No hay
pistas ni resultados esperados**: el comportamiento se deduce leyendo el código.

## Archivos pendientes

| Integrante | Archivo |
|---|---|
| Sebastián Samacá | `api/tests/unit/equipo/integrante_2_seguridad/test_integrante_2_seguridad.py` |
| Kevin Pinzón | `api/tests/unit/equipo/integrante_4_datos/test_integrante_4_datos.py` |

## 1. Qué se entrega

Un archivo `.py` con **exactamente 10 pruebas**, con estos nombres y en este
orden. No se pueden cambiar ni agregar pruebas extra.

### Sebastián Samacá

Módulos: `api/utils/jwt_utils.py` y `api/utils/decorators.py`.

```text
test_token_lleva_el_id_como_texto
test_token_con_firma_alterada_se_descarta
test_token_vencido_se_descarta
test_esquema_bearer_ignora_mayusculas
test_token_sin_esquema_se_acepta
test_identidad_no_numerica_devuelve_none
test_token_de_usuario_inexistente_responde_401
test_usuario_inactivo_responde_401
test_tecnico_no_entra_a_vista_de_admin
test_cliente_no_entra_a_vista_de_tecnico
```

### Kevin Pinzón

Módulos: `api/services/profile_service.py` y `api/services/event_service.py`.

```text
test_decimal_entero_se_guarda_como_entero
test_decimal_con_fraccion_conserva_decimales
test_fecha_se_guarda_en_iso
test_segundo_registro_actualiza_sin_duplicar
test_fuente_fuera_del_catalogo_es_rechazada
test_confianza_fuera_de_rango_es_rechazada
test_eliminar_atributos_devuelve_la_cantidad
test_evento_invalido_no_lanza_sin_strict
test_evento_invalido_lanza_en_strict
test_metadata_vacia_se_guarda_como_dict
```

> El nombre de cada prueba dice qué comportamiento se espera. Qué función usar,
> qué datos pasar y qué comparar es tu trabajo.

## 2. Formato obligatorio

```python
import pytest

pytestmark = pytest.mark.unit


def test_nombre_del_contrato():
    """Caso: la situación que pruebas.
    Entrada: los datos exactos que usas.
    Esperado: lo que comprobaste al leer el código.
    Cubre: api/utils/jwt_utils.py::decode_token
    """
    # Arrange
    ...

    # Act
    ...

    # Assert
    assert resultado == valor_real
```

| Regla | Detalle |
|---|---|
| `Cubre:` | `ruta/del/modulo.py::simbolo`. La ruta debe ser uno de tus módulos y el símbolo debe existir. |
| Uso real | La prueba debe **llamar** al símbolo (o usar la constante), no solo nombrarlo. |
| Assert | Comparación real (`==`, `!=`, `in`, `is None`, `>`, ...) o `pytest.raises` con una excepción específica. |
| Tamaño | Máximo 25 líneas por prueba. |
| Símbolos | Al menos 3 símbolos distintos en todo el archivo. |
| Prohibido | `mock`, `monkeypatch`, `MagicMock`, `parametrize`, `skip`, `xfail`, `random`, `sleep` y leer el código fuente en tiempo de ejecución. |

Si necesitas base de datos, usa `@pytest.mark.django_db` y las fábricas de
`api/tests/factories.py`.

## 3. Cómo se aprueba

La entrega se acepta solo si pasa **todo** esto, automáticamente:

1. Cumple el formato.
2. Las 10 pruebas pasan en SQLite.
3. Las 10 pruebas pasan en PostgreSQL y en MySQL (lo corre GitHub).
4. El archivo detecta **al menos el 60 %** de los fallos inyectados en los
   símbolos que declaras en `Cubre:` y un mínimo absoluto de 6. Los fallos son
   invisibles: no sabes cuáles son ni cuántos.

El punto 4 significa que el sistema rompe el código a propósito y ejecuta tus
pruebas. Si tus pruebas se dan cuenta, cuentan. Una prueba que solo verifica que
"no explota" no detecta nada.

## 4. Antes de entregar

```powershell
.\venv\Scripts\python.exe scripts\check_test_duplicates.py
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py --solo-pendientes
.\venv\Scripts\python.exe scripts\mutar_entrega.py --integrante sebastian --ronda base
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
```

Cambia `sebastian` por `kevin` según el caso.

## 5. Entrega

No tienes permiso de escritura en `Ricy24/plomaap_django`:

1. Entra al repositorio y pulsa **Fork**.
2. En tu fork, crea una rama: `pruebas/tu-nombre`.
3. Sube **solo tu archivo**.
4. Abre un **Pull Request** desde tu fork hacia `main`.
5. El PR queda bloqueado hasta que pasen los checks y el responsable lo apruebe.

Si el PR queda en rojo, el detalle aparece en **Checks**. Corrige, sube otra vez
y espera.

## 6. Después de aprobado

El Excel de evidencia lo genera el sistema. No lo llenas tú. Tus 10 filas
aparecen con tu nombre en el informe de entrega.

## 7. Si te trabas

En [`RECURSOS.md`](RECURSOS.md) hay documentación y videos por tema. No hay
ayuda sobre las respuestas: solo sobre cómo se escribe una prueba.
