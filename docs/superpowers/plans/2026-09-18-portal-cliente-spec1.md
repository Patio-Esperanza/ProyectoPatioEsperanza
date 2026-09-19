# Portal Cliente — Spec 1: Fundación Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que el admin dé de alta empresas cliente (RFC), que el personal de esas empresas se autoregistre (validando RFC + código de verificación por correo vía SendGrid) y que, una vez activo, un usuario cliente cree una solicitud de entrada de contenedor con fecha estimada de retiro (sin elegir patio — se autoasigna).

**Architecture:** Backend FastAPI: nuevo router `clientes.py` (CRUD admin de empresas + registro/verificación pública), nuevo endpoint `POST /api/contenedores/solicitar` (cliente-only, reutiliza el modelo `Contenedor` existente), extensión retrocompatible del JWT para portar `cliente_id`, wrapper genérico de SendGrid. Frontend Next.js: páginas públicas de registro/verificación, página `/solicitar` (cliente-only) y `/clientes` (admin-only), mismo patrón ya establecido (`AuthGuard`, CSS Modules, `lib/api.ts` tipado).

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + Pydantic + `sendgrid==6.12.5` (backend), Next.js 14 + TypeScript + Vitest/RTL (frontend). Sin cambios de infraestructura Docker/DB.

## Global Constraints

- `fecha_estimada_retiro` se expone en la API mapeando a la columna real `contenedores.fecha_estimada_salida` (ya existe, migración 0005) — no se crea columna nueva para esto.
- La solicitud del cliente **es** un `Contenedor` naciendo en `estado=solicitud_ingreso` — no hay tabla `Solicitud` separada.
- El cliente **no** elige `patio_id` al solicitar — se asigna el primer `Patio` con `activo=true` ordenado por `codigo` ascendente.
- Registro de personal cliente: SIEMPRE se crea el `Usuario` (inactivo), incluso si el RFC no coincide con ningún `Cliente` activo — nunca se revela si un RFC existe o no vía el status code.
- Activación requiere AMBAS condiciones: código de 6 dígitos correcto (no expirado) Y RFC coincidente con un `Cliente` activo al momento del registro.
- `create_access_token` se extiende con un parámetro opcional al final (`cliente_id: str | None = None`) — ninguna llamada posicional existente se rompe.
- No se usa `pydantic.EmailStr` (el paquete `email-validator` no está en `requirements.txt`) — los campos de correo son `str` simples, igual que en `UsuarioCreate` (`app/schemas/usuario.py`).
- `SENDGRID_API_KEY` y `SENDGRID_FROM_EMAIL` ya están en `backend/.env` (no committeado). Los tests mockean el envío — nunca llaman a la API real de SendGrid.
- Sin verificación de RFC contra el SAT ni reenvío explícito de código — reintentar registro con el mismo email sobreescribe el código pendiente.

---

## File Structure

```
backend/
├── requirements.txt                          # MODIFICAR: agregar sendgrid==6.12.5
├── app/
│   ├── config.py                              # MODIFICAR: sendgrid_api_key, sendgrid_from_email
│   ├── main.py                                # MODIFICAR: registrar router clientes
│   ├── core/
│   │   ├── security.py                        # MODIFICAR: create_access_token con cliente_id opcional
│   │   └── email.py                            # NUEVO: enviar_correo()
│   ├── api/
│   │   ├── deps.py                             # MODIFICAR: CurrentUser.cliente_id
│   │   └── routes/
│   │       ├── auth.py                         # MODIFICAR: login pasa cliente_id al token
│   │       ├── clientes.py                     # NUEVO: CRUD admin + registro + verificar
│   │       └── contenedores.py                 # MODIFICAR: POST /solicitar
│   ├── models/
│   │   └── usuario.py                          # MODIFICAR: codigo_verificacion, codigo_verificacion_expira
│   ├── schemas/
│   │   ├── cliente.py                          # NUEVO
│   │   └── contenedor.py                       # MODIFICAR: ContenedorSolicitud, fecha_estimada_retiro
│   └── alembic/versions/
│       └── 0007_verificacion_correo.py         # NUEVO
├── .env.example                                # MODIFICAR: placeholders CORS/SendGrid
└── tests/
    ├── conftest.py                              # MODIFICAR: env defaults SendGrid
    ├── test_security.py                         # MODIFICAR: test cliente_id en token
    ├── test_auth.py                             # MODIFICAR: test login de cliente incluye cliente_id
    ├── test_clientes_api.py                     # NUEVO
    ├── test_registro_cliente_api.py             # NUEVO
    └── test_contenedores_api.py                 # MODIFICAR: tests de /solicitar

frontend/
├── lib/
│   ├── api.ts                                  # MODIFICAR: Cliente, registrarCliente, verificarCliente, solicitarContenedor
│   └── api.test.ts                             # MODIFICAR
├── components/
│   ├── NavBar.tsx                               # MODIFICAR: links "Solicitar entrada" (cliente), "Clientes" (admin)
│   └── NavBar.test.tsx                          # MODIFICAR
└── app/
    ├── registro/
    │   ├── page.tsx                             # NUEVO
    │   ├── page.module.css                      # NUEVO
    │   ├── page.test.tsx                        # NUEVO
    │   └── verificar/
    │       ├── page.tsx                         # NUEVO
    │       └── page.test.tsx                    # NUEVO
    ├── solicitar/
    │   ├── page.tsx                             # NUEVO
    │   ├── page.module.css                      # NUEVO
    │   └── page.test.tsx                        # NUEVO
    └── clientes/
        ├── page.tsx                             # NUEVO
        ├── page.module.css                      # NUEVO
        └── page.test.tsx                        # NUEVO
```

---

### Task 1: Backend — migración, modelo `Usuario`, config SendGrid

