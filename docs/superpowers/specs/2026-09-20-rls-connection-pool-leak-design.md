# Bug: fuga de estado RLS entre requests por reuso de conexión del pool — Design

**Fecha:** 2026-09-20

## Contexto

Encontrado verificando en navegador el flujo de Solicitud de Salida (Spec 2026-09-19): `GET /api/contenedores/{id}/pin` devolvía 404 "Este contenedor no tiene PIN asociado" con un PIN real y visible en la base de datos, de forma 100% reproducible cada vez que la página de detalle (`GET /api/contenedores/{id}`, que usa `get_scoped_db`) se cargaba antes de pedir el PIN (que usa `get_db` plano).

## Causa raíz (verificada con diagnóstico directo, no supuesta)

`get_scoped_db` (`backend/app/api/deps.py`) fija dos GUCs personalizados de Postgres por request:

```python
await db.execute(text("SELECT set_config('app.rol', :rol, true)"), {"rol": user.rol.value})
await db.execute(text("SELECT set_config('app.patios_asignados', :patios, true)"), {"patios": ...})
```

El tercer argumento `true` los hace `LOCAL` (viven solo dentro de la transacción actual). El request nunca hace `commit()` explícito (es un `GET`); al cerrarse la sesión, SQLAlchemy hace `ROLLBACK`, que debería descartar el `SET LOCAL`.

Probado directamente contra Postgres (script en la sesión, reproducible):

```
1 fresh session (GUC nunca tocado)          -> current_setting('app.rol', true) = None (NULL real)
2 SET LOCAL 'admin' (misma transacción)     -> 'admin'
3 RESET app.rol (misma transacción)         -> ''
4 después de commit                          -> ''
5 sesión nueva, misma conexión del pool     -> ''
```

Postgres trata `app.rol` como una **GUC personalizada tipo placeholder** (no declarada en `postgresql.conf`). La primera vez que se toca (aunque sea con `SET LOCAL` y luego rollback), Postgres crea el placeholder en esa conexión con valor base `''` (cadena vacía) — **nunca vuelve a `NULL`**, ni con `RESET`, ni con rollback, ni con una sesión SQLAlchemy nueva sobre la misma conexión física. Es irreversible para la vida de esa conexión del pool.

La política RLS (`backend/app/alembic/versions/0006_rls_policies.py`) para `contenedores`/`movimientos`/`auditoria`:

```sql
USING (
  current_setting('app.rol', true) IS NULL
  OR current_setting('app.rol', true) = 'admin'
  OR patio_id::text = ANY(string_to_array(coalesce(current_setting('app.patios_asignados', true), ''), ','))
)
```

Una vez que `app.rol` queda en `''` (ni `NULL`, ni `'admin'`), **ninguna de las tres condiciones es verdadera** — la política bloquea todas las filas, para cualquier rol, incluido admin, en cualquier request posterior que reutilice esa conexión sin volver a llamar `get_scoped_db`.

**Alcance real:** `get_scoped_db` solo la usa `obtener_contenedor` (`GET /api/contenedores/{id}`) — un solo endpoint. Pero como el pool de conexiones (`create_async_engine(settings.database_url)`, pool por defecto tamaño 5) reutiliza conexiones entre requests no relacionados, **cualquier request posterior de cualquier usuario** que caiga en una conexión ya "tocada" por ese único endpoint queda ciego a `contenedores`/`movimientos`/`auditoria` — incluyendo escritura correcta pero lectura posterior fallida (los `INSERT` no se filtran, `WITH CHECK (true)`, pero los `SELECT` sí).

**Por qué nunca lo agarraron los 80 tests de pytest:** el fixture `client`/`db_session` (`backend/tests/conftest.py`) liga *todos* los "requests" de un test a **una sola conexión con savepoints anidados** (`join_transaction_mode="create_savepoint"`), nunca pasa por el pool real de `app.db.engine`. Ese patrón de aislamiento no reproduce el reuso de conexión entre requests independientes que sí ocurre en producción.

## Por qué el resto de los endpoints "funcionan" hoy

Todos los endpoints salvo `obtener_contenedor` usan `get_db` plano — nunca tocan los GUCs. Su autorización real (dueño del contenedor, rol, patio) se hace en Python (`WHERE cliente_id == user.cliente_id`, chequeos explícitos), no depende de RLS. Funcionan hoy **por accidente**: mientras el GUC nunca se toca, `current_setting(..., true) IS NULL` es verdadero y la política deja pasar todo sin filtrar. El bug es justamente que ese accidente se rompe en cuanto *cualquier* request toca el GUC una sola vez.

## Decisión de diseño

Dos cambios, ambos necesarios — uno solo no alcanza:

