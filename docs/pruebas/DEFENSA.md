# Defensa oral de la entrega

La entrega no se aprueba solo porque el pipeline esté en verde. El responsable
hace una defensa corta para confirmar que el integrante entiende lo que escribió.

## Cómo se genera

```powershell
.\venv\Scripts\python.exe scripts\defensa_entrega.py --integrante sebastian --preguntas 3
.\venv\Scripts\python.exe scripts\defensa_entrega.py --integrante kevin --ronda avanzada --preguntas 5
```

El script elige pruebas al azar y arma preguntas sobre el caso, el dato de
entrada, el resultado esperado y el símbolo cubierto. **No muestra respuestas.**

## Reglas

1. El integrante responde **sin abrir el archivo**.
2. Debe explicar por qué eligió ese dato de entrada y qué rama del código cubre.
3. Debe poder decir qué pasaría si el dato cambia a un caso límite.
4. Debe explicar por qué su prueba no es una copia de otra.
5. Si falla una respuesta, se repite la defensa con otras pruebas.

## Criterio de aprobación

| Nivel | Criterio |
|---|---|
| Aprobado | Responde las 3 preguntas con precisión y justifica los datos. |
| Aprobado con observación | Responde 2 de 3 y corrige con una pista mínima. |
| No aprobado | No puede explicar el assert o confunde el símbolo cubierto. |

## Por qué existe

Una prueba generada sin entender el código suele:

- usar datos que no ejercitan la rama importante;
- comparar contra el valor que devuelve la función en vez de un valor esperado;
- repetir el mismo caso con otro nombre;
- no detectar ninguna rotura.

La defensa y el puntaje de mutación detectan eso. La solución de referencia vive
**fuera del repositorio** y solo la usa el responsable para calibrar el reto; no
se comparte con el equipo ni se publica en GitHub.
