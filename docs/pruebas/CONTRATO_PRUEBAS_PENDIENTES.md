# Contrato de las pruebas pendientes

Este documento fija **qué pruebas** debe entregar cada integrante y **qué función**
debe cubrir cada una. No incluye los resultados esperados: eso lo tienes que
deducir leyendo el código del proyecto.

| Integrante | Archivo a crear | Responsable |
|---|---|---|
| Sebastián Samacá | `api/tests/unit/equipo/test_integrante_2_seguridad.py` | Sebastián Samacá |
| Kevin Pinzón | `api/tests/unit/equipo/test_integrante_4_datos.py` | Kevin Pinzón |

---

## Formato obligatorio

Cada archivo debe empezar así:

```python
import pytest

pytestmark = pytest.mark.unit
```

Cada prueba debe tener exactamente este docstring:

```python
def test_nombre_del_contrato():
    """Caso: qué situación pruebas.
    Entrada: los datos exactos que usas.
    Esperado: el resultado que comprobaste al leer el código.
    Cubre: ruta/del/archivo.py::simbolo
    """
    # Arrange
    ...

    # Act
    ...

    # Assert
    assert resultado == valor_que_encontraste
```

Reglas del `assert`:

- Debe comparar de verdad (`==`, `!=`, `is True`, `in`, `>`, `<`, etc.).
- No sirve `assert True`, `assert 1` ni `assert resultado is not None`.
- Si la función debe lanzar un error, usa `with pytest.raises(...)`.

El nombre de la prueba y la ruta de `Cubre:` **no se pueden cambiar**: son los del
contrato. Si cambias uno, el pipeline rechaza la entrega.

---

## Sebastián Samacá - Seguridad y sesión

Archivo: `test_integrante_2_seguridad.py`
Módulos: `api/utils/jwt_utils.py` y `api/utils/decorators.py`

| # | Nombre exacto de la prueba | Debe cubrir | Pista |
|---|---|---|---|
| 1 | `test_generar_token_devuelve_texto` | `api/utils/jwt_utils.py::generate_token` | Mira qué tipo devuelve y cuántas partes tiene. |
| 2 | `test_token_contiene_identidad_del_usuario` | `api/utils/jwt_utils.py::decode_token` | Mira qué dato del usuario queda guardado. |
| 3 | `test_token_alterado_es_rechazado` | `api/utils/jwt_utils.py::decode_token` | Cambia un carácter y observa qué devuelve. |
| 4 | `test_token_expirado_es_rechazado` | `api/utils/jwt_utils.py::decode_token` | Genera uno ya vencido y observa qué devuelve. |
| 5 | `test_extraer_token_con_bearer` | `api/utils/jwt_utils.py::get_token_from_request` | Simula `Authorization: Bearer <token>`. |
| 6 | `test_extraer_token_sin_encabezado` | `api/utils/jwt_utils.py::get_token_from_request` | Simula una petición sin encabezado. |
| 7 | `test_identidad_del_token_es_entero` | `api/utils/jwt_utils.py::get_current_user_id` | Mira el tipo del dato que devuelve. |
| 8 | `test_vista_protegida_sin_token_responde_401` | `api/utils/decorators.py::jwt_required` | Mira el código HTTP cuando no hay token. |
| 9 | `test_vista_de_admin_rechaza_a_un_cliente` | `api/utils/decorators.py::admin_only` | Autentica un cliente y mira el código HTTP. |
| 10 | `test_jwt_optional_permite_peticion_sin_token` | `api/utils/decorators.py::jwt_optional` | Mira qué pasa con la petición sin token. |

---

## Kevin Pinzón - Perfil, eventos y recomendaciones

Archivo: `test_integrante_4_datos.py`
Módulos: `api/services/profile_service.py`, `api/services/event_service.py` y
`api/services/recommendation_service.py`

| # | Nombre exacto de la prueba | Debe cubrir | Pista |
|---|---|---|---|
| 1 | `test_registrar_atributo_nuevo` | `api/services/profile_service.py::record_attribute` | Mira qué queda guardado en la base. |
| 2 | `test_actualizar_atributo_existente` | `api/services/profile_service.py::record_attribute` | Guarda dos veces lo mismo y cuenta las filas. |
| 3 | `test_rechazar_fuente_desconocida` | `api/services/profile_service.py::record_attribute` | Usa una fuente que no esté en el catálogo. |
| 4 | `test_rechazar_confianza_fuera_de_rango` | `api/services/profile_service.py::record_attribute` | Usa una confianza fuera del rango permitido. |
| 5 | `test_consultar_atributos_de_entidad` | `api/services/profile_service.py::get_entity_attributes` | Guarda atributos y mira qué devuelve la consulta. |
| 6 | `test_eliminar_atributos_de_entidad` | `api/services/profile_service.py::delete_entity_attributes` | Guarda, borra y mira qué devuelve. |
| 7 | `test_registrar_evento_valido` | `api/services/event_service.py::track_event` | Mira qué se crea al registrar un evento permitido. |
| 8 | `test_evento_desconocido_no_rompe` | `api/services/event_service.py::track_event` | Mira qué devuelve con un evento que no existe. |
| 9 | `test_registrar_clic_en_recomendacion` | `api/services/recommendation_service.py::track_recommendation_click` | Mira qué se registra al marcar un clic. |
| 10 | `test_respetar_limite_de_recomendaciones` | `api/services/recommendation_service.py::generate_recommendations` | Pide más de los permitidos y cuenta cuántos vuelven. |

---

## Prohibiciones

- `assert True`, `assert 1`, `assert resultado is not None` o cualquier aserción
  que siempre pase.
- Pruebas vacías, con `pass` o solo con `print`.
- Copiar una prueba de otro integrante, aunque se cambien los nombres.
- Probar la función con `mock` de la propia función que se evalúa.
- Depender de internet, del correo real o de la base de datos de producción.
- Dejar pruebas sin docstring o con etiquetas diferentes.
- Renombrar las pruebas del contrato o agregar pruebas que no estén en él.

## Cómo se valida

Antes de entregar, ejecuta:

```powershell
.\venv\Scripts\python.exe scripts\check_test_duplicates.py
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
```

El pipeline ejecuta lo mismo y bloquea el Pull Request si algo falla.

## Cómo se llena el Excel

El archivo de evidencia **no se llena a mano**. Cuando tu entrega cumple el
contrato y las pruebas pasan, se registra con:

```powershell
.\venv\Scripts\python.exe scripts\registrar_entrega.py --integrante sebastian
.\venv\Scripts\python.exe scripts\registrar_entrega.py --integrante kevin
```

El script valida el contrato, ejecuta tus pruebas y, solo si todo está bien,
agrega tus 10 filas al Excel con tu nombre. Si algo falla, **no escribe nada**.

## Cómo se entrega en GitHub

No tienes permiso de escritura en el repositorio principal. El proceso es:

1. Haz un **fork** de `Ricy24/plomaap_django`.
2. Crea una rama con tu nombre en tu fork.
3. Sube tu archivo a **tu fork**.
4. Abre un Pull Request desde tu fork hacia `main`.
5. Espera: las pruebas deben pasar y el responsable debe aprobar.

Nada entra al repositorio sin pasar por ese proceso.

## Defensa oral

La entrega no termina con el PR aprobado. En la evaluación se elegirán **3 pruebas
al azar** de tu archivo y deberás explicar, sin leer el código:

- qué datos de entrada usaste y por qué,
- qué hace la función del proyecto que estás probando,
- qué pasaría si esa función se rompe,
- por qué tu aserción detecta el error.

Si no puedes explicar una prueba, esa prueba no cuenta.
