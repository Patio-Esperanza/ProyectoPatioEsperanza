# Mapa visual del patio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una pantalla `/mapa` que muestre la ocupación del patio en vista de planta y permita colocar un contenedor en una ubicación libre.

**Architecture:** El backend gana un endpoint que agrega la ocupación por tira (no por ubicación, para no mandar 7,200 filas) y otro que devuelve el detalle de los 5 niveles de una tira. El frontend dibuja la cuadrícula con CSS grid sobre DOM, con `role="grid"` y roving tabindex. La colocación reusa `POST /api/movimientos`, que ya bloquea la ubicación destino y responde 409 si está ocupada.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Postgres con RLS. Next.js App Router, React, TypeScript, CSS Modules, Vitest con Testing Library.

## Global Constraints

- Spec de referencia: `docs/superpowers/specs/2026-09-22-mapa-patio-design.md`.
- Roles con acceso al mapa: `operador`, `supervisor`, `admin`. El rol `cliente` recibe 403.
- Todo endpoint nuevo pasa por `require_roles` de `app/api/deps.py`, que fija los GUC `app.rol` y `app.patios_asignados` con `set_config(..., true)`. No escribir GUC a mano: la migración `0010_rls_fail_closed` depende de ese contrato.
- Sin `datetime.utcnow()`. El código existente usa `datetime.now(timezone.utc)`.
- El color nunca es el único indicador de estado en la interfaz. Cada celda imprime su texto `n/5`.
- Los tests de backend corren contra Postgres real en el puerto 5433, según `backend/tests/conftest.py`. La base debe estar arriba antes de correrlos.
- Textos de interfaz en español, igual que el resto de las páginas.
- Los archivos de componente nuevos van acompañados de su `.module.css` y su `.test.tsx`, como los nueve componentes de `frontend/components/ui/`.

## Estructura de archivos

Backend, se crean:

| Archivo | Responsabilidad |
| --- | --- |
| `backend/app/alembic/versions/0011_patio_punto_entrada.py` | Agrega `patios.ubicacion_entrada_id` |
| `backend/app/services/mapa_patio.py` | Consultas de ocupación agregada y de detalle de tira |
| `backend/app/schemas/mapa.py` | Modelos Pydantic del mapa y del detalle de tira |
| `backend/app/api/routes/tiras.py` | `GET /api/tiras/{tira_id}` |
| `backend/scripts/seed_patio_layout.py` | Carga el layout de un patio |
| `backend/tests/test_mapa_patio.py` | Tests del servicio y de los dos endpoints |

Backend, se modifican:

| Archivo | Cambio |
| --- | --- |
| `backend/app/models/ubicacion.py` | Campo `ubicacion_entrada_id` en `Patio` |
| `backend/app/schemas/patio.py` | `PatioOut` expone `ubicacion_entrada_id` |
| `backend/app/api/routes/patios.py` | `GET /{patio_id}/mapa` |
| `backend/app/api/routes/contenedores.py` | Filtro `sin_ubicacion` |
| `backend/app/schemas/ubicacion.py` | `SugerenciaUbicacionResponse` gana `tira_id` y `nivel` |
| `backend/app/services/ubicacion_algoritmo.py` | `CandidatoUbicacion` gana `tira_id` y `nivel` |
| `backend/app/api/routes/ubicaciones.py` | Devuelve los dos campos nuevos |
| `backend/app/main.py` | Monta el router `tiras` |

Frontend, se crean:

| Archivo | Responsabilidad |
| --- | --- |
| `frontend/components/mapa/CeldaTira.tsx` | Una celda de la cuadrícula |
| `frontend/components/mapa/MapaPatio.tsx` | La cuadrícula completa, con leyenda y filtro por carril |
| `frontend/components/mapa/DetalleTira.tsx` | Los 5 niveles de una tira |
| `frontend/components/mapa/PanelPendientes.tsx` | Contenedores sin ubicación |
| `frontend/app/mapa/page.tsx` | Orquesta el estado y las llamadas a la API |

Frontend, se modifican:

| Archivo | Cambio |
| --- | --- |
| `frontend/lib/api.ts` | Tipos y funciones del mapa |
| `frontend/lib/rutas.ts` | `"/mapa": [...ROLES_STAFF]` |
| `frontend/components/Sidebar.tsx` | Enlace al mapa |

---

### Task 1: Punto de entrada del patio

**Files:**
- Create: `backend/app/alembic/versions/0011_patio_punto_entrada.py`
- Modify: `backend/app/models/ubicacion.py`
- Modify: `backend/app/schemas/patio.py`
- Test: `backend/tests/test_patios_api.py`

**Interfaces:**
- Consumes: nada.
- Produces: `Patio.ubicacion_entrada_id: Mapped[uuid.UUID | None]`, y el campo `ubicacion_entrada_id: uuid.UUID | None` en la respuesta de `GET /api/patios`.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `backend/tests/test_patios_api.py`:

```python
@pytest.mark.anyio
async def test_patio_expone_punto_de_entrada_nulo(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/patios",
        json={"nombre": "Patio Entrada", "codigo": "PE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get("/api/patios", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    patio = next(p for p in response.json() if p["codigo"] == "PE")
    assert patio["ubicacion_entrada_id"] is None
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && pytest tests/test_patios_api.py::test_patio_expone_punto_de_entrada_nulo -v`
Expected: FAIL con `KeyError: 'ubicacion_entrada_id'`

- [ ] **Step 3: Escribir la migración**

Crear `backend/app/alembic/versions/0011_patio_punto_entrada.py`:

```python
"""punto de entrada del patio para el mapa

Revision ID: 0011_patio_punto_entrada
Revises: 0010_rls_fail_closed
Create Date: 2026-09-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_patio_punto_entrada"
down_revision = "0010_rls_fail_closed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patios",
        sa.Column("ubicacion_entrada_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # La llave cierra un ciclo: patios -> ubicaciones -> tiras -> tramos -> carriles -> patios.
    # Postgres lo acepta porque la restriccion se agrega despues de que las dos tablas existen.
    op.create_foreign_key(
        "fk_patio_ubicacion_entrada",
        "patios",
        "ubicaciones",
        ["ubicacion_entrada_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_patio_ubicacion_entrada", "patios", type_="foreignkey")
    op.drop_column("patios", "ubicacion_entrada_id")
```

- [ ] **Step 4: Agregar el campo al modelo**

En `backend/app/models/ubicacion.py`, dentro de `class Patio`, después de la línea de `anticipacion_minima_horas`:

```python
    ubicacion_entrada_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=True
    )
```

- [ ] **Step 5: Exponer el campo en el schema**

En `backend/app/schemas/patio.py`, dentro de `class PatioOut`, después de `anticipacion_minima_horas`:

```python
    ubicacion_entrada_id: uuid.UUID | None = None
```

- [ ] **Step 6: Correr los tests de patios**

Run: `cd backend && pytest tests/test_patios_api.py -v`
Expected: PASS, incluyendo los tests que ya existían

- [ ] **Step 7: Commit**

```bash
git add backend/app/alembic/versions/0011_patio_punto_entrada.py backend/app/models/ubicacion.py backend/app/schemas/patio.py backend/tests/test_patios_api.py
git commit -m "feat: punto de entrada del patio para el mapa"
```

---

### Task 2: Servicio y endpoint del mapa

**Files:**
- Create: `backend/app/services/mapa_patio.py`
- Create: `backend/app/schemas/mapa.py`
- Create: `backend/tests/test_mapa_patio.py`
- Modify: `backend/app/api/routes/patios.py`

**Interfaces:**
- Consumes: `Patio.ubicacion_entrada_id` de la Task 1.
- Produces:
  - `async def obtener_mapa(db: AsyncSession, patio_id: uuid.UUID) -> MapaPatioOut`
  - `GET /api/patios/{patio_id}/mapa` con cuerpo `MapaPatioOut`
  - Clases `TiraMapaOut`, `TramoMapaOut`, `CarrilMapaOut`, `ResumenMapaOut`, `MapaPatioOut` en `app/schemas/mapa.py`

- [ ] **Step 1: Escribir los schemas**

Crear `backend/app/schemas/mapa.py`:

```python
import uuid

from pydantic import BaseModel

from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


class TiraMapaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    orden: int
    niveles_totales: int
    niveles_activos: int
    niveles_ocupados: int


class TramoMapaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    orden: int
    tiras: list[TiraMapaOut]


class CarrilMapaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    orden: int
    tipo_teorico: TipoContenedor | None
    tramos: list[TramoMapaOut]


class ResumenMapaOut(BaseModel):
    ubicaciones_activas: int
    ocupadas: int


class MapaPatioOut(BaseModel):
    patio_id: uuid.UUID
    ubicacion_entrada_id: uuid.UUID | None
    resumen: ResumenMapaOut
    carriles: list[CarrilMapaOut]


class ContenedorEnNivelOut(BaseModel):
    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    peso_kg: int
    estado: EstadoContenedor


class NivelTiraOut(BaseModel):
    nivel: int
    ubicacion_id: uuid.UUID
    codigo: str
    activo: bool
    capacidad_peso_kg: int
    contenedor: ContenedorEnNivelOut | None


class DetalleTiraOut(BaseModel):
    tira_id: uuid.UUID
    codigo: str
    niveles: list[NivelTiraOut]
```

- [ ] **Step 2: Escribir el test que falla**

Crear `backend/tests/test_mapa_patio.py`:

```python
import uuid

import pytest

from app.core.security import create_access_token
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario, TamanoContenedor, TipoContenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.models.usuario import Usuario
from app.services.mapa_patio import obtener_mapa

_USUARIO_ID = "00000000-0000-0000-0000-000000000051"


def _token(rol: RolUsuario, patios: list[str] | None = None) -> str:
    return create_access_token(_USUARIO_ID, rol.value, patios or [], 60)


async def _crear_usuario(db_session, rol: RolUsuario) -> None:
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=rol,
            email=f"mapa-{rol.value}@patio.mx",
            password_hash="hash",
            activo=True,
        )
    )
    await db_session.commit()


async def _crear_layout(db_session, sufijo: str) -> tuple[Patio, Tira, list[Ubicacion]]:
    """Un patio con un carril, un tramo, una tira y tres niveles.

    El nivel 3 queda inactivo, para poder distinguir niveles_totales de niveles_activos.
    """
    patio = Patio(nombre=f"Patio {sufijo}", codigo=f"MP{sufijo}")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="A1", orden=0, tipo_teorico=TipoContenedor.LLENO)
    db_session.add(carril)
    await db_session.flush()

    tramo = Tramo(carril_id=carril.id, codigo="T1", orden=0)
    db_session.add(tramo)
    await db_session.flush()

    tira = Tira(tramo_id=tramo.id, codigo="R1", orden=0)
    db_session.add(tira)
    await db_session.flush()

    ubicaciones = [
        Ubicacion(tira_id=tira.id, nivel=1, codigo="A1-T1-R1-N1", activo=True),
        Ubicacion(tira_id=tira.id, nivel=2, codigo="A1-T1-R1-N2", activo=True),
        Ubicacion(tira_id=tira.id, nivel=3, codigo="A1-T1-R1-N3", activo=False),
    ]
    db_session.add_all(ubicaciones)
    await db_session.commit()
    return patio, tira, ubicaciones


@pytest.mark.anyio
async def test_obtener_mapa_cuenta_niveles_totales_activos_y_ocupados(db_session):
    patio, _tira, ubicaciones = await _crear_layout(db_session, "A")
    db_session.add(
        Contenedor(
            numero_contenedor="CAIU1112223",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.CUARENTA,
            patio_id=patio.id,
            ubicacion_id=ubicaciones[0].id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=28000,
        )
    )
    await db_session.commit()

    mapa = await obtener_mapa(db_session, patio.id)

    assert len(mapa.carriles) == 1
    tira_out = mapa.carriles[0].tramos[0].tiras[0]
    assert tira_out.niveles_totales == 3
    assert tira_out.niveles_activos == 2
    assert tira_out.niveles_ocupados == 1
    assert mapa.resumen.ubicaciones_activas == 2
    assert mapa.resumen.ocupadas == 1
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `cd backend && pytest tests/test_mapa_patio.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.mapa_patio'`

