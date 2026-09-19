# Portal Cliente — Spec 2: PIN de 4 dígitos — Design

**Fecha:** 2026-09-19

## Contexto

Continuación de `docs/superpowers/specs/2026-09-18-portal-cliente-spec1-design.md`, que partió el pedido original en 3 specs. Spec 1 (fundación: alta de clientes, registro, solicitud de entrada) ya está implementada y commiteada (commit `2cdb245`, 63/63 tests). Esta spec cubre el punto 2: PIN de 4 dígitos que el cliente recibe al solicitar entrada y que el operador verifica en portería antes de dejar pasar el contenedor.

`EstadoContenedor` ya define 12 estados incluyendo `QR_INGRESO_EMITIDO` y `EN_PORTERIA`, heredados del máquina de estados original (`docs/superpowers/plans/2026-09-14-backend-foundation.md:1638`), que dejó "QR firmado/portería" explícitamente fuera de alcance del plan de fundación. El PIN es un mecanismo de verificación independiente del QR (Spec 3, aún no diseñada) — no reutiliza `QR_INGRESO_EMITIDO`, usa directamente `EN_PORTERIA` como estado de llegada confirmada.

`POST /movimientos` (`backend/app/api/routes/movimientos.py`) hoy no valida el `estado` del contenedor antes de ubicarlo — cualquier contenedor puede pasar a `UBICADO` sin importar su estado previo. Esta spec no cambia eso (ver Decisiones).

## Decisiones confirmadas con el usuario

- El PIN se envía únicamente al usuario que creó la solicitud (no a todo el personal de la empresa cliente).
- Verificar el PIN en portería **no bloquea** `POST /movimientos`. Solo cambia el `estado` del contenedor como registro/auditoría de que pasó por portería. `movimientos.py` no se toca — fuera de alcance de esta spec.
- Sin límite de reintentos de PIN incorrecto. Igual que el código de verificación de Spec 1: el operador puede volver a intentar, `422` con mensaje claro, sin bloqueo ni rate limiting.

## Arquitectura

### Backend

**Migración Alembic nueva** — agrega a `contenedores`:
- `pin_confirmacion: str | None` (`VARCHAR(4)`)
- `pin_verificado_en: datetime | None` (`TIMESTAMPTZ`)
- `pin_verificado_por: uuid.UUID | None` (FK `usuarios.id`)

`backend/app/models/contenedor.py`: agregar los tres campos anteriores a `Contenedor`.

`backend/app/schemas/contenedor.py`: nuevos schemas
- `PinOut { pin_confirmacion: str }`
- `PinVerificar { numero_contenedor: str, pin: str }` (el `pin` valida longitud exacta 4 y que sean dígitos, mismo estilo de validador que `validar_iso6346`).

`ContenedorOut` **no cambia** — `pin_confirmacion` nunca se serializa ahí. Esto es deliberado: `GET /api/contenedores/{id}` es accesible por cualquier usuario autenticado (`get_current_user`, sin `require_roles`), y el PIN debe quedar restringido a admin + cliente dueño. Mezclar visibilidad condicional dentro de un único `response_model` compartido por todos los roles es más frágil que mantener el campo fuera del schema y exponerlo solo por un endpoint dedicado con su propio chequeo de rol.

`backend/app/api/routes/contenedores.py`:
- `solicitar_contenedor` (ya existe, Spec 1) se extiende: después de crear el `Contenedor` y hacer `flush()`, genera `pin = f"{secrets.randbelow(10000):04d}"` (módulo `secrets`, no `random` — no debe ser predecible), lo asigna a `contenedor.pin_confirmacion`, y llama a `enviar_correo` (reutilizado de `backend/app/core/email.py`, Spec 1) con el PIN al correo del `user` que hizo la solicitud. Mismo manejo de fallo que Spec 1: si `enviar_correo` lanza, se responde `502` ("No se pudo enviar el correo con tu PIN, contacta al administrador o consúltalo después") pero el `Contenedor` ya quedó commiteado (recuperable vía el endpoint de PIN de abajo).
- Nuevo `GET /api/contenedores/{id}/pin` (`Depends(get_current_user)`, sin `require_roles` — el chequeo es condicional): si `user.rol == ADMIN` o (`user.rol == CLIENTE` y `contenedor.cliente_id == user.cliente_id`) → devuelve `PinOut`. Si no → `403`. Si el contenedor no existe → `404`. Si `pin_confirmacion is None` (no debería pasar, pero por robustez) → `404` ("Este contenedor no tiene PIN asociado").
- Nuevo `POST /api/contenedores/verificar-pin` (`require_roles(OPERADOR, SUPERVISOR, ADMIN)` — reutiliza `_ROLES_ESCRITURA` ya definido en el archivo). Body `PinVerificar`. Busca `Contenedor` por `numero_contenedor` (el operador solo conoce el número físico impreso en el contenedor, no el UUID interno — evita tener que construir una pantalla de búsqueda/listado que hoy no existe). Si no hay ningún contenedor con ese número → `404`. Si `estado != SOLICITUD_INGRESO` → `409` ("Este contenedor no está pendiente de verificación de PIN"). Si `pin_confirmacion != payload.pin` → `422` ("PIN incorrecto"). Si coincide: `estado = EN_PORTERIA`, `pin_verificado_en = now()`, `pin_verificado_por = user.id`, registra auditoría (`accion="verificar_pin"`, patrón igual a los demás handlers del archivo), `commit()`, devuelve `ContenedorOut`.

