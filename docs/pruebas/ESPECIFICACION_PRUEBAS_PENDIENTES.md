# Especificación de las pruebas pendientes

Esta especificación aplica a las **20 pruebas pendientes** de:

| Integrante | Archivo | Módulos asignados |
|---|---|---|
| Sebastián Samacá | `api/tests/unit/equipo/test_integrante_2_seguridad.py` | `api/utils/jwt_utils.py`, `api/utils/decorators.py` |
| Kevin Pinzón | `api/tests/unit/equipo/test_integrante_4_datos.py` | `api/services/profile_service.py`, `api/services/event_service.py`, `api/services/recommendation_service.py` |

El pipeline **rechaza** la entrega si no cumple todo lo de este documento.

---

## 1. Entregable

- Un archivo `.py` por integrante, con **exactamente 10 pruebas**.
- Cada prueba debe ser independiente: no puede depender del orden de ejecución.
- El archivo debe empezar con:

```python
import pytest

pytestmark = pytest.mark.unit
```

## 2. Estructura obligatoria: Arrange - Act - Assert

Cada prueba debe tener las tres partes separadas por una línea en blanco y un
comentario que las identifique:

```python
def test_genera_token_con_tres_segmentos():
    """Caso: un usuario válido solicita un token.
    Entrada: id de usuario 42.
    Esperado: el token tiene 3 segmentos separados por punto.
    Cubre: api/utils/jwt_utils.py::generate_token
    """
    # Arrange
    usuario_id = 42

    # Act
    token = generate_token(usuario_id)

    # Assert
    assert len(token.split(".")) == 3
```

## 3. Docstring obligatorio

Cada prueba debe tener un docstring con **estas cuatro etiquetas exactas**, en
este orden:

| Etiqueta | Contenido |
|---|---|
| `Caso:` | Qué situación concreta se prueba, en una frase |
| `Entrada:` | Los datos exactos que se usan |
| `Esperado:` | El resultado exacto que se comprueba |
| `Cubre:` | `ruta/del/archivo.py::simbolo` |

Reglas de `Cubre:`:

- La ruta debe ser uno de los módulos asignados a tu archivo.
- El símbolo debe existir realmente en ese archivo (función, clase o constante).
- No se aceptan rutas inventadas ni símbolos que no estén definidos.
- Como mínimo debes cubrir **4 símbolos distintos** (integrante 2) o
  **6 símbolos distintos** (integrante 4) en las 10 pruebas.

## 4. Nombres de las pruebas

- Deben empezar con `test_`.
- Deben describir el comportamiento en español, no el número de prueba.
- Ejemplos válidos:
  - `test_token_alterado_es_rechazado`
  - `test_evento_desconocido_no_rompe_la_peticion`
- Ejemplos inválidos:
  - `test_1`, `test_caso2`, `test_prueba`
  - `test_genera_token` (no dice qué se espera)

## 5. Qué debe cubrir cada integrante

### Integrante 2 - Seguridad y sesión

Debe probar, como mínimo, estos comportamientos:

1. Generación de un token para un usuario.
2. Lectura del `sub` (identidad) dentro del token.
3. Rechazo de un token con la firma alterada.
4. Rechazo de un token vencido.
5. Extracción del token desde `Authorization: Bearer <token>`.
6. Comportamiento cuando no hay encabezado `Authorization`.
7. Una vista protegida sin token responde `401`.
8. Un usuario sin rol de administrador recibe `403` en una vista de admin.
9. El decorador `jwt_optional` deja pasar la petición sin token.
10. Conversión de la identidad del token a entero.

Puedes usar `RequestFactory` para simular peticiones. No levantes el servidor.

### Integrante 4 - Perfil, eventos y recomendaciones

Debe probar, como mínimo, estos comportamientos:

1. Registrar un atributo nuevo en el perfil.
2. Actualizar un atributo que ya existe sin duplicarlo.
3. Rechazar una fuente de dato que no está en el catálogo.
4. Rechazar una confianza fuera del rango permitido.
5. Eliminar todos los atributos de una entidad.
6. Registrar un evento válido.
7. Ignorar un evento desconocido sin romper la petición.
8. Lanzar error con un evento desconocido en modo estricto.
9. Registrar el clic en una recomendación.
10. Respetar el límite de resultados en las recomendaciones.

Usa las fábricas de `api/tests/factories.py` y la base SQLite en memoria.

## 6. Prohibiciones

- `assert True`, `assert 1` o cualquier aserción que siempre pase.
- Pruebas vacías, con `pass` o solo con `print`.
- Copiar una prueba de otro integrante, aunque se cambien los nombres.
- Probar la función con `mock` de la propia función que se evalúa.
- Depender de internet, del correo real o de la base de datos de producción.
- Dejar pruebas sin docstring o con etiquetas diferentes.

## 7. Validación automática

Antes de abrir el Pull Request, ejecuta en tu máquina:

```powershell
.\venv\Scripts\python.exe scripts\check_test_duplicates.py
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
```

Los tres comandos deben terminar sin errores. El pipeline ejecuta los mismos
controles y **bloquea el PR** si alguno falla.

## 8. Cómo entregar en GitHub

1. Haz un **fork** del repositorio `Ricy24/plomaap_django`.
2. Crea una rama con tu nombre, por ejemplo `pruebas/sebastian`.
3. Sube tus cambios a **tu fork** (no tienes permiso de escritura en el repo
   principal).
4. Abre un Pull Request desde tu fork hacia `main` del repositorio principal.
5. Espera la revisión: el responsable debe aprobar el PR y las pruebas deben
   pasar.

No se aceptan entregas por fuera de GitHub ni archivos enviados por chat.

## 9. Defensa oral

La entrega no termina con el PR aprobado. En la evaluación se elegirán
**3 pruebas al azar** de tu archivo y deberás explicar, sin leer el código:

- qué datos de entrada usaste y por qué,
- qué hace la función del proyecto que estás probando,
- qué pasaría si esa función se rompe,
- por qué tu aserción detecta el error.

Si no puedes explicar una prueba, esa prueba no cuenta.