- [ ] **Step 4: Escribir el servicio**

Crear `backend/app/services/mapa_patio.py`:

```python
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contenedor import Contenedor
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
from app.schemas.mapa import (
    CarrilMapaOut,
    MapaPatioOut,
    ResumenMapaOut,
    TiraMapaOut,
    TramoMapaOut,
)


async def obtener_mapa(db: AsyncSession, patio_id: uuid.UUID) -> MapaPatioOut:
    """Ocupacion del patio agregada por tira.

    Una sola consulta. El mapa nunca carga las ubicaciones una por una: en un patio
    mediano son unas 7,200 filas contra unas 1,440 tiras.
    """
    patio_result = await db.execute(select(Patio).where(Patio.id == patio_id))
    patio = patio_result.scalar_one()

    filas = await db.execute(
        select(
            Carril.id.label("carril_id"),
            Carril.codigo.label("carril_codigo"),
            Carril.orden.label("carril_orden"),
            Carril.tipo_teorico.label("carril_tipo"),
            Tramo.id.label("tramo_id"),
            Tramo.codigo.label("tramo_codigo"),
            Tramo.orden.label("tramo_orden"),
            Tira.id.label("tira_id"),
            Tira.codigo.label("tira_codigo"),
            Tira.orden.label("tira_orden"),
            func.count(Ubicacion.id).label("niveles_totales"),
            func.count(Ubicacion.id)
            .filter(Ubicacion.activo.is_(True))
            .label("niveles_activos"),
            func.count(Contenedor.id).label("niveles_ocupados"),
        )
        .select_from(Carril)
        .join(Tramo, Tramo.carril_id == Carril.id)
        .join(Tira, Tira.tramo_id == Tramo.id)
        .outerjoin(Ubicacion, Ubicacion.tira_id == Tira.id)
        .outerjoin(Contenedor, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Carril.patio_id == patio_id)
        .group_by(
            Carril.id,
            Carril.codigo,
            Carril.orden,
            Carril.tipo_teorico,
            Tramo.id,
            Tramo.codigo,
            Tramo.orden,
            Tira.id,
            Tira.codigo,
            Tira.orden,
        )
        .order_by(Carril.orden, Tramo.orden, Tira.orden)
    )

    carriles: list[CarrilMapaOut] = []
    ubicaciones_activas = 0
    ocupadas = 0

    for fila in filas:
        if not carriles or carriles[-1].id != fila.carril_id:
            carriles.append(
                CarrilMapaOut(
                    id=fila.carril_id,
                    codigo=fila.carril_codigo,
                    orden=fila.carril_orden,
                    tipo_teorico=fila.carril_tipo,
                    tramos=[],
                )
            )
        carril = carriles[-1]

        if not carril.tramos or carril.tramos[-1].id != fila.tramo_id:
            carril.tramos.append(
                TramoMapaOut(
                    id=fila.tramo_id,
                    codigo=fila.tramo_codigo,
                    orden=fila.tramo_orden,
                    tiras=[],
                )
            )
        tramo = carril.tramos[-1]

        tramo.tiras.append(
            TiraMapaOut(
                id=fila.tira_id,
                codigo=fila.tira_codigo,
                orden=fila.tira_orden,
                niveles_totales=fila.niveles_totales,
                niveles_activos=fila.niveles_activos,
                niveles_ocupados=fila.niveles_ocupados,
            )
        )
        ubicaciones_activas += fila.niveles_activos
        ocupadas += fila.niveles_ocupados

    return MapaPatioOut(
        patio_id=patio.id,
        ubicacion_entrada_id=patio.ubicacion_entrada_id,
        resumen=ResumenMapaOut(ubicaciones_activas=ubicaciones_activas, ocupadas=ocupadas),
        carriles=carriles,
    )
```

- [ ] **Step 5: Correr el test del servicio**

Run: `cd backend && pytest tests/test_mapa_patio.py -v`
Expected: PASS

- [ ] **Step 6: Escribir el test del endpoint**

Agregar a `backend/tests/test_mapa_patio.py`:

```python
@pytest.mark.anyio
async def test_endpoint_mapa_devuelve_la_jerarquia(client, db_session):
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    patio, _tira, _ubicaciones = await _crear_layout(db_session, "B")
    token = _token(RolUsuario.OPERADOR, [str(patio.id)])

    response = await client.get(
        f"/api/patios/{patio.id}/mapa", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["carriles"][0]["codigo"] == "A1"
    assert cuerpo["carriles"][0]["tramos"][0]["tiras"][0]["niveles_totales"] == 3
    assert cuerpo["ubicacion_entrada_id"] is None


@pytest.mark.anyio
async def test_endpoint_mapa_rechaza_al_cliente(client, db_session):
    await _crear_usuario(db_session, RolUsuario.CLIENTE)
    patio, _tira, _ubicaciones = await _crear_layout(db_session, "C")
    token = _token(RolUsuario.CLIENTE, [str(patio.id)])

    response = await client.get(
        f"/api/patios/{patio.id}/mapa", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_endpoint_mapa_404_si_el_patio_no_existe(client, db_session):
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)
    inexistente = uuid.uuid4()

    response = await client.get(
        f"/api/patios/{inexistente}/mapa", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
```

- [ ] **Step 7: Correr los tests y verificar que fallan**

Run: `cd backend && pytest tests/test_mapa_patio.py -v`
Expected: los tres tests nuevos fallan con 404 de ruta no encontrada

- [ ] **Step 8: Escribir el endpoint**

En `backend/app/api/routes/patios.py`, agregar a los imports:

```python
from app.schemas.mapa import MapaPatioOut
from app.services.mapa_patio import obtener_mapa
```

Y agregar al final del archivo:

```python
_ROLES_MAPA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/{patio_id}/mapa", response_model=MapaPatioOut)
async def mapa_patio(
    patio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_MAPA)),
) -> MapaPatioOut:
    existe = await db.execute(select(Patio.id).where(Patio.id == patio_id))
    if existe.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patio no encontrado")
    return await obtener_mapa(db, patio_id)
```

Agregar `import uuid` al inicio de `backend/app/api/routes/patios.py` si no está.

- [ ] **Step 9: Correr los tests**

Run: `cd backend && pytest tests/test_mapa_patio.py tests/test_patios_api.py -v`
Expected: PASS

- [ ] **Step 10: Cubrir la RLS**

El spec exige que el mapa respete el aislamiento por patio. Antes de escribir el test, leer
`backend/app/alembic/versions/0006_rls_policies.py` y
`backend/app/alembic/versions/0010_rls_fail_closed.py` y anotar cuáles de las tablas
`carriles`, `tramos`, `tiras`, `ubicaciones` y `contenedores` tienen política de fila.

Luego escribir el test según lo que se encontró:

- Si `contenedores` tiene política por patio pero las tablas de geometría no, entonces un
  operador sin el patio asignado ve la estructura con `niveles_ocupados` en cero. Escribir
  un test que afirme exactamente eso, y agregar un comentario en el test explicando que la
  estructura del patio no es dato confidencial pero la ocupación sí.
- Si las tablas de geometría también tienen política, escribir un test que afirme que
  `carriles` regresa vacío para un operador sin el patio asignado.

En los dos casos el token se construye con `_token(RolUsuario.OPERADOR, [])`, es decir sin
patios asignados, y se compara contra el mismo layout que crea `_crear_layout`.

Run: `cd backend && pytest tests/test_mapa_patio.py -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add backend/app/services/mapa_patio.py backend/app/schemas/mapa.py backend/app/api/routes/patios.py backend/tests/test_mapa_patio.py
git commit -m "feat: endpoint de ocupacion agregada del patio"
```

---

### Task 3: Detalle de tira

**Files:**
- Create: `backend/app/api/routes/tiras.py`
- Modify: `backend/app/services/mapa_patio.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_mapa_patio.py`

**Interfaces:**
- Consumes: `DetalleTiraOut`, `NivelTiraOut` y `ContenedorEnNivelOut` de `app/schemas/mapa.py`, definidos en la Task 2.
- Produces:
  - `async def obtener_detalle_tira(db: AsyncSession, tira_id: uuid.UUID) -> DetalleTiraOut | None`
  - `GET /api/tiras/{tira_id}` con cuerpo `DetalleTiraOut`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `backend/tests/test_mapa_patio.py`:

```python
@pytest.mark.anyio
async def test_detalle_tira_devuelve_niveles_con_y_sin_contenedor(client, db_session):
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    patio, tira, ubicaciones = await _crear_layout(db_session, "D")
    db_session.add(
        Contenedor(
            numero_contenedor="MSCU1234567",
            tipo=TipoContenedor.LLENO,
            tamano=TamanoContenedor.VEINTE,
            patio_id=patio.id,
            ubicacion_id=ubicaciones[0].id,
            estado=EstadoContenedor.UBICADO,
            peso_kg=2400,
        )
    )
    await db_session.commit()
    token = _token(RolUsuario.OPERADOR, [str(patio.id)])

    response = await client.get(
        f"/api/tiras/{tira.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["codigo"] == "A1-T1-R1"
    assert len(cuerpo["niveles"]) == 3
    assert cuerpo["niveles"][0]["nivel"] == 1
    assert cuerpo["niveles"][0]["contenedor"]["numero_contenedor"] == "MSCU1234567"
    assert cuerpo["niveles"][1]["contenedor"] is None
    assert cuerpo["niveles"][2]["activo"] is False


@pytest.mark.anyio
async def test_detalle_tira_404_si_no_existe(client, db_session):
    await _crear_usuario(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)

    response = await client.get(
        f"/api/tiras/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd backend && pytest tests/test_mapa_patio.py -k detalle_tira -v`
