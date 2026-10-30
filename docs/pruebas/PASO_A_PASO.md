# Paso a paso

## Para el responsable

### 1. Instalar herramientas

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 2. Verificar el estado

```powershell
.\venv\Scripts\python.exe scripts\check_entrega_equipo.py
.\venv\Scripts\python.exe -m pytest api\tests\unit\equipo -q
```

### 3. Excel actualizado automáticamente (configuración única)

El job `informe` genera `docs/pruebas/Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx`
con las filas de quien cumplió todo y lo guarda en el repositorio automáticamente.
Para que el commit automático funcione, crea un **Personal Access Token** una sola vez:

1. Ve a **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Pulsa **Generate new token**.
3. Nombre: `plomaap-informe`. Expiración: la que prefieras.
4. Repository access: **Only select repositories** → `Ricy24/plomaap_django`.
5. Permissions → **Contents: Read and write**.
6. Genera y **copia el token**.
7. En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `GIT_PUSH_TOKEN`
   - Secret: el token copiado.

Sin este token el Excel se sigue generando como artefacto descargable, pero no se
commitea automáticamente al repositorio.

### 4. Calibrar un reto antes de publicarlo

   La solución de referencia está fuera del repositorio, en la carpeta privada
   del responsable. Cópiala temporalmente a la ruta que espera el pipeline,
   ejecuta:

   ```powershell
   .\venv\Scripts\python.exe scripts\mutar_entrega.py --integrante <clave> --ronda <ronda>
   ```

   Si la referencia no alcanza el mínimo, ajusta el umbral o mejora la
   referencia. Después **borra la copia** del repositorio.

4. **Revisar el PR**

   - El PR debe tocar solo la carpeta del integrante.
   - Todos los checks deben estar en verde.
   - Si aprueba, mergea. El job `informe` genera el Excel.

5. **Evidencia interna**

   El archivo de 470 casos está en `docs/.interno/`. Esa carpeta está en
   `.gitignore`: no se publica y no se edita. La base versionada es
   `docs/pruebas/Plan_de_Pruebas_PlomApp_SENA_entrega_equipo.xlsx`.

## Para cada integrante

1. Entra a tu carpeta en `api/tests/unit/equipo/integrante_*`.
2. Lee tu contrato:
   - ronda base: [`CONTRATO_PRUEBAS_PENDIENTES.md`](CONTRATO_PRUEBAS_PENDIENTES.md);
   - ronda avanzada: [`RETO_AVANZADO.md`](RETO_AVANZADO.md).
3. Abre los módulos asignados y responde, para cada nombre de prueba:
   - ¿qué función voy a llamar?
   - ¿qué dato de entrada ejercita la rama?
   - ¿qué valor espero y por qué?
   - ¿qué símbolo declaro en `Cubre:`?
4. Escribe el archivo con los nombres exactos. No agregues pruebas extra.
5. Ejecuta:

   ```powershell
   .\venv\Scripts\python.exe -m pytest api\tests\unit\equipo\integrante_X -q
   .\venv\Scripts\python.exe scripts\check_entrega_equipo.py --integrante <clave>
   .\venv\Scripts\python.exe scripts\mutar_entrega.py --integrante <clave> --ronda <ronda>
   ```

6. Si todo pasa, sube **solo tu archivo** a una rama `pruebas/tu-nombre` en tu
   fork y abre un PR hacia `main`. El paso a paso con comandos está en
   [`COMO_SUBIR.md`](COMO_SUBIR.md).
7. Espera los checks. Si algo está en rojo, corrige y vuelve a subir.

## Regla de oro

No hay atajo. El pipeline rompe el código a propósito y comprueba si tus pruebas
se dan cuenta. Una prueba que solo verifica que "no explota" no detecta nada.
