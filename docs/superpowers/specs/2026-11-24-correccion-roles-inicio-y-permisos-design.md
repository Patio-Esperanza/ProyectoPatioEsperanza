# Corrección de compilación, inicio por rol y alineación de permisos

Fecha: 2026-11-24
Estado: propuesto
Continúa: `2026-11-17-experiencia-usuario-portal-design.md` (paso 2 del orden de entrega)

## Contexto

La revisión del merge `feature/mejora-operativa-fase1` a `master` del 17 nov encontró tres
defectos que rompen el frontend o dejan a roles reales sin poder trabajar. Este spec los
corrige sin construir pantallas nuevas del spec de UX: solo deja la base coherente para
que las siguientes fases se monten encima.

### Defecto 1: `PanelCuadrilla.tsx` no compila

- `<Alert variant="error">`: `Alert` exige `tone` (`info | success | warning | danger`) y no
  declara `variant`. Es un error de tipos y además el componente se renderiza sin clase
  de tono ni icono.
- `<Button variant="outline">`: `Button` solo acepta `primary | secondary | danger | ghost`.

`npx tsc --noEmit` deja de salir limpio, cosa que `context.md` daba como garantía.

### Defecto 2: después del login nadie llega a su inicio

- `app/login/page.tsx` hace `router.push(tomarRutaRetorno() ?? "/patios")`.
- `app/page.tsx` hace `router.replace(user ? "/patios" : "/login")`.
- `homePorRol` existe en `lib/rutas.ts`, pero solo la usa `AccesoDenegado`, y para
  `guardia`, `despachador` y `operador_grua` devuelve `/patios`, que solo admite
  `operador`, `supervisor` y `admin`.

Consecuencia: la cuadrilla inicia sesión y ve "No tienes permiso para ver esta página".
El botón "Ir al inicio" de esa pantalla manda a guardia, despachador y operador de grúa a
`/patios`, que les vuelve a negar el acceso. Es un callejón sin salida.

### Defecto 3: el frontend y el backend no coinciden en quién puede qué

| Ruta | Roles en `ROLES_POR_RUTA` hoy | Lo que acepta el backend para la acción principal | Efecto |
| --- | --- | --- | --- |
| `/servicios` | cuadrilla, operador_grua, operador, supervisor, admin | `GET /api/servicios`: cliente, cuadrilla, supervisor, admin, operador. `iniciar` y `terminar`: cuadrilla, supervisor, admin | operador_grua recibe 403 al cargar. Operador ve botones Iniciar y Terminar que responden 403 |
| `/mapa` | operador_grua, operador, supervisor, admin | `GET /api/patios/{id}/mapa`: operador, supervisor, admin. La página además mueve contenedores con `POST /api/movimientos` (operador, supervisor, admin) | operador_grua recibe 403 al cargar |
| `/porteria` | operador, supervisor, admin | `POST /api/contenedores/verificar-pin`: operador, supervisor, admin | guardia, el rol que trabaja la portería, no puede entrar |
| `/salidas` | operador, supervisor, admin | `GET /api/contenedores`: cualquier sesión, filtrado por patio vía RLS | despachador, el rol que trabaja salidas, no puede entrar |

La página `/porteria` sigue usando el flujo de PIN de Spec 2 (`verificar-pin`). El flujo
nuevo de Fase 1 (`POST /api/porteria/ingresos` con fotos obligatorias) no tiene interfaz
todavía; migrarla es trabajo del paso 3 del spec de UX, no de este.

## Decisiones

### 1. Corregir tipos en `PanelCuadrilla`

- `Alert variant="error"` pasa a `Alert tone="danger"`.
- `Button variant="outline"` pasa a `Button variant="secondary"`.
- Se agrega una prueba que fuerza el error de carga y comprueba que el aviso aparece con
  `role="alert"`. Hoy la única prueba solo busca el título fijo y pasaría aunque el panel
  no cargara nada.

### 2. Inicio por rol desde una sola función

`homePorRol` es la única fuente del inicio de cada rol. La usan el login, la raíz `/` y
`AccesoDenegado`.

| Rol | Inicio |
| --- | --- |
| `cliente` | `/mis-contenedores` |
| `cuadrilla` | `/servicios` |
| `guardia` | `/porteria` |
| `despachador` | `/salidas` |
| `operador`, `supervisor`, `admin` | `/patios` |
| `operador_grua` | `/inicio` |
| cualquier otro valor | `/inicio` |