Expected: FAIL, la ruta `/api/tiras/{id}` no existe todavía

- [ ] **Step 3: Escribir el servicio**

Agregar a `backend/app/services/mapa_patio.py`, en los imports:

```python
from app.schemas.mapa import ContenedorEnNivelOut, DetalleTiraOut, NivelTiraOut
```

Y al final del archivo:

```python
async def obtener_detalle_tira(db: AsyncSession, tira_id: uuid.UUID) -> DetalleTiraOut | None:
    """Los niveles de una tira con el contenedor de cada uno.

    El codigo que devuelve es el compuesto carril-tramo-tira, porque ese es el que el
    operador ve en el patio; el `codigo` de la tabla `tiras` solo distingue dentro del tramo.
    """
    encabezado = await db.execute(
        select(Carril.codigo, Tramo.codigo, Tira.codigo)
        .select_from(Tira)
        .join(Tramo, Tira.tramo_id == Tramo.id)
        .join(Carril, Tramo.carril_id == Carril.id)
        .where(Tira.id == tira_id)
    )
    fila_encabezado = encabezado.one_or_none()
    if fila_encabezado is None:
        return None
    carril_codigo, tramo_codigo, tira_codigo = fila_encabezado

    filas = await db.execute(
        select(Ubicacion, Contenedor)
        .outerjoin(Contenedor, Contenedor.ubicacion_id == Ubicacion.id)
        .where(Ubicacion.tira_id == tira_id)
        .order_by(Ubicacion.nivel)
    )

    niveles: list[NivelTiraOut] = []
    for ubicacion, contenedor in filas:
        niveles.append(
            NivelTiraOut(
                nivel=ubicacion.nivel,
                ubicacion_id=ubicacion.id,
                codigo=ubicacion.codigo,
                activo=ubicacion.activo,
                capacidad_peso_kg=ubicacion.capacidad_peso_kg,
                contenedor=(
                    None
                    if contenedor is None
                    else ContenedorEnNivelOut(
                        id=contenedor.id,
                        numero_contenedor=contenedor.numero_contenedor,
                        tipo=contenedor.tipo,
                        tamano=contenedor.tamano,
                        peso_kg=contenedor.peso_kg,
                        estado=contenedor.estado,
                    )
                ),
            )
        )

    return DetalleTiraOut(
        tira_id=tira_id,
        codigo=f"{carril_codigo}-{tramo_codigo}-{tira_codigo}",
        niveles=niveles,
    )
```

- [ ] **Step 4: Escribir el router**

Crear `backend/app/api/routes/tiras.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.db import get_db
from app.models.enums import RolUsuario
from app.schemas.mapa import DetalleTiraOut
from app.services.mapa_patio import obtener_detalle_tira

router = APIRouter()

_ROLES = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.get("/{tira_id}", response_model=DetalleTiraOut)
async def detalle_tira(
    tira_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES)),
) -> DetalleTiraOut:
    detalle = await obtener_detalle_tira(db, tira_id)
    if detalle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tira no encontrada")
    return detalle
```

- [ ] **Step 5: Montar el router**

En `backend/app/main.py`, cambiar la línea de import de rutas por:

```python
from app.api.routes import (
    auth,
    clientes,
    contenedores,
    movimientos,
    patios,
    tiras,
    ubicaciones,
    usuarios,
)
```

Y agregar después de la línea de `ubicaciones.router`:

```python
app.include_router(tiras.router, prefix="/api/tiras", tags=["tiras"])
```

- [ ] **Step 6: Correr los tests**

Run: `cd backend && pytest tests/test_mapa_patio.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/tiras.py backend/app/services/mapa_patio.py backend/app/main.py backend/tests/test_mapa_patio.py
git commit -m "feat: endpoint de detalle de tira con sus niveles"
```

---

### Task 4: Filtro de contenedores sin ubicación

**Files:**
- Modify: `backend/app/api/routes/contenedores.py:32-60`
- Test: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Consumes: nada de tareas previas.
- Produces: el query param `sin_ubicacion: bool | None` en `GET /api/contenedores`.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `backend/tests/test_contenedores_api.py`. Reusar los helpers que el archivo ya define para crear usuario y token; si sus nombres difieren de los de aquí, usar los del archivo.

```python
@pytest.mark.anyio
async def test_listar_contenedores_filtra_los_que_no_tienen_ubicacion(client, db_session):
    """El panel de pendientes del mapa necesita solo los contenedores sin ubicar."""
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)
    patio = Patio(nombre="Patio Filtro", codigo="PF")
    db_session.add(patio)
    await db_session.flush()

    carril = Carril(patio_id=patio.id, codigo="A9", orden=0)
    db_session.add(carril)
    await db_session.flush()
    tramo = Tramo(carril_id=carril.id, codigo="T9", orden=0)
    db_session.add(tramo)
    await db_session.flush()
    tira = Tira(tramo_id=tramo.id, codigo="R9", orden=0)
    db_session.add(tira)
    await db_session.flush()
    ubicacion = Ubicacion(tira_id=tira.id, nivel=1, codigo="A9-T9-R9-N1", activo=True)
    db_session.add(ubicacion)
    await db_session.flush()

    db_session.add_all(
        [
            Contenedor(
                numero_contenedor="AAAU0000001",
                tipo=TipoContenedor.LLENO,
                tamano=TamanoContenedor.CUARENTA,
                patio_id=patio.id,
                ubicacion_id=None,
                estado=EstadoContenedor.INGRESADO,
                peso_kg=1000,
            ),
            Contenedor(
                numero_contenedor="AAAU0000002",
                tipo=TipoContenedor.LLENO,
                tamano=TamanoContenedor.CUARENTA,
                patio_id=patio.id,
                ubicacion_id=ubicacion.id,
                estado=EstadoContenedor.UBICADO,
                peso_kg=1000,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(
        f"/api/contenedores?patio_id={patio.id}&sin_ubicacion=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    numeros = [c["numero_contenedor"] for c in response.json()]
    assert numeros == ["AAAU0000001"]
```

Agregar los imports que falten al inicio del archivo de test:

```python
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && pytest tests/test_contenedores_api.py::test_listar_contenedores_filtra_los_que_no_tienen_ubicacion -v`
Expected: FAIL, la respuesta trae los dos contenedores porque el filtro se ignora

- [ ] **Step 3: Agregar el filtro**

En `backend/app/api/routes/contenedores.py`, en la firma de `listar_contenedores`, agregar el parámetro después de `cliente_id`:

```python
    sin_ubicacion: bool | None = Query(default=None),
```

Y dentro del cuerpo, justo después del bloque `if estado is not None:`, agregar:

```python
    if sin_ubicacion:
        query = query.where(Contenedor.ubicacion_id.is_(None))
```

- [ ] **Step 4: Correr los tests**

Run: `cd backend && pytest tests/test_contenedores_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/contenedores.py backend/tests/test_contenedores_api.py
git commit -m "feat: filtro sin_ubicacion en el listado de contenedores"
```

---

### Task 5: La sugerencia dice a qué tira pertenece

**Files:**
- Modify: `backend/app/services/ubicacion_algoritmo.py:26-31,142`
- Modify: `backend/app/schemas/ubicacion.py`
- Modify: `backend/app/api/routes/ubicaciones.py`
- Test: `backend/tests/test_ubicacion_algoritmo.py`

**Interfaces:**
- Consumes: nada de tareas previas.
- Produces: `CandidatoUbicacion` con los campos `ubicacion_id`, `codigo`, `costo`, `tira_id`, `nivel`, en ese orden posicional. `SugerenciaUbicacionResponse` con `tira_id: uuid.UUID` y `nivel: int` además de los tres campos que ya tenía.

**Por qué:** el mapa necesita resaltar la tira sugerida. Hoy la respuesta solo trae `ubicacion_id`, y el frontend tendría que recorrer todo el mapa buscándola.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `backend/tests/test_ubicacion_algoritmo.py`:

```python
@pytest.mark.anyio
async def test_la_sugerencia_incluye_tira_y_nivel(db_session):
    """El mapa resalta la tira sugerida, asi que el candidato debe decir cual es."""
    patio, ubicaciones = await _crear_patio_con_ubicaciones(db_session)
    contenedor = await _crear_contenedor(db_session, patio)
    referencia = ubicaciones[0]

    candidato = await sugerir_ubicacion(
        db_session,
        patio_id=patio.id,
        contenedor=contenedor,
        punto_referencia_ubicacion_id=referencia.id,
    )

    elegida = next(u for u in ubicaciones if u.id == candidato.ubicacion_id)
    assert candidato.tira_id == elegida.tira_id
    assert candidato.nivel == elegida.nivel
```

Los helpers `_crear_patio_con_ubicaciones` y `_crear_contenedor` deben tomarse de los que ya existen en `backend/tests/test_ubicacion_algoritmo.py`. Leer el archivo primero y usar los nombres reales; si el helper existente devuelve otra forma, adaptar el test a esa forma sin cambiar lo que afirma.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd backend && pytest tests/test_ubicacion_algoritmo.py::test_la_sugerencia_incluye_tira_y_nivel -v`
Expected: FAIL con `AttributeError: 'CandidatoUbicacion' object has no attribute 'tira_id'`

- [ ] **Step 3: Agregar los campos al dataclass**

En `backend/app/services/ubicacion_algoritmo.py`, reemplazar el bloque de `CandidatoUbicacion`:

```python
@dataclass(frozen=True)
class CandidatoUbicacion:
    ubicacion_id: uuid.UUID
    codigo: str
    costo: float
    tira_id: uuid.UUID
    nivel: int
```

Y en `sugerir_ubicacion`, reemplazar la línea que arma el candidato:

```python
        evaluados.append(
            CandidatoUbicacion(
                ubicacion.id, ubicacion.codigo, costo, ubicacion.tira_id, ubicacion.nivel
            )
        )
```

- [ ] **Step 4: Agregar los campos al schema**

En `backend/app/schemas/ubicacion.py`, reemplazar `SugerenciaUbicacionResponse`:

```python
class SugerenciaUbicacionResponse(BaseModel):
    ubicacion_id: uuid.UUID
    codigo: str
    costo: float
    tira_id: uuid.UUID
    nivel: int
```

- [ ] **Step 5: Devolver los campos en la ruta**

En `backend/app/api/routes/ubicaciones.py`, reemplazar el `return` final:

```python
    return SugerenciaUbicacionResponse(
        ubicacion_id=candidato.ubicacion_id,
        codigo=candidato.codigo,
        costo=candidato.costo,
        tira_id=candidato.tira_id,
        nivel=candidato.nivel,
    )
