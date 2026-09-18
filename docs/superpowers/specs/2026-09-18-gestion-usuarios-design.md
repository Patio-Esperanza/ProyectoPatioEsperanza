# Gestión de usuarios internos + auto-relleno de patio — Design

**Fecha:** 2026-09-18

## Problema

No existe forma de dar de alta a los operadores/supervisores/guardias/despachadores que van a usar el sistema día a día. El único usuario existente se sembró a mano vía script (`backend/scripts/seed_admin.py`), fuera del flujo normal de la app. Además, las pantallas de `Contenedores` (crear) y `Sugerir ubicación` piden el `patio_id` como texto libre (UUID escrito a mano), lo que facilita que un operador se equivoque de patio al operar.

## Alcance

**Dentro de alcance:**
- Backend: endpoints para crear y listar usuarios internos, con rol y patio(s) asignados.
- Frontend: pantalla `/usuarios` (solo admin) para alta y listado.
- Frontend: reemplazar el input de texto libre de `patio_id` por un `<select>` auto-rellenado, en `Contenedores` (crear) y `Sugerir ubicación`.

**Fuera de alcance (queda para una tarea de seguimiento):**
- Editar o desactivar usuarios existentes.
- Auto-relleno o listado de `contenedor_id` / `ubicacion_destino_id` (requeriría nuevos endpoints de backend para listar contenedores/ubicaciones por patio — limitación conocida ya documentada en `docs/superpowers/plans/2026-09-17-frontend-dashboard.md`, sección Self-Review).
- Rol `cliente` (pertenece al portal externo, fuera de alcance del sistema interno).
- `Movimientos`: no tiene campo `patio_id` en su payload (`contenedor_id`, `ubicacion_destino_id`, `tipo`), así que el auto-relleno no aplica ahí.

## Arquitectura

### Backend

Nuevo módulo `backend/app/api/routes/usuarios.py`, mismo patrón que `patios.py` / `contenedores.py`: `require_roles(RolUsuario.ADMIN)`, `registrar_auditoria` en cada escritura.

- `POST /api/usuarios` (admin-only) — crea el usuario y sus filas en `usuario_patio`.
- `GET /api/usuarios` (admin-only) — lista usuarios con sus patios asignados (join).

Nuevo `backend/app/schemas/usuario.py`:

```python
class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str  # min_length=8
    tipo: RolUsuario  # excluye CLIENTE a nivel de validación
    patio_ids: list[uuid.UUID] = []

class UsuarioOut(BaseModel):
    id: uuid.UUID
    nombre: str | None
    email: str
    tipo: RolUsuario
    activo: bool
    patios: list[PatioOut]
```

Reutiliza `hash_password` de `app/core/security.py` (ya existe, usado por `seed_admin.py` y por el propio login).

### Frontend

`frontend/lib/api.ts`: agrega `Usuario`, `listUsuarios(token)`, `createUsuario(token, payload)`. `RolUsuario` como union type de los 5 roles internos (`"operador" | "supervisor" | "admin" | "guardia" | "despachador"`).

`frontend/app/usuarios/page.tsx`: mismo patrón que `app/patios/page.tsx` — `AuthGuard` + contenido que se ajusta por rol. El formulario de alta (rol select + checkboxes de patios, poblados con `listPatios()`) solo se renderiza si `user.rol === "admin"`; la tabla/lista es visible a cualquier rol interno. `NavBar` gana el link "Usuarios", visible solo para admin (mismo criterio que el resto de la nav, que hoy no filtra por rol — este es el primer link condicional).

**Auto-relleno de patio** (`Contenedores` crear, `Sugerir ubicación`): ambas páginas ya llaman o pueden llamar `listPatios()`. Se agrega:

```
patiosDisponibles = user.rol === "admin"
  ? todosLosPatios
  : todosLosPatios.filter(p => user.patios.includes(p.id))
```

El campo `patio_id` pasa de `<input>` a `<select>` con esas opciones. Si `patiosDisponibles.length === 1`, se preselecciona y se deshabilita (`disabled`) — el operador no puede elegir mal. Si son 0 (caso raro: admin sin patios y sin patios en el sistema, o usuario recién creado sin asignar) se muestra un mensaje en vez del select.

## Validación y manejo de errores

- Email duplicado: pre-check (`SELECT` por email) antes del `INSERT` → `409 Conflict` con mensaje "Email ya registrado", igual que hoy hace `contenedores.py` para otras validaciones de negocio (evita que un `IntegrityError` crudo llegue al cliente).
- `password` con menos de 8 caracteres → `422` (validación Pydantic, mensaje de FastAPI por defecto).
- `tipo == cliente` → `422` (rechazado por el enum/validación de `UsuarioCreate`, ese rol no se crea desde esta pantalla).
- `tipo != admin` y `patio_ids` vacío → `422` explícito ("Este rol requiere al menos un patio asignado").
- Creación de usuario y sus filas `usuario_patio` va en una sola transacción (igual que el resto de los endpoints de escritura: `db.flush()` + `registrar_auditoria` + `db.commit()`).

## Testing

**Backend** (`backend/tests/test_usuarios_api.py`, seguir convenciones de `test_patios_api.py`):
- Admin crea usuario con 1+ patios → 201, `usuario_patio` pobladas, auditoría registrada.
- No-admin intenta crear → 403.
- Email duplicado → 409.
- Rol no-admin sin `patio_ids` → 422.
- `GET /api/usuarios` incluye los patios asignados por usuario.

**Frontend**:
- `lib/api.test.ts`: tests para `listUsuarios` / `createUsuario` (mismo patrón que `listPatios`/`createPatio`).
- `app/usuarios/page.test.tsx`: lista usuarios, oculta el form de alta para no-admin, crea usuario y refresca la lista (mismo patrón que `app/patios/page.test.tsx`).
- `app/contenedores/page.test.tsx` y `app/ubicaciones/sugerir/page.test.tsx`: se actualizan los tests existentes para reflejar el `<select>` de patio (con `getByLabelText` + `selectOptions` en vez de `type` sobre un input de texto), incluyendo el caso de patio único auto-seleccionado y deshabilitado.

## Self-review

- Sin placeholders/TBD.
- Consistente con los patrones ya establecidos en el backend (`require_roles`, `registrar_auditoria`, schemas Pydantic) y frontend (`AuthGuard`, CSS Modules, `lib/api.ts` tipado) del plan `2026-09-17-frontend-dashboard.md`.
- Alcance acotado: una sola tarea de implementación (backend + frontend), sin tocar `Movimientos` ni agregar endpoints de listado de contenedores/ubicaciones.
- Ambigüedad resuelta explícitamente: roles internos = todos menos `cliente`; patio_ids obligatorio solo para roles no-admin.