`operador_grua` no tiene pantalla todavía. "Por ubicar" llega con el paso 3 del spec de UX.
Mientras tanto aterriza en `/inicio`, una página nueva protegida solo por sesión que
explica, sin culpa del usuario, que su rol aún no tiene pantalla de trabajo y que le pida
a un supervisor lo que necesite. El rol desconocido cae ahí mismo en lugar de en una
pantalla de acceso denegado que lo regresa a otra pantalla de acceso denegado.

En el login, el rol se lee del token recién recibido con `decodeTokenSafe` de `lib/jwt.ts`,
porque `user` del contexto todavía no está actualizado en ese mismo manejador. La ruta de
retorno guardada sigue teniendo prioridad sobre el inicio del rol.

Invariante que se prueba: para cada valor de `RolUsuario`, `homePorRol(rol)` es una ruta
que ese rol puede ver según `ROLES_POR_RUTA` (o que no tiene restricción de rol).

### 3. Alinear permisos

Regla: una ruta del frontend lista exactamente los roles que el backend acepta para la
acción principal de esa página. Donde la página necesita varios endpoints, manda el más
restrictivo de los que la página usa siempre.

| Ruta | Roles nuevos | Cambio en backend |
| --- | --- | --- |
| `/servicios` | cuadrilla, supervisor, admin | ninguno |
| `/mapa` | operador, supervisor, admin | ninguno |
| `/porteria` | guardia, operador, supervisor, admin | `verificar-pin` acepta `guardia` |
| `/salidas` | despachador, operador, supervisor, admin | ninguno |

Se quita `operador_grua` de `/servicios` y de `/mapa` en vez de abrirle el backend: el mapa
le permitiría mover contenedores por `POST /api/movimientos`, y esa decisión (si el
operador de grúa reubica desde el mapa o solo desde "Por ubicar") pertenece al paso 3.

Se quita `operador` de `/servicios` porque no puede iniciar ni terminar órdenes. Si se
quiere que operación consulte órdenes sin operarlas, eso es una vista de solo lectura que
no existe todavía.

#### Cambio en `POST /api/contenedores/verificar-pin`

- Roles: `operador`, `supervisor`, `admin` y `guardia`.
- Un guardia sin patios asignados recibe 403 "Guardia sin patios asignados", igual que en
  `backend/app/api/porteria.py`.
- Un guardia solo encuentra contenedores de sus patios. La consulta filtra por
  `Contenedor.patio_id.in_(user.patios)` en Python, además del filtro de RLS, para no
  depender de RLS como única barrera (ver deuda técnica sobre el bypass `IS NULL`). Un
  contenedor de otro patio responde 404, igual que uno inexistente, para no revelar que
  existe.

## Fuera de alcance

- Pantalla "Por ubicar" del operador de grúa.
- Migrar `/porteria` al flujo de ingreso con fotos de Fase 1.
- `lib/estados.ts`, `EstadoBadge` y el resto de componentes del spec de UX.
- Mostrar número de contenedor en lugar de UUID en `PanelCuadrilla`, filtrar por día y por
  patio, y captura de foto con cámara.
- Dar al despachador acceso al mapa.
- Las consultas N+1 de `GET /api/servicios`.

## Pruebas

Frontend:

- `lib/rutas.test.ts`: la invariante de inicio para los ocho roles, la tabla de roles por
  ruta de este spec, y que ninguna ruta de staff admite `cliente`.
- `app/login/page.test.tsx`: un token de `cuadrilla` termina en `/servicios`; la ruta de
  retorno guardada sigue teniendo prioridad.
- `app/page.test.tsx`: `cliente` va a `/mis-contenedores` y `guardia` a `/porteria`.
- `app/inicio/page.test.tsx`: muestra el rol y el mensaje.
- `tests/servicios_cuadrilla.test.tsx`: el error de carga se muestra como alerta.

Backend (`tests/test_contenedores_api.py`):

- Guardia con el patio del contenedor verifica el PIN: 200 y estado `en_porteria`.
- Guardia sin patios: 403.
- Guardia de otro patio: 404.

Verificación final: `npx tsc --noEmit`, `npx vitest run` y `pytest` en verde.

## Preguntas abiertas

- [ ] ¿Operación (`operador`) debe ver las órdenes de servicio en modo de solo lectura?
- [ ] ¿El operador de grúa reubicará desde el mapa o solo desde "Por ubicar"?
