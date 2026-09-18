# Portal Cliente — Spec 1: Fundación (alta de clientes, registro, solicitud de entrada) — Design

**Fecha:** 2026-09-18

## Contexto

"Portal cliente" quedó explícitamente fuera de alcance del plan original de backend (`docs/superpowers/plans/2026-09-14-backend-foundation.md`, línea 11: "QR firmado/portería, portal cliente..."). El pedido actual del usuario junta varios subsistemas independientes (alta de cliente, solicitud con fecha de retiro, PIN de 4 dígitos + SendGrid, QR de confirmación). Se decidió partirlo en 3 specs:

- **Spec 1 (esta):** fundación — alta de empresas cliente, registro/verificación de personal del cliente, solicitud de entrada de contenedor con fecha estimada de retiro.
- **Spec 2:** PIN de 4 dígitos (generación, visibilidad restringida a admin+cliente, envío por SendGrid, verificación por el operador en patio).
- **Spec 3:** código QR de confirmación de la solicitud.

## Decisiones confirmadas con el usuario

- `fecha_estimada_retiro` se captura al crear la solicitud de **entrada** (no en salida) — ayuda a decidir dónde ubicar el contenedor. Ya existe la columna `fecha_estimada_salida` en `contenedores` (migración 0005), nunca expuesta vía API — se reutiliza, expuesta en los schemas como `fecha_estimada_retiro`.
- No se crea una tabla `Solicitud` separada: la solicitud del cliente **es** el `Contenedor` naciendo en `estado=solicitud_ingreso` (primer valor del enum `EstadoContenedor`, ya existente).
- Alta de empresa (`Cliente`, con RFC) la hace el admin. El personal de la empresa se **autoregistra** dando su RFC; si el RFC no coincide con un `Cliente` activo, la cuenta queda inactiva permanentemente hasta que el admin resuelva el caso manualmente (no hay endpoint de "aprobar" en esta spec).
- Además del RFC, se requiere **verificación de correo por código** (6 dígitos, no link) antes de activar la cuenta.
- El cliente **no elige el patio** al crear la solicitud — se asigna automáticamente el primer patio activo (por `codigo` ascendente) hasta que exista una rutina de asignación inteligente (fuera de alcance).
- SendGrid ya tiene cuenta y remitente verificados (`SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL=noreplay@patiolaesperanza.com.mx`, ya en `backend/.env`, nunca commiteado).

## Arquitectura

### Backend

**Nuevo:** `backend/app/models/cliente.py` ya existe (`Cliente`: `razon_social`, `rfc`, `tipo`, `activo`) — no se toca el modelo. Se agregan:

- `backend/app/schemas/cliente.py`: `ClienteCreate`, `ClienteOut`, `ClienteRegistro`, `ClienteVerificar`.
- `backend/app/api/routes/clientes.py`:
  - `POST /api/clientes` (admin-only, `require_roles(ADMIN)`) — alta de empresa, mismo patrón que `patios.py`.
  - `GET /api/clientes` (admin-only) — listado.
  - `POST /api/clientes/registro` (público, sin auth) — alta de `Usuario(tipo=cliente, activo=false)`, genera código de 6 dígitos, envía correo.
  - `POST /api/clientes/verificar` (público, sin auth) — valida código, activa si el RFC también coincidió.
- `backend/app/core/email.py`: función genérica `enviar_correo(destinatario, asunto, contenido_html)` usando el SDK `sendgrid` (nueva dependencia, `sendgrid==6.12.5` en `requirements.txt`, verificada contra PyPI). Reutilizable por Spec 2/3.
- `backend/app/config.py`: agregar `sendgrid_api_key: str`, `sendgrid_from_email: str`.
- Migración Alembic nueva: agrega a `usuarios` las columnas `codigo_verificacion: str | None`, `codigo_verificacion_expira: datetime | None`.
- `backend/app/models/usuario.py`: agregar esas dos columnas a `Usuario`.

**Cambio en infraestructura de auth (compartido, necesario para que `/solicitar` sepa a qué cliente pertenece el contenedor):**

- `backend/app/core/security.py::create_access_token`: se le agrega un parámetro **opcional** al final, `cliente_id: str | None = None`, para no romper ninguna llamada existente (todas usan argumentos posicionales `(usuario_id, rol, patios, expires_minutes)`). Si se pasa, se incluye como claim `cliente_id` en el JWT.
- `backend/app/api/routes/auth.py::login`: al armar el token, si `usuario.tipo == RolUsuario.CLIENTE`, pasa `cliente_id=str(usuario.cliente_id)`.
- `backend/app/api/deps.py::CurrentUser`: nuevo campo `cliente_id: uuid.UUID | None`. `get_current_user` lo lee de `payload.get("cliente_id")`.

**Nuevo endpoint de solicitud** (en `backend/app/api/routes/contenedores.py`, junto al `crear_contenedor` existente, sin tocarlo):

- `POST /api/contenedores/solicitar` (`require_roles(RolUsuario.CLIENTE)`). Payload: `{numero_contenedor, tipo, tamano, peso_kg, fecha_estimada_retiro}` (mismo validador ISO 6346 que `ContenedorCreate`, reutilizado vía herencia o composición). El handler:
  1. Busca el primer `Patio` con `activo=True` ordenado por `codigo` ascendente. Si no hay ninguno → `422` ("No hay patios activos configurados").
  2. Crea el `Contenedor` con `estado=EstadoContenedor.SOLICITUD_INGRESO`, `cliente_id=user.cliente_id`, `patio_id` del paso 1, `fecha_estimada_salida=payload.fecha_estimada_retiro`.
  3. Registra auditoría (mismo patrón que `crear_contenedor`).