**Files:**
- Create: `backend/app/alembic/versions/0007_verificacion_correo.py`
- Modify: `backend/app/models/usuario.py`
- Modify: `backend/app/config.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Produces: columnas `usuarios.codigo_verificacion` (`str | None`), `usuarios.codigo_verificacion_expira` (`datetime | None`); `settings.sendgrid_api_key`, `settings.sendgrid_from_email`. Consumidas por Tasks 2 y 5.

- [ ] **Step 1: `backend/app/alembic/versions/0007_verificacion_correo.py`**

```python
"""codigo de verificacion de correo para usuarios cliente

Revision ID: 0007_verificacion_correo
Revises: 0006_rls_policies
Create Date: 2026-09-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_verificacion_correo"
down_revision = "0006_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("codigo_verificacion", sa.String(6), nullable=True))
    op.add_column(
        "usuarios", sa.Column("codigo_verificacion_expira", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("usuarios", "codigo_verificacion_expira")
    op.drop_column("usuarios", "codigo_verificacion")
```

- [ ] **Step 2: Aplicar la migración en la base de datos local**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. alembic upgrade head
```
Esperado: `Running upgrade 0006_rls_policies -> 0007_verificacion_correo, codigo de verificacion de correo para usuarios cliente`

- [ ] **Step 3: Agregar las columnas a `backend/app/models/usuario.py`**

Reemplazar el archivo completo:

```python
import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import RolUsuario


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True
    )
    tipo: Mapped[RolUsuario] = mapped_column(
        Enum(
            RolUsuario,
            name="rol_usuario",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    codigo_verificacion: Mapped[str | None] = mapped_column(String(6), nullable=True)
    codigo_verificacion_expira: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UsuarioPatio(Base):
    __tablename__ = "usuario_patio"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    patio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patios.id"), primary_key=True
    )
```

- [ ] **Step 4: Agregar los settings de SendGrid a `backend/app/config.py`**

Reemplazar el archivo completo:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    migrations_database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    sendgrid_api_key: str
    sendgrid_from_email: str

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
```

- [ ] **Step 5: Agregar `sendgrid` a `backend/requirements.txt`**

Agregar esta línea al final del archivo:

```
sendgrid==6.12.5
```

- [ ] **Step 6: Instalar la nueva dependencia**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
pip install -r requirements.txt
```
Esperado: instala `sendgrid`, `python-http-client`, `cryptography`, `cffi`, `pycparser`, `werkzeug` sin errores (`sendgrid` ya puede estar instalado de una verificación previa; `pip install -r` es idempotente).

- [ ] **Step 7: Agregar placeholders a `backend/.env.example`**

Reemplazar el archivo completo:

```
DATABASE_URL=postgresql+asyncpg://patio_app:patio_app@localhost:5433/patio_dev
MIGRATIONS_DATABASE_URL=postgresql+asyncpg://patio:patio@localhost:5433/patio_dev
JWT_SECRET=dev-secret-change-me
JWT_EXPIRES_MINUTES=60
CORS_ORIGINS=http://localhost:3000
SENDGRID_API_KEY=CAMBIAR_POR_API_KEY
SENDGRID_FROM_EMAIL=noreply@tudominio.com
```

- [ ] **Step 8: Agregar defaults de test a `backend/tests/conftest.py`**

Cambiar:

```python
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_EXPIRES_MINUTES", "60")
```

por:

```python
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_EXPIRES_MINUTES", "60")
os.environ.setdefault("SENDGRID_API_KEY", "test-sendgrid-key")
os.environ.setdefault("SENDGRID_FROM_EMAIL", "test@patio.mx")
```

- [ ] **Step 9: Correr la suite completa, confirmar que sigue pasando**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (41 tests — sin cambios de comportamiento todavía, solo infraestructura)

- [ ] **Step 10: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/alembic/versions/0007_verificacion_correo.py backend/app/models/usuario.py \
  backend/app/config.py backend/requirements.txt backend/.env.example backend/tests/conftest.py
git commit -m "feat: columnas de verificacion de correo + config SendGrid"
```

---

### Task 2: Backend — wrapper de envío de correo (SendGrid)

**Files:**
- Create: `backend/app/core/email.py`

**Interfaces:**
- Produces: `enviar_correo(destinatario: str, asunto: str, contenido_html: str) -> None`. Consumida por Task 5.
- Consumes: `settings.sendgrid_api_key`, `settings.sendgrid_from_email` (Task 1).

- [ ] **Step 1: `backend/app/core/email.py`**

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import settings


def enviar_correo(destinatario: str, asunto: str, contenido_html: str) -> None:
    mensaje = Mail(
        from_email=settings.sendgrid_from_email,
        to_emails=destinatario,
        subject=asunto,
        html_content=contenido_html,
    )
    cliente = SendGridAPIClient(settings.sendgrid_api_key)
    cliente.send(mensaje)
```

- [ ] **Step 2: Verificar que importa sin errores**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. python -c "from app.core.email import enviar_correo; print('ok')"
```
Esperado: `ok`

- [ ] **Step 3: Correr la suite completa, confirmar que sigue pasando**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (41 tests)

- [ ] **Step 4: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/core/email.py
git commit -m "feat: wrapper generico de envio de correo via SendGrid"
```

---

### Task 3: Backend — `cliente_id` opcional en el JWT

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/tests/test_security.py`
- Modify: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `create_access_token(usuario_id, rol, patios, expires_minutes, cliente_id=None)`; `CurrentUser.cliente_id: uuid.UUID | None`. Consumida por Task 6 (`require_roles(RolUsuario.CLIENTE)` en `/solicitar` necesita `user.cliente_id`).
- Consumes: nada nuevo — extiende infraestructura ya existente (`app/core/security.py`, `app/api/deps.py`, `app/api/routes/auth.py`).

- [ ] **Step 1: Escribir el test que falla — `test_security.py`**

Agregar a `backend/tests/test_security.py`, al final del archivo:

```python


def test_create_access_token_incluye_cliente_id_opcional():
    token = create_access_token("usr-1", "cliente", [], expires_minutes=60, cliente_id="cli-1")
    payload = decode_access_token(token)
    assert payload["cliente_id"] == "cli-1"


def test_create_access_token_sin_cliente_id_no_incluye_el_claim():
    token = create_access_token("usr-1", "operador", [], expires_minutes=60)
    payload = decode_access_token(token)
    assert "cliente_id" not in payload
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_security.py -v
```
Esperado: FAIL — `create_access_token() got an unexpected keyword argument 'cliente_id'`

- [ ] **Step 3: Modificar `backend/app/core/security.py`**

Reemplazar el archivo completo:

```python
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(
    usuario_id: str,
    rol: str,
    patios: list[str],
    expires_minutes: int,
    cliente_id: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": usuario_id,
        "rol": rol,
        "patios": patios,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if cliente_id is not None:
        payload["cliente_id"] = cliente_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_security.py -v
```
Esperado: PASS (6 tests)

- [ ] **Step 5: Escribir el test que falla — `test_auth.py`**

Agregar a `backend/tests/test_auth.py`, al final del archivo:

```python


@pytest.mark.anyio
async def test_login_de_cliente_incluye_cliente_id_en_token(client, db_session):
    from app.core.security import decode_access_token
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    cliente = Cliente(
        razon_social="Importadora Demo",
        rfc="AAA010101AA9",
        tipo=TipoCliente.IMPORTADOR_EXPORTADOR,
        activo=True,
    )
    db_session.add(cliente)
    await db_session.flush()

    usuario = Usuario(
        tipo=RolUsuario.CLIENTE,
        email="cliente@empresa.mx",
        password_hash=hash_password("clave123"),
        cliente_id=cliente.id,
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login", data={"username": "cliente@empresa.mx", "password": "clave123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = decode_access_token(token)
    assert payload["cliente_id"] == str(cliente.id)
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_auth.py -v
```
Esperado: FAIL — `KeyError: 'cliente_id'` (el login todavía no lo pasa al token)

- [ ] **Step 7: Modificar `backend/app/api/deps.py`**

Reemplazar el archivo completo:

```python
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db import get_db
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class CurrentUser:
    id: uuid.UUID
    rol: RolUsuario
    patios: list[uuid.UUID]
    cliente_id: uuid.UUID | None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    usuario_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")

    cliente_id_claim = payload.get("cliente_id")

    return CurrentUser(
        id=usuario.id,
        rol=RolUsuario(payload["rol"]),
        patios=[uuid.UUID(p) for p in payload.get("patios", [])],
        cliente_id=uuid.UUID(cliente_id_claim) if cliente_id_claim else None,
    )


def require_roles(*roles: RolUsuario):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No autorizado para este recurso")
        return user

    return dependency


async def get_scoped_db(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AsyncSession:
    await db.execute(text("SELECT set_config('app.rol', :rol, true)"), {"rol": user.rol.value})
    await db.execute(
        text("SELECT set_config('app.patios_asignados', :patios, true)"),
        {"patios": ",".join(str(p) for p in user.patios)},
    )
    return db
```

- [ ] **Step 8: Modificar `backend/app/api/routes/auth.py`**

Reemplazar el archivo completo:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.db import get_db
from app.models.usuario import Usuario, UsuarioPatio
from app.schemas.auth import TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    result = await db.execute(
        select(Usuario).where(Usuario.email == form.username, Usuario.activo.is_(True))
    )
    usuario = result.scalar_one_or_none()
    if (
        usuario is None
        or usuario.password_hash is None
        or not verify_password(form.password, usuario.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    patios_result = await db.execute(
        select(UsuarioPatio.patio_id).where(UsuarioPatio.usuario_id == usuario.id)
    )
    patios = [str(row[0]) for row in patios_result.all()]

    token = create_access_token(
        str(usuario.id),
        usuario.tipo.value,
        patios,
        settings.jwt_expires_minutes,
        cliente_id=str(usuario.cliente_id) if usuario.cliente_id else None,
    )
    return TokenResponse(access_token=token)
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_auth.py -v
```
Esperado: PASS (4 tests)

- [ ] **Step 10: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (44 tests: 41 + 2 nuevos en `test_security.py` + 1 nuevo en `test_auth.py`)

- [ ] **Step 11: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/core/security.py backend/app/api/deps.py backend/app/api/routes/auth.py \
  backend/tests/test_security.py backend/tests/test_auth.py
git commit -m "feat: cliente_id opcional en el JWT (retrocompatible)"
```

---

### Task 4: Backend — CRUD admin de `Cliente` (empresas)

**Files:**
- Create: `backend/app/schemas/cliente.py`
- Create: `backend/app/api/routes/clientes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_clientes_api.py`

**Interfaces:**
- Produces: `POST /api/clientes` (admin-only, 201), `GET /api/clientes` (admin-only, 200) → `ClienteOut { id, razon_social, rfc, tipo, activo }`. Consumida por Tasks 5, 6, 10 (frontend).
- Consumes: `require_roles`, `CurrentUser`, `registrar_auditoria`, `Cliente` (modelo ya existente).

- [ ] **Step 1: Escribir tests que fallan**

`backend/tests/test_clientes_api.py`:

```python
import uuid

import pytest

from app.core.security import create_access_token
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

_USUARIO_ID = "00000000-0000-0000-0000-000000000001"


def _token(rol: RolUsuario) -> str:
    return create_access_token(_USUARIO_ID, rol.value, [], 60)


async def _crear_usuario_autenticado(db_session, rol: RolUsuario) -> None:
    db_session.add(
        Usuario(
            id=uuid.UUID(_USUARIO_ID),
            tipo=rol,
            email=f"{rol.value}@patio.mx",
            password_hash="hash",
            activo=True,
        )
    )
    await db_session.commit()


@pytest.mark.anyio
async def test_admin_crea_cliente(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)

    response = await client.post(
        "/api/clientes",
        json={"razon_social": "Importadora Demo", "rfc": "AAA010101AA1", "tipo": "importador_exportador"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["rfc"] == "AAA010101AA1"
    assert body["activo"] is True


@pytest.mark.anyio
async def test_operador_no_puede_crear_cliente(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.OPERADOR)
    token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/clientes",
        json={"razon_social": "Importadora Demo", "rfc": "AAA010101AA2", "tipo": "importador_exportador"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_listar_clientes(client, db_session):
    await _crear_usuario_autenticado(db_session, RolUsuario.ADMIN)
    token = _token(RolUsuario.ADMIN)
    await client.post(
        "/api/clientes",
        json={"razon_social": "Transportes Demo", "rfc": "AAA010101AA3", "tipo": "transportista"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get("/api/clientes", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert any(c["rfc"] == "AAA010101AA3" for c in response.json())
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_clientes_api.py -v
```
Esperado: FAIL — `404 Not Found` (la ruta no existe todavía)

- [ ] **Step 3: `backend/app/schemas/cliente.py`**

```python
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TipoCliente


class ClienteCreate(BaseModel):
    razon_social: str
    rfc: str
    tipo: TipoCliente


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    razon_social: str
    rfc: str
    tipo: TipoCliente
    activo: bool


class ClienteRegistro(BaseModel):
    nombre: str
    email: str
    password: str = Field(min_length=8)
    rfc: str


class ClienteVerificar(BaseModel):
    email: str
    codigo: str
```

- [ ] **Step 4: `backend/app/api/routes/clientes.py`** (solo el CRUD admin en este paso — `registro`/`verificar` se agregan en Task 5)

```python
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.cliente import Cliente
from app.models.enums import RolUsuario
from app.schemas.cliente import ClienteCreate, ClienteOut

router = APIRouter()


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    payload: ClienteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Cliente:
    cliente = Cliente(razon_social=payload.razon_social, rfc=payload.rfc, tipo=payload.tipo, activo=True)
    db.add(cliente)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="clientes",
        entidad_id=str(cliente.id),
        valor_anterior=None,
        valor_nuevo={"razon_social": cliente.razon_social, "rfc": cliente.rfc},
        patio_id=None,
    )
    await db.commit()
    return cliente


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> list[Cliente]:
    result = await db.execute(select(Cliente))
    return list(result.scalars().all())
```

- [ ] **Step 5: Registrar el router en `backend/app/main.py`**

Cambiar:

```python
from app.api.routes import auth, contenedores, movimientos, patios, ubicaciones, usuarios
```

por:

```python
from app.api.routes import auth, clientes, contenedores, movimientos, patios, ubicaciones, usuarios
```

Y agregar, junto a los demás `include_router`:

```python
app.include_router(clientes.router, prefix="/api/clientes", tags=["clientes"])
```

- [ ] **Step 6: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_clientes_api.py -v
```
Esperado: PASS (3 tests)

- [ ] **Step 7: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (47 tests)

- [ ] **Step 8: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/cliente.py backend/app/api/routes/clientes.py backend/app/main.py \
  backend/tests/test_clientes_api.py
git commit -m "feat: CRUD admin de clientes (empresas)"
```

---

### Task 5: Backend — registro y verificación de personal del cliente

**Files:**
- Modify: `backend/app/api/routes/clientes.py`
- Test: `backend/tests/test_registro_cliente_api.py`

**Interfaces:**
- Produces: `POST /api/clientes/registro` (público, 201), `POST /api/clientes/verificar` (público, 200). Consumida por Task 8 (frontend).
- Consumes: `enviar_correo` (Task 2), `hash_password` (ya existente), `Usuario.codigo_verificacion`/`codigo_verificacion_expira` (Task 1).

- [ ] **Step 1: Escribir tests que fallan**

`backend/tests/test_registro_cliente_api.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.cliente import Cliente
from app.models.enums import TipoCliente
from app.models.usuario import Usuario


@pytest.fixture
def enviados(monkeypatch):
    capturados = []

    def _fake(destinatario, asunto, contenido_html):
        capturados.append((destinatario, asunto, contenido_html))

    monkeypatch.setattr("app.api.routes.clientes.enviar_correo", _fake)
    return capturados


async def _crear_cliente_activo(db_session, rfc: str) -> Cliente:
    cliente = Cliente(
        razon_social="Importadora Demo", rfc=rfc, tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    return cliente


@pytest.mark.anyio
async def test_registro_con_rfc_valido_crea_usuario_inactivo(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA1")

    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Juan", "email": "juan@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA1"},
    )

    assert response.status_code == 201
    assert len(enviados) == 1
    assert enviados[0][0] == "juan@empresa.mx"

    result = await db_session.execute(select(Usuario).where(Usuario.email == "juan@empresa.mx"))
    usuario = result.scalar_one()
    assert usuario.activo is False
    assert usuario.cliente_id is not None
    assert usuario.codigo_verificacion is not None


@pytest.mark.anyio
async def test_registro_con_rfc_invalido_tambien_crea_usuario_inactivo(client, db_session, enviados):
    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Juan", "email": "juan2@empresa.mx", "password": "clave1234", "rfc": "ZZZ999999ZZ9"},
    )

    assert response.status_code == 201
    assert len(enviados) == 1

    result = await db_session.execute(select(Usuario).where(Usuario.email == "juan2@empresa.mx"))
    usuario = result.scalar_one()
    assert usuario.activo is False
    assert usuario.cliente_id is None


@pytest.mark.anyio
async def test_verificar_con_codigo_correcto_y_rfc_valido_activa(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA2")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Ana", "email": "ana@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA2"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "ana@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion

    response = await client.post(
        "/api/clientes/verificar", json={"email": "ana@empresa.mx", "codigo": codigo}
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Cuenta activada"
    await db_session.refresh(usuario)
    assert usuario.activo is True
    assert usuario.codigo_verificacion is None


@pytest.mark.anyio
async def test_verificar_con_codigo_correcto_y_rfc_invalido_no_activa(client, db_session, enviados):
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Beto", "email": "beto@empresa.mx", "password": "clave1234", "rfc": "ZZZ999999ZZ8"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "beto@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion

    response = await client.post(
        "/api/clientes/verificar", json={"email": "beto@empresa.mx", "codigo": codigo}
    )

    assert response.status_code == 200
    assert "no está registrada" in response.json()["detail"]
    await db_session.refresh(usuario)
    assert usuario.activo is False


@pytest.mark.anyio
async def test_verificar_con_codigo_incorrecto_falla(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA3")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Cami", "email": "cami@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA3"},
    )

    response = await client.post(
        "/api/clientes/verificar", json={"email": "cami@empresa.mx", "codigo": "000000"}
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_verificar_con_codigo_expirado_falla(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA4")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Dani", "email": "dani@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA4"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "dani@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion
    usuario.codigo_verificacion_expira = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    response = await client.post(
        "/api/clientes/verificar", json={"email": "dani@empresa.mx", "codigo": codigo}
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_login_falla_mientras_no_esta_verificado(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA5")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Eli", "email": "eli@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA5"},
    )

    response = await client.post(
        "/api/auth/login", data={"username": "eli@empresa.mx", "password": "clave1234"}
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_reregistro_de_email_inactivo_sobreescribe_codigo(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA6")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Fer", "email": "fer@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA6"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "fer@empresa.mx"))
    primer_codigo = result.scalar_one().codigo_verificacion

    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Fer", "email": "fer@empresa.mx", "password": "clave5678", "rfc": "AAA010101AA6"},
    )

    assert response.status_code == 201
    assert len(enviados) == 2
    result = await db_session.execute(select(Usuario).where(Usuario.email == "fer@empresa.mx"))
    usuario = result.scalar_one()
    assert usuario.codigo_verificacion != primer_codigo


@pytest.mark.anyio
async def test_registro_con_email_ya_activo_devuelve_409(client, db_session, enviados):
    await _crear_cliente_activo(db_session, "AAA010101AA7")
    await client.post(
        "/api/clientes/registro",
        json={"nombre": "Gus", "email": "gus@empresa.mx", "password": "clave1234", "rfc": "AAA010101AA7"},
    )
    result = await db_session.execute(select(Usuario).where(Usuario.email == "gus@empresa.mx"))
    usuario = result.scalar_one()
    codigo = usuario.codigo_verificacion
    await client.post("/api/clientes/verificar", json={"email": "gus@empresa.mx", "codigo": codigo})

    response = await client.post(
        "/api/clientes/registro",
        json={"nombre": "Gus", "email": "gus@empresa.mx", "password": "otraClave1", "rfc": "AAA010101AA7"},
    )

    assert response.status_code == 409
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_registro_cliente_api.py -v
```
Esperado: FAIL — `404 Not Found` en todos (las rutas `registro`/`verificar` no existen todavía)

- [ ] **Step 3: Agregar `registro` y `verificar` a `backend/app/api/routes/clientes.py`**

Reemplazar el archivo completo:

```python
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.core.auditoria import registrar_auditoria
from app.core.email import enviar_correo
from app.core.security import hash_password
from app.db import get_db
from app.models.cliente import Cliente
from app.models.enums import RolUsuario
from app.models.usuario import Usuario
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteRegistro, ClienteVerificar

router = APIRouter()

_CODIGO_EXPIRA_MINUTOS = 15


def _generar_codigo() -> str:
    return "".join(random.choices(string.digits, k=6))


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    payload: ClienteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> Cliente:
    cliente = Cliente(razon_social=payload.razon_social, rfc=payload.rfc, tipo=payload.tipo, activo=True)
    db.add(cliente)
    await db.flush()

    await registrar_auditoria(
        db,
        usuario_id=user.id,
        rol=user.rol.value,
        ip=request.client.host if request.client else "desconocida",
        dispositivo=request.headers.get("user-agent", "desconocido"),
        accion="crear",
        entidad="clientes",
        entidad_id=str(cliente.id),
        valor_anterior=None,
        valor_nuevo={"razon_social": cliente.razon_social, "rfc": cliente.rfc},
        patio_id=None,
    )
    await db.commit()
    return cliente


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(RolUsuario.ADMIN)),
) -> list[Cliente]:
    result = await db.execute(select(Cliente))
    return list(result.scalars().all())


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registrar_cliente(
    payload: ClienteRegistro,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    existente_result = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    existente = existente_result.scalar_one_or_none()
    if existente is not None and existente.activo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ya registrado")

    cliente_result = await db.execute(
        select(Cliente).where(Cliente.rfc == payload.rfc, Cliente.activo.is_(True))
    )
    cliente = cliente_result.scalar_one_or_none()

    codigo = _generar_codigo()
    expira = datetime.now(timezone.utc) + timedelta(minutes=_CODIGO_EXPIRA_MINUTOS)

    if existente is not None:
        existente.nombre = payload.nombre
        existente.password_hash = hash_password(payload.password)
        existente.cliente_id = cliente.id if cliente else None
        existente.codigo_verificacion = codigo
        existente.codigo_verificacion_expira = expira
    else:
        db.add(
            Usuario(
                nombre=payload.nombre,
                email=payload.email,
                password_hash=hash_password(payload.password),
                tipo=RolUsuario.CLIENTE,
                cliente_id=cliente.id if cliente else None,
                activo=False,
                codigo_verificacion=codigo,
                codigo_verificacion_expira=expira,
            )
        )
    await db.commit()

    try:
        enviar_correo(
            payload.email,
            "Código de verificación — Patio Esperanza",
            f"<p>Tu código de verificación es <strong>{codigo}</strong>. "
            f"Expira en {_CODIGO_EXPIRA_MINUTOS} minutos.</p>",
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No se pudo enviar el correo de verificación, intenta de nuevo",
        ) from exc

    return {"detail": "Código de verificación enviado"}


@router.post("/verificar")
async def verificar_cliente(
    payload: ClienteVerificar,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(select(Usuario).where(Usuario.email == payload.email))
    usuario = result.scalar_one_or_none()
    if usuario is None or usuario.codigo_verificacion is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código incorrecto")

    if usuario.codigo_verificacion != payload.codigo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código incorrecto")

    if (
        usuario.codigo_verificacion_expira is None
        or usuario.codigo_verificacion_expira < datetime.now(timezone.utc)
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Código expirado, solicita uno nuevo")

    usuario.codigo_verificacion = None
    usuario.codigo_verificacion_expira = None

    if usuario.cliente_id is None:
        await db.commit()
        return {"detail": "Código correcto. Tu empresa (RFC) no está registrada, contacta al administrador"}

    usuario.activo = True
    await db.commit()
    return {"detail": "Cuenta activada"}
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_registro_cliente_api.py -v
```
Esperado: PASS (9 tests)

- [ ] **Step 5: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (56 tests)

- [ ] **Step 6: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/api/routes/clientes.py backend/tests/test_registro_cliente_api.py
git commit -m "feat: registro y verificacion por codigo de personal cliente"
```

---

### Task 6: Backend — `POST /api/contenedores/solicitar`

**Files:**
- Modify: `backend/app/schemas/contenedor.py`
- Modify: `backend/app/api/routes/contenedores.py`
- Modify: `backend/tests/test_contenedores_api.py`

**Interfaces:**
- Produces: `POST /api/contenedores/solicitar` (cliente-only, 201) → `ContenedorOut` (ahora incluye `fecha_estimada_retiro`). Consumida por Task 9 (frontend).
- Consumes: `CurrentUser.cliente_id` (Task 3), `Patio` (`app/models/ubicacion.py`, ya existente).

- [ ] **Step 1: Escribir tests que fallan**

Agregar a `backend/tests/test_contenedores_api.py`, al final del archivo:

```python


async def _crear_patio(db_session, nombre: str, codigo: str):
    from app.models.ubicacion import Patio

    patio = Patio(nombre=nombre, codigo=codigo, activo=True)
    db_session.add(patio)
    await db_session.commit()
    await db_session.refresh(patio)
    return patio


async def _crear_cliente(db_session, rfc: str):
    from app.models.cliente import Cliente
    from app.models.enums import TipoCliente

    cliente = Cliente(
        razon_social="Importadora Demo", rfc=rfc, tipo=TipoCliente.IMPORTADOR_EXPORTADOR, activo=True
    )
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    return cliente


@pytest.mark.anyio
async def test_cliente_solicita_contenedor_con_patio_autoasignado(client, db_session):
    patio = await _crear_patio(db_session, "Patio Norte", "PN4")
    cliente = await _crear_cliente(db_session, "AAA010101AA1")
    token = create_access_token(_USUARIO_ID, "cliente", [], 60, cliente_id=str(cliente.id))

    response = await client.post(
        "/api/contenedores/solicitar",
        json={
            "numero_contenedor": "CSQU3054383",
            "tipo": "lleno",
            "tamano": "40",
            "peso_kg": 18000,
            "fecha_estimada_retiro": "2026-10-01",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "solicitud_ingreso"
    assert body["patio_id"] == str(patio.id)
    assert body["fecha_estimada_retiro"].startswith("2026-10-01")


@pytest.mark.anyio
async def test_operador_no_puede_solicitar_contenedor(client, db_session):
    await _crear_usuario_autenticado(db_session)
    token = _token(RolUsuario.OPERADOR)

    response = await client.post(
        "/api/contenedores/solicitar",
        json={"numero_contenedor": "CSQU3054383", "tipo": "lleno", "tamano": "40", "peso_kg": 18000},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -v
```
Esperado: FAIL — `404 Not Found` en `test_cliente_solicita_contenedor_con_patio_autoasignado` y `test_operador_no_puede_solicitar_contenedor` (la ruta `/solicitar` no existe todavía)

- [ ] **Step 3: Modificar `backend/app/schemas/contenedor.py`**

Reemplazar el archivo completo:

```python
import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.iso6346 import validar_iso6346
from app.models.enums import EstadoContenedor, TamanoContenedor, TipoContenedor


def _numero_valido(value: str) -> str:
    value = value.strip().upper()
    if not validar_iso6346(value):
        raise ValueError("numero_contenedor no cumple el checksum ISO 6346")
    return value


class ContenedorCreate(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    peso_kg: int

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)


class ContenedorSolicitud(BaseModel):
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    peso_kg: int
    fecha_estimada_retiro: datetime.datetime | None = None

    @field_validator("numero_contenedor")
    @classmethod
    def numero_valido(cls, value: str) -> str:
        return _numero_valido(value)


class ContenedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero_contenedor: str
    tipo: TipoContenedor
    tamano: TamanoContenedor
    patio_id: uuid.UUID
    estado: EstadoContenedor
    peso_kg: int
    fecha_estimada_retiro: datetime.datetime | None = Field(
        default=None, validation_alias="fecha_estimada_salida"
    )
```

- [ ] **Step 4: Modificar `backend/app/api/routes/contenedores.py`**

Reemplazar el archivo completo:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_scoped_db, require_roles
from app.core.auditoria import registrar_auditoria
from app.db import get_db
from app.models.contenedor import Contenedor
from app.models.enums import EstadoContenedor, RolUsuario
from app.models.ubicacion import Patio
from app.schemas.contenedor import ContenedorCreate, ContenedorOut, ContenedorSolicitud

router = APIRouter()

_ROLES_ESCRITURA = (RolUsuario.OPERADOR, RolUsuario.SUPERVISOR, RolUsuario.ADMIN)


@router.post("", response_model=ContenedorOut, status_code=status.HTTP_201_CREATED)
async def crear_contenedor(
    payload: ContenedorCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> Contenedor:
    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=payload.patio_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=payload.peso_kg,
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
    return contenedor


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

    contenedor = Contenedor(
        numero_contenedor=payload.numero_contenedor,
        tipo=payload.tipo,
        tamano=payload.tamano,
        patio_id=patio.id,
        cliente_id=user.cliente_id,
        estado=EstadoContenedor.SOLICITUD_INGRESO,
        peso_kg=payload.peso_kg,
        fecha_estimada_salida=payload.fecha_estimada_retiro,
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
    return contenedor


@router.get("/{contenedor_id}", response_model=ContenedorOut)
async def obtener_contenedor(
    contenedor_id: str,
    db: AsyncSession = Depends(get_scoped_db),
    user: CurrentUser = Depends(get_current_user),
) -> Contenedor:
    result = await db.execute(select(Contenedor).where(Contenedor.id == contenedor_id))
    contenedor = result.scalar_one_or_none()
    if contenedor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
    return contenedor
```

- [ ] **Step 5: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/test_contenedores_api.py -v
```
Esperado: PASS (5 tests)

- [ ] **Step 6: Correr la suite completa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```
Esperado: PASS (58 tests)

- [ ] **Step 7: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add backend/app/schemas/contenedor.py backend/app/api/routes/contenedores.py \
  backend/tests/test_contenedores_api.py
git commit -m "feat: solicitud de entrada de contenedor por el cliente"
```

---

### Task 7: Frontend — cliente HTTP (`lib/api.ts`)

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/api.test.ts`

**Interfaces:**
- Produces: `TipoCliente`, `Cliente`, `listClientes(token)`, `createCliente(token, payload)`, `registrarCliente(payload)`, `verificarCliente(payload)`, `solicitarContenedor(token, payload)`. `Contenedor` gana `fecha_estimada_retiro?: string | null`. Consumidas por Tasks 8, 9, 10.
- Consumes: `request`, `ApiError`, `TipoContenedor`, `TamanoContenedor` (ya existentes).

- [ ] **Step 1: Escribir tests que fallan**

Agregar `listClientes, createCliente, type Cliente, registrarCliente, verificarCliente, solicitarContenedor` al import existente desde `"./api"` en `frontend/lib/api.test.ts`, y este bloque al final del archivo:

```ts
const CLIENTE: Cliente = {
  id: "cl1",
  razon_social: "Importadora Demo",
  rfc: "AAA010101AA1",
  tipo: "importador_exportador",
  activo: true,
};

describe("listClientes", () => {
  it("sends the bearer token and returns the list", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => [CLIENTE] });

    const result = await listClientes("token-123");

    expect(result).toEqual([CLIENTE]);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes");
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });
});

describe("createCliente", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => CLIENTE });

    const result = await createCliente("token-123", {
      razon_social: "Importadora Demo",
      rfc: "AAA010101AA1",
      tipo: "importador_exportador",
    });

    expect(result).toEqual(CLIENTE);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes");
    expect(options.method).toBe("POST");
  });
});

describe("registrarCliente", () => {
  it("posts the payload without a bearer token", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ detail: "Código de verificación enviado" }),
    });

    const result = await registrarCliente({
      nombre: "Juan",
      email: "juan@empresa.mx",
      password: "clave1234",
      rfc: "AAA010101AA1",
    });

    expect(result).toEqual({ detail: "Código de verificación enviado" });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes/registro");
    expect(options.headers.Authorization).toBeUndefined();
  });
});

describe("verificarCliente", () => {
  it("posts email and codigo", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ detail: "Cuenta activada" }),
    });

    const result = await verificarCliente({ email: "juan@empresa.mx", codigo: "123456" });

    expect(result).toEqual({ detail: "Cuenta activada" });
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/clientes/verificar");
  });
});

describe("solicitarContenedor", () => {
  it("posts the payload as JSON with the bearer token", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => CONTENEDOR });

    const result = await solicitarContenedor("token-123", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      peso_kg: 18000,
      fecha_estimada_retiro: "2026-10-01",
    });

    expect(result).toEqual(CONTENEDOR);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/contenedores/solicitar");
    expect(options.method).toBe("POST");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: FAIL — `listClientes`/`createCliente`/`Cliente`/`registrarCliente`/`verificarCliente`/`solicitarContenedor` no existen en `./api`.

- [ ] **Step 3: Agregar a `frontend/lib/api.ts`** (al final del archivo)

```ts
export type TipoCliente =
  | "agencia_aduanal"
  | "importador_exportador"
  | "transportista"
  | "socio_api";

export interface Cliente {
  id: string;
  razon_social: string;
  rfc: string;
  tipo: TipoCliente;
  activo: boolean;
}

export async function listClientes(token: string): Promise<Cliente[]> {
  return request<Cliente[]>("/api/clientes", { token });
}

export async function createCliente(
  token: string,
  payload: { razon_social: string; rfc: string; tipo: TipoCliente }
): Promise<Cliente> {
  return request<Cliente>("/api/clientes", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export async function registrarCliente(payload: {
  nombre: string;
  email: string;
  password: string;
  rfc: string;
}): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/clientes/registro", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verificarCliente(payload: {
  email: string;
  codigo: string;
}): Promise<{ detail: string }> {
  return request<{ detail: string }>("/api/clientes/verificar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function solicitarContenedor(
  token: string,
  payload: {
    numero_contenedor: string;
    tipo: TipoContenedor;
    tamano: TamanoContenedor;
    peso_kg: number;
    fecha_estimada_retiro?: string;
  }
): Promise<Contenedor> {
  return request<Contenedor>("/api/contenedores/solicitar", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
```

También agregar el campo nuevo a la interfaz `Contenedor` ya existente (buscar `export interface Contenedor {` y agregar la última línea antes del cierre `}`):

```ts
  fecha_estimada_retiro?: string | null;
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- lib/api.test.ts
```
Esperado: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat: cliente HTTP para clientes, registro y solicitud de entrada"
```

---

### Task 8: Frontend — páginas públicas `/registro` y `/registro/verificar`

**Files:**
- Create: `frontend/app/registro/page.tsx`
- Create: `frontend/app/registro/page.module.css`
- Test: `frontend/app/registro/page.test.tsx`
- Create: `frontend/app/registro/verificar/page.tsx`
- Test: `frontend/app/registro/verificar/page.test.tsx`

**Interfaces:**
- Consumes: `registrarCliente`, `verificarCliente`, `ApiError` (Task 7).

- [ ] **Step 1: Escribir test que falla — `/registro`**

`frontend/app/registro/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegistroPage from "./page";
import { registrarCliente, ApiError } from "@/lib/api";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, registrarCliente: vi.fn() };
});

beforeEach(() => {
  pushMock.mockClear();
  vi.mocked(registrarCliente).mockReset();
});

describe("RegistroPage", () => {
  it("registers and redirects to the verify page with the email", async () => {
    const user = userEvent.setup();
    vi.mocked(registrarCliente).mockResolvedValue({ detail: "Código de verificación enviado" });

    render(<RegistroPage />);

    await user.type(screen.getByLabelText("Nombre"), "Juan");
    await user.type(screen.getByLabelText("Correo"), "juan@empresa.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave1234");
    await user.type(screen.getByLabelText("RFC de tu empresa"), "AAA010101AA1");
    await user.click(screen.getByRole("button", { name: "Registrarme" }));

    expect(registrarCliente).toHaveBeenCalledWith({
      nombre: "Juan",
      email: "juan@empresa.mx",
      password: "clave1234",
      rfc: "AAA010101AA1",
    });
    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/registro/verificar?email=juan%40empresa.mx")
    );
  });

  it("shows the backend error message on failure", async () => {
    const user = userEvent.setup();
    vi.mocked(registrarCliente).mockRejectedValue(new ApiError(409, "Email ya registrado"));

    render(<RegistroPage />);

    await user.type(screen.getByLabelText("Nombre"), "Juan");
    await user.type(screen.getByLabelText("Correo"), "juan@empresa.mx");
    await user.type(screen.getByLabelText("Contraseña"), "clave1234");
    await user.type(screen.getByLabelText("RFC de tu empresa"), "AAA010101AA1");
    await user.click(screen.getByRole("button", { name: "Registrarme" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email ya registrado");
  });
});
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/registro/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 3: `frontend/app/registro/page.module.css`**

```css
.main {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  width: 340px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card h1 {
  color: var(--azul);
  font-size: 1.3rem;
  margin: 0 0 12px;
}

.card input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.9rem;
}

.card button {
  margin-top: 8px;
  background: var(--azul);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px;
  font-weight: 600;
}

.card button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: var(--danger);
  background: var(--danger-soft);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 0.85rem;
  margin: 0;
}

.ok {
  color: #2e7d46;
  background: #e4f2e8;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 0.85rem;
  margin: 0;
}
```

- [ ] **Step 4: `frontend/app/registro/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, registrarCliente } from "@/lib/api";
import styles from "./page.module.css";

export default function RegistroPage() {
  const router = useRouter();
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rfc, setRfc] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await registrarCliente({ nombre, email, password, rfc });
      router.push(`/registro/verificar?email=${encodeURIComponent(email)}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar el registro");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1>Registro de cliente</h1>
        <label htmlFor="nombre">Nombre</label>
        <input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <label htmlFor="email">Correo</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        <label htmlFor="rfc">RFC de tu empresa</label>
        <input id="rfc" value={rfc} onChange={(e) => setRfc(e.target.value)} required />
        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {submitting ? "Enviando..." : "Registrarme"}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 5: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/registro/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 6: Escribir test que falla — `/registro/verificar`**

`frontend/app/registro/verificar/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VerificarPage from "./page";
import { verificarCliente, ApiError } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("email=juan%40empresa.mx"),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, verificarCliente: vi.fn() };
});

beforeEach(() => {
  vi.mocked(verificarCliente).mockReset();
});

describe("VerificarPage", () => {
  it("prefills the email from the query string and shows the success message", async () => {
    const user = userEvent.setup();
    vi.mocked(verificarCliente).mockResolvedValue({ detail: "Cuenta activada" });

    render(<VerificarPage />);

    expect(screen.getByLabelText("Correo")).toHaveValue("juan@empresa.mx");
    await user.type(screen.getByLabelText("Código de 6 dígitos"), "123456");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(verificarCliente).toHaveBeenCalledWith({ email: "juan@empresa.mx", codigo: "123456" });
    expect(await screen.findByText("Cuenta activada")).toBeInTheDocument();
  });

  it("shows the backend error message on failure", async () => {
    const user = userEvent.setup();
    vi.mocked(verificarCliente).mockRejectedValue(new ApiError(422, "Código incorrecto"));

    render(<VerificarPage />);

    await user.type(screen.getByLabelText("Código de 6 dígitos"), "000000");
    await user.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Código incorrecto");
  });
});
```

- [ ] **Step 7: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/registro/verificar/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 8: `frontend/app/registro/verificar/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, verificarCliente } from "@/lib/api";
import styles from "../page.module.css";

export default function VerificarPage() {
  const searchParams = useSearchParams();
  const emailInicial = searchParams.get("email") ?? "";
  const [email, setEmail] = useState(emailInicial);
  const [codigo, setCodigo] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMensaje(null);
    setSubmitting(true);
    try {
      const { detail } = await verificarCliente({ email, codigo });
      setMensaje(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo verificar el código");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1>Verifica tu correo</h1>
        <label htmlFor="email">Correo</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="codigo">Código de 6 dígitos</label>
        <input
          id="codigo"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          required
          maxLength={6}
        />
        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
        {mensaje && <p className={styles.ok}>{mensaje}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Verificando..." : "Verificar"}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/registro/verificar/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 10: Correr toda la suite de frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS (todos los tests hasta este punto)

- [ ] **Step 11: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/registro
git commit -m "feat: paginas publicas de registro y verificacion de cliente"
```

---

### Task 9: Frontend — página `/solicitar` (cliente) + link en NavBar

**Files:**
- Create: `frontend/app/solicitar/page.tsx`
- Create: `frontend/app/solicitar/page.module.css`
- Test: `frontend/app/solicitar/page.test.tsx`
- Modify: `frontend/components/NavBar.tsx`
- Modify: `frontend/components/NavBar.test.tsx`

**Interfaces:**
- Consumes: `solicitarContenedor` (Task 7); `AuthGuard`, `useAuth`.

- [ ] **Step 1: Escribir test que falla — NavBar**

Agregar a `frontend/components/NavBar.test.tsx`, dentro del `describe("NavBar", ...)`:

```tsx
  it("shows the Solicitar entrada link only for cliente", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    const { rerender } = render(<NavBar />);
    expect(screen.queryByText("Solicitar entrada")).not.toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "cliente", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    rerender(<NavBar />);
    expect(screen.getByText("Solicitar entrada")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: FAIL — `screen.getByText("Solicitar entrada")` no encuentra nada.

- [ ] **Step 3: Modificar `frontend/components/NavBar.tsx`**

Cambiar:

```tsx
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
      </div>
```

por:

```tsx
        <Link href="/ubicaciones/sugerir">Sugerir ubicación</Link>
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
      </div>
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: PASS (4 tests)

- [ ] **Step 5: Escribir test que falla — página `/solicitar`**

`frontend/app/solicitar/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SolicitarPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { solicitarContenedor } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, solicitarContenedor: vi.fn() };
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
  vi.mocked(solicitarContenedor).mockReset();
});

describe("SolicitarPage", () => {
  it("shows a not-authorized message for non-cliente roles", () => {
    mockAuth("operador");

    render(<SolicitarPage />);

    expect(screen.getByRole("alert")).toHaveTextContent("No autorizado");
  });

  it("submits a solicitud with the form values", async () => {
    mockAuth("cliente");
    vi.mocked(solicitarContenedor).mockResolvedValue({
      id: "c1",
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      patio_id: "p1",
      estado: "solicitud_ingreso",
      peso_kg: 18000,
      fecha_estimada_retiro: "2026-10-01T00:00:00+00:00",
    });

    const user = userEvent.setup();
    render(<SolicitarPage />);

    await user.type(screen.getByLabelText("Número de contenedor"), "CSQU3054383");
    await user.type(screen.getByLabelText("Peso (kg)"), "18000");
    await user.click(screen.getByRole("button", { name: "Enviar solicitud" }));

    expect(solicitarContenedor).toHaveBeenCalledWith("token", {
      numero_contenedor: "CSQU3054383",
      tipo: "lleno",
      tamano: "40",
      peso_kg: 18000,
      fecha_estimada_retiro: undefined,
    });
    expect(await screen.findByText(/estado solicitud_ingreso/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/solicitar/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/solicitar/page.module.css`**

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

.form input,
.form select {
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

- [ ] **Step 8: `frontend/app/solicitar/page.tsx`**

```tsx
"use client";

import { useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  solicitarContenedor,
  type Contenedor,
  type TamanoContenedor,
  type TipoContenedor,
} from "@/lib/api";
import styles from "./page.module.css";

function SolicitarContent() {
  const { token, user } = useAuth();
  const [numero, setNumero] = useState("");
  const [tipo, setTipo] = useState<TipoContenedor>("lleno");
  const [tamano, setTamano] = useState<TamanoContenedor>("40");
  const [pesoKg, setPesoKg] = useState("");
  const [fechaEstimadaRetiro, setFechaEstimadaRetiro] = useState("");
  const [creado, setCreado] = useState<Contenedor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setCreado(null);
    try {
      const contenedor = await solicitarContenedor(token, {
        numero_contenedor: numero,
        tipo,
        tamano,
        peso_kg: Number(pesoKg),
        fecha_estimada_retiro: fechaEstimadaRetiro || undefined,
      });
      setCreado(contenedor);
      setNumero("");
      setPesoKg("");
      setFechaEstimadaRetiro("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar la solicitud");
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
      <h1>Solicitar entrada de contenedor</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {creado && (
        <p className={styles.ok}>
          Solicitud registrada: <span className="mono">{creado.numero_contenedor}</span> — estado{" "}
          {creado.estado}
        </p>
      )}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="numero">Número de contenedor</label>
        <input
          id="numero"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          required
          maxLength={11}
        />

        <label htmlFor="tipo">Tipo</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoContenedor)}>
          <option value="lleno">Lleno</option>
          <option value="vacio">Vacío</option>
        </select>

        <label htmlFor="tamano">Tamaño</label>
        <select
          id="tamano"
          value={tamano}
          onChange={(e) => setTamano(e.target.value as TamanoContenedor)}
        >
          <option value="20">20&apos;</option>
          <option value="40">40&apos;</option>
          <option value="45">45&apos;</option>
        </select>

        <label htmlFor="peso_kg">Peso (kg)</label>
        <input
          id="peso_kg"
          type="number"
          value={pesoKg}
          onChange={(e) => setPesoKg(e.target.value)}
          required
        />

        <label htmlFor="fecha_estimada_retiro">Fecha posible de retiro</label>
        <input
          id="fecha_estimada_retiro"
          type="date"
          value={fechaEstimadaRetiro}
          onChange={(e) => setFechaEstimadaRetiro(e.target.value)}
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Enviando..." : "Enviar solicitud"}
        </button>
      </form>
    </main>
  );
}

export default function SolicitarPage() {
  return (
    <AuthGuard>
      <SolicitarContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/solicitar/page.test.tsx
```
Esperado: PASS (2 tests)

- [ ] **Step 10: Correr toda la suite de frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS (todos los tests hasta este punto)

- [ ] **Step 11: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/solicitar frontend/components/NavBar.tsx frontend/components/NavBar.test.tsx
git commit -m "feat: pagina de solicitud de entrada (cliente) y link en NavBar"
```

---

### Task 10: Frontend — página `/clientes` (admin) + link en NavBar

**Files:**
- Create: `frontend/app/clientes/page.tsx`
- Create: `frontend/app/clientes/page.module.css`
- Test: `frontend/app/clientes/page.test.tsx`
- Modify: `frontend/components/NavBar.tsx`
- Modify: `frontend/components/NavBar.test.tsx`

**Interfaces:**
- Consumes: `listClientes`, `createCliente`, `type Cliente`, `type TipoCliente` (Task 7); `AuthGuard`, `useAuth`.

- [ ] **Step 1: Escribir test que falla — NavBar**

Agregar a `frontend/components/NavBar.test.tsx`, dentro del `describe("NavBar", ...)`:

```tsx
  it("shows the Clientes link only for admin", () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "operador", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    const { rerender } = render(<NavBar />);
    expect(screen.queryByText("Clientes")).not.toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({
      user: { id: "1", rol: "admin", patios: [] },
      token: "token",
      ready: true,
      setToken: vi.fn(),
      logout: vi.fn(),
    });
    rerender(<NavBar />);
    expect(screen.getByText("Clientes")).toBeInTheDocument();
  });
```

- [ ] **Step 2: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: FAIL — `screen.getByText("Clientes")` no encuentra nada.

- [ ] **Step 3: Modificar `frontend/components/NavBar.tsx`**

Cambiar:

```tsx
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
      </div>
```

por:

```tsx
        {user.rol === "admin" && <Link href="/usuarios">Usuarios</Link>}
        {user.rol === "admin" && <Link href="/clientes">Clientes</Link>}
        {user.rol === "cliente" && <Link href="/solicitar">Solicitar entrada</Link>}
      </div>
```

- [ ] **Step 4: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- components/NavBar.test.tsx
```
Esperado: PASS (5 tests)

- [ ] **Step 5: Escribir test que falla — página `/clientes`**

`frontend/app/clientes/page.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ClientesPage from "./page";
import { useAuth } from "@/lib/auth-context";
import { listClientes, createCliente } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/auth-context", () => ({ useAuth: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listClientes: vi.fn(), createCliente: vi.fn() };
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
  vi.mocked(listClientes).mockReset();
  vi.mocked(createCliente).mockReset();
});

describe("ClientesPage", () => {
  it("shows a not-authorized message for non-admin roles", async () => {
    mockAuth("operador");

    render(<ClientesPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No autorizado");
    expect(listClientes).not.toHaveBeenCalled();
  });

  it("lists the clientes returned by the backend for admin", async () => {
    mockAuth("admin");
    vi.mocked(listClientes).mockResolvedValue([
      { id: "cl1", razon_social: "Importadora Demo", rfc: "AAA010101AA1", tipo: "importador_exportador", activo: true },
    ]);

    render(<ClientesPage />);

    expect(await screen.findByText(/Importadora Demo/)).toBeInTheDocument();
  });

  it("lets an admin create a cliente and refreshes the list", async () => {
    mockAuth("admin");
    vi.mocked(listClientes)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        { id: "cl2", razon_social: "Transportes Demo", rfc: "AAA010101AA2", tipo: "transportista", activo: true },
      ]);
    vi.mocked(createCliente).mockResolvedValue({
      id: "cl2",
      razon_social: "Transportes Demo",
      rfc: "AAA010101AA2",
      tipo: "transportista",
      activo: true,
    });

    const user = userEvent.setup();
    render(<ClientesPage />);

    await screen.findByRole("button", { name: "Crear cliente" });
    await user.type(screen.getByLabelText("Razón social"), "Transportes Demo");
    await user.type(screen.getByLabelText("RFC"), "AAA010101AA2");
    await user.selectOptions(screen.getByLabelText("Tipo"), "transportista");
    await user.click(screen.getByRole("button", { name: "Crear cliente" }));

    expect(createCliente).toHaveBeenCalledWith("token", {
      razon_social: "Transportes Demo",
      rfc: "AAA010101AA2",
      tipo: "transportista",
    });
    expect(await screen.findByText(/Transportes Demo/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Correr, confirmar que falla**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/clientes/page.test.tsx
```
Esperado: FAIL — `Cannot find module './page'`

- [ ] **Step 7: `frontend/app/clientes/page.module.css`**

```css
.main {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
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

.form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}

.form input,
.form select {
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
```

- [ ] **Step 8: `frontend/app/clientes/page.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { useAuth } from "@/lib/auth-context";
import { ApiError, createCliente, listClientes, type Cliente, type TipoCliente } from "@/lib/api";
import styles from "./page.module.css";

const TIPOS: TipoCliente[] = [
  "agencia_aduanal",
  "importador_exportador",
  "transportista",
  "socio_api",
];

function ClientesContent() {
  const { token, user } = useAuth();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [razonSocial, setRazonSocial] = useState("");
  const [rfc, setRfc] = useState("");
  const [tipo, setTipo] = useState<TipoCliente>("importador_exportador");
  const [creating, setCreating] = useState(false);

  const cargarClientes = useCallback(async () => {
    if (!token || user?.rol !== "admin") return;
    setLoading(true);
    try {
      const data = await listClientes(token);
      setClientes(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los clientes");
    } finally {
      setLoading(false);
    }
  }, [token, user]);

  useEffect(() => {
    cargarClientes();
  }, [cargarClientes]);

  async function handleCrear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setCreating(true);
    setError(null);
    try {
      await createCliente(token, { razon_social: razonSocial, rfc, tipo });
      setRazonSocial("");
      setRfc("");
      await cargarClientes();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el cliente");
    } finally {
      setCreating(false);
    }
  }

  if (user?.rol !== "admin") {
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
      <h1>Clientes</h1>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <ul className={styles.list}>
          {clientes.map((c) => (
            <li key={c.id}>
              <span className="mono">{c.rfc}</span> — {c.razon_social} — {c.tipo}
            </li>
          ))}
        </ul>
      )}

      <form className={styles.form} onSubmit={handleCrear}>
        <h2>Nuevo cliente</h2>
        <label htmlFor="razon_social">Razón social</label>
        <input
          id="razon_social"
          value={razonSocial}
          onChange={(e) => setRazonSocial(e.target.value)}
          required
        />
        <label htmlFor="rfc">RFC</label>
        <input id="rfc" value={rfc} onChange={(e) => setRfc(e.target.value)} required />
        <label htmlFor="tipo">Tipo</label>
        <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoCliente)}>
          {TIPOS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button type="submit" disabled={creating}>
          {creating ? "Creando..." : "Crear cliente"}
        </button>
      </form>
    </main>
  );
}

export default function ClientesPage() {
  return (
    <AuthGuard>
      <ClientesContent />
    </AuthGuard>
  );
}
```

- [ ] **Step 9: Correr, confirmar que pasa**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test -- app/clientes/page.test.tsx
```
Esperado: PASS (3 tests)

- [ ] **Step 10: Correr toda la suite de frontend**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npm test
```
Esperado: PASS — todos los tests del proyecto.

- [ ] **Step 11: Correr `tsc --noEmit`**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza/frontend
npx tsc --noEmit
```
Esperado: sin salida (sin errores de tipos). Nota: `npm run build` puede fallar en este sandbox por el límite de conexiones concurrentes a fonts.gstatic.com (ver sesión previa) — no es indicativo de un error de código; verificar con `tsc --noEmit` y correr `npm run build` fuera del sandbox antes de desplegar.

- [ ] **Step 12: Commit**

```bash
cd /home/tony/Developer/ProyectoPatioEsperanza
git add frontend/app/clientes frontend/components/NavBar.tsx frontend/components/NavBar.test.tsx
git commit -m "feat: pagina de clientes (alta + listado, solo admin) y link en NavBar"
```

---

## Self-Review

**Cobertura del spec** (`docs/superpowers/specs/2026-09-18-portal-cliente-spec1-design.md`):
- Alta de empresas cliente (admin) → Task 4.
- Registro de personal + validación RFC + código de verificación por correo (SendGrid) → Tasks 1, 2, 5.
- Activación requiere código correcto Y RFC válido; RFC inválido dado dobre de manera indistinguible del válido en el registro (mismo 201 siempre) → Task 5.
- `cliente_id` disponible en el backend para el endpoint de solicitud, sin romper JWTs/tests existentes → Task 3.
- Solicitud de entrada = `Contenedor` en `estado=solicitud_ingreso`, patio autoasignado, `fecha_estimada_retiro` expuesta desde `fecha_estimada_salida` → Task 6.
- Frontend: registro público, verificación pública, solicitud (cliente-only), gestión de clientes (admin-only), NavBar condicional por rol → Tasks 8, 9, 10.
- Fuera de alcance (PIN, QR, rutina inteligente de patio, listado de "mis contenedores", reenvío explícito de código, rate limiting) → ninguna task lo implementa.

**Placeholder scan:** sin "TBD"/"similar a Task N"/pasos sin código — cada step tiene el archivo completo.

**Consistencia de tipos:** `Cliente`, `TipoCliente` coinciden campo a campo entre `ClienteOut` (backend, Task 4) y `lib/api.ts` (Task 7). `ContenedorSolicitud`/`solicitarContenedor` coinciden en los mismos 5 campos (`numero_contenedor`, `tipo`, `tamano`, `peso_kg`, `fecha_estimada_retiro`) entre Tasks 6 y 7. `create_access_token(..., cliente_id=None)` (Task 3) se usa con la misma firma en Task 6 (`cliente_id=str(cliente.id)`) y en los tests de Task 3.
