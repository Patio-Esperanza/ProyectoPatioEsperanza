# Bugs de autorización en el frontend + rediseño de la interfaz — Design

## Contexto

Las pruebas E2E en navegador del 2026-09-20 dejaron tres defectos de autenticación sin
corregir, aprobados por el usuario como tarea aparte. En la misma sesión el usuario pidió
mejorar la interfaz del dashboard. Ambos trabajos tocan los mismos archivos
(`AuthGuard`, `NavBar`, layout raíz), así que se diseñan juntos y se implementan en fases.

## Parte 1: bugs de autorización

### Bug 1 — `AuthGuard` no valida el rol

`frontend/components/AuthGuard.tsx` solo comprueba que exista sesión. Cualquier usuario
autenticado abre cualquier ruta escribiendo la URL. Verificado en navegador: un usuario con
rol `cliente` entra a `/patios`. El `NavBar` sí filtra los enlaces por rol, pero eso es
cosmético.

Las 11 páginas internas ya envuelven su contenido en `AuthGuard`. Las 4 públicas
(`/login`, `/`, `/registro`, `/registro/verificar`) no lo usan, y es correcto.

### Bug 2 — el botón "Salir" no cierra la sesión

`logout` en `frontend/lib/auth-context.tsx` limpia `localStorage` y el estado, pero nadie
navega después. La página queda montada. `AuthGuard` sí redirige cuando `user` pasa a
`null`, pero su `useEffect` depende de que el árbol se vuelva a renderizar; en la prueba
manual la página se quedó en `/patios`.

### Bug 3 — el formulario de login falla de forma intermitente

En una prueba el clic en "Entrar" nunca produjo una petición HTTP. Se leyeron
`app/login/page.tsx`, `lib/api.ts` y `lib/auth-context.tsx` y **el código es correcto**. No
hay causa raíz identificada. Este bug no se "arregla" en esta spec: se instrumenta para
poder diagnosticarlo la próxima vez que ocurra. Inventar un fix sin reproducción sería
adivinar.

### Decisión de diseño

**`AuthGuard` acepta una prop opcional `roles`.** Sin `roles` se comporta como hoy: exige
sesión. Con `roles`, si `user.rol` no está en la lista, renderiza una pantalla de acceso
denegado en vez de redirigir. Se eligió la pantalla explicativa sobre el redirect
silencioso porque un redirect deja al usuario sin saber qué pasó y puede encadenar bucles.

```tsx
<AuthGuard roles={["operador", "supervisor", "admin"]}>
  <PatiosContent />
</AuthGuard>
```

**`logout` sigue siendo puro.** Limpia almacenamiento y estado, nada más. La navegación la
hace quien llama: el componente de sesión ejecuta `logout()` y luego
`router.replace("/login")`. Un contenedor de estado no debe navegar por su cuenta; hacerlo
lo vuelve difícil de probar y esconde el efecto.

