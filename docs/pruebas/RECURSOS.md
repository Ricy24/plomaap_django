# Recursos para las entregas

Documentación para aprender a escribir las pruebas. **No contiene respuestas**
del proyecto: solo explica las herramientas.

## Lo mínimo de pytest

| Tema | Enlace |
|---|---|
| Escribir `assert` y qué significa un fallo | https://docs.pytest.org/en/stable/how-to/assert.html |
| Ejecutar y filtrar pruebas | https://docs.pytest.org/en/stable/how-to/run.html |
| Marcar pruebas (`pytestmark`, `django_db`) | https://docs.pytest.org/en/stable/how-to/mark.html |
| `pytest.raises` para errores esperados | https://docs.pytest.org/en/stable/how-to/assert.html#assertions-about-expected-exceptions |
| Fixtures y `conftest.py` | https://docs.pytest.org/en/stable/how-to/fixtures.html |
| Salida detallada y `-x` | https://docs.pytest.org/en/stable/how-to/usage.html |

## Django y base de datos

| Tema | Enlace |
|---|---|
| Pruebas con bases de datos en Django | https://docs.djangoproject.com/en/stable/topics/testing/overview/ |
| `pytest-django`: `@pytest.mark.django_db` | https://pytest-django.readthedocs.io/en/latest/database.html |
| Fábricas de datos (`factory_boy`) | https://factoryboy.readthedocs.io/en/stable/ |
| Consultas al ORM desde una prueba | https://docs.djangoproject.com/en/stable/topics/db/queries/ |
| `JsonResponse` y cómo leer su contenido | https://docs.djangoproject.com/en/stable/ref/request-response/#jsonresponse-objects |
| `RequestFactory` para simular peticiones | https://docs.djangoproject.com/en/stable/topics/testing/advanced/#django.test.RequestFactory |

## Seguridad y tokens

| Tema | Enlace |
|---|---|
| `PyJWT`: codificar y decodificar | https://pyjwt.readthedocs.io/en/stable/usage.html |
| Errores de PyJWT (`ExpiredSignatureError`, `InvalidTokenError`) | https://pyjwt.readthedocs.io/en/stable/api.html#exceptions |
| Cabeceras HTTP en Django (`HTTP_AUTHORIZATION`) | https://docs.djangoproject.com/en/stable/ref/request-response/ |
| Decoradores en Python | https://docs.python.org/3/glossary.html#term-decorator |

## Datos, tiempo y serialización

| Tema | Enlace |
|---|---|
| `Decimal` y aritmética exacta | https://docs.python.org/3/library/decimal.html |
| `datetime.date` y `isoformat` | https://docs.python.org/3/library/datetime.html#datetime.date.isoformat |
| Campos JSON en Django | https://docs.djangoproject.com/en/stable/ref/models/fields/#jsonfield |
| Congelar el tiempo con `freezegun` | https://freezegun.readthedocs.io/en/latest/ |

## Búsqueda, embeddings y pgvector

| Tema | Enlace |
|---|---|
| Similitud coseno (concepto) | https://es.wikipedia.org/wiki/Similitud_coseno |
| pgvector: operadores y distancia | https://github.com/pgvector/pgvector |
| `vector(512)` e índice HNSW | https://github.com/pgvector/pgvector#hnsw |
| JSON en Python | https://docs.python.org/3/library/json.html |

## Mutación y calidad

| Tema | Enlace |
|---|---|
| Qué es una prueba de mutación | https://en.wikipedia.org/wiki/Mutation_testing |
| Cómo se mide la calidad de una prueba | https://stryker-mutator.io/docs/ |
| Cobertura con `coverage.py` | https://coverage.readthedocs.io/ |

## Videos

Búsquedas directas (elige el que entiendas, no hay uno obligatorio):

- pytest desde cero: https://www.youtube.com/results?search_query=pytest+desde+cero+espa%C3%B1ol
- pytest + Django: https://www.youtube.com/results?search_query=pytest+django+tutorial+espa%C3%B1ol
- factory_boy: https://www.youtube.com/results?search_query=factory+boy+django+testing
- PyJWT: https://www.youtube.com/results?search_query=jwt+python+pyjwt+tutorial
- freezegun: https://www.youtube.com/results?search_query=freezegun+python+pytest
- pgvector: https://www.youtube.com/results?search_query=pgvector+postgresql+tutorial
- mutation testing: https://www.youtube.com/results?search_query=mutation+testing+python+pytest

## Regla de oro

Si no sabes qué esperar de una función, **no la pruebes todavía**: ábrela,
léela y ejecútala en la consola hasta entenderla.

```powershell
.\venv\Scripts\python.exe manage.py shell
```

> La referencia de respuestas no está en el repositorio. El pipeline mide si tus
> pruebas detectan fallos reales; no hay atajo para eso.