```

- [ ] **Step 6: Correr los tests**

Run: `cd backend && pytest tests/test_ubicacion_algoritmo.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ubicacion_algoritmo.py backend/app/schemas/ubicacion.py backend/app/api/routes/ubicaciones.py backend/tests/test_ubicacion_algoritmo.py
git commit -m "feat: la sugerencia de ubicacion incluye tira y nivel"
```

---

### Task 6: Seed del layout del patio

**Files:**
- Create: `backend/scripts/seed_patio_layout.py`

**Interfaces:**
- Consumes: `Patio.ubicacion_entrada_id` de la Task 1.
- Produces: un script de línea de comandos. No lo consume ninguna tarea posterior, pero sin él no hay datos para probar el mapa a mano.

**Nota:** este script no lleva test automatizado. Es una herramienta de operación, no código de producción, y la verificación es correrlo y contar filas.

- [ ] **Step 1: Escribir el script**

Crear `backend/scripts/seed_patio_layout.py`:

```python
"""Carga el layout de un patio: carriles, tramos, tiras y ubicaciones.

Es idempotente: si ya existe un carril con el codigo que va a generar, lo salta.

Ejemplo:
    python -m scripts.seed_patio_layout --patio-codigo PN \\
        --carriles 12 --tramos 10 --tiras 12 --niveles 5 --entrada A01-T01-R01-N1
"""
import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.ubicacion import Carril, Patio, Tira, Tramo, Ubicacion


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carga el layout de un patio")
    parser.add_argument("--patio-codigo", required=True)
    parser.add_argument("--carriles", type=int, required=True)
    parser.add_argument("--tramos", type=int, required=True)
    parser.add_argument("--tiras", type=int, required=True)
    parser.add_argument("--niveles", type=int, default=5, choices=range(1, 6))
    parser.add_argument(
        "--entrada",
        help="Codigo de la ubicacion que sirve de punto de entrada, por ejemplo A01-T01-R01-N1",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        patio_result = await db.execute(select(Patio).where(Patio.codigo == args.patio_codigo))
        patio = patio_result.scalar_one_or_none()
        if patio is None:
            print(f"No existe un patio con codigo {args.patio_codigo}.")
            return 1

        creados = 0
        saltados = 0

        for c in range(args.carriles):
            carril_codigo = f"A{c + 1:02d}"
            existente = await db.execute(
                select(Carril).where(
                    Carril.patio_id == patio.id, Carril.codigo == carril_codigo
                )
            )
            if existente.scalar_one_or_none() is not None:
                saltados += 1
                continue

            carril = Carril(patio_id=patio.id, codigo=carril_codigo, orden=c)
            db.add(carril)
            await db.flush()

            for t in range(args.tramos):
                tramo = Tramo(carril_id=carril.id, codigo=f"T{t + 1:02d}", orden=t)
                db.add(tramo)
                await db.flush()

                for r in range(args.tiras):
                    tira = Tira(tramo_id=tramo.id, codigo=f"R{r + 1:02d}", orden=r)
                    db.add(tira)
                    await db.flush()

                    for n in range(1, args.niveles + 1):
                        db.add(
                            Ubicacion(
                                tira_id=tira.id,
                                nivel=n,
                                codigo=f"{carril.codigo}-{tramo.codigo}-{tira.codigo}-N{n}",
                                activo=True,
                            )
                        )
                        creados += 1

        await db.commit()
        print(f"Ubicaciones creadas: {creados}. Carriles saltados por ya existir: {saltados}.")

        if args.entrada:
            entrada_result = await db.execute(
                select(Ubicacion).where(Ubicacion.codigo == args.entrada)
            )
            entrada = entrada_result.scalar_one_or_none()
            if entrada is None:
                print(f"No existe la ubicacion {args.entrada}. El punto de entrada no se fijo.")
                await engine.dispose()
                return 1
            patio.ubicacion_entrada_id = entrada.id
            await db.commit()
            print(f"Punto de entrada del patio fijado en {args.entrada}.")

    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Verificar el script a mano**

Con la base de datos de desarrollo arriba y un patio existente con código `PN`:

```bash
cd backend && python -m scripts.seed_patio_layout --patio-codigo PN --carriles 2 --tramos 2 --tiras 3 --niveles 5 --entrada A01-T01-R01-N1
```

Expected: `Ubicaciones creadas: 60. Carriles saltados por ya existir: 0.` seguido de `Punto de entrada del patio fijado en A01-T01-R01-N1.`

- [ ] **Step 3: Verificar que es idempotente**

Correr el mismo comando otra vez.
Expected: `Ubicaciones creadas: 0. Carriles saltados por ya existir: 2.`

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed_patio_layout.py
git commit -m "feat: script de seed para el layout de un patio"
```

---

### Task 7: Cliente de API del mapa

**Files:**
- Modify: `frontend/lib/api.ts`
- Test: `frontend/lib/api.test.ts`

**Interfaces:**
- Consumes: los endpoints de las Tasks 2, 3, 4 y 5.
- Produces:
  - `interface TiraMapa { id, codigo, orden, niveles_totales, niveles_activos, niveles_ocupados }`
  - `interface TramoMapa { id, codigo, orden, tiras: TiraMapa[] }`
  - `interface CarrilMapa { id, codigo, orden, tipo_teorico, tramos: TramoMapa[] }`
  - `interface MapaPatio { patio_id, ubicacion_entrada_id, resumen, carriles }`
  - `interface NivelTira` y `interface DetalleTira`
  - `obtenerMapaPatio(token: string, patioId: string): Promise<MapaPatio>`
  - `obtenerDetalleTira(token: string, tiraId: string): Promise<DetalleTira>`
  - `listarContenedores` acepta `sin_ubicacion?: boolean`
  - `crearMovimiento` acepta `score_sugerido?: number` y `score_elegido?: number`
  - `SugerenciaUbicacion` incluye `tira_id: string` y `nivel: number`

- [ ] **Step 1: Escribir el test que falla**

Agregar a `frontend/lib/api.test.ts`. Revisar primero cómo el archivo simula `fetch` y seguir ese mismo patrón; el bloque de abajo asume un `vi.stubGlobal("fetch", ...)`.

```typescript
describe("obtenerMapaPatio", () => {
  it("pide el mapa del patio con el token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        patio_id: "p1",
        ubicacion_entrada_id: "u1",
        resumen: { ubicaciones_activas: 10, ocupadas: 3 },
        carriles: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const mapa = await obtenerMapaPatio("token", "p1");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/patios/p1/mapa",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer token" }) })
    );
    expect(mapa.resumen.ocupadas).toBe(3);
  });
});