### Frontend

- `frontend/app/registro/page.tsx` (público, sin `AuthGuard`): formulario `{nombre, email, password, rfc}` → `POST /api/clientes/registro` → redirige a `/registro/verificar?email=...`.
- `frontend/app/registro/verificar/page.tsx` (público): formulario `{email, codigo}` → `POST /api/clientes/verificar` → si activa, redirige a `/login`.
- `frontend/app/solicitar/page.tsx` (`AuthGuard`, visible solo si `user.rol === "cliente"`): formulario de solicitud de entrada, mismos campos que `Contenedores` (crear) menos `patio_id`, más `fecha_estimada_retiro` (input `type="date"`).
- `frontend/lib/api.ts`: `registrarCliente`, `verificarCliente`, `solicitarContenedor`, tipos `Cliente`, `ClienteRegistroPayload`.
- `NavBar`: el link "Contenedores" actual no aplica a rol `cliente` (ese formulario es de staff); se agrega un link "Solicitar entrada" visible solo si `user.rol === "cliente"`. Login page sin cambios (mismo formulario sirve para cualquier rol).
- Página de admin para `Cliente` (alta + listado de empresas) — mismo patrón que `/patios`, nueva ruta `/clientes`, visible solo admin en NavBar.

## Validación y manejo de errores

- RFC no coincide con ningún `Cliente` activo → el registro **igual se crea** (para no filtrar qué RFCs existen), pero queda inactivo. El código de verificación se sigue enviando (si el correo es válido); al verificar el código correctamente el mensaje es "Código correcto. Tu empresa (RFC) no está registrada, contacta al administrador" y `activo` sigue en `false`.
- Código incorrecto o expirado → `422`, mensaje claro (`"Código incorrecto"` / `"Código expirado, solicita uno nuevo"`). Reenvío de código: fuera de alcance de esta spec (el cliente puede volver a registrarse con el mismo email si expira — el registro debe permitir sobrescribir el código de un usuario `activo=false` existente en vez de fallar por email duplicado).
- Email duplicado en registro: si el `Usuario` ya existe y está `activo=true` → `409` normal. Si existe pero `activo=false` (registro previo no completado) → se sobreescribe `password_hash`, `codigo_verificacion`, `codigo_verificacion_expira` y se reenvía el correo (permite reintentar sin quedar atorado).
- `POST /api/contenedores/solicitar` con rol distinto de `cliente` → `403` (`require_roles`).
- Falla de envío de SendGrid (API caída, key inválida): el registro **no debe fallar** silenciosamente ni bloquear al usuario — se registra el error en logs y se devuelve `502` con mensaje "No se pudo enviar el correo de verificación, intenta de nuevo" (el `Usuario` ya se creó/actualizó en la misma transacción antes del intento de envío, así que un reintento de registro con el mismo email lo recupera).

## Testing

**Backend:**
- `test_clientes_api.py`: admin crea/lista clientes, no-admin no puede.
- `test_registro_cliente_api.py`: registro con RFC válido genera código y usuario inactivo; registro con RFC inválido igual crea usuario inactivo; verificar con código correcto + RFC válido activa; verificar con código correcto + RFC inválido no activa; verificar con código incorrecto/expirado falla; login falla mientras `activo=false`; re-registro de un email inactivo sobreescribe el código en vez de fallar. SendGrid se mockea (no se llama a la API real en tests).
- `test_contenedores_api.py` (ampliado): `POST /api/contenedores/solicitar` como cliente crea contenedor en `solicitud_ingreso` con el patio autoasignado y `cliente_id` correcto; como operador/admin da `403`.

**Frontend:** tests para `/registro`, `/registro/verificar`, `/solicitar`, y las funciones nuevas de `lib/api.ts`, siguiendo el patrón TDD ya establecido en el resto del proyecto.

## Fuera de alcance de Spec 1

- PIN de 4 dígitos (Spec 2).
- Código QR de confirmación (Spec 3).
- Rutina inteligente de asignación de patio por lleno/vacío (mencionada por el usuario como trabajo futuro).
- Listado "mis contenedores/solicitudes" para el cliente (no se pidió).
- Reenvío de código de verificación como acción explícita (se resuelve reintentando el registro).
- Rate limiting / protección anti-abuso en `registro`/`verificar` (a evaluar en una spec de hardening si se vuelve necesario).

## Self-review

- Sin placeholders/TBD.
- `fecha_estimada_retiro` verificado contra el esquema real (`Contenedor.fecha_estimada_salida`, migración 0005) en vez de asumir que hace falta una columna nueva.
- `create_access_token` se extiende de forma retrocompatible (parámetro opcional al final) — no rompe las llamadas posicionales existentes en `auth.py` ni en los tests de `test_patios_api.py`, `test_contenedores_api.py`, `test_movimientos_api.py`, `test_usuarios_api.py`.
- Paquete `sendgrid==6.12.5` verificado contra PyPI, no adivinado.
- Alcance acotado a una sola spec implementable de punta a punta (backend + frontend), sin tocar PIN/QR.