1. **Fijar los GUCs en cada request autenticado, siempre, sin depender de que quede "sin tocar".** Se mueve la lógica de `set_config` de `get_scoped_db` a `get_current_user` (`backend/app/api/deps.py`), que es dependencia de **todas** las rutas protegidas (directa o vía `require_roles`). Como FastAPI cachea la resolución de dependencias por request, el `db` que recibe `get_current_user` es el mismo objeto que después usa el handler — fijar ahí los GUCs los deja correctos antes de cualquier query de la ruta. Esto hace innecesario y elimina `get_scoped_db` (con esto, ya no hay una distinción "ruta con RLS" vs "ruta sin RLS" — todas quedan con el contexto correcto siempre). `obtener_contenedor` pasa a usar `get_db` plano como el resto.

   Con esto, ninguna ruta depende ya de que el GUC esté "sin tocar" (`IS NULL`) — todas lo fijan explícitamente con el rol real del usuario autenticado en cada request.

2. **La política RLS deja de tener una rama que falla abierta (`IS NULL OR ...`).** Ya no hace falta — el punto 1 garantiza que el GUC siempre está fijado por una fuente confiable antes de cualquier query. Se reemplaza `IS NULL OR` por una rama explícita para `cliente` (`current_setting('app.rol', true) = 'cliente'`): el rol `cliente` nunca estuvo filtrado por patio (su autorización es por `cliente_id`, en Python, ya implementada en cada endpoint) — dejar pasar explícitamente ese rol documenta la intención real en vez de depender de un efecto colateral de "GUC nunca tocado". Quitar la rama `IS NULL` cierra el fail-open por completo: cualquier conexión que por algún motivo futuro no pase por `get_current_user` queda bloqueada (fail-closed) en vez de expuesta sin filtro.

## Alternativas consideradas y descartadas

- **Solo agregar `OR current_setting('app.rol', true) = ''` a la política:** band-aid, no arregla la causa — sigue dependiendo de un estado "vacío" ambiguo, y no explica ni corrige por qué una conexión terminó en ese estado para el usuario equivocado. Rechazada.
- **Usar `set_config(..., false)` (session-level) en vez de `true` (local):** no resuelve nada — el problema no es local-vs-session, es que el placeholder nunca vuelve a `NULL`; con `false` el valor quedaría fijo indefinidamente en el pool con el rol del *último* usuario que lo tocó, ligeramente peor (persiste sin ni siquiera un rollback de por medio). Rechazada.
- **Deshabilitar RLS y mover todo el filtrado a Python:** correcto a largo plazo para `contenedores` (ya está mayormente ahí), pero cambia el modelo de seguridad completo del proyecto (`movimientos`, `auditoria`) sin necesidad para cerrar este bug puntual. Fuera de alcance.

## Testing

El fixture existente (`db_session`/`client`, una sola conexión con savepoints) **no puede reproducir el bug** — se necesita un test que use el engine real (`app.db.engine`/`SessionLocal`) con una conexión explícita reutilizada entre dos "requests" simulados, igual que el diagnóstico manual de esta sesión.

- `backend/tests/test_deps_rls_context.py` (nuevo): usa `engine.connect()` directo (una sola conexión física, reuso garantizado, determinístico) para simular dos requests consecutivos con roles distintos (`admin` → `operador`) y confirmar que `get_current_user` deja el GUC en el valor correcto para el *segundo* request, no en un residuo del primero.
- `backend/tests/test_rls.py` (ampliado): rama `cliente` de la política dejando ver filas sin restricción de patio; confirmar que sin ningún GUC fijado (simulando una conexión que se saltara `get_current_user`, escenario que ya no debería ocurrir) la política ahora bloquea (fail-closed) en vez de dejar pasar.
- Suite completa de pytest debe seguir en verde (ningún endpoint depende hoy de la rama `IS NULL` a propósito).
- Verificación manual en navegador: repetir la secuencia exacta que reprodujo el bug (`GET /{id}` como admin → `GET /{id}/pin`) contra el servidor real, confirmar 200 con el PIN correcto.

## Fuera de alcance

- Rediseñar el modelo de RLS para usar `cliente_id` en la política en vez de bypass total del rol `cliente` (la autorización por dueño ya está en Python en cada endpoint; duplicarla en RLS es trabajo futuro, no necesario para cerrar este bug).
- Cambiar el tamaño o configuración del pool de conexiones.
- Cualquier cambio al fixture `db_session`/`client` existente (se deja intacto; el nuevo test usa el engine real por separado).

## Self-review

- Causa raíz verificada con un script de diagnóstico real contra Postgres, no asumida — ver la secuencia de 5 pasos arriba.
- Confirmado con `grep` que `get_scoped_db` tiene un solo call site (`obtener_contenedor`) antes de decidir eliminarla.
- Confirmado que `WITH CHECK (true)` en la política existente significa que los `INSERT` nunca estuvieron filtrados — el bug es puramente de lectura (`SELECT`/`USING`), consistente con los síntomas observados (solicitudes se crean bien, se leen mal).
- Sin placeholders ni TBD.
