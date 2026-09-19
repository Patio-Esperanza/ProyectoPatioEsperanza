# Portal Cliente Spec 2 (PIN de 4 dígitos) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Reparto de trabajo (CLAUDE.md del proyecto):** la construcción de cada tarea se delega al subagente `codex-rescue`. Claude planea, revisa cada entrega de Codex, y decide si pasa a la siguiente tarea o si la tarea regresa a Claude tras dos fallos.

**Goal:** El cliente recibe un PIN de 4 dígitos por correo al solicitar entrada de un contenedor; el operador lo verifica en portería para confirmar la llegada.

**Architecture:** Se extiende `Contenedor` con tres columnas nuevas (`pin_confirmacion`, `pin_verificado_en`, `pin_verificado_por`). El PIN se genera y envía dentro del endpoint existente `POST /api/contenedores/solicitar`. Dos endpoints nuevos: `GET /api/contenedores/{id}/pin` (lectura restringida a admin/cliente dueño) y `POST /api/contenedores/verificar-pin` (escritura para operador/supervisor/admin, busca por `numero_contenedor`). El campo `pin_confirmacion` nunca se expone en `ContenedorOut`.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend), Next.js App Router + vitest (frontend). Reutiliza `sendgrid` (ya instalado, Spec 1) y `app.core.email.enviar_correo` sin cambios.

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-09-19-portal-cliente-spec2-pin-design.md`.
- El PIN se genera con el módulo `secrets` (`secrets.randbelow`), nunca con `random`.
- `pin_confirmacion` no se agrega a `ContenedorOut` bajo ninguna circunstancia — visibilidad solo vía `GET /{id}/pin`.
- `POST /movimientos` no se toca en este plan (decisión confirmada: verificar PIN no bloquea ubicación).
- Sin límite de reintentos de PIN incorrecto (sin rate limiting).
- Todos los comandos de backend corren desde `/home/tony/Developer/ProyectoPatioEsperanza/backend` con `source .venv/bin/activate` y `PYTHONPATH=.` antes de `alembic`/`pytest`.
- Todos los comandos de frontend corren desde `/home/tony/Developer/ProyectoPatioEsperanza/frontend` con `npm test -- <archivo>`.

---

### Task 1: Backend — migración y columnas en `Contenedor`

**Files:**
- Create: `backend/app/alembic/versions/0008_pin_confirmacion.py`
- Modify: `backend/app/models/contenedor.py`

**Interfaces:**
- Produces: columnas `contenedores.pin_confirmacion` (`str | None`, máx 4 chars), `contenedores.pin_verificado_en` (`datetime | None`), `contenedores.pin_verificado_por` (`uuid.UUID | None`, FK `usuarios.id`). Consumidas por Tasks 2, 3 y 4.

- [ ] **Step 1: Crear `backend/app/alembic/versions/0008_pin_confirmacion.py`**

```python
"""pin de confirmacion de 4 digitos para contenedores

Revision ID: 0008_pin_confirmacion
Revises: 0007_verificacion_correo
Create Date: 2026-09-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_pin_confirmacion"
down_revision = "0007_verificacion_correo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contenedores", sa.Column("pin_confirmacion", sa.String(4), nullable=True))
    op.add_column(
        "contenedores", sa.Column("pin_verificado_en", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "contenedores",
        sa.Column(
            "pin_verificado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("contenedores", "pin_verificado_por")
    op.drop_column("contenedores", "pin_verificado_en")
    op.drop_column("contenedores", "pin_confirmacion")
```

- [ ] **Step 2: Aplicar la migración**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. alembic upgrade head
```
Esperado: `Running upgrade 0007_verificacion_correo -> 0008_pin_confirmacion, pin de confirmacion de 4 digitos para contenedores`

- [ ] **Step 3: Agregar las columnas a `backend/app/models/contenedor.py`**

Reemplazar el archivo completo:

```python
import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor, TipoMovimiento


class Contenedor(Base):
    __tablename__ = "contenedores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_contenedor: Mapped[str] = mapped_column(String(11), nullable=False)
    tipo: Mapped[TipoContenedor] = mapped_column(
        Enum(TipoContenedor, name="tipo_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    tamano: Mapped[TamanoContenedor] = mapped_column(
        Enum(TamanoContenedor, name="tamano_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    ubicacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    estado: Mapped[EstadoContenedor] = mapped_column(
        Enum(EstadoContenedor, name="estado_contenedor", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    peso_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_estimada_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_confirmacion: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pin_verificado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_verificado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_contenedor_ubicacion_activa",
            "ubicacion_id",
            unique=True,
            postgresql_where=(ubicacion_id.is_not(None)),
        ),
    )


class Movimiento(Base):
    __tablename__ = "movimientos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contenedor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contenedores.id"), nullable=False)
    patio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patios.id"), nullable=False)
    tipo: Mapped[TipoMovimiento] = mapped_column(
        Enum(TipoMovimiento, name="tipo_movimiento", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    ubicacion_origen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    ubicacion_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
    operador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    override_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score_sugerido: Mapped[float | None] = mapped_column(nullable=True)
    score_elegido: Mapped[float | None] = mapped_column(nullable=True)
    motivo_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_movimiento_contenedor_ts", "contenedor_id", "ts"),)
```

- [ ] **Step 4: Correr la suite completa, confirmar que sigue pasando**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (63 tests — sin cambios de comportamiento todavía, solo columnas nuevas).

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/alembic/versions/0008_pin_confirmacion.py backend/app/models/contenedor.py
git commit -m "feat: columnas de pin de confirmacion en contenedores"
```

---

### Task 2: Backend — generación y envío del PIN en `POST /solicitar`

**Files:**
- Modify: `backend/app/schemas/contenedor.py`
- Modify: `backend/app/api/routes/contenedores.py`
- Modify: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Consumes: `Contenedor.pin_confirmacion` (Task 1), `enviar_correo(destinatario, asunto, contenido_html) -> None` (`app.core.email`, ya existe).
- Produces: `PinOut { pin_confirmacion: str }`, `PinVerificar { numero_contenedor: str, pin: str }` (schemas). Consumidos por Tasks 3 y 4. `solicitar_contenedor` ahora genera y envía el PIN — no cambia su firma ni su `response_model` (`ContenedorOut`).

- [ ] **Step 1: Escribir el test que falla — PIN generado y correo enviado**

Agregar al final de `backend/tests/test_contenedores_api.py`:

```python
@pytest.fixture
def enviados_pin(monkeypatch):
    capturados = []

    def _fake(destinatario, asunto, contenido_html):
        capturados.append((destinatario, asunto, contenido_html))

    monkeypatch.setattr("app.api.routes.contenedores.enviar_correo", _fake)
    return capturados


@pytest.mark.anyio
async def test_solicitar_genera_pin_y_envia_correo(client, db_session, enviados_pin):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    patio = await _crear_patio(db_session, "Patio Norte", "PN5")
    cliente = Cliente(
        razon_social="Importadora PIN", rfc="BBB020202BB2", tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=RolUsuario.CLIENTE,
            email="pin-cliente@empresa.mx",
            password_hash="hash",
            cliente_id=cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    token = create_access_token(_USUARIO_ID, "cliente", [], 60, cliente_id=str(cliente.id))

    response = await client.post(
        "/api/contenedores/solicitar",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "peso_kg": 18000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert "pin_confirmacion" not in response.json()
    assert len(enviados_pin) == 1
    destinatario, asunto, contenido = enviados_pin[0]
    assert destinatario == "pin-cliente@empresa.mx"
    assert "PIN" in asunto

    from sqlalchemy import select as sa_select

    result = await db_session.execute(
        sa_select(Contenedor).where(Contenedor.numero_contenedor == "CSQU3054383")
    )
    contenedor = result.scalar_one()
    assert contenedor.pin_confirmacion is not None
    assert len(contenedor.pin_confirmacion) == 4
    assert contenedor.pin_confirmacion.isdigit()
    assert contenedor.pin_confirmacion in contenido
```

Agregar el import que falta al inicio del archivo (junto a los demás imports):

```python
from app.models.contenedor import Contenedor
```

Modificar la prueba existente `test_cliente_solicita_contenedor_con_patio_autoasignado` (ya está en el archivo) para que reciba el fixture `enviados_pin` y no intente enviar un correo real:

Cambiar la firma:

```python
async def test_cliente_solicita_contenedor_con_patio_autoasignado(client, db_session):
```

por:

```python
async def test_cliente_solicita_contenedor_con_patio_autoasignado(client, db_session, enviados_pin):
```

- [ ] **Step 2: Correr el test nuevo, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py::test_solicitar_genera_pin_y_envia_correo -v
```
Esperado: FAIL (SendGrid intenta llamar con la API key falsa de test, o `pin_confirmacion` sigue `None` — `enviar_correo` aún no se importa/llama en `contenedores.py`).

- [ ] **Step 3: Agregar `PinOut` y `PinVerificar` a `backend/app/schemas/contenedor.py`**

Agregar al final del archivo:

```python


class PinOut(BaseModel):
    pin_confirmacion: str


class PinVerificar(BaseModel):
    numero_contenedor: str
    pin: str = Field(min_length=4, max_length=4)

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)

    @field_validator("pin")
    @classmethod
    def pin_valido(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("pin debe ser 4 dígitos")
        return value
```

- [ ] **Step 4: Implementar la generación y envío del PIN en `solicitar_contenedor`**

En `backend/app/api/routes/contenedores.py`, agregar los imports al inicio del archivo:

```python
import secrets
```

y

```python
from app.core.email import enviar_correo
```

Reemplazar la función `solicitar_contenedor` completa:

```python
@router.post("/solicitar", response_model=ContenedorOut, status_code=status.HTTP_201_CREATED)
async def solicitar_contenedor(
    payload: ContenedorSolicitud,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE)),
) -> Contenedor:
    patio_result = await db.execute(
        select(Patio).where(Patio.activo.is_(True)).order_by(Patio.codigo).limit(1)
    )
    patio = patio_result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hay patios activos configurados")

    pin = f"{secrets.randbelow(10000):04d}"

    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=patio.id,
        cliente_id=user.cliente_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=payload.peso_kg,
        fecha_estimada_salida=payload.fecha_estimada_retiro,
        pin_confirmacion=pin,
    )
    db.add(contenedor)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior=None,
        valor_nuevo={"numero_contenedor": contenedor.numero_contenedor, "estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()

    usuario_result = await db.execute(select(Usuario).where(Usuario.id == user.id))
    usuario = usuario_result.scalar_one()
    try:
        enviar_correo(
            usuario.email,
            "PIN de confirmación — Patio Esperanza",
            f"<p>Tu PIN de confirmación es <strong>{pin}</strong>. "
            f"Preséntalo al operador en la entrada del patio.</p>",
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo enviar el correo con tu PIN, consúltalo después o contacta al administrador",
        ) from exc

    return contenedor
```

Agregar el import de `Usuario` al inicio del archivo (junto a los demás imports de `app.models`):

```python
from app.models.usuario import Usuario
```

- [ ] **Step 5: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -v
```
Esperado: PASS (todos los tests de `test_contenedores_api.py`, incluyendo el nuevo y el modificado).

- [ ] **Step 6: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (65 tests).

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/contenedor.py backend/app/api/routes/contenedores.py backend/tests/test_contenedores_api.py
git commit -m "feat: generar y enviar pin de confirmacion al solicitar entrada"
```

---

### Task 3: Backend — `GET /api/contenedores/{id}/pin`

**Files:**
- Modify: `backend/app/api/routes/contenedores.py`
- Modify: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Consumes: `PinOut` (Task 2), `CurrentUser { id, rol, patios, cliente_id }` (`app.api.deps`, ya existe).
- Produces: `GET /api/contenedores/{id}/pin` → `PinOut`. No consumido por otras tasks de este plan (lo usa el frontend en Task 7).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `backend/tests/test_contenedores_api.py`:

```python
async def _crear_solicitud_con_pin(client, db_session, usuario_id: str, cliente_rfc: str, numero: str):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    patio = await _crear_patio(db_session, f"Patio {numero}", numero[:6])
    cliente = Cliente(
        razon_social="Importadora Test", rfc=cliente_rfc, tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    db_session.add(
        Usuario(
            id=uuid.UUID(usuario_id),
            tipo=RolUsuario.CLIENTE,
            email=f"{usuario_id}@empresa.mx",
            password_hash="hash",
            cliente_id=cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    token = create_access_token(usuario_id, "cliente", [], 60, cliente_id=str(cliente.id))

    response = await client.post(
        "/api/contenedores/solicitar",
        json={"numero_contenedor": numero, "tipo": "lleno", "tamano": "40", "peso_kg": 18000},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"], cliente


@pytest.mark.anyio
async def test_admin_ve_pin(client, db_session, enviados_pin):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000002", "CCC030303CC3", "CSQU3054384"
    )

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()["pin_confirmacion"]) == 4


@pytest.mark.anyio
async def test_cliente_dueno_ve_pin(client, db_session, enviados_pin):
    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000003", "DDD040404DD4", "CSQU3054385"
    )
    token = create_access_token(
        "00000000-0000-0000-0000-000000000003", "cliente", [], 60, cliente_id=str(cliente.id)
    )

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()["pin_confirmacion"]) == 4


@pytest.mark.anyio
async def test_cliente_de_otra_empresa_no_ve_pin(client, db_session, enviados_pin):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000004", "EEE050505EE5", "CSQU3054386"
    )

    otro_cliente = Cliente(
        razon_social="Otra Empresa", rfc="FFF060606FF6", tipo=TipoCliente.TRANSPORTISTA, activo=True
    )
    db_session.add(otro_cliente)
    await db_session.commit()
    await db_session.refresh(otro_cliente)
    otro_token = create_access_token(
        "00000000-0000-0000-0000-000000000005", "cliente", [], 60, cliente_id=str(otro_cliente.id)
    )
    db_session.add(
        Usuario(
            id=uuid.UUID("00000000-0000-0000-0000-000000000005"),
            tipo=RolUsuario.CLIENTE,
            email="otro@empresa.mx",
            password_hash="hash",
            cliente_id=otro_cliente.id,
            activo=True,
        )
    )
    await db_session.commit()

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {otro_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_operador_no_ve_pin(client, db_session, enviados_pin):
    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000006", "GGG070707GG7", "CSQU3054387"
    )

    response = await client.get(
        f"/api/contenedores/{contenedor_id}/pin",
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_pin_de_contenedor_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)

    response = await client.get(
        "/api/contenedores/00000000-0000-0000-0000-0000000000ff/pin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -k "pin" -v
```
Esperado: FAIL con `404 Not Found` en todos (la ruta `/pin` no existe todavía).

- [ ] **Step 3: Implementar `GET /{id}/pin`**

En `backend/app/api/routes/contenedores.py`, agregar `PinOut` al import de schemas (línea del `from app.schemas.contenedor import ...`):

```python
from app.schemas.contenedor import ContenedorCreate, ContenedorOut, ContenedorSolicitud, PinOut
```

Agregar al final del archivo:

```python


@router.get("/{contenedor_id}/pin", response_model=PinOut)
async def obtener_pin(
    contenedor_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None or contenedor.pin_confirmacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este contenedor no tiene PIN asociado")

    es_dueno = user.rol == RolUsuario.CLIENTE and contenedor.cliente_id == user.cliente_id
    if user.rol != RolUsuario.ADMIN and not es_dueno:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para ver este PIN")

    return contenedor
```

- [ ] **Step 4: Correr los tests, confirmar que pasan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -v
```
Esperado: PASS (todos).

- [ ] **Step 5: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (70 tests).

- [ ] **Step 6: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/api/routes/contenedores.py backend/tests/test_contenedores_api.py
git commit -m "feat: GET /api/contenedores/id/pin restringido a admin y cliente dueno"
```

---

### Task 4: Backend — `POST /api/contenedores/verificar-pin`

**Files:**
- Modify: `backend/app/api/routes/contenedores.py`
- Modify: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Consumes: `PinVerificar` (Task 2), `_ROLES_ESCRITURA` (ya definido en el archivo, Task previa a este plan).
- Produces: `POST /api/contenedores/verificar-pin` → `ContenedorOut`. No consumido por otras tasks backend; lo usa el frontend en Task 6.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `backend/tests/test_contenedores_api.py`:

```python
@pytest.mark.anyio
async def test_operador_verifica_pin_correcto(client, db_session, enviados_pin):
    from sqlalchemy import select as sa_select

    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000007", "HHH080808HH8", "CSQU3054388"
    )
    result = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one()
    pin_real = contenedor.pin_confirmacion

    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054388", "pin": pin_real},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "en_porteria"

    await db_session.refresh(contenedor)
    assert contenedor.pin_verificado_en is not None
    assert str(contenedor.pin_verificado_por) == "00000000-0000-0000-0000-000000000001"


@pytest.mark.anyio
async def test_verificar_pin_incorrecto_422(client, db_session, enviados_pin):
    await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000008", "III090909II9", "CSQU3054389"
    )
    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054389", "pin": "0000"},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "PIN incorrecto"


@pytest.mark.anyio
async def test_verificar_pin_numero_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054399", "pin": "1234"},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_verificar_pin_estado_no_pendiente_409(client, db_session, enviados_pin):
    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000a", "JJJ101010JJ1", "CSQU3054390"
    )
    from sqlalchemy import select as sa_select

    result = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one()
    pin_real = contenedor.pin_confirmacion

    await _crear_usuario_autenticado(db_session)
    op_token = _token(RolUsuario.OPERADOR)

    primera = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054390", "pin": pin_real},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert primera.status_code == 200

    segunda = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054390", "pin": pin_real},
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert segunda.status_code == 409


@pytest.mark.anyio
async def test_cliente_no_puede_verificar_pin(client, db_session, enviados_pin):
    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000b", "KKK111111KK1", "CSQU3054391"
    )
    token = create_access_token(
        "00000000-0000-0000-0000-00000000000b", "cliente", [], 60, cliente_id=str(cliente.id)
    )

    response = await client.post(
        "/api/contenedores/verificar-pin",
        json={"numero_contenedor": "CSQU3054391", "pin": "1234"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -k "verificar_pin" -v
```
Esperado: FAIL con `404 Not Found` en todos (la ruta `verificar-pin` no existe todavía; nota: debe declararse **antes** de `@router.get("/{contenedor_id}")` en el archivo para que FastAPI no la confunda con un `contenedor_id` literal — igual que `/solicitar` ya está antes de `/{contenedor_id}`).

- [ ] **Step 3: Implementar `POST /verificar-pin`**

En `backend/app/api/routes/contenedores.py`, agregar `PinVerificar` al import de schemas:

```python
from app.schemas.contenedor import ContenedorCreate, ContenedorOut, ContenedorSolicitud, PinOut, PinVerificar
```

Agregar la ruta **inmediatamente después de `solicitar_contenedor`** (antes de `obtener_contenedor`, para que `/{contenedor_id}` no la intercepte):

```python
@router.post("/verificar-pin", response_model=ContenedorOut)
async def verificar_pin(
    payload: PinVerificar,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Contenedor:
    result = await db.execute(
        select(Contenedor).where(Contenedor.numero_contenedor == payload.numero_contenedor)
    )
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if contenedor.estado != EstadoContenedor.SOLICITUD_INGRESO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Este contenedor no está pendiente de verificación de PIN"
        )

    if contenedor.pin_confirmacion != payload.pin:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PIN incorrecto")

    contenedor.estado = EstadoContenedor.EN_PORTERIA
    contenedor.pin_verificado_en = func.now()
    contenedor.pin_verificado_por = user.id

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="verificar_pin",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": EstadoContenedor.SOLICITUD_INGRESO.value},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)
    return contenedor
```

Agregar el import de `func` al inicio del archivo:

```python
from sqlalchemy.sql import func
```

- [ ] **Step 4: Correr los tests, confirmar que pasan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -v
```
Esperado: PASS (todos).

- [ ] **Step 5: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (75 tests).

- [ ] **Step 6: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/api/routes/contenedores.py backend/tests/test_contenedores_api.py
git commit -m "feat: POST /api/contenedores/verificar-pin para operador en porteria"
```

---

### Task 5: Frontend — `lib/api.ts` (`obtenerPin`, `verificarPin`)

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/api.test.ts` (extender si ya existe, agregar los tests al final)

**Interfaces:**
- Consumes: `request<T>(path, options)` (helper ya existente en el archivo), `ApiError`, `Contenedor` (ya existente).
- Produces: `obtenerPin(token: string, id: string): Promise<{ pin_confirmacion: string }>`, `verificarPin(token: string, payload: { numero_contenedor: string; pin: string }): Promise<Contenedor>`. Consumidos por Tasks 6 y 7.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `frontend/lib/api.test.ts`:

```typescript
describe("obtenerPin", () => {
  it("returns the pin for an authorized user", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ pin_confirmacion: "4821" })
    );

    const result = await obtenerPin("token", "c1");

    expect(result).toEqual({ pin_confirmacion: "4821" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores/c1/pin",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
  });
});

describe("verificarPin", () => {
  it("posts numero_contenedor and pin", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "en_porteria",
        peso_kg: 18000,
      })
    );

    const result = await verificarPin("token", { numero_contenedor: "CSQU3054383", pin: "4821" });

    expect(result.estado).toBe("en_porteria");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores/verificar-pin",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ numero_contenedor: "CSQU3054383", pin: "4821" }),
      })
    );
  });
});
```

Si `frontend/lib/api.test.ts` no importa `obtenerPin`/`verificarPin` todavía, agregar al import existente de `@/lib/api` (o el import relativo que use el archivo) los dos nombres nuevos. Revisar el inicio del archivo existente para confirmar el patrón exacto de `fetchMock`/`jsonResponse` ya usado por los demás `describe` (mismo patrón que `solicitarContenedor`/`getContenedor` ya testeados ahí) y reutilizarlo sin modificarlo.

- [ ] **Step 2: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `obtenerPin`/`verificarPin` no están exportados por `lib/api.ts`.

- [ ] **Step 3: Implementar las funciones en `frontend/lib/api.ts`**

Agregar después de `export async function getContenedor(...)`:

```typescript
export async function obtenerPin(token: string, id: string): Promise<{ pin_confirmacion: string }> {
  return request<{ pin_confirmacion: string }>(`/api/contenedores/${id}/pin`, { token });
}

export async function verificarPin(
  token: string,
  payload: { numero_contenedor: string; pin: string }
): Promise<Contenedor> {
  return request<Contenedor>("/api/contenedores/verificar-pin", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Correr los tests, confirmar que pasan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: PASS (todos).

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat: cliente HTTP para pin de confirmacion (obtenerPin, verificarPin)"
```

---

### Task 6: Frontend — página `/porteria` (verificar PIN) + link en NavBar

**Files:**
- Create: `frontend/app/porteria/page.tsx`
- Create: `frontend/app/porteria/page.module.css`
- Create: `frontend/app/porteria/page.test.tsx`
- Modify: `frontend/components/NavBar.tsx`
- Modify: `frontend/components/NavBar.test.tsx`

**Interfaces:**
- Consumes: `verificarPin(token, payload)` (Task 5), `AuthGuard` (`@/components/AuthGuard`, ya existe), `useAuth()` (`@/lib/auth-context`, ya existe, expone `{ user: { id, rol, patios } | null, token, ready, setToken, logout }`).
- Produces: ruta `/porteria`, sin interfaz consumida por otras tasks.

- [ ] **Step 1: Escribir el test que falla — `NavBar` muestra "Portería" solo para operador/supervisor/admin**

Agregar a `frontend/components/NavBar.test.tsx`, dentro del `describe("NavBar", ...)`:

```typescript
  it("shows the Porteria link only for operador, supervisor and admin", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "cliente", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    const { rerender } = render(<NavBar />);
    expect(screen.queryByText("Portería")).not.toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    rerender(<NavBar />);
    expect(screen.getByText("Portería")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: FAIL — el link "Portería" no existe.

- [ ] **Step 3: Agregar el link a `frontend/components/NavBar.tsx`**

Reemplazar el bloque `<div className={styles.links}>` completo:

```tsx
      <div className={styles.links}>
        <Link href="/patios">Patios</Link>
        <Link href="/contenedores">Contenedores</Link>
        <Link href="/movimientos">Movimientos</Link>
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
        {(user.rol === "operador" || user.rol === "supervisor" || user.rol === "admin") && (
          <Link href="/porteria">Portería</Link>
        )}
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "admin" && <Link href="/clientes">Clientes</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
      </div>
```

- [ ] **Step 4: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: PASS (todos).

- [ ] **Step 5: Commit del link de NavBar**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/components/NavBar.tsx frontend/components/NavBar.test.tsx
git commit -m "feat: link Porteria en NavBar para operador, supervisor y admin"
```

- [ ] **Step 6: Escribir `frontend/app/porteria/page.test.tsx`**

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PorteriaPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { verificarPin } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, verificarPin: vi.fn() };
});

function mockAuth(rol: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol, patios: [] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
}

beforeEach(() => {
  vi.mocked(verificarPin).mockReset();
});

describe("PorteriaPage", () => {
  it("shows a not-authorized message for cliente role", () => {
    mockAuth("cliente");

    render(<PorteriaPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("No autorizado");
  });

  it("submits numero_contenedor and pin, shows success", async () => {
    mockAuth("operador");
    vi.mocked(verificarPin).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "en_porteria",
      peso_kg: 18000,
    });

    const user = userEvent.setup();
    render(<PorteriaPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("PIN"), "4821");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(verificarPin).toHaveBeenCalledWith("token", {
      numero_contenedor: "CSQU3054383",
      pin: "4821",
    });
    expect(await screen.findByText(/en_porteria/)).toBeInTheDocument();
  });

  it("shows the API error message on failure", async () => {
    mockAuth("operador");
    const { ApiError } = await import("@/lib/api");
    vi.mocked(verificarPin).mockRejectedValue(new ApiError(422, "PIN incorrecto"));

    const user = userEvent.setup();
    render(<PorteriaPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("PIN"), "0000");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("PIN incorrecto");
  });
});
```

- [ ] **Step 7: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/porteria/page.test.tsx
```
Esperado: FAIL — el módulo `./page` no existe.

- [ ] **Step 8: Crear `frontend/app/porteria/page.module.css`**

```css
.main {
  max-width: 480px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.form input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.form button {
  align-self: flex-start;
  background: var(--azul);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 10px;
  border-radius: 6px;
}

.ok {
  color: #2e7d46;
  background: #e4f2e8;
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 9: Crear `frontend/app/porteria/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, verificarPin, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function PorteriaContent() {
  const { token, user } = useAuth();
  const [numero, setNumero] = useState("");
  const [pin, setPin] = useState("");
  const [verificado, setVerificado] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setVerificado(null);
    try {
      const contenedor = await verificarPin(token, { numero_contenedor: numero, pin });
      setVerificado(contenedor);
      setNumero("");
      setPin("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo verificar el PIN");
    } finally {
      setSubmitting(false);
    }
  }

  if (user?.rol !== "operador" && user?.rol !== "supervisor" && user?.rol !== "admin") {
    return (
      <main className={styles.main}>
        <p role="alert" className={styles.error}>
          No autorizado para ver esta página
        </p>
      </main>
    );
  }

  return (
    <main className={styles.main}>
      <h1>Verificar PIN en portería</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {verificado && (
        <p className={styles.ok}>
          Contenedor <span className="mono">{verificado.numero_contenedor}</span> verificado —
          estado {verificado.estado}
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="numero_contenedor">Número de contenedor</label>
        <input
          id="numero_contenedor"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          required
          maxLength={11}
        />

        <label htmlFor="pin">PIN</label>
        <input
          id="pin"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          required
          maxLength={4}
          inputMode="numeric"
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Verificando..." : "Verificar"}
        </button>
      </form>
    </main>
  );
}

export default function PorteriaPage() {
  return (
    <AuthGuard>
      <PorteriaContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 10: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/porteria/page.test.tsx
```
Esperado: PASS (todos).

- [ ] **Step 11: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/porteria
git commit -m "feat: pagina de verificacion de pin en porteria (operador/supervisor/admin)"
```

---

### Task 7: Frontend — botón "Ver PIN" en `/contenedores/[id]`

**Files:**
- Modify: `frontend/app/contenedores/[id]/page.tsx`
- Modify: `frontend/app/contenedores/[id]/page.test.tsx`

**Interfaces:**
- Consumes: `obtenerPin(token, id)` (Task 5), `getContenedor(token, id)` (ya existente).

- [ ] **Step 1: Revisar el test existente**

Leer `frontend/app/contenedores/[id]/page.test.tsx` completo antes de modificarlo, para replicar el patrón exacto de mocks (`vi.mock("@/lib/api", ...)`, `mockAuth`, `useParams`) ya usado ahí. No adivinar la estructura — copiar el estilo del archivo real.

- [ ] **Step 2: Escribir el test que falla — botón "Ver PIN" solo para admin**

Agregar al `describe` existente en `frontend/app/contenedores/[id]/page.test.tsx` (siguiendo el mismo patrón de mocks que ya usa el archivo para `getContenedor`):

```typescript
  it("shows a Ver PIN button only for admin, and fetches the pin on click", async () => {
    mockAuth("admin");
    vi.mocked(getContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_ingreso",
      peso_kg: 18000,
    });
    vi.mocked(obtenerPin).mockResolvedValue({ pin_confirmacion: "4821" });

    const user = userEvent.setup();
    render(<ContenedorDetallePage />);

    const boton = await screen.findByRole("button", { name: "Ver PIN" });
    await user.click(boton);

    expect(obtenerPin).toHaveBeenCalledWith("token", "c1");
    expect(await screen.findByText("4821")).toBeInTheDocument();
  });

  it("does not show the Ver PIN button for non-admin roles", async () => {
    mockAuth("operador");
    vi.mocked(getContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_ingreso",
      peso_kg: 18000,
    });

    render(<ContenedorDetallePage />);

    await screen.findByText("CSQU3054383");
    expect(screen.queryByRole("button", { name: "Ver PIN" })).not.toBeInTheDocument();
  });
```

Si el archivo no tiene una función `mockAuth` reutilizable ya definida, o si `vi.mock("@/lib/api", ...)` no incluye `obtenerPin`, ajustar el mock de `@/lib/api` al inicio del archivo para incluir `obtenerPin: vi.fn()` junto a `getContenedor: vi.fn()`, siguiendo el mismo patrón `importOriginal` que usan las demás páginas (`solicitar/page.test.tsx`, `porteria/page.test.tsx`).

- [ ] **Step 3: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- "app/contenedores/[id]/page.test.tsx"
```
Esperado: FAIL — no existe el botón "Ver PIN".

- [ ] **Step 4: Implementar el botón en `frontend/app/contenedores/[id]/page.tsx`**

Reemplazar el archivo completo:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, getContenedor, obtenerPin, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function ContenedorDetalleContent() {
  const params = useParams<{ id: string }>();
  const { token, user } = useAuth();
  const [contenedor, setContenedor] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pin, setPin] = useState<string | null>(null);
  const [pinError, setPinError] = useState<string | null>(null);
  const [pinLoading, setPinLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelado = false;
    setLoading(true);
    getContenedor(token, params.id)
      .then((data) => {
        if (!cancelado) setContenedor(data);
      })
      .catch((err) => {
        if (!cancelado) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el contenedor");
        }
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token, params.id]);

  async function handleVerPin() {
    if (!token) return;
    setPinLoading(true);
    setPinError(null);
    try {
      const resultado = await obtenerPin(token, params.id);
      setPin(resultado.pin_confirmacion);
    } catch (err) {
      setPinError(err instanceof ApiError ? err.message : "No se pudo obtener el PIN");
    } finally {
      setPinLoading(false);
    }
  }

  if (loading) return <p>Cargando...</p>;
  if (error)
    return (
      <p role="alert" className={styles.error}>
        {error}
      </p>
    );
  if (!contenedor) return null;

  return (
    <main className={styles.main}>
      <h1 className="mono">{contenedor.numero_contenedor}</h1>
      <dl className={styles.detalle}>
        <dt>Tipo</dt>
        <dd>{contenedor.tipo}</dd>
        <dt>Tamaño</dt>
        <dd>{contenedor.tamano}&apos;</dd>
        <dt>Estado</dt>
        <dd>{contenedor.estado}</dd>
        <dt>Peso</dt>
        <dd>{contenedor.peso_kg} kg</dd>
      </dl>
      {user?.rol === "admin" && (
        <div>
          <button onClick={handleVerPin} disabled={pinLoading}>
            {pinLoading ? "Cargando..." : "Ver PIN"}
          </button>
          {pinError && (
            <p role="alert" className={styles.error}>
              {pinError}
            </p>
          )}
          {pin && <p className="mono">{pin}</p>}
        </div>
      )}
    </main>
  );
}

export default function ContenedorDetallePage() {
  return (
    <AuthGuard>
      <ContenedorDetalleContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 5: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- "app/contenedores/[id]/page.test.tsx"
```
Esperado: PASS (todos).

- [ ] **Step 6: Correr la suite de frontend completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS (todos los archivos).

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add "frontend/app/contenedores/[id]/page.tsx" "frontend/app/contenedores/[id]/page.test.tsx"
git commit -m "feat: boton Ver PIN en detalle de contenedor, solo admin"
```

---

## Self-Review

**Cobertura del spec:**
- PIN generado con `secrets` al solicitar → Task 2.
- Envío por SendGrid solo al solicitante → Task 2.
- `pin_confirmacion` nunca en `ContenedorOut` → Task 1 (columna fuera del schema), verificado explícitamente en el test de Task 2 (`assert "pin_confirmacion" not in response.json()`).
- Visibilidad restringida a admin + cliente dueño → Task 3.
- Verificación por operador en patio, por `numero_contenedor` → Task 4.
- Sin gate en `movimientos.py` → confirmado, ningún task lo toca.
- Sin límite de reintentos → Task 4 no implementa contador ni bloqueo.
- Frontend: página de portería (Task 6), botón admin en detalle (Task 7), cliente HTTP (Task 5).

**Placeholders:** ninguno — todo paso de código trae el archivo completo o el bloque exacto a insertar.

**Consistencia de tipos:** `PinOut { pin_confirmacion: str }` (Task 2) se usa igual en Task 3 (`response_model=PinOut`) y Task 7 (`{ pin_confirmacion: string }` en TS). `PinVerificar { numero_contenedor, pin }` (Task 2) se usa igual en Task 4 (`payload.numero_contenedor`, `payload.pin`) y Task 6 (`verificarPin(token, { numero_contenedor, pin })`). `obtenerPin`/`verificarPin` (Task 5) se consumen con la misma firma en Tasks 6 y 7.

**Orden de rutas:** `POST /verificar-pin` se declara antes de `GET /{contenedor_id}` en el archivo (Task 4, ya existía el mismo patrón con `/solicitar`) — evita que FastAPI intente resolver `verificar-pin` como un `contenedor_id`.