describe("listarContenedores", () => {
  it("manda sin_ubicacion en la query cuando se pide", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await listarContenedores("token", { patio_id: "p1", sin_ubicacion: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/contenedores?patio_id=p1&sin_ubicacion=true",
      expect.anything()
    );
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run lib/api.test.ts`
Expected: FAIL, `obtenerMapaPatio` no está exportada

- [ ] **Step 3: Agregar los tipos y las funciones del mapa**

Agregar al final de `frontend/lib/api.ts`:

```typescript
export interface TiraMapa {
  id: string;
  codigo: string;
  orden: number;
  niveles_totales: number;
  niveles_activos: number;
  niveles_ocupados: number;
}

export interface TramoMapa {
  id: string;
  codigo: string;
  orden: number;
  tiras: TiraMapa[];
}

export interface CarrilMapa {
  id: string;
  codigo: string;
  orden: number;
  tipo_teorico: TipoContenedor | null;
  tramos: TramoMapa[];
}

export interface MapaPatio {
  patio_id: string;
  ubicacion_entrada_id: string | null;
  resumen: { ubicaciones_activas: number; ocupadas: number };
  carriles: CarrilMapa[];
}

export interface ContenedorEnNivel {
  id: string;
  numero_contenedor: string;
  tipo: TipoContenedor;
  tamano: TamanoContenedor;
  peso_kg: number;
  estado: EstadoContenedor;
}

export interface NivelTira {
  nivel: number;
  ubicacion_id: string;
  codigo: string;
  activo: boolean;
  capacidad_peso_kg: number;
  contenedor: ContenedorEnNivel | null;
}

export interface DetalleTira {
  tira_id: string;
  codigo: string;
  niveles: NivelTira[];
}

export async function obtenerMapaPatio(token: string, patioId: string): Promise<MapaPatio> {
  return request<MapaPatio>(`/api/patios/${patioId}/mapa`, { token });
}

export async function obtenerDetalleTira(token: string, tiraId: string): Promise<DetalleTira> {
  return request<DetalleTira>(`/api/tiras/${tiraId}`, { token });
}
```

- [ ] **Step 4: Extender listarContenedores, crearMovimiento y SugerenciaUbicacion**

En `frontend/lib/api.ts`, reemplazar la firma y el cuerpo de `listarContenedores`:

```typescript
export async function listarContenedores(
  token: string,
  filtros?: {
    estado?: EstadoContenedor;
    patio_id?: string;
    cliente_id?: string;
    sin_ubicacion?: boolean;
  }
): Promise<Contenedor[]> {
  const params = new URLSearchParams();
  if (filtros?.estado) params.set("estado", filtros.estado);
  if (filtros?.patio_id) params.set("patio_id", filtros.patio_id);
  if (filtros?.cliente_id) params.set("cliente_id", filtros.cliente_id);
  if (filtros?.sin_ubicacion) params.set("sin_ubicacion", "true");
  const query = params.toString();
  return request<Contenedor[]>(`/api/contenedores${query ? `?${query}` : ""}`, { token });
}
```

Reemplazar el tipo del payload de `crearMovimiento` por:

```typescript
export async function crearMovimiento(
  token: string,
  payload: {
    contenedor_id: string;
    ubicacion_destino_id: string;
    tipo: TipoMovimiento;
    override_manual?: boolean;
    motivo_override?: string;
    score_sugerido?: number;
    score_elegido?: number;
  }
): Promise<Movimiento> {
  return request<Movimiento>("/api/movimientos", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
```

Reemplazar `SugerenciaUbicacion` por:

```typescript
export interface SugerenciaUbicacion {
  ubicacion_id: string;
  codigo: string;
  costo: number;
  tira_id: string;
  nivel: number;
}
```

- [ ] **Step 5: Correr los tests y el compilador**

Run: `cd frontend && npx vitest run lib/api.test.ts && npx tsc --noEmit`
Expected: PASS y sin errores de tipos

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat: cliente de api del mapa del patio"
```

---

### Task 8: CeldaTira

**Files:**
- Create: `frontend/components/mapa/CeldaTira.tsx`
- Create: `frontend/components/mapa/CeldaTira.module.css`
- Test: `frontend/components/mapa/CeldaTira.test.tsx`

**Interfaces:**
- Consumes: `TiraMapa` de la Task 7.
- Produces:

```typescript
interface CeldaTiraProps {
  tira: TiraMapa;
  carrilCodigo: string;
  tramoCodigo: string;
  seleccionada: boolean;
  sugerida: boolean;
  tabIndex: number;
  onSeleccionar: (tiraId: string) => void;
}
export function CeldaTira(props: CeldaTiraProps): JSX.Element
```

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/components/mapa/CeldaTira.test.tsx`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CeldaTira } from "./CeldaTira";
import type { TiraMapa } from "@/lib/api";

function tira(overrides: Partial<TiraMapa> = {}): TiraMapa {
  return {
    id: "t1",
    codigo: "R1",
    orden: 0,
    niveles_totales: 5,
    niveles_activos: 5,
    niveles_ocupados: 3,
    ...overrides,
  };
}

describe("CeldaTira", () => {
  it("imprime la ocupacion como texto, no solo con color", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("3/5")).toBeVisible();
  });

  it("describe la celda completa para lectores de pantalla", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(
      screen.getByRole("gridcell", {
        name: "Carril A1, tramo T1, tira R1, 3 de 5 niveles ocupados",
      })
    ).toBeVisible();
  });

  it("anuncia que esta sugerida", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("Sugerido")).toBeVisible();
  });

  it("marca la seleccion con aria-selected", () => {
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada
        sugerida={false}
        tabIndex={0}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByRole("gridcell")).toHaveAttribute("aria-selected", "true");
  });

  it("avisa cuando la tira esta inactiva y no deja seleccionarla", async () => {
    const onSeleccionar = vi.fn();
    render(
      <CeldaTira
        tira={tira({ niveles_activos: 0, niveles_ocupados: 0 })}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={onSeleccionar}
      />
    );
    const celda = screen.getByRole("gridcell");
    expect(celda).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(celda);
    expect(onSeleccionar).not.toHaveBeenCalled();
  });

  it("llama onSeleccionar con el id de la tira", async () => {
    const onSeleccionar = vi.fn();
    render(
      <CeldaTira
        tira={tira()}
        carrilCodigo="A1"
        tramoCodigo="T1"
        seleccionada={false}
        sugerida={false}
        tabIndex={0}
        onSeleccionar={onSeleccionar}
      />
    );
    await userEvent.click(screen.getByRole("gridcell"));
    expect(onSeleccionar).toHaveBeenCalledWith("t1");
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run components/mapa/CeldaTira.test.tsx`
Expected: FAIL, el módulo `./CeldaTira` no existe

- [ ] **Step 3: Escribir el componente**

Crear `frontend/components/mapa/CeldaTira.tsx`:

```typescript
import type { TiraMapa } from "@/lib/api";
import styles from "./CeldaTira.module.css";

interface CeldaTiraProps {
  tira: TiraMapa;
  carrilCodigo: string;
  tramoCodigo: string;
  seleccionada: boolean;
  sugerida: boolean;
  /** Roving tabindex: solo la celda activa vale 0, el resto -1. */
  tabIndex: number;
  onSeleccionar: (tiraId: string) => void;
}

type Llenado = "vacia" | "parcial" | "llena" | "inactiva";

function calcularLlenado(tira: TiraMapa): Llenado {
  if (tira.niveles_activos === 0) return "inactiva";
  if (tira.niveles_ocupados === 0) return "vacia";
  if (tira.niveles_ocupados >= tira.niveles_activos) return "llena";
  return "parcial";
}

export function CeldaTira({
  tira,
  carrilCodigo,
  tramoCodigo,
  seleccionada,
  sugerida,
  tabIndex,
  onSeleccionar,
}: CeldaTiraProps) {
  const llenado = calcularLlenado(tira);
  const inactiva = llenado === "inactiva";

  // El color nunca es el unico indicador: la celda siempre imprime su conteo, y el
  // aria-label lo repite en palabras para quien no ve la cuadricula.
  const etiqueta = `Carril ${carrilCodigo}, tramo ${tramoCodigo}, tira ${tira.codigo}, ${tira.niveles_ocupados} de ${tira.niveles_totales} niveles ocupados`;

  return (
    <div
      role="gridcell"
      aria-label={etiqueta}
      aria-selected={seleccionada}
      aria-disabled={inactiva}
      tabIndex={tabIndex}
      className={[
        styles.celda,
        styles[llenado],
        seleccionada ? styles.seleccionada : "",
        sugerida ? styles.sugerida : "",
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={() => {
        if (!inactiva) onSeleccionar(tira.id);
      }}
      onKeyDown={(event) => {
        if (inactiva) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSeleccionar(tira.id);
        }
      }}
    >
      <span className={styles.conteo}>
        {tira.niveles_ocupados}/{tira.niveles_totales}
      </span>
      {sugerida && <span className={styles.sugerencia}>Sugerido</span>}
    </div>
  );
}
```

- [ ] **Step 4: Escribir los estilos**

Crear `frontend/components/mapa/CeldaTira.module.css`:

```css
.celda {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 44px;
  min-height: 44px;
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  line-height: var(--leading-tight);
  cursor: pointer;
  user-select: none;
}

.celda:focus-visible {
  outline: 2px solid var(--color-ring);
  outline-offset: 2px;
}

.vacia {
  background: var(--color-surface);
  color: var(--color-on-surface-muted);
}

.parcial {
  background: var(--color-warning-surface);
  color: var(--color-warning);
}

.llena {
  background: var(--color-danger-surface);
  color: var(--color-danger);
}

.inactiva {
  background: var(--color-surface-sunken);
  color: var(--color-on-surface-muted);
  cursor: not-allowed;
}

.seleccionada {
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-primary);
}

.sugerida {
  border-color: var(--color-success);
  box-shadow: inset 0 0 0 2px var(--color-success);
}

.conteo {
  font-weight: 600;
}

.sugerencia {
  font-size: 10px;
  color: var(--color-success);
}
```

- [ ] **Step 5: Correr los tests**

Run: `cd frontend && npx vitest run components/mapa/CeldaTira.test.tsx`
Expected: PASS, seis tests

- [ ] **Step 6: Commit**

```bash
git add frontend/components/mapa/CeldaTira.tsx frontend/components/mapa/CeldaTira.module.css frontend/components/mapa/CeldaTira.test.tsx
git commit -m "feat: celda de tira del mapa con ocupacion legible"
```

---

### Task 9: MapaPatio con leyenda, filtro y navegación por teclado

**Files:**
- Create: `frontend/components/mapa/MapaPatio.tsx`
- Create: `frontend/components/mapa/MapaPatio.module.css`
- Test: `frontend/components/mapa/MapaPatio.test.tsx`

**Interfaces:**
- Consumes: `CeldaTira` de la Task 8, `MapaPatio` (el tipo) de la Task 7.
- Produces:

```typescript
interface MapaPatioProps {
  mapa: MapaPatioData;          // el tipo MapaPatio de lib/api, renombrado en el import
  tiraSeleccionadaId: string | null;
  tiraSugeridaId: string | null;
  onSeleccionarTira: (tiraId: string) => void;
}
export function MapaPatio(props: MapaPatioProps): JSX.Element
```

La leyenda vive dentro de este componente. No merece archivo propio: son cuatro etiquetas y cambia siempre junto con los colores de la celda.

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/components/mapa/MapaPatio.test.tsx`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MapaPatio } from "./MapaPatio";
import type { MapaPatio as MapaPatioData } from "@/lib/api";

const MAPA: MapaPatioData = {
  patio_id: "p1",
  ubicacion_entrada_id: "u1",
  resumen: { ubicaciones_activas: 20, ocupadas: 7 },
  carriles: [
    {
      id: "c1",
      codigo: "A1",
      orden: 0,
      tipo_teorico: "lleno",
      tramos: [
        {
          id: "tr1",
          codigo: "T1",
          orden: 0,
          tiras: [
            { id: "t1", codigo: "R1", orden: 0, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 5 },
            { id: "t2", codigo: "R2", orden: 1, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 2 },
          ],
        },
      ],
    },
    {
      id: "c2",
      codigo: "A2",
      orden: 1,
      tipo_teorico: null,
      tramos: [
        {
          id: "tr2",
          codigo: "T1",
          orden: 0,
          tiras: [
            { id: "t3", codigo: "R1", orden: 0, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 0 },
          ],
        },
      ],
    },
  ],
};

describe("MapaPatio", () => {
  it("agrupa las tiras por carril y por tramo", () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    const carrilA1 = screen.getByRole("group", { name: /Carril A1/ });
    expect(within(carrilA1).getAllByRole("gridcell")).toHaveLength(2);
  });

  it("muestra el resumen de ocupacion del patio", () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    expect(screen.getByText("7 de 20 ubicaciones ocupadas")).toBeVisible();
  });

  it("filtra a un solo carril", async () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    await userEvent.selectOptions(screen.getByLabelText("Filtrar por carril"), "c2");
    expect(screen.queryByRole("group", { name: /Carril A1/ })).not.toBeInTheDocument();
    expect(screen.getByRole("group", { name: /Carril A2/ })).toBeVisible();
  });

  it("expone un solo tab stop y mueve el foco con las flechas", async () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId={null}
        onSeleccionarTira={vi.fn()}
      />
    );
    const celdas = screen.getAllByRole("gridcell");
    expect(celdas.filter((c) => c.getAttribute("tabindex") === "0")).toHaveLength(1);

    await userEvent.tab();
    expect(celdas[0]).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(celdas[1]).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(celdas[0]).toHaveFocus();
  });

  it("marca la tira sugerida", () => {
    render(
      <MapaPatio
        mapa={MAPA}
        tiraSeleccionadaId={null}
        tiraSugeridaId="t2"
        onSeleccionarTira={vi.fn()}
      />
    );
    expect(screen.getByText("Sugerido")).toBeVisible();
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run components/mapa/MapaPatio.test.tsx`
Expected: FAIL, el módulo `./MapaPatio` no existe

- [ ] **Step 3: Escribir el componente**

Crear `frontend/components/mapa/MapaPatio.tsx`:

```typescript
"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { MapaPatio as MapaPatioData } from "@/lib/api";
import { CeldaTira } from "./CeldaTira";
import styles from "./MapaPatio.module.css";

interface MapaPatioProps {
  mapa: MapaPatioData;
  tiraSeleccionadaId: string | null;
  tiraSugeridaId: string | null;
  onSeleccionarTira: (tiraId: string) => void;
}

export function MapaPatio({
  mapa,
  tiraSeleccionadaId,
  tiraSugeridaId,
  onSeleccionarTira,
}: MapaPatioProps) {
  const filtroId = useId();
  const [carrilFiltrado, setCarrilFiltrado] = useState("");
  const [indiceActivo, setIndiceActivo] = useState(0);
  const contenedorRef = useRef<HTMLDivElement>(null);

  const carriles = useMemo(
    () => (carrilFiltrado ? mapa.carriles.filter((c) => c.id === carrilFiltrado) : mapa.carriles),
    [mapa.carriles, carrilFiltrado]
  );

  // Orden de recorrido con teclado: el mismo en el que se dibujan las celdas.
  const idsEnOrden = useMemo(
    () => carriles.flatMap((c) => c.tramos.flatMap((t) => t.tiras.map((tira) => tira.id))),
    [carriles]
  );

  useEffect(() => {
    setIndiceActivo(0);
  }, [carrilFiltrado]);

  function moverFoco(siguiente: number) {
    const acotado = Math.max(0, Math.min(siguiente, idsEnOrden.length - 1));
    setIndiceActivo(acotado);
    const celdas = contenedorRef.current?.querySelectorAll<HTMLElement>('[role="gridcell"]');
    celdas?.[acotado]?.focus();
  }

  return (
    <section className={styles.contenedor}>
      <div className={styles.barra}>
        <p className={styles.resumen}>
          {mapa.resumen.ocupadas} de {mapa.resumen.ubicaciones_activas} ubicaciones ocupadas
        </p>
        <div className={styles.filtro}>
          <label htmlFor={filtroId}>Filtrar por carril</label>
          <select
            id={filtroId}
            value={carrilFiltrado}
            onChange={(event) => setCarrilFiltrado(event.target.value)}
          >
            <option value="">Todos los carriles</option>
            {mapa.carriles.map((carril) => (
              <option key={carril.id} value={carril.id}>
                {carril.codigo}
              </option>
            ))}
          </select>
        </div>
      </div>

      <ul className={styles.leyenda}>
        <li>
          <span className={`${styles.muestra} ${styles.vacia}`} /> Vacía
        </li>
        <li>
          <span className={`${styles.muestra} ${styles.parcial}`} /> Parcial
        </li>
        <li>
          <span className={`${styles.muestra} ${styles.llena}`} /> Llena
        </li>
        <li>
          <span className={`${styles.muestra} ${styles.inactiva}`} /> Inactiva
        </li>
      </ul>

      <div
        ref={contenedorRef}
        role="grid"
        aria-label="Mapa del patio"
        className={styles.mapa}
        onKeyDown={(event) => {
          // Roving tabindex: la cuadricula es un solo tab stop y las flechas mueven el foco.
          // Con 1,440 celdas, un tab stop por celda dejaria la pantalla inutilizable.
          if (event.key === "ArrowRight") {
            event.preventDefault();
            moverFoco(indiceActivo + 1);
          } else if (event.key === "ArrowLeft") {
            event.preventDefault();
            moverFoco(indiceActivo - 1);
          } else if (event.key === "Home") {
            event.preventDefault();
            moverFoco(0);
          } else if (event.key === "End") {
            event.preventDefault();
            moverFoco(idsEnOrden.length - 1);
          }
        }}
      >
        {carriles.map((carril) => (
          <div
            key={carril.id}
            role="group"
            aria-label={`Carril ${carril.codigo}`}
            className={styles.carril}
          >
            <h3 className={styles.carrilTitulo}>
              Carril {carril.codigo}
              {carril.tipo_teorico && (
                <span className={styles.carrilTipo}> · {carril.tipo_teorico}</span>
              )}
            </h3>
            <div className={styles.tramos}>
              {carril.tramos.map((tramo) => (
                <div key={tramo.id} className={styles.tramo}>
                  <p className={styles.tramoTitulo}>{tramo.codigo}</p>
                  <div role="row" className={styles.tiras}>
                    {tramo.tiras.map((tira) => (
                      <CeldaTira
                        key={tira.id}
                        tira={tira}
                        carrilCodigo={carril.codigo}
                        tramoCodigo={tramo.codigo}
                        seleccionada={tira.id === tiraSeleccionadaId}
                        sugerida={tira.id === tiraSugeridaId}
                        tabIndex={idsEnOrden[indiceActivo] === tira.id ? 0 : -1}
                        onSeleccionar={onSeleccionarTira}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Escribir los estilos**

Crear `frontend/components/mapa/MapaPatio.module.css`:

```css
.contenedor {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.barra {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  justify-content: space-between;
  gap: var(--space-4);
}

.resumen {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-on-surface-muted);
}

.filtro {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-sm);
}

.leyenda {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-xs);
  color: var(--color-on-surface-muted);
}

.leyenda li {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.muestra {
  width: 12px;
  height: 12px;
  border: 1px solid var(--color-border);
  border-radius: 3px;
}

.vacia {
  background: var(--color-surface);
}

.parcial {
  background: var(--color-warning-surface);
}

.llena {
  background: var(--color-danger-surface);
}

.inactiva {
  background: var(--color-surface-sunken);
}

.mapa {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  overflow-x: auto;
}

.carril {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.carrilTitulo {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
}

.carrilTipo {
  font-weight: 400;
  color: var(--color-on-surface-muted);
}

.tramos {
  display: flex;
  gap: var(--space-4);
}

.tramo {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.tramoTitulo {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-on-surface-muted);
}

.tiras {
  display: flex;
  gap: var(--space-1);
}
```

- [ ] **Step 5: Correr los tests**

Run: `cd frontend && npx vitest run components/mapa/MapaPatio.test.tsx`
Expected: PASS, cinco tests

- [ ] **Step 6: Commit**

```bash
git add frontend/components/mapa/MapaPatio.tsx frontend/components/mapa/MapaPatio.module.css frontend/components/mapa/MapaPatio.test.tsx
git commit -m "feat: cuadricula del mapa del patio con leyenda y navegacion por teclado"
```

---

### Task 10: DetalleTira

**Files:**
- Create: `frontend/components/mapa/DetalleTira.tsx`
- Create: `frontend/components/mapa/DetalleTira.module.css`
- Test: `frontend/components/mapa/DetalleTira.test.tsx`

**Interfaces:**
- Consumes: `DetalleTira` (el tipo) y `NivelTira` de la Task 7; `Badge` y `Button` de `@/components/ui`.
- Produces:

```typescript
interface DetalleTiraProps {
  detalle: DetalleTiraData;
  contenedorSeleccionado: string | null;  // id del contenedor pendiente, o null
  ubicacionSugeridaId: string | null;
  colocando: boolean;
  onColocar: (ubicacionId: string, motivo: string | null) => void;
}
export function DetalleTira(props: DetalleTiraProps): JSX.Element
```

Cuando el operador elige un nivel distinto al sugerido, el componente pide el motivo antes de llamar `onColocar`. Con el nivel sugerido, `motivo` va en `null`.

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/components/mapa/DetalleTira.test.tsx`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DetalleTira } from "./DetalleTira";
import type { DetalleTira as DetalleTiraData } from "@/lib/api";

const DETALLE: DetalleTiraData = {
  tira_id: "t1",
  codigo: "A1-T1-R1",
  niveles: [
    {
      nivel: 1,
      ubicacion_id: "u1",
      codigo: "A1-T1-R1-N1",
      activo: true,
      capacidad_peso_kg: 30000,
      contenedor: {
        id: "c1",
        numero_contenedor: "CAIU1112223",
        tipo: "lleno",
        tamano: "40",
        peso_kg: 28000,
        estado: "ubicado",
      },
    },
    {
      nivel: 2,
      ubicacion_id: "u2",
      codigo: "A1-T1-R1-N2",
      activo: true,
      capacidad_peso_kg: 30000,
      contenedor: null,
    },
  ],
};

describe("DetalleTira", () => {
  it("muestra el contenedor del nivel ocupado", () => {
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado={null}
        ubicacionSugeridaId={null}
        colocando={false}
        onColocar={vi.fn()}
      />
    );
    expect(screen.getByText("CAIU1112223")).toBeVisible();
  });

  it("marca el nivel libre como libre", () => {
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado={null}
        ubicacionSugeridaId={null}
        colocando={false}
        onColocar={vi.fn()}
      />
    );
    expect(screen.getByText("Libre")).toBeVisible();
  });

  it("no ofrece colocar si no hay contenedor seleccionado", () => {
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado={null}
        ubicacionSugeridaId={null}
        colocando={false}
        onColocar={vi.fn()}
      />
    );
    expect(screen.queryByRole("button", { name: /Colocar aquí/ })).not.toBeInTheDocument();
  });

  it("coloca sin motivo cuando el nivel es el sugerido", async () => {
    const onColocar = vi.fn();
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado="c9"
        ubicacionSugeridaId="u2"
        colocando={false}
        onColocar={onColocar}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Colocar aquí" }));
    expect(onColocar).toHaveBeenCalledWith("u2", null);
  });

  it("exige motivo cuando el nivel no es el sugerido", async () => {
    const onColocar = vi.fn();
    render(
      <DetalleTira
        detalle={DETALLE}
        contenedorSeleccionado="c9"
        ubicacionSugeridaId="u7"
        colocando={false}
        onColocar={onColocar}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "Colocar aquí" }));
    expect(onColocar).not.toHaveBeenCalled();

    await userEvent.type(
      screen.getByLabelText("Motivo para no usar la ubicación sugerida"),
      "Equipo en mantenimiento"
    );
    await userEvent.click(screen.getByRole("button", { name: "Confirmar colocación" }));
    expect(onColocar).toHaveBeenCalledWith("u2", "Equipo en mantenimiento");
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run components/mapa/DetalleTira.test.tsx`
Expected: FAIL, el módulo `./DetalleTira` no existe

- [ ] **Step 3: Escribir el componente**

Crear `frontend/components/mapa/DetalleTira.tsx`:

```typescript
"use client";

import { useState } from "react";
import type { DetalleTira as DetalleTiraData } from "@/lib/api";
import { Badge, Button, Field } from "@/components/ui";
import styles from "./DetalleTira.module.css";

interface DetalleTiraProps {
  detalle: DetalleTiraData;
  /** Id del contenedor pendiente elegido en el panel, o null si no hay ninguno. */
  contenedorSeleccionado: string | null;
  ubicacionSugeridaId: string | null;
  colocando: boolean;
  onColocar: (ubicacionId: string, motivo: string | null) => void;
}

export function DetalleTira({
  detalle,
  contenedorSeleccionado,
  ubicacionSugeridaId,
  colocando,
  onColocar,
}: DetalleTiraProps) {
  const [pidiendoMotivo, setPidiendoMotivo] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");

  function intentarColocar(ubicacionId: string) {
    if (ubicacionId === ubicacionSugeridaId) {
      onColocar(ubicacionId, null);
      return;
    }
    // Desviarse de la sugerencia queda registrado en el movimiento, y el motivo es lo que
    // hace util ese registro despues.
    setPidiendoMotivo(ubicacionId);
  }

  // Del nivel mas alto al mas bajo: asi se ve la pila en el patio.
  const nivelesDescendentes = [...detalle.niveles].sort((a, b) => b.nivel - a.nivel);

  return (
    <section className={styles.panel} aria-label={`Tira ${detalle.codigo}`}>
      <h2 className={styles.titulo}>{detalle.codigo}</h2>
      <ul className={styles.niveles}>
        {nivelesDescendentes.map((nivel) => (
          <li key={nivel.ubicacion_id} className={styles.nivel}>
            <span className={styles.etiquetaNivel}>N{nivel.nivel}</span>
            {nivel.contenedor ? (
              <span className={styles.datos}>
                <span className="mono">{nivel.contenedor.numero_contenedor}</span>
                <Badge tone="info">{nivel.contenedor.tamano} ft</Badge>
                <Badge tone={nivel.contenedor.tipo === "lleno" ? "warning" : "neutral"}>
                  {nivel.contenedor.tipo}
                </Badge>
                <span className={styles.peso}>{nivel.contenedor.peso_kg} kg</span>
              </span>
            ) : (
              <span className={styles.datos}>
                <Badge tone={nivel.activo ? "success" : "neutral"}>
                  {nivel.activo ? "Libre" : "Inactiva"}
                </Badge>
                {nivel.ubicacion_id === ubicacionSugeridaId && <Badge tone="success">Sugerido</Badge>}
                {nivel.activo && contenedorSeleccionado && (
                  <Button
                    variant="secondary"
                    disabled={colocando}
                    onClick={() => intentarColocar(nivel.ubicacion_id)}
                  >
                    Colocar aquí
                  </Button>
                )}
              </span>
            )}
          </li>
        ))}
      </ul>

      {pidiendoMotivo && (
        <div className={styles.motivo}>
          <Field
            id="motivo-override"
            label="Motivo para no usar la ubicación sugerida"
            value={motivo}
            onChange={setMotivo}
            required
          />
          <Button
            disabled={colocando || motivo.trim() === ""}
            onClick={() => {
              onColocar(pidiendoMotivo, motivo.trim());
              setPidiendoMotivo(null);
              setMotivo("");
            }}
          >
            Confirmar colocación
          </Button>
        </div>
      )}
    </section>
  );
}
```

Antes de escribir este archivo, leer `frontend/components/ui/Field.tsx` y `frontend/components/ui/Button.tsx` y ajustar las props de `Field` y `Button` a sus firmas reales. Este bloque asume `Field` con `id`, `label`, `value`, `onChange` y `required`, y `Button` con `variant`, `disabled` y `onClick`. Si difieren, manda la firma real del componente.

- [ ] **Step 4: Escribir los estilos**

Crear `frontend/components/mapa/DetalleTira.module.css`:

```css
.panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-1);
}

.titulo {
  margin: 0;
  font-size: var(--text-lg);
}

.niveles {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.nivel {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.etiquetaNivel {
  min-width: 32px;
  font-weight: 600;
  color: var(--color-on-surface-muted);
}

.datos {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.peso {
  color: var(--color-on-surface-muted);
}

.motivo {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}
```

- [ ] **Step 5: Correr los tests**

Run: `cd frontend && npx vitest run components/mapa/DetalleTira.test.tsx`
Expected: PASS, cinco tests

- [ ] **Step 6: Commit**

```bash
git add frontend/components/mapa/DetalleTira.tsx frontend/components/mapa/DetalleTira.module.css frontend/components/mapa/DetalleTira.test.tsx
git commit -m "feat: panel de detalle de tira con colocacion por nivel"
```

---

### Task 11: PanelPendientes

**Files:**
- Create: `frontend/components/mapa/PanelPendientes.tsx`
- Create: `frontend/components/mapa/PanelPendientes.module.css`
- Test: `frontend/components/mapa/PanelPendientes.test.tsx`

**Interfaces:**
- Consumes: `Contenedor` de `@/lib/api`; `EmptyState` y `SkeletonText` de `@/components/ui`.
- Produces:

```typescript
interface PanelPendientesProps {
  contenedores: Contenedor[];
  seleccionadoId: string | null;
  cargando: boolean;
  onSeleccionar: (contenedorId: string) => void;
}
export function PanelPendientes(props: PanelPendientesProps): JSX.Element
```

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/components/mapa/PanelPendientes.test.tsx`:

```typescript
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PanelPendientes } from "./PanelPendientes";
import type { Contenedor } from "@/lib/api";

const CONTENEDORES: Contenedor[] = [
  {
    id: "c1",
    numero_contenedor: "MSCU1234567",
    tipo: "lleno",
    tamano: "40",
    patio_id: "p1",
    estado: "ingresado",
    peso_kg: 18000,
  },
  {
    id: "c2",
    numero_contenedor: "TCLU7654321",
    tipo: "vacio",
    tamano: "20",
    patio_id: "p1",
    estado: "ingresado",
    peso_kg: 3900,
  },
];

describe("PanelPendientes", () => {
  it("lista los contenedores por ubicar", () => {
    render(
      <PanelPendientes
        contenedores={CONTENEDORES}
        seleccionadoId={null}
        cargando={false}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("MSCU1234567")).toBeVisible();
    expect(screen.getByText("TCLU7654321")).toBeVisible();
  });

  it("avisa cuando no hay pendientes", () => {
    render(
      <PanelPendientes
        contenedores={[]}
        seleccionadoId={null}
        cargando={false}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByText("No hay contenedores por ubicar")).toBeVisible();
  });

  it("marca el contenedor elegido con aria-pressed", () => {
    render(
      <PanelPendientes
        contenedores={CONTENEDORES}
        seleccionadoId="c2"
        cargando={false}
        onSeleccionar={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /TCLU7654321/ })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("avisa el id del contenedor al elegirlo", async () => {
    const onSeleccionar = vi.fn();
    render(
      <PanelPendientes
        contenedores={CONTENEDORES}
        seleccionadoId={null}
        cargando={false}
        onSeleccionar={onSeleccionar}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /MSCU1234567/ }));
    expect(onSeleccionar).toHaveBeenCalledWith("c1");
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run components/mapa/PanelPendientes.test.tsx`
Expected: FAIL, el módulo `./PanelPendientes` no existe

- [ ] **Step 3: Escribir el componente**

Crear `frontend/components/mapa/PanelPendientes.tsx`:

```typescript
"use client";

import type { Contenedor } from "@/lib/api";
import { EmptyState, SkeletonText } from "@/components/ui";
import styles from "./PanelPendientes.module.css";

interface PanelPendientesProps {
  contenedores: Contenedor[];
  seleccionadoId: string | null;
  cargando: boolean;
  onSeleccionar: (contenedorId: string) => void;
}

export function PanelPendientes({
  contenedores,
  seleccionadoId,
  cargando,
  onSeleccionar,
}: PanelPendientesProps) {
  return (
    <section className={styles.panel} aria-label="Contenedores por ubicar">
      <h2 className={styles.titulo}>Por ubicar</h2>
      {cargando && <SkeletonText lines={3} />}
      {!cargando && contenedores.length === 0 && (
        <EmptyState titulo="No hay contenedores por ubicar" />
      )}
      {!cargando && contenedores.length > 0 && (
        <ul className={styles.lista}>
          {contenedores.map((contenedor) => (
            <li key={contenedor.id}>
              <button
                type="button"
                aria-pressed={contenedor.id === seleccionadoId}
                className={styles.item}
                onClick={() => onSeleccionar(contenedor.id)}
              >
                <span className="mono">{contenedor.numero_contenedor}</span>
                <span className={styles.meta}>
                  {contenedor.tamano} ft · {contenedor.tipo} · {contenedor.peso_kg} kg
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

Antes de escribir este archivo, leer `frontend/components/ui/EmptyState.tsx` y `frontend/components/ui/Skeleton.tsx` y ajustar las props a sus firmas reales. Este bloque asume `EmptyState` con `titulo` y `SkeletonText` con `lines`.

- [ ] **Step 4: Escribir los estilos**

Crear `frontend/components/mapa/PanelPendientes.module.css`:

```css
.panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-1);
}

.titulo {
  margin: 0;
  font-size: var(--text-lg);
}

.lista {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-sm);
}

.item[aria-pressed="true"] {
  border-color: var(--color-primary);
  box-shadow: inset 0 0 0 2px var(--color-primary);
}

.item:focus-visible {
  outline: 2px solid var(--color-ring);
  outline-offset: 2px;
}

.meta {
  color: var(--color-on-surface-muted);
  font-size: var(--text-xs);
}
```

- [ ] **Step 5: Correr los tests**

Run: `cd frontend && npx vitest run components/mapa/PanelPendientes.test.tsx`
Expected: PASS, cuatro tests

- [ ] **Step 6: Commit**

```bash
git add frontend/components/mapa/PanelPendientes.tsx frontend/components/mapa/PanelPendientes.module.css frontend/components/mapa/PanelPendientes.test.tsx
git commit -m "feat: panel de contenedores por ubicar"
```

---

### Task 12: Página del mapa

**Files:**
- Create: `frontend/app/mapa/page.tsx`
- Create: `frontend/app/mapa/page.module.css`
- Create: `frontend/app/mapa/page.test.tsx`
- Modify: `frontend/lib/rutas.ts`
- Modify: `frontend/components/Sidebar.tsx`

**Interfaces:**
- Consumes: `MapaPatio` (Task 9), `DetalleTira` (Task 10), `PanelPendientes` (Task 11), y de `@/lib/api`: `obtenerMapaPatio`, `obtenerDetalleTira`, `listarContenedores`, `sugerirUbicacion`, `crearMovimiento`.
- Produces: la ruta `/mapa`.

- [ ] **Step 1: Escribir el test que falla**

Crear `frontend/app/mapa/page.test.tsx`:

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MapaPage from "./page";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  crearMovimiento,
  listPatios,
  listarContenedores,
  obtenerDetalleTira,
  obtenerMapaPatio,
  sugerirUbicacion,
} from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listPatios: vi.fn(),
    listarContenedores: vi.fn(),
    obtenerMapaPatio: vi.fn(),
    obtenerDetalleTira: vi.fn(),
    sugerirUbicacion: vi.fn(),
    crearMovimiento: vi.fn(),
  };
});

const PATIOS = [
  { id: "p1", nombre: "Patio Norte", codigo: "PN", activo: true, anticipacion_minima_horas: 24 },
];

const MAPA = {
  patio_id: "p1",
  ubicacion_entrada_id: "u0",
  resumen: { ubicaciones_activas: 5, ocupadas: 0 },
  carriles: [
    {
      id: "c1",
      codigo: "A1",
      orden: 0,
      tipo_teorico: null,
      tramos: [
        {
          id: "tr1",
          codigo: "T1",
          orden: 0,
          tiras: [
            { id: "t1", codigo: "R1", orden: 0, niveles_totales: 5, niveles_activos: 5, niveles_ocupados: 0 },
          ],
        },
      ],
    },
  ],
};

const DETALLE = {
  tira_id: "t1",
  codigo: "A1-T1-R1",
  niveles: [
    {
      nivel: 1,
      ubicacion_id: "u1",
      codigo: "A1-T1-R1-N1",
      activo: true,
      capacidad_peso_kg: 30000,
      contenedor: null,
    },
  ],
};

const PENDIENTES = [
  {
    id: "c9",
    numero_contenedor: "MSCU1234567",
    tipo: "lleno" as const,
    tamano: "40" as const,
    patio_id: "p1",
    estado: "ingresado" as const,
    peso_kg: 18000,
  },
];

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: "1", rol: "operador", patios: ["p1"] },
    token: "token",
    ready: true,
    setToken: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(listPatios).mockResolvedValue(PATIOS);
  vi.mocked(obtenerMapaPatio).mockResolvedValue(MAPA);
  vi.mocked(listarContenedores).mockResolvedValue(PENDIENTES);
  vi.mocked(obtenerDetalleTira).mockResolvedValue(DETALLE);
  vi.mocked(sugerirUbicacion).mockResolvedValue({
    ubicacion_id: "u1",
    codigo: "A1-T1-R1-N1",
    costo: 1.5,
    tira_id: "t1",
    nivel: 1,
  });
  vi.mocked(crearMovimiento).mockReset();
});

describe("MapaPage", () => {
  it("pide solo los contenedores sin ubicacion del patio", async () => {
    render(<MapaPage />);
    expect(await screen.findByText("MSCU1234567")).toBeVisible();
    expect(listarContenedores).toHaveBeenCalledWith("token", {
      patio_id: "p1",
      sin_ubicacion: true,
    });
  });

  it("coloca el contenedor en la ubicacion sugerida", async () => {
    vi.mocked(crearMovimiento).mockResolvedValue({
      id: "m1",
      contenedor_id: "c9",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
    });
    const user = userEvent.setup();
    render(<MapaPage />);

    await user.click(await screen.findByRole("button", { name: /MSCU1234567/ }));
    await user.click(await screen.findByRole("gridcell"));
    await user.click(await screen.findByRole("button", { name: "Colocar aquí" }));

    expect(crearMovimiento).toHaveBeenCalledWith("token", {
      contenedor_id: "c9",
      ubicacion_destino_id: "u1",
      tipo: "ingreso",
      override_manual: false,
      score_sugerido: 1.5,
      score_elegido: 1.5,
    });
  });

  it("muestra el conflicto 409 y recarga el mapa", async () => {
    vi.mocked(crearMovimiento).mockRejectedValue(new ApiError(409, "Ubicación ya ocupada"));
    const user = userEvent.setup();
    render(<MapaPage />);

    await user.click(await screen.findByRole("button", { name: /MSCU1234567/ }));
    await user.click(await screen.findByRole("gridcell"));
    await user.click(await screen.findByRole("button", { name: "Colocar aquí" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ubicación ya ocupada");
    expect(obtenerMapaPatio).toHaveBeenCalledTimes(2);
  });

  it("avisa cuando el patio no tiene punto de entrada y no pide sugerencia", async () => {
    vi.mocked(obtenerMapaPatio).mockResolvedValue({ ...MAPA, ubicacion_entrada_id: null });
    const user = userEvent.setup();
    render(<MapaPage />);

    await user.click(await screen.findByRole("button", { name: /MSCU1234567/ }));

    expect(sugerirUbicacion).not.toHaveBeenCalled();
    expect(
      await screen.findByText(
        "Este patio no tiene punto de entrada, así que no se puede sugerir una ubicación."
      )
    ).toBeVisible();
  });
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run app/mapa/page.test.tsx`
Expected: FAIL, el módulo `./page` no existe

- [ ] **Step 3: Escribir la página**

Crear `frontend/app/mapa/page.tsx`:

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { PatioSelect } from "@/components/PatioSelect";
import { MapaPatio } from "@/components/mapa/MapaPatio";
import { DetalleTira } from "@/components/mapa/DetalleTira";
import { PanelPendientes } from "@/components/mapa/PanelPendientes";
import { Alert, Button, PageHeader } from "@/components/ui";
import { ROLES_POR_RUTA } from "@/lib/rutas";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  crearMovimiento,
  listarContenedores,
  obtenerDetalleTira,
  obtenerMapaPatio,
  sugerirUbicacion,
  type Contenedor,
  type DetalleTira as DetalleTiraData,
  type MapaPatio as MapaPatioData,
  type SugerenciaUbicacion,
} from "@/lib/api";
import styles from "./page.module.css";

const SIN_ENTRADA =
  "Este patio no tiene punto de entrada, así que no se puede sugerir una ubicación.";

function MapaContent() {
  const { token } = useAuth();
  const [patioId, setPatioId] = useState("");
  const [mapa, setMapa] = useState<MapaPatioData | null>(null);
  const [pendientes, setPendientes] = useState<Contenedor[]>([]);
  const [cargandoPendientes, setCargandoPendientes] = useState(false);
  const [contenedorId, setContenedorId] = useState<string | null>(null);
  const [sugerencia, setSugerencia] = useState<SugerenciaUbicacion | null>(null);
  const [tiraId, setTiraId] = useState<string | null>(null);
  const [detalle, setDetalle] = useState<DetalleTiraData | null>(null);
  const [colocando, setColocando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargarMapa = useCallback(async () => {
    if (!token || !patioId) return;
    try {
      setMapa(await obtenerMapaPatio(token, patioId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el mapa");
    }
  }, [token, patioId]);

  const cargarPendientes = useCallback(async () => {
    if (!token || !patioId) return;
    setCargandoPendientes(true);
    try {
      setPendientes(await listarContenedores(token, { patio_id: patioId, sin_ubicacion: true }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los pendientes");
    } finally {
      setCargandoPendientes(false);
    }
  }, [token, patioId]);

  useEffect(() => {
    void cargarMapa();
    void cargarPendientes();
  }, [cargarMapa, cargarPendientes]);

  async function elegirContenedor(id: string) {
    setContenedorId(id);
    setError(null);
    setAviso(null);
    setSugerencia(null);
    if (!token || !mapa) return;
    if (!mapa.ubicacion_entrada_id) {
      setAviso(SIN_ENTRADA);
      return;
    }
    try {
      const propuesta = await sugerirUbicacion(token, {
        patio_id: mapa.patio_id,
        contenedor_id: id,
        punto_referencia_ubicacion_id: mapa.ubicacion_entrada_id,
      });
      setSugerencia(propuesta);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo calcular la sugerencia");
    }
  }

  async function elegirTira(id: string) {
    setTiraId(id);
    setError(null);
    if (!token) return;
    try {
      setDetalle(await obtenerDetalleTira(token, id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la tira");
    }
  }

  async function colocar(ubicacionId: string, motivo: string | null) {
    if (!token || !contenedorId) return;
    setColocando(true);
    setError(null);
    try {
      await crearMovimiento(token, {
        contenedor_id: contenedorId,
        ubicacion_destino_id: ubicacionId,
        tipo: "ingreso",
        override_manual: motivo !== null,
        ...(motivo !== null ? { motivo_override: motivo } : {}),
        ...(sugerencia ? { score_sugerido: sugerencia.costo, score_elegido: sugerencia.costo } : {}),
      });
      setContenedorId(null);
      setSugerencia(null);
      setDetalle(null);
      setTiraId(null);
      await Promise.all([cargarMapa(), cargarPendientes()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo colocar el contenedor");
      // El mapa que se estaba viendo ya no describe el patio: alguien mas gano la ubicacion.
      await cargarMapa();
    } finally {
      setColocando(false);
    }
  }

  return (
    <main className={styles.main}>
      <PageHeader
        titulo="Mapa del patio"
        acciones={
          <Button variant="secondary" onClick={() => void cargarMapa()}>
            Actualizar
          </Button>
        }
      />

      <div className={styles.selector}>
        <label htmlFor="patio_id">Patio</label>
        <PatioSelect id="patio_id" value={patioId} onChange={setPatioId} />
      </div>

      {error && <Alert tone="danger">{error}</Alert>}
      {aviso && <Alert tone="info">{aviso}</Alert>}

      <div className={styles.columnas}>
        <PanelPendientes
          contenedores={pendientes}
          seleccionadoId={contenedorId}
          cargando={cargandoPendientes}
          onSeleccionar={(id) => void elegirContenedor(id)}
        />

        <div className={styles.central}>
          {mapa && (
            <MapaPatio
              mapa={mapa}
              tiraSeleccionadaId={tiraId}
              tiraSugeridaId={sugerencia?.tira_id ?? null}
              onSeleccionarTira={(id) => void elegirTira(id)}
            />
          )}
          {detalle && (
            <DetalleTira
              detalle={detalle}
              contenedorSeleccionado={contenedorId}
              ubicacionSugeridaId={sugerencia?.ubicacion_id ?? null}
              colocando={colocando}
              onColocar={(ubicacionId, motivo) => void colocar(ubicacionId, motivo)}
            />
          )}
        </div>
      </div>
    </main>
  );
}

export default function MapaPage() {
  return (
    <AuthGuard roles={ROLES_POR_RUTA["/mapa"]}>
      <MapaContent />
    </AuthGuard>
  );
}
```

Antes de escribir este archivo, leer `frontend/components/ui/PageHeader.tsx` y `frontend/components/ui/Alert.tsx` y ajustar sus props a las firmas reales. Este bloque asume `PageHeader` con `titulo` y `acciones`, y `Alert` con `tone`.

- [ ] **Step 4: Escribir los estilos**

Crear `frontend/app/mapa/page.module.css`:

```css
.main {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-6);
}

.selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-width: 320px;
  font-size: var(--text-sm);
}

.columnas {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: var(--space-6);
  align-items: start;
}

.central {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

@media (max-width: 900px) {
  .columnas {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 5: Registrar la ruta y el enlace**

En `frontend/lib/rutas.ts`, agregar dentro de `ROLES_POR_RUTA`, justo antes de la entrada de `/contenedores`:

```typescript
  // `GET /api/patios/{id}/mapa` usa los mismos roles que _ROLES_ESCRITURA.
  "/mapa": [...ROLES_STAFF],
```

En `frontend/components/Sidebar.tsx`, dentro de la sección de operación de `SECCIONES`, agregar como primer enlace:

```typescript
      { href: "/mapa", texto: "Mapa del patio" },
```

- [ ] **Step 6: Correr la suite completa y el compilador**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: PASS, sin errores de tipos, y el conteo de suites sube respecto a las 33 previas

- [ ] **Step 7: Commit**

```bash
git add frontend/app/mapa frontend/lib/rutas.ts frontend/components/Sidebar.tsx
git commit -m "feat: pantalla del mapa del patio con colocacion de contenedores"
```

---

## Verificación final

- [ ] **Backend completo**

Run: `cd backend && pytest -q`
Expected: todos los tests pasan

- [ ] **Frontend completo**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: sin errores de tipos, todos los tests pasan

- [ ] **Verificación manual en el navegador**

1. Levantar la base y el backend con `docker compose up`.
2. Correr `cd backend && python -m scripts.seed_patio_layout --patio-codigo PN --carriles 4 --tramos 3 --tiras 6 --niveles 5 --entrada A01-T01-R01-N1`.
3. Crear un contenedor en ese patio y dejarlo sin ubicar.
4. Abrir `/mapa`, elegir el patio, elegir el contenedor pendiente y confirmar que el mapa resalta una tira como sugerida.
5. Colocar el contenedor y confirmar que la celda pasa de `0/5` a `1/5` y que el contenedor desaparece del panel de pendientes.
6. Recorrer el mapa solo con teclado: un Tab entra a la cuadrícula, las flechas mueven entre celdas, Enter abre el detalle.