**Bug 3 se instrumenta, no se parchea.** Se agrega manejo del caso en que `fetch` falla por
red (hoy un `TypeError` de `fetch` cae en el `catch` genérico y muestra "No se pudo iniciar
sesión", indistinguible de credenciales malas). Se separan los dos mensajes. Si el fallo
vuelve a ocurrir, el mensaje dirá si hubo petición o no.

### Mapa de rutas y roles

Derivado de `require_roles` en el backend, no inventado:

| Ruta | Roles en el frontend | Origen en el backend |
|---|---|---|
| `/patios` | operador, supervisor, admin | `GET /api/patios` no exige rol; la restricción es de UX, ver nota |
| `/contenedores` | operador, supervisor, admin | `POST /api/contenedores` usa `_ROLES_ESCRITURA` |
| `/contenedores/[id]` | cualquier sesión | `GET /api/contenedores/{id}` no exige rol |
| `/movimientos` | operador, supervisor, admin | `POST /api/movimientos` usa `_ROLES_ESCRITURA` |
| `/ubicaciones/sugerir` | operador, supervisor, admin | `POST /api/ubicaciones/sugerir` usa `_ROLES` |
| `/porteria` | operador, supervisor, admin | `POST /api/contenedores/verificar-pin` |
| `/salidas` | operador, supervisor, admin | cola de planeación, consume `GET /api/contenedores` |
| `/usuarios` | admin | `require_roles(RolUsuario.ADMIN)` |
| `/clientes` | admin | `require_roles(RolUsuario.ADMIN)` |
| `/solicitar` | cliente | `require_roles(RolUsuario.CLIENTE)` |
| `/mis-contenedores` | cliente | `require_roles(RolUsuario.CLIENTE)` |

Nota sobre `/patios`: el backend deja que cualquier sesión liste patios. El frontend lo
restringe a staff porque la página existe para administrar el patio y no le sirve a un
cliente. Es una decisión de interfaz, no de seguridad. La seguridad sigue en el backend.

Hallazgo colateral: los roles `guardia` y `despachador` existen en `RolUsuario` pero
**ningún endpoint los acepta** para escribir. Un usuario con esos roles puede autenticarse
y no puede hacer nada. Queda fuera de alcance de esta spec; se registra como pendiente.

### El `home` de cada rol

`cliente` va a `/mis-contenedores`. Cualquier otro rol va a `/patios`. Lo usan la pantalla
de acceso denegado, la raíz `/` y el destino después del login.

## Parte 2: rediseño de la interfaz

### Problema

- 701 líneas de CSS repartidas en 14 archivos `page.module.css`. Las reglas `.main`,
  `.form`, `.error` y `.list` están duplicadas con valores casi idénticos en cada uno.
- No existe ningún componente de UI compartido. Cada página reimplementa botones, campos,
  tarjetas y listas.
- `max-width: 720px` en páginas que muestran listados de contenedores.
- Sin estados de foco visibles. Incumple el requisito de accesibilidad más básico.
- Sin estados vacíos. Una lista sin datos deja la pantalla en blanco.
- Carga representada como el texto "Cargando...".
- `NavBar` con más de diez enlaces en una fila, sin indicador de ruta activa y sin
  comportamiento responsive.

### Decisiones confirmadas con el usuario

- **Navegación:** sidebar fija en escritorio con las rutas agrupadas por sección
  (Operación, Administración, Cliente) y drawer en móvil. Reemplaza al `NavBar` horizontal.
- **Reparto:** por fases. Primero el sistema de diseño, los componentes compartidos y tres
  páginas piloto. El usuario revisa la dirección antes de tocar las once restantes.
- **Rol denegado:** pantalla explicativa, no redirect silencioso.
- **Modo oscuro:** se definen los tokens de la paleta oscura pero no se expone el
  interruptor todavía.

### Sistema de diseño

Se conserva la paleta de marca existente (azul `#000056`, café `#AF8235`, amarillo
`#F0D579`, gris `#504D4C`) y la tipografía IBM Plex Sans y Mono. Lo que se agrega son los
tokens que hoy faltan y que provocan que cada página invente sus propios valores:

- Escala de espaciado en múltiplos de 4: 4, 8, 12, 16, 24, 32, 48.
- Escala tipográfica: 12, 14, 16, 18, 24, 32.
- Escala de radios: 6, 8, 12.
- Escala de elevación: tres niveles, de tarjeta a modal.
- Tokens semánticos sobre los de marca: `--color-primary`, `--color-surface`,
  `--color-on-surface`, `--color-danger`, `--color-warning`, `--color-success`,
  `--color-ring`. Los componentes usan los semánticos, nunca el hex ni el token de marca
  directamente. Esto es lo que hace barato activar el modo oscuro después.
- Tokens de la paleta oscura definidos bajo `@media (prefers-color-scheme: dark)` con la
  guarda `:root:not([data-theme="light"])`, más `:root[data-theme="dark"]`, sin
  interruptor en la interfaz todavía.
- Un anillo de foco visible y único para todo lo interactivo.
- Cifras tabulares en las columnas numéricas y en los códigos de contenedor.

### Componentes compartidos

Viven en `frontend/components/ui/`, cada uno con su test al lado:

| Componente | Reemplaza |
|---|---|
| `Button` | los `<button>` con estilos repetidos en 13 páginas, con estado de carga |
| `Field` | la pareja `<label>` más `<input>` repetida, con texto de ayuda y error debajo |
| `Card` | las superficies `.form` y `.list li` |
| `DataTable` | las `<ul>` usadas como tablas, con desbordamiento horizontal en móvil |
| `Badge` | los estados de contenedor, hoy texto plano |
| `EmptyState` | el vacío actual cuando no hay datos |
| `Skeleton` | el texto "Cargando..." |
| `Alert` | los `<p role="alert">` repetidos |
| `PageHeader` | el `<h1>` suelto más la acción primaria |

Regla que se aplica al construirlos: **una sola acción primaria por pantalla**. Las demás
quedan visualmente subordinadas.

### Estructura del layout

```
AppShell
├── Sidebar          (escritorio ≥1024px, fija; móvil: drawer)
│   ├── Marca
│   ├── Secciones filtradas por rol, con la ruta activa marcada
│   └── Sesión: rol actual y "Salir"
└── Contenido
    ├── PageHeader
    └── children
```

El ancho del contenido sube de 720px a 1280px para los listados. Los formularios de una
sola columna conservan una medida de lectura cómoda.

### Fases

**Fase 0 — bugs de autorización.** `AuthGuard` con `roles`, pantalla de acceso denegado,
`logout` con navegación explícita, separación de los mensajes de error del login. Se aplica
el mapa de rutas a las 11 páginas. TDD, sin tocar estilos.

**Fase 1 — fundación visual y piloto.** Tokens en `globals.css`, los nueve componentes
compartidos con sus tests, `AppShell` con la sidebar, y tres páginas migradas: `/login`,
`/patios` y `/contenedores`. El usuario revisa aquí.

**Fase 2 — el resto.** Las once páginas restantes migradas a los componentes compartidos.
Es trabajo repetitivo sobre una plantilla ya validada; se delega a Codex por bloques y se
revisa lo que vuelva.

## Testing

- `AuthGuard.test.tsx` ampliado: rol permitido renderiza, rol no permitido muestra la
  pantalla de acceso denegado sin redirigir, sin `roles` se comporta como antes.
- Test nuevo del componente de sesión: "Salir" llama a `logout` y luego a
  `router.replace("/login")`.
- `login/page.test.tsx` ampliado: fallo de red y fallo de credenciales producen mensajes
  distintos.
- Cada componente de `components/ui/` con su test de render y de estados.
- Las 22 suites existentes deben seguir en verde. Las páginas migradas actualizan su test
  cuando cambie el marcado, nunca se borra un caso para que pase.
- Verificación manual en navegador al cerrar cada fase.

## Fuera de alcance

- Causa raíz del fallo intermitente de login. Se instrumenta, no se resuelve.
- Habilitar el interruptor de modo oscuro.
- Dar rutas útiles a los roles `guardia` y `despachador`.
- Cambiar cualquier endpoint del backend.
- Editar o desactivar usuarios, y el resto de los huecos funcionales listados en
  `context.md`.
- Librería de componentes externa. El proyecto no usa ninguna y no se introduce ahora.