Nota: si dos contenedores distintos comparten `numero_contenedor` y ambos están en `SOLICITUD_INGRESO` (caso borde no contemplado — `numero_contenedor` no tiene constraint de unicidad en el esquema actual), la búsqueda toma el primero que devuelva la query. Aceptado como fuera de alcance; no se agrega constraint de unicidad en esta spec.

### Frontend

- `frontend/app/porteria/page.tsx` (nuevo, con `AuthGuard`, visible solo si `user.rol` es `operador`, `supervisor` o `admin`): formulario `{numero_contenedor, pin}` → `POST /api/contenedores/verificar-pin`. Mensaje de éxito ("Contenedor verificado, estado: en portería") o error (`422`/`404`/`409` mostrados tal cual los devuelve la API).
- `frontend/app/contenedores/[id]/page.tsx` (ya existe): agrega botón "Ver PIN" visible solo si `user.rol === "admin"` → llama `GET /pin`, muestra el PIN en pantalla (no se persiste en estado global, solo se pide on-demand).
- `frontend/lib/api.ts`: nuevas funciones `obtenerPin(token, id): Promise<{pin_confirmacion: string}>`, `verificarPin(token, payload: {numero_contenedor, pin}): Promise<Contenedor>`.
- `NavBar`: nuevo link "Portería" visible para roles `operador`, `supervisor`, `admin`.

## Validación y manejo de errores

- `PinVerificar.pin`: exactamente 4 caracteres, todos dígitos (validador Pydantic, `422` de FastAPI si no cumple el schema, antes de tocar la DB).
- `numero_contenedor` no encontrado → `404`.
- Contenedor encontrado pero no en `SOLICITUD_INGRESO` (ya verificado, o en cualquier otro estado) → `409`.
- PIN no coincide → `422`, sin límite de reintentos (confirmado con el usuario).
- `GET /pin` con rol no autorizado (operador, guardia, despachador, o cliente que no es dueño) → `403`.
- Falla de SendGrid al enviar el PIN → `502`, contenedor ya creado, recuperable vía `GET /pin`.

## Testing

**Backend:**
- `test_contenedores_api.py` (ampliado):
  - `POST /solicitar` genera `pin_confirmacion` de 4 dígitos y llama a `enviar_correo` (mockeado, no se llama a la API real).
  - `GET /{id}/pin` como admin devuelve el PIN; como cliente dueño devuelve el PIN; como cliente de otra empresa da `403`; como operador da `403`; contenedor sin PIN o inexistente da `404`.
  - `POST /verificar-pin` con PIN correcto y estado `SOLICITUD_INGRESO` cambia a `EN_PORTERIA` y registra `pin_verificado_por`/`pin_verificado_en`; con PIN incorrecto da `422` y no cambia estado; con contenedor en otro estado da `409`; con `numero_contenedor` inexistente da `404`; como cliente (rol no autorizado) da `403`.

**Frontend:** tests para `/porteria` (formulario, éxito, errores `422`/`404`/`409`), botón "Ver PIN" en `/contenedores/[id]` (solo admin), y las dos funciones nuevas de `lib/api.ts` — mismo patrón TDD del resto del proyecto.

## Fuera de alcance de Spec 2

- Código QR de confirmación (Spec 3).
- Gate en `POST /movimientos` que impida ubicar un contenedor sin PIN verificado.
- Límite de reintentos / bloqueo por PIN incorrecto repetido.
- Reenvío explícito de PIN (se resuelve con `GET /pin` para quien tenga permiso).
- Constraint de unicidad sobre `numero_contenedor` en contenedores activos.
- Listado "mis solicitudes" para el cliente (seguía fuera de alcance desde Spec 1).

## Self-review

- Sin placeholders/TBD.
- Verificado que `ContenedorOut` es el único punto de fuga posible para el PIN (`GET /{id}` sin `require_roles`) antes de decidir excluirlo del schema — no se asumió.
- Verificado que `POST /movimientos` no tiene precondición de estado hoy (leído el handler), por eso la decisión de "no bloquear" es consistente con el comportamiento actual, no lo cambia.
- `numero_contenedor` como clave de búsqueda en `verificar-pin` en vez de UUID: justificado porque no existe pantalla de búsqueda/listado y el operador solo conoce el número físico — evita construir una feature no pedida.
- Alcance acotado a PIN únicamente, sin tocar QR (Spec 3) ni `movimientos.py`.
