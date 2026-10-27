# Guía: 10 pruebas unitarias básicas de PlomApp

## ¿Qué es una prueba unitaria?

Una prueba unitaria revisa **una sola función** o **una sola regla** del código,
sin usar base de datos, sin levantar el servidor y sin internet.

En este caso probamos los validadores de `api/utils/validators.py`. Son funciones
que reciben un dato y devuelven `True` o `False`.

## ¿Dónde están?

```text
api/tests/unit/test_unit_10_basicas.py
```

En el Excel están en la hoja **Pruebas Unitarias**, como `UNIT-01` a
`UNIT-10`.

## ¿Cómo se ejecutan?

```powershell
cd C:\Users\Anrid\backend_plomaap
.\venv\Scripts\python.exe -m pytest api\tests\unit\test_unit_10_basicas.py -v
```

Resultado esperado:

```text
10 passed
```

## ¿Cómo está escrita cada prueba?

Todas siguen el patrón **AAA**:

| Parte | Qué significa | Ejemplo |
|---|---|---|
| Arrange | Preparar el dato | `email = "usuario@plomaap.com"` |
| Act | Ejecutar la función | `resultado = validate_email(email)` |
| Assert | Comprobar el resultado | `assert resultado is True` |

## Las 10 pruebas

| # | Prueba | Dato de entrada | Resultado esperado | Qué demuestra |
|---|---|---|---|---|
| 1 | `test_01_email_valido` | `usuario@plomaap.com` | `True` | Acepta un correo con formato correcto |
| 2 | `test_02_email_invalido` | `usuario@` | `False` | Rechaza un correo sin dominio |
| 3 | `test_03_telefono_valido` | `3229874810` | `True` | Acepta un teléfono de 10 dígitos |
| 4 | `test_04_telefono_invalido` | `123` | `False` | Rechaza un teléfono demasiado corto |
| 5 | `test_05_password_valido` | `PlomApp2026*` | `True` | Acepta una contraseña de 8 o más caracteres |
| 6 | `test_06_password_corto` | `1234567` | `False` | Rechaza una contraseña de 7 caracteres |
| 7 | `test_07_nombre_valido` | `Andrés` | `True` | Acepta un nombre de 2 o más caracteres |
| 8 | `test_08_nombre_corto` | `A` | `False` | Rechaza un nombre de una sola letra |
| 9 | `test_09_fecha_y_hora_validas` | `2026-11-02` / `09:00` | `True` | Acepta fecha y hora con formato correcto |
| 10 | `test_10_fecha_y_hora_invalidas` | `2026-13-01` / `09:00` | `False` | Rechaza un mes que no existe |

## Cómo explicar cada prueba en una frase

1. **Email válido:** verifico que un correo bien escrito sea aceptado.
2. **Email inválido:** verifico que un correo mal escrito sea rechazado.
3. **Teléfono válido:** verifico que un número de 10 dígitos sea aceptado.
4. **Teléfono inválido:** verifico que un número muy corto sea rechazado.
5. **Contraseña válida:** verifico que una contraseña de 8 caracteres o más sea aceptada.
6. **Contraseña corta:** verifico que una contraseña de 7 caracteres sea rechazada.
7. **Nombre válido:** verifico que un nombre normal sea aceptado.
8. **Nombre corto:** verifico que una sola letra sea rechazada.
9. **Fecha y hora válidas:** verifico que una fecha real y una hora correcta sean aceptadas.
10. **Fecha y hora inválidas:** verifico que un mes inexistente sea rechazado.

## ¿Por qué estas sí son unitarias?

- No usan base de datos.
- No usan el servidor ni el navegador.
- No usan internet.
- Prueban funciones pequeñas y aisladas.
- Son rápidas: las 10 corren en menos de un segundo.

## Consejos para la entrega

- No inventes resultados: ejecuta el comando y muestra el `10 passed`.
- No uses datos aleatorios; usa datos fijos para saber qué esperar.
- Cada prueba debe tener un nombre claro.
- Cada prueba debe revisar una sola cosa.
- Si una prueba falla, primero revisa si el dato de entrada o el resultado esperado está mal.
