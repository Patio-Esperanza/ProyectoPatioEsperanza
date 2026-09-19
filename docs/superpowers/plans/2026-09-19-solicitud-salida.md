# Solicitud de Salida + Cola de Planeación de Grúa Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Reparto de trabajo (CLAUDE.md del proyecto):** la construcción de cada tarea se delega al subagente `codex-rescue`. Claude planea, revisa cada entrega de Codex, y decide si pasa a la siguiente tarea o si la tarea regresa a Claude tras dos fallos.

**Goal:** El cliente ve sus contenedores en el patio y solicita la salida de uno específico con fecha deseada; el staff ve una cola ordenada de esas solicitudes para planear los movimientos de grúa.

**Architecture:** Nuevo endpoint de listado `GET /api/contenedores` (no existía) con scoping por rol: cliente ve solo los suyos, staff filtra por `estado`/`patio_id`/`cliente_id`. `POST /api/contenedores/{id}/solicitar-salida` valida dueño, estado `UBICADO`, y anticipación mínima leída del `Patio` (nuevo campo `anticipacion_minima_horas`, editable vía `PATCH /api/patios/{id}`, primer endpoint de edición del proyecto). Dos páginas nuevas en frontend: `/mis-contenedores` (cliente) y `/salidas` (staff).

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend), Next.js App Router + vitest (frontend). Mismos patrones que Spec 1/Spec 2 de Portal Cliente.

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-09-19-solicitud-salida-design.md`.
- Elegibilidad para solicitar salida: solo `estado == UBICADO` (único estado "en el patio" alcanzable hoy vía API).
- `GET /api/contenedores` usa `db: AsyncSession = Depends(get_db)` (plano, **no** `get_scoped_db`) — mismo patrón ya usado por `solicitar_contenedor`, `verificar_pin` y `obtener_pin` en este archivo. Usar `get_scoped_db` bloquearía por RLS toda solicitud del rol `cliente` (su `patios_asignados` siempre está vacío), porque la política RLS de `contenedores` (migración `0006_rls_policies`) no distingue por `cliente_id`, solo por `patio_id`. La autorización se hace explícita en Python, igual que en `obtener_pin`.
- `anticipacion_minima_horas` no se agrega a `ContenedorOut` — vive solo en `PatioOut` (ya accesible a cualquier rol autenticado vía `GET /api/patios`, sin `require_roles`). Evita relaciones ORM nuevas (el proyecto no usa `relationship()` en ningún modelo hoy) o joins ad-hoc para un solo campo.
- `fecha_deseada_salida` y `salida_solicitada_en` son columnas nuevas en `contenedores`, distintas de `fecha_estimada_salida` (ya usada por Spec 1, expuesta como `fecha_estimada_retiro`).
- Todos los comandos de backend corren desde `/home/tony/Developer/ProyectoPatioEsperanza/backend` con `source .venv/bin/activate` y `PYTHONPATH=.` antes de `alembic`/`pytest`. El contenedor Postgres del proyecto debe estar arriba (`docker start proyectopatioesperanza-db-1` si no lo está).
- Todos los comandos de frontend corren desde `/home/tony/Developer/ProyectoPatioEsperanza/frontend` con `npm test -- <archivo>`.

---

### Task 1: Backend — migración y columnas (`Patio.anticipacion_minima_horas`, `Contenedor.fecha_deseada_salida`, `Contenedor.salida_solicitada_en`)

**Files:**
- Create: `backend/app/alembic/versions/0009_solicitud_salida.py`
- Modify: `backend/app/models/ubicacion.py`
- Modify: `backend/app/models/contenedor.py`

**Interfaces:**
- Produces: `Patio.anticipacion_minima_horas: int`, `Contenedor.fecha_deseada_salida: datetime | None`, `Contenedor.salida_solicitada_en: datetime | None`. Consumidas por Tasks 2, 3, 4.

- [ ] **Step 1: Crear `backend/app/alembic/versions/0009_solicitud_salida.py`**

```python
"""anticipacion minima por patio y solicitud de salida de contenedores

Revision ID: 0009_solicitud_salida
Revises: 0008_pin_confirmacion
Create Date: 2026-09-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_solicitud_salida"
down_revision = "0008_pin_confirmacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patios",
        sa.Column("anticipacion_minima_horas", sa.Integer(), nullable=False, server_default="24"),
    )
    op.add_column(
        "contenedores", sa.Column("fecha_deseada_salida", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "contenedores", sa.Column("salida_solicitada_en", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("contenedores", "salida_solicitada_en")
    op.drop_column("contenedores", "fecha_deseada_salida")
    op.drop_column("patios", "anticipacion_minima_horas")
```

- [ ] **Step 2: Levantar Postgres si no está arriba, y aplicar la migración**

```bash
docker start proyectopatioesperanza-db-1 2>/dev/null; true
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. alembic upgrade head
```
Esperado: `Running upgrade 0008_pin_confirmacion -> 0009_solicitud_salida, anticipacion minima por patio y solicitud de salida de contenedores`

- [ ] **Step 3: Agregar la columna a `backend/app/models/ubicacion.py`**

En la clase `Patio`, después de la línea `activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)`, agregar:

```python
    anticipacion_minima_horas: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
```

(`Integer` ya está importado en ese archivo.)

- [ ] **Step 4: Agregar las columnas a `backend/app/models/contenedor.py`**

En la clase `Contenedor`, después de `pin_verificado_por` (última columna antes de `created_at`), agregar:

```python
    fecha_deseada_salida: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    salida_solicitada_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Deben quedar antes de la línea `created_at: Mapped[datetime.datetime] = mapped_column(...)`.

- [ ] **Step 5: Correr la suite completa, confirmar que sigue pasando**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (69 tests — sin cambios de comportamiento todavía, solo columnas nuevas).

- [ ] **Step 6: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/alembic/versions/0009_solicitud_salida.py backend/app/models/ubicacion.py backend/app/models/contenedor.py
git commit -m "feat: columnas de anticipacion minima y solicitud de salida"
```

---

### Task 2: Backend — `PATCH /api/patios/{id}` (anticipación mínima)

**Files:**
- Modify: `backend/app/schemas/patio.py`
- Modify: `backend/app/api/routes/patios.py`
- Modify: `backend/tests/test_patios_api.py`

**Interfaces:**
- Produces: `PatioUpdate { anticipacion_minima_horas: int }`, `PatioOut` gana `anticipacion_minima_horas: int`. `PATCH /api/patios/{id}` → `PatioOut`. Consumido por el frontend en Task 6.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `backend/tests/test_patios_api.py`:

```python
@pytest.mark.anyio
async def test_admin_actualiza_anticipacion_minima(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Este", "codigo": "PE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]
    assert creado.json()["anticipacion_minima_horas"] == 24

    response = await client.patch(
        f"/api/patios/{patio_id}",
        json={"anticipacion_minima_horas": 48},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["anticipacion_minima_horas"] == 48


@pytest.mark.anyio
async def test_operador_no_puede_actualizar_patio(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    admin_token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Oeste", "codigo": "PO"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    patio_id = creado.json()["id"]

    op_token = _token(RolUsuario.OPERADOR)
    response = await client.patch(
        f"/api/patios/{patio_id}",
        json={"anticipacion_minima_horas": 48},
        headers={"Authorization": f"Bearer {op_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_actualizar_patio_valor_invalido(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    creado = await client.post(
        "/api/patios", json={"nombre": "Patio Centro", "codigo": "PC"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patio_id = creado.json()["id"]

    response = await client.patch(
        f"/api/patios/{patio_id}",
        json={"anticipacion_minima_horas": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_actualizar_patio_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.patch(
        "/api/patios/00000000-0000-0000-0000-0000000000ff",
        json={"anticipacion_minima_horas": 48},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_patios_api.py -v
```
Esperado: `test_admin_crea_patio` y otros existentes ahora también fallan si assertions nuevas los tocan (no es el caso aquí, no se tocan). Los 4 tests nuevos fallan: los tres primeros con `404 Not Found` (no existe `PATCH /api/patios/{id}`), el último también `404` en vez del `404` esperado por patio inexistente pero por ruta inexistente (mismo código, verificar en el mensaje/cuerpo que la ruta no está registrada — no confundir con el 404 correcto que se espera tras implementar).

- [ ] **Step 3: Reemplazar `backend/app/schemas/patio.py` completo**

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field


class PatioCreate(BaseModel):
    nombre: str
    codigo: str
    anticipacion_minima_horas: int = Field(default=24, gt=0)


class PatioUpdate(BaseModel):
    anticipacion_minima_horas: int = Field(gt=0)


class PatioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    codigo: str
    activo: bool
    anticipacion_minima_horas: int
```

- [ ] **Step 4: Reemplazar `backend/app/api/routes/patios.py` completo**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.ubicacion import Patio
from app.schemas.patio import PatioCreate, PatioOut, PatioUpdate

router = APIRouter()


@router.post("", response_model=PatioOut, status_code=status.HTTP_201_CREATED)
async def crear_patio(
    payload: PatioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Patio:
    patio = Patio(
        nombre=payload.nombre,
        codigo=payload.codigo,
        anticipacion_minima_horas=payload.anticipacion_minima_horas,
    )
    db.add(patio)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior=None,
        valor_nuevo={"nombre": patio.nombre, "codigo": patio.codigo},
        patio_id=patio.id,
    )
    await db.commit()
    return patio


@router.get("", response_model=list[PatioOut])
async def listar_patios(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[Patio]:
    result = await db.execute(select(Patio))
    return list(result.scalars().all())


@router.patch("/{patio_id}", response_model=PatioOut)
async def actualizar_patio(
    patio_id: str,
    payload: PatioUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Patio:
    result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = result.scalar_one_or_none()
    if patio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")

    valor_anterior = patio.anticipacion_minima_horas
    patio.anticipacion_minima_horas = payload.anticipacion_minima_horas

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="actualizar",
        entidad="patios",
        entidad_id=str(patio.id),
        valor_anterior={"anticipacion_minima_horas": valor_anterior},
        valor_nuevo={"anticipacion_minima_horas": patio.anticipacion_minima_horas},
        patio_id=patio.id,
    )
    await db.commit()
    await db.refresh(patio)
    return patio
```

- [ ] **Step 5: Correr los tests, confirmar que pasan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_patios_api.py -v
```
Esperado: PASS (todos, incluidos los 4 nuevos).

- [ ] **Step 6: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (73 tests).

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/patio.py backend/app/api/routes/patios.py backend/tests/test_patios_api.py
git commit -m "feat: PATCH /api/patios/id para anticipacion minima, admin-only"
```

---

### Task 3: Backend — `GET /api/contenedores` (listado con scoping por rol)

**Files:**
- Modify: `backend/app/api/routes/contenedores.py`
- Modify: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Consumes: `ContenedorOut` (ya existe), `RolUsuario`, `CurrentUser`.
- Produces: `GET /api/contenedores` → `list[ContenedorOut]`, filtros query `estado`, `patio_id`, `cliente_id`. No consumido por otras tasks backend; lo usa el frontend en Tasks 7 y 8.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `backend/tests/test_contenedores_api.py`:

```python
@pytest.mark.anyio
async def test_listar_contenedores_cliente_solo_ve_los_suyos(client, db_session, enviados_pin):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    _, cliente_a = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000c", "LLL121212LL1", "CSQU3053924"
    )
    otro_cliente = Cliente(
        razon_social="Otra Importadora", rfc="MMM131313MM1", tipo=TipoCliente.TRANSPORTISTA, activo=True
    )
    db_session.add(otro_cliente)
    await db_session.commit()
    await db_session.refresh(otro_cliente)
    db_session.add(
        Usuario(
            id=uuid.UUID("00000000-0000-0000-0000-00000000000d"),
            tipo=RolUsuario.CLIENTE,
            email="otro-listado@empresa.mx",
            password_hash="hash",
            cliente_id=otro_cliente.id,
            activo=True,
        )
    )
    await db_session.commit()
    otro_token = create_access_token(
        "00000000-0000-0000-0000-00000000000d", "cliente", [], 60, cliente_id=str(otro_cliente.id)
    )
    patio_b = await _crear_patio(db_session, "Patio Listado B", "PLB")
    await client.post(
        "/api/contenedores/solicitar",
        json={"numero_contenedor": "CSQU3053939", "tipo": "lleno", "tamano": "40", "peso_kg": 18000},
        headers={"Authorization": f"Bearer {otro_token}"},
    )

    token_a = create_access_token(
        "00000000-0000-0000-0000-00000000000c", "cliente", [], 60, cliente_id=str(cliente_a.id)
    )
    response = await client.get("/api/contenedores", headers={"Authorization": f"Bearer {token_a}"})

    assert response.status_code == 200
    numeros = [c["numero_contenedor"] for c in response.json()]
    assert numeros == ["CSQU3053924"]


@pytest.mark.anyio
async def test_listar_contenedores_staff_filtra_por_estado_ordenado_por_fecha(client, db_session, enviados_pin):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select as sa_select

    contenedor_id_1, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000e", "NNN141414NN1", "CSQU3053944"
    )
    contenedor_id_2, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-00000000000f", "OOO151515OO1", "CSQU3053959"
    )

    result1 = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id_1))
    c1 = result1.scalar_one()
    c1.estado = "solicitud_salida"
    c1.fecha_deseada_salida = datetime.now(timezone.utc) + timedelta(days=5)

    result2 = await db_session.execute(sa_select(Contenedor).where(Contenedor.id == contenedor_id_2))
    c2 = result2.scalar_one()
    c2.estado = "solicitud_salida"
    c2.fecha_deseada_salida = datetime.now(timezone.utc) + timedelta(days=1)
    await db_session.commit()

    await _crear_usuario_autenticado(db_session)
    admin_token = _token(RolUsuario.ADMIN)

    response = await client.get(
        "/api/contenedores?estado=solicitud_salida",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    ids = [c["id"] for c in response.json()]
    assert ids == [str(contenedor_id_2), str(contenedor_id_1)]
```

- [ ] **Step 2: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -k "listar_contenedores" -v
```
Esperado: FAIL con `405 Method Not Allowed` o `404` (no existe `GET /api/contenedores` sin id).

- [ ] **Step 3: Implementar `GET /api/contenedores`**

En `backend/app/api/routes/contenedores.py`, agregar `import uuid` al inicio (antes de `import secrets`), y agregar `Query` al import de fastapi:

```python
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
```

Agregar la ruta **antes de `crear_contenedor`** (para que quede junto a las demás rutas de nivel raíz y sea claro que `GET ""` es el listado):

```python
@router.get("", response_model=list[ContenedorOut])
async def listar_contenedores(
    estado: EstadoContenedor | None = Query(default=None),
    patio_id: uuid.UUID | None = Query(default=None),
    cliente_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[Contenedor]:
    query = select(Contenedor)

    if user.rol == RolUsuario.CLIENTE:
        query = query.where(Contenedor.cliente_id == user.cliente_id)
    else:
        if patio_id is not None:
            query = query.where(Contenedor.patio_id == patio_id)
        if cliente_id is not None:
            query = query.where(Contenedor.cliente_id == cliente_id)

    if estado is not None:
        query = query.where(Contenedor.estado == estado)

    if estado == EstadoContenedor.SOLICITUD_SALIDA:
        query = query.order_by(Contenedor.fecha_deseada_salida.asc())
    else:
        query = query.order_by(Contenedor.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())
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
git commit -m "feat: GET /api/contenedores listado con scoping por rol y filtros"
```

---

### Task 4: Backend — `POST /api/contenedores/{id}/solicitar-salida`

**Files:**
- Modify: `backend/app/schemas/contenedor.py`
- Modify: `backend/app/api/routes/contenedores.py`
- Modify: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Consumes: `Patio.anticipacion_minima_horas` (Task 1).
- Produces: `SolicitudSalida { fecha_deseada_salida: datetime }` (schema), `POST /api/contenedores/{id}/solicitar-salida` → `ContenedorOut`. No consumido por otras tasks backend; lo usa el frontend en Task 7.

- [ ] **Step 1: Escribir el helper de test y los tests que fallan**

Agregar al final de `backend/tests/test_contenedores_api.py`. `_crear_solicitud_con_pin` (ya existe en el archivo, de Spec 2) devuelve `(contenedor_id, cliente)` — el token del cliente dueño se arma con `cliente.id`:

```python
async def _ubicar_contenedor(client, db_session, contenedor_id: str, patio, sufijo: str) -> None:
    from app.models.ubicacion import Carril, Tira, Tramo, Ubicacion

    carril = Carril(patio_id=patio.id, codigo=f"A-{sufijo}", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="S1", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo=f"UB-{sufijo}")
    db_session.add(ubicacion)
    await db_session.commit()

    admin_id = "00000000-0000-0000-0000-0000000000ad"
    from sqlalchemy import select as sa_select

    existente = await db_session.execute(sa_select(Usuario).where(Usuario.id == uuid.UUID(admin_id)))
    if existente.scalar_one_or_none() is None:
        db_session.add(
            Usuario(
                id=uuid.UUID(admin_id),
                tipo=RolUsuario.ADMIN,
                email="admin-ubicar@patio.mx",
                password_hash="hash",
                activo=True,
            )
        )
        await db_session.commit()
    admin_token = create_access_token(admin_id, "admin", [], 60)

    mov = await client.post(
        "/api/movimientos",
        json={
            "contenedor_id": contenedor_id,
            "ubicacion_destino_id": str(ubicacion.id),
            "tipo": "ingreso",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert mov.status_code == 201


@pytest.mark.anyio
async def test_solicitar_salida_caso_feliz(client, db_session, enviados_pin):
    from datetime import datetime, timedelta, timezone

    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000010", "PPP161616PP1", "CSQU3053964"
    )
    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    patio_id = result.scalar_one().patio_id
    from app.models.ubicacion import Patio as PatioModel

    patio_result = await db_session.execute(select(PatioModel).where(PatioModel.id == patio_id))
    patio = patio_result.scalar_one()

    await _ubicar_contenedor(client, db_session, contenedor_id, patio, "SS1")

    token = create_access_token(
        "00000000-0000-0000-0000-000000000010", "cliente", [], 60, cliente_id=str(cliente.id)
    )
    fecha = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    response = await client.post(
        f"/api/contenedores/{contenedor_id}/solicitar-salida",
        json={"fecha_deseada_salida": fecha},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "solicitud_salida"


@pytest.mark.anyio
async def test_solicitar_salida_de_otro_cliente_403(client, db_session, enviados_pin):
    from datetime import datetime, timedelta, timezone
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    contenedor_id, _ = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000011", "QQQ171717QQ1", "CSQU3053979"
    )
    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    patio_id = result.scalar_one().patio_id
    from app.models.ubicacion import Patio as PatioModel

    patio_result = await db_session.execute(select(PatioModel).where(PatioModel.id == patio_id))
    patio = patio_result.scalar_one()
    await _ubicar_contenedor(client, db_session, contenedor_id, patio, "SS2")

    otro_cliente = Cliente(
        razon_social="Intrusa SA", rfc="RRR181818RR1", tipo=TipoCliente.TRANSPORTISTA, activo=True
    )
    db_session.add(otro_cliente)
    await db_session.commit()
    await db_session.refresh(otro_cliente)
    otro_token = create_access_token(
        "00000000-0000-0000-0000-000000000012", "cliente", [], 60, cliente_id=str(otro_cliente.id)
    )
    fecha = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    response = await client.post(
        f"/api/contenedores/{contenedor_id}/solicitar-salida",
        json={"fecha_deseada_salida": fecha},
        headers={"Authorization": f"Bearer {otro_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_solicitar_salida_estado_no_ubicado_409(client, db_session, enviados_pin):
    from datetime import datetime, timedelta, timezone

    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000013", "SSS191919SS1", "CSQU3053984"
    )
    token = create_access_token(
        "00000000-0000-0000-0000-000000000013", "cliente", [], 60, cliente_id=str(cliente.id)
    )
    fecha = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    response = await client.post(
        f"/api/contenedores/{contenedor_id}/solicitar-salida",
        json={"fecha_deseada_salida": fecha},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_solicitar_salida_antes_de_anticipacion_minima_422(client, db_session, enviados_pin):
    from datetime import datetime, timedelta, timezone

    contenedor_id, cliente = await _crear_solicitud_con_pin(
        client, db_session, "00000000-0000-0000-0000-000000000014", "TTT202020TT1", "CSQU3053995"
    )
    result = await db_session.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    patio_id = result.scalar_one().patio_id
    from app.models.ubicacion import Patio as PatioModel

    patio_result = await db_session.execute(select(PatioModel).where(PatioModel.id == patio_id))
    patio = patio_result.scalar_one()
    await _ubicar_contenedor(client, db_session, contenedor_id, patio, "SS3")

    token = create_access_token(
        "00000000-0000-0000-0000-000000000014", "cliente", [], 60, cliente_id=str(cliente.id)
    )
    fecha = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    response = await client.post(
        f"/api/contenedores/{contenedor_id}/solicitar-salida",
        json={"fecha_deseada_salida": fecha},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_solicitar_salida_contenedor_inexistente_404(client, db_session):
    await _crear_usuario_autenticado(db_session)
    token = create_access_token(
        "00000000-0000-0000-0000-000000000001", "cliente", [], 60,
        cliente_id="00000000-0000-0000-0000-000000000099",
    )
    from datetime import datetime, timedelta, timezone

    fecha = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    response = await client.post(
        "/api/contenedores/00000000-0000-0000-0000-0000000000ff/solicitar-salida",
        json={"fecha_deseada_salida": fecha},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
```

(El primer bloque de este Step, marcado "no usar tal cual", se incluye solo como advertencia explícita para quien ejecute la task — el bloque correcto que sí debe escribirse en el archivo es el segundo, completo, con las 5 funciones/tests desde `_ubicar_contenedor` hasta `test_solicitar_salida_contenedor_inexistente_404`.)

- [ ] **Step 2: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -k "solicitar_salida" -v
```
Esperado: FAIL con `404 Not Found` en todos (la ruta `solicitar-salida` no existe todavía).

- [ ] **Step 3: Agregar `SolicitudSalida` a `backend/app/schemas/contenedor.py`**

Agregar al final del archivo:

```python


class SolicitudSalida(BaseModel):
    fecha_deseada_salida: datetime.datetime
```

- [ ] **Step 4: Agregar `fecha_deseada_salida` a `ContenedorOut`**

En `backend/app/schemas/contenedor.py`, dentro de `class ContenedorOut`, después del campo `fecha_estimada_retiro`, agregar:

```python
    fecha_deseada_salida: datetime.datetime | None = None
```

- [ ] **Step 5: Implementar `POST /{contenedor_id}/solicitar-salida`**

En `backend/app/api/routes/contenedores.py`, agregar `import datetime` al inicio (junto a `import secrets` y `import uuid`):

```python
import datetime
import secrets
import uuid
```

Agregar `SolicitudSalida` al import de schemas:

```python
from app.schemas.contenedor import (
    ContenedorCreate,
    ContenedorOut,
    ContenedorSolicitud,
    PinOut,
    PinVerificar,
    SolicitudSalida,
)
```

Agregar la ruta **después de `verificar_pin`** (antes de `obtener_pin`):

```python
@router.post("/{contenedor_id}/solicitar-salida", response_model=ContenedorOut)
async def solicitar_salida(
    contenedor_id: str,
    payload: SolicitudSalida,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.CLIENTE)),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")

    if contenedor.cliente_id != user.cliente_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "No autorizado para solicitar la salida de este contenedor"
        )

    if contenedor.estado != EstadoContenedor.UBICADO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Este contenedor no está disponible para solicitar salida"
        )

    patio_result = await db.execute(select(Patio).where(Patio.id == contenedor.patio_id))
    patio = patio_result.scalar_one()

    fecha_deseada = payload.fecha_deseada_salida
    if fecha_deseada.tzinfo is None:
        fecha_deseada = fecha_deseada.replace(tzinfo=datetime.timezone.utc)
    minimo = datetime.timedelta(hours=patio.anticipacion_minima_horas)
    ahora = datetime.datetime.now(datetime.timezone.utc)
    if fecha_deseada < ahora + minimo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La fecha de salida debe ser al menos {patio.anticipacion_minima_horas} horas "
            "después de ahora para este patio",
        )

    contenedor.estado = EstadoContenedor.SOLICITUD_SALIDA
    contenedor.fecha_deseada_salida = fecha_deseada
    contenedor.salida_solicitada_en = func.now()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="solicitar_salida",
        entidad="contenedores",
        entidad_id=str(contenedor.id),
        valor_anterior={"estado": EstadoContenedor.UBICADO.value},
        valor_nuevo={"estado": contenedor.estado.value},
        patio_id=contenedor.patio_id,
    )
    await db.commit()
    await db.refresh(contenedor)
    return contenedor
```

- [ ] **Step 6: Correr los tests, confirmar que pasan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -v
```
Esperado: PASS (todos).

- [ ] **Step 7: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (80 tests).

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/contenedor.py backend/app/api/routes/contenedores.py backend/tests/test_contenedores_api.py
git commit -m "feat: POST /api/contenedores/id/solicitar-salida con validacion de anticipacion"
```

---

### Task 5: Frontend — `lib/api.ts` (listado, solicitar salida, anticipación de patio)

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`
- Modify: `frontend/app/patios/page.test.tsx` (agregar `anticipacion_minima_horas` a los mocks existentes de `Patio`, requerido por el cambio de tipo)

**Interfaces:**
- Produces: `listarContenedores(token, filtros?: { estado?: EstadoContenedor; patio_id?: string; cliente_id?: string }): Promise<Contenedor[]>`, `solicitarSalida(token, id, fecha_deseada_salida: string): Promise<Contenedor>`, `actualizarPatio(token, id, anticipacion_minima_horas: number): Promise<Patio>`. `Patio` gana `anticipacion_minima_horas: number` (requerido). `Contenedor` gana `fecha_deseada_salida?: string | null` (opcional, mismo patrón que `fecha_estimada_retiro`). Consumidos por Tasks 6, 7, 8.

- [ ] **Step 1: Actualizar los mocks de `Patio` existentes en `frontend/app/patios/page.test.tsx`**

Los tres literales `{ id: ..., nombre: ..., codigo: ..., activo: true }` en ese archivo deben ganar `anticipacion_minima_horas: 24` (el tipo `Patio` va a requerir el campo). Ejemplo del primero:

```typescript
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);
```

Aplicar el mismo agregado a los otros dos literales de `Patio` en ese archivo (la llamada `mockResolvedValueOnce([{ id: "2", nombre: "Patio Sur", codigo: "PS", activo: true }])` y el `createPatio.mockResolvedValue({ id: "2", nombre: "Patio Sur", codigo: "PS", activo: true })`).

- [ ] **Step 2: Escribir los tests que fallan en `frontend/lib/api.test.ts`**

Leer primero el archivo completo para replicar el patrón exacto de `fetchMock`/`jsonResponse` que ya usa (mismo patrón usado en Spec 2 para `obtenerPin`/`verificarPin`). Agregar al final:

```typescript
describe("listarContenedores", () => {
  it("requests without filters", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([]));

    await listarContenedores("token");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
  });

  it("requests with query filters", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([]));

    await listarContenedores("token", { estado: "solicitud_salida", patio_id: "p1" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores?estado=solicitud_salida&patio_id=p1",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
  });
});

describe("solicitarSalida", () => {
  it("posts fecha_deseada_salida", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "solicitud_salida",
        peso_kg: 18000,
      })
    );

    const result = await solicitarSalida("token", "c1", "2026-10-05T12:00:00Z");

    expect(result.estado).toBe("solicitud_salida");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores/c1/solicitar-salida",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ fecha_deseada_salida: "2026-10-05T12:00:00Z" }),
      })
    );
  });
});

describe("actualizarPatio", () => {
  it("patches anticipacion_minima_horas", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 48 })
    );

    const result = await actualizarPatio("token", "p1", 48);

    expect(result.anticipacion_minima_horas).toBe(48);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/patios/p1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ anticipacion_minima_horas: 48 }),
      })
    );
  });
});
```

- [ ] **Step 3: Correr los tests, confirmar que fallan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `listarContenedores`, `solicitarSalida`, `actualizarPatio` no están exportados.

- [ ] **Step 4: Actualizar `frontend/lib/api.ts`**

Reemplazar la interfaz `Patio` completa:

```typescript
export interface Patio {
  id: string;
  nombre: string;
  codigo: string;
  activo: boolean;
  anticipacion_minima_horas: number;
}
```

Reemplazar la interfaz `Contenedor` completa:

```typescript
export interface Contenedor {
  id: string;
  numero_contenedor: string;
  tipo: TipoContenedor;
  tamano: TamanoContenedor;
  patio_id: string;
  estado: EstadoContenedor;
  peso_kg: number;
  fecha_estimada_retiro?: string | null;
  fecha_deseada_salida?: string | null;
}
```

Agregar después de `export async function listPatios(...)`:

```typescript
export async function actualizarPatio(
  token: string,
  id: string,
  anticipacion_minima_horas: number
): Promise<Patio> {
  return request<Patio>(`/api/patios/${id}`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ anticipacion_minima_horas }),
  });
}
```

Agregar después de `export async function getContenedor(...)`:

```typescript
export async function listarContenedores(
  token: string,
  filtros?: { estado?: EstadoContenedor; patio_id?: string; cliente_id?: string }
): Promise<Contenedor[]> {
  const params = new URLSearchParams();
  if (filtros?.estado) params.set("estado", filtros.estado);
  if (filtros?.patio_id) params.set("patio_id", filtros.patio_id);
  if (filtros?.cliente_id) params.set("cliente_id", filtros.cliente_id);
  const query = params.toString();
  return request<Contenedor[]>(`/api/contenedores${query ? `?${query}` : ""}`, { token });
}

export async function solicitarSalida(
  token: string,
  id: string,
  fecha_deseada_salida: string
): Promise<Contenedor> {
  return request<Contenedor>(`/api/contenedores/${id}/solicitar-salida`, {
    method: "POST",
    token,
    body: JSON.stringify({ fecha_deseada_salida }),
  });
}
```

- [ ] **Step 5: Correr los tests, confirmar que pasan**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
npm test -- app/patios/page.test.tsx
```
Esperado: PASS (ambos).

- [ ] **Step 6: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts frontend/app/patios/page.test.tsx
git commit -m "feat: cliente HTTP para listado de contenedores, solicitar salida y anticipacion de patio"
```

---

### Task 6: Frontend — edición de anticipación mínima en `/patios`

**Files:**
- Modify: `frontend/app/patios/page.tsx`
- Modify: `frontend/app/patios/page.test.tsx`

**Interfaces:**
- Consumes: `actualizarPatio(token, id, anticipacion_minima_horas)` (Task 5).

- [ ] **Step 1: Escribir el test que falla**

Agregar al `describe("PatiosPage", ...)` en `frontend/app/patios/page.test.tsx`:

```typescript
  it("lets an admin update the anticipacion minima of a patio", async () => {
    mockAuth("admin");
    vi.mocked(listPatios).mockResolvedValue([
      { id: "1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);
    vi.mocked(actualizarPatio).mockResolvedValue({
      id: "1",
      nombre: "Patio Norte",
      codigo: "PN",
      activo: true,
      anticipacion_minima_horas: 48,
    });

    const user = userEvent.setup();
    render(<PatiosPage />);

    const input = await screen.findByLabelText("Anticipación mínima (h) — PN");
    await user.clear(input);
    await user.type(input, "48");
    await user.tab();

    expect(actualizarPatio).toHaveBeenCalledWith("token", "1", 48);
  });
```

Agregar `actualizarPatio` al mock de `@/lib/api` al inicio del archivo:

```typescript
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listPatios: vi.fn(), createPatio: vi.fn(), actualizarPatio: vi.fn() };
});
```

Y agregar `actualizarPatio` al import de `@/lib/api` en la primera línea de imports del archivo:

```typescript
import { listPatios, createPatio, actualizarPatio } from "@/lib/api";
```

Y resetear el mock en `beforeEach`:

```typescript
beforeEach(() => {
  vi.mocked(listPatios).mockReset();
  vi.mocked(createPatio).mockReset();
  vi.mocked(actualizarPatio).mockReset();
});
```

- [ ] **Step 2: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/patios/page.test.tsx
```
Esperado: FAIL — no existe el input "Anticipación mínima (h) — PN".

- [ ] **Step 3: Implementar en `frontend/app/patios/page.tsx`**

Reemplazar el import de `@/lib/api`:

```typescript
import { ApiError, actualizarPatio, createPatio, listPatios, type Patio } from "@/lib/api";
```

Reemplazar la función `PatiosContent` completa:

```tsx
function PatiosContent() {
  const { token, user } = useAuth();
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [creating, setCreating] = useState(false);

  const cargarPatios = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listPatios(token);
      setPatios(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los patios");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    cargarPatios();
  }, [cargarPatios]);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createPatio(token, { nombre, codigo });
      setNombre("");
      setCodigo("");
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el patio");
    } finally {
      setCreating(false);
    }
  }

  async function handleActualizarAnticipacion(patioId: string, valor: number) {
    if (!token || Number.isNaN(valor) || valor <= 0) return;
    try {
      await actualizarPatio(token, patioId, valor);
      await cargarPatios();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la anticipación");
    }
  }

  return (
    <main className={styles.main}>
      <h1>Patios</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {patios.map((patio) => (
            <li key={patio.id}>
              <span className="mono">{patio.codigo}</span> — {patio.nombre}
              {user?.rol === "admin" && (
                <span className={styles.anticipacion}>
                  <label htmlFor={`anticipacion-${patio.id}`}>
                    Anticipación mínima (h) — {patio.codigo}
                  </label>
                  <input
                    id={`anticipacion-${patio.id}`}
                    type="number"
                    min={1}
                    defaultValue={patio.anticipacion_minima_horas}
                    onBlur={(e) => handleActualizarAnticipacion(patio.id, Number(e.target.value))}
                  />
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {user?.rol === "admin" && (
        <form className={styles.form} onSubmit={handleCrear}>
          <h2>Nuevo patio</h2>
          <label htmlFor="nombre">Nombre</label>
          <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          <label htmlFor="codigo">Código</label>
          <input id="codigo" value={codigo} onChange={(e) => setCodigo(e.target.value)} required />
          <button type="submit" disabled={creating}>
            {creating ? "Creando..." : "Crear patio"}
          </button>
        </form>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/patios/page.test.tsx
```
Esperado: PASS (todos).

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/patios/page.tsx frontend/app/patios/page.test.tsx
git commit -m "feat: edicion inline de anticipacion minima por patio, admin-only"
```

---

### Task 7: Frontend — página `/mis-contenedores` (cliente) + link en NavBar

**Files:**
- Create: `frontend/app/mis-contenedores/page.tsx`
- Create: `frontend/app/mis-contenedores/page.module.css`
- Create: `frontend/app/mis-contenedores/page.test.tsx`
- Modify: `frontend/components/NavBar.tsx`
- Modify: `frontend/components/NavBar.test.tsx`

**Interfaces:**
- Consumes: `listarContenedores(token)`, `solicitarSalida(token, id, fecha)`, `listPatios(token)` (todas de Task 5).

- [ ] **Step 1: Escribir el test que falla — link en NavBar**

Agregar a `frontend/components/NavBar.test.tsx`:

```typescript
  it("shows the Mis contenedores link only for cliente", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    const { rerender } = render(<NavBar />);
    expect(screen.queryByText("Mis contenedores")).not.toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "cliente", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    rerender(<NavBar />);
    expect(screen.getByText("Mis contenedores")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: FAIL.

- [ ] **Step 3: Agregar el link en `frontend/components/NavBar.tsx`**

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
        {(user.rol === "operador" || user.rol === "supervisor" || user.rol === "admin") && (
          <Link href="/salidas">Salidas</Link>
        )}
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "admin" && <Link href="/clientes">Clientes</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
        {user.rol === "cliente" && <Link href="/mis-contenedores">Mis contenedores</Link>}
      </div>
```

(Este Step ya deja también el link "Salidas" listo para la Task 8 — evita tocar `NavBar.tsx` dos veces.)

- [ ] **Step 4: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: PASS.

- [ ] **Step 5: Commit del NavBar**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/components/NavBar.tsx frontend/components/NavBar.test.tsx
git commit -m "feat: links Mis contenedores y Salidas en NavBar"
```

- [ ] **Step 6: Escribir `frontend/app/mis-contenedores/page.test.tsx`**

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MisContenedoresPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listarContenedores, listPatios, solicitarSalida } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listarContenedores: vi.fn(),
    listPatios: vi.fn(),
    solicitarSalida: vi.fn(),
  };
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
  vi.mocked(listarContenedores).mockReset();
  vi.mocked(listPatios).mockReset();
  vi.mocked(solicitarSalida).mockReset();
});

describe("MisContenedoresPage", () => {
  it("shows a not-authorized message for non-cliente roles", async () => {
    mockAuth("operador");

    render(<MisContenedoresPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("No autorizado");
  });

  it("lists the client's contenedores and shows Solicitar salida only for ubicado", async () => {
    mockAuth("cliente");
    vi.mocked(listarContenedores).mockResolvedValue([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "ubicado",
        peso_kg: 18000,
      },
      {
        id: "c2",
        numero_contenedor: "TRHU1866154",
        tipo: "lleno",
        tamano: "20",
        patio_id: "p1",
        estado: "solicitud_ingreso",
        peso_kg: 12000,
      },
    ]);
    vi.mocked(listPatios).mockResolvedValue([
      { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);

    render(<MisContenedoresPage />);

    expect(await screen.findByText(/CSQU3054383/)).toBeInTheDocument();
    expect(screen.getByText(/TRHU1866154/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Solicitar salida" })).toHaveLength(1);
    expect(screen.getByText(/24 horas/)).toBeInTheDocument();
  });

  it("submits a solicitud de salida", async () => {
    mockAuth("cliente");
    vi.mocked(listarContenedores).mockResolvedValue([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "ubicado",
        peso_kg: 18000,
      },
    ]);
    vi.mocked(listPatios).mockResolvedValue([
      { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
    ]);
    vi.mocked(solicitarSalida).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_salida",
      peso_kg: 18000,
    });

    const user = userEvent.setup();
    render(<MisContenedoresPage />);

    await user.click(await screen.findByRole("button", { name: "Solicitar salida" }));
    await user.type(screen.getByLabelText("Fecha y hora deseada"), "2026-10-05T12:00");
    await user.click(screen.getByRole("button", { name: "Confirmar solicitud" }));

    expect(solicitarSalida).toHaveBeenCalledWith("token", "c1", "2026-10-05T12:00");
    expect(await screen.findByText(/solicitud_salida/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/mis-contenedores/page.test.tsx
```
Esperado: FAIL — el módulo `./page` no existe.

- [ ] **Step 8: Crear `frontend/app/mis-contenedores/page.module.css`**

```css
.main {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list li {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 8px;
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

- [ ] **Step 9: Crear `frontend/app/mis-contenedores/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  listPatios,
  listarContenedores,
  solicitarSalida,
  type Contenedor,
  type Patio,
} from "@/lib/api";
import styles from "./page.module.css";

function MisContenedoresContent() {
  const { token, user } = useAuth();
  const [contenedores, setContenedores] = useState<Contenedor[]>([]);
  const [patios, setPatios] = useState<Patio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abiertoId, setAbiertoId] = useState<string | null>(null);
  const [fecha, setFecha] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function cargar() {
    if (!token) return;
    setLoading(true);
    try {
      const [datosContenedores, datosPatios] = await Promise.all([
        listarContenedores(token),
        listPatios(token),
      ]);
      setContenedores(datosContenedores);
      setPatios(datosPatios);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar tus contenedores");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleSolicitar(id: string) {
    if (!token || !fecha) return;
    setSubmitting(true);
    setError(null);
    try {
      await solicitarSalida(token, id, fecha);
      setAbiertoId(null);
      setFecha("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo solicitar la salida");
    } finally {
      setSubmitting(false);
    }
  }

  if (user?.rol !== "cliente") {
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
      <h1>Mis contenedores</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {contenedores.map((c) => {
            const patio = patios.find((p) => p.id === c.patio_id);
            return (
              <li key={c.id}>
                <span className="mono">{c.numero_contenedor}</span> — estado {c.estado}
                {c.estado === "ubicado" && (
                  <>
                    <button onClick={() => setAbiertoId(c.id)}>Solicitar salida</button>
                    {abiertoId === c.id && (
                      <div className={styles.form}>
                        {patio && (
                          <p>Este patio requiere al menos {patio.anticipacion_minima_horas} horas de anticipación.</p>
                        )}
                        <label htmlFor={`fecha-${c.id}`}>Fecha y hora deseada</label>
                        <input
                          id={`fecha-${c.id}`}
                          type="datetime-local"
                          value={fecha}
                          onChange={(e) => setFecha(e.target.value)}
                        />
                        <button disabled={submitting} onClick={() => handleSolicitar(c.id)}>
                          {submitting ? "Enviando..." : "Confirmar solicitud"}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}

export default function MisContenedoresPage() {
  return (
    <AuthGuard>
      <MisContenedoresContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 10: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/mis-contenedores/page.test.tsx
```
Esperado: PASS (todos).

- [ ] **Step 11: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/mis-contenedores
git commit -m "feat: pagina Mis contenedores con solicitud de salida, solo cliente"
```

---

### Task 8: Frontend — página `/salidas` (cola de planeación, staff)

**Files:**
- Create: `frontend/app/salidas/page.tsx`
- Create: `frontend/app/salidas/page.module.css`
- Create: `frontend/app/salidas/page.test.tsx`

**Interfaces:**
- Consumes: `listarContenedores(token, { estado, patio_id })` (Task 5), `PatioSelect` (`@/components/PatioSelect`, ya existe).

- [ ] **Step 1: Escribir `frontend/app/salidas/page.test.tsx`**

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import SalidasPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listarContenedores } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listarContenedores: vi.fn(), listPatios: vi.fn() };
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
  vi.mocked(listarContenedores).mockReset();
});

describe("SalidasPage", () => {
  it("shows a not-authorized message for cliente role", () => {
    mockAuth("cliente");

    render(<SalidasPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("No autorizado");
  });

  it("lists pending salida requests ordered by fecha_deseada_salida", async () => {
    mockAuth("operador");
    vi.mocked(listarContenedores).mockResolvedValue([
      {
        id: "c1",
        numero_contenedor: "CSQU3054383",
        tipo: "lleno",
        tamano: "40",
        patio_id: "p1",
        estado: "solicitud_salida",
        peso_kg: 18000,
        fecha_deseada_salida: "2026-10-05T12:00:00Z",
      },
    ]);

    render(<SalidasPage />);

    await waitFor(() =>
      expect(listarContenedores).toHaveBeenCalledWith("token", { estado: "solicitud_salida" })
    );
    expect(await screen.findByText(/CSQU3054383/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Correr el test, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/salidas/page.test.tsx
```
Esperado: FAIL — el módulo `./page` no existe.

- [ ] **Step 3: Crear `frontend/app/salidas/page.module.css`**

```css
.main {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list li {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 10px;
  border-radius: 6px;
}
```

- [ ] **Step 4: Crear `frontend/app/salidas/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, listarContenedores, type Contenedor } from "@/lib/api";
import styles from "./page.module.css";

function SalidasContent() {
  const { token, user } = useAuth();
  const [contenedores, setContenedores] = useState<Contenedor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelado = false;
    setLoading(true);
    listarContenedores(token, { estado: "solicitud_salida" })
      .then((data) => {
        if (!cancelado) setContenedores(data);
      })
      .catch((err) => {
        if (!cancelado) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar la cola de salidas");
        }
      })
      .finally(() => {
        if (!cancelado) setLoading(false);
      });
    return () => {
      cancelado = true;
    };
  }, [token]);

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
      <h1>Cola de salidas</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : contenedores.length === 0 ? (
        <p>No hay solicitudes de salida pendientes.</p>
      ) : (
        <ul className={styles.list}>
          {contenedores.map((c) => (
            <li key={c.id}>
              <span className="mono">{c.numero_contenedor}</span> — salida deseada{" "}
              {c.fecha_deseada_salida
                ? new Date(c.fecha_deseada_salida).toLocaleString()
                : "sin fecha"}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default function SalidasPage() {
  return (
    <AuthGuard>
      <SalidasContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 5: Correr el test, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/salidas/page.test.tsx
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
git add frontend/app/salidas
git commit -m "feat: pagina Salidas, cola de planeacion para operador/supervisor/admin"
```

---

## Self-Review

**Cobertura del spec:**
- Cliente inicia solicitud de salida, como la entrada → Task 4 (backend), Task 7 (frontend).
- `fecha_estimada_retiro` intacta, nuevo campo `fecha_deseada_salida` distinto → Task 1, Task 4 Step 4.
- Cola simple ordenada por fecha, sin cálculo de capacidad → Task 3 (orden por `fecha_deseada_salida` solo cuando `estado=solicitud_salida`), Task 8 (página sin ningún cálculo de capacidad).
- Anticipación mínima configurable por patio → Task 1 (columna), Task 2 (`PATCH`), Task 6 (UI admin).
- Elegibilidad solo `UBICADO` → Task 4 Step 5 (`if contenedor.estado != EstadoContenedor.UBICADO`).

**Placeholders:** ninguno — todo paso de código trae el archivo completo o el bloque exacto a insertar.

**Consistencia de tipos:** `Patio.anticipacion_minima_horas: int` (Task 1) se usa igual en `PatioOut`/`PatioUpdate` (Task 2), en TS `Patio.anticipacion_minima_horas: number` (Task 5) y en las páginas (Tasks 6, 7). `Contenedor.fecha_deseada_salida` (Task 1, columna) → `ContenedorOut.fecha_deseada_salida` (Task 4) → TS `Contenedor.fecha_deseada_salida?: string | null` (Task 5) → usado en Tasks 7 y 8. `listarContenedores`/`solicitarSalida`/`actualizarPatio` (Task 5) se consumen con la misma firma en Tasks 6, 7 y 8.

**Riesgo de RLS documentado:** `GET /api/contenedores` usa `get_db` plano, no `get_scoped_db` — documentado en Global Constraints con la razón exacta (política RLS de `contenedores` no distingue `cliente_id`, solo `patio_id`; cliente siempre tiene `patios_asignados` vacío).

**Orden de rutas:** `POST /{contenedor_id}/solicitar-salida` va después de `verificar_pin` y antes de `obtener_pin`/`obtener_contenedor` — mismo criterio ya usado en Spec 2 (rutas con segmento literal después del id van antes que el `GET /{contenedor_id}` genérico, aunque aquí no hay colisión real de método+patrón, se mantiene por legibilidad y consistencia).
