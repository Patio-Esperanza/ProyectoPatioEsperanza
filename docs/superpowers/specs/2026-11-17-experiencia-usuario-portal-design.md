# Experiencia de usuario interna y portal del cliente

Fecha: 2026-11-17
Estado: propuesto; continúa `2026-09-20-auth-frontend-y-rediseno-ui-design.md`
Versión editable: https://claude.ai/artifact/FxgedpJGGMkRtQrqiVN6jd

## Relación con specs existentes

- **Roles existentes**: `operador`, `supervisor`, `admin`, `guardia`, `despachador` y
  `cliente`. La tabla de navegación de abajo no incluye a `operador` ni a `supervisor`
  porque se escribió sin conocerlos: hay que decidir si `operador_grua` es el `operador`
  existente y si "operación" en los specs nuevos equivale a `supervisor`.
- **`/mapa`** (`2026-09-22-mapa-patio-design.md`) y **`/reportes`**
  (`2026-09-30-modulo-reportes-design.md`, `2026-10-22-reportes-cliente-design.md`) ya
  existen y ya están en `lib/rutas.ts` y el `Sidebar`. Este spec solo cambia a qué roles
  se muestran y cuál es la pantalla de inicio de cada rol.
- **Reportes del cliente** ya existen con filtros, Excel y PDF por impresión. La sección
  "Reportes" del portal apunta ahí.

## Resumen y principios

Cada persona entra directo a la pantalla de su trabajo del día, en el dispositivo que de
verdad usa: el celular en portería y en patio, el escritorio en la oficina y el que
prefiera el cliente. Este spec define la navegación por rol, el lenguaje y los componentes
que comparten las fases 1 a 4. Continúa el rediseño en curso, que ya entregó `AppShell`,
`Sidebar` y el mapa de rutas por rol.

### Principios

1. **Inicio por rol**: nadie aterriza en una página genérica. El guardia abre Portería; el
   cliente, Mis contenedores.
2. **Una acción principal por pantalla**: un botón primario, grande y abajo en móvil.
3. **Nunca un UUID** a la vista ni en un campo. Se busca por número de contenedor, nombre o
   etiqueta de ubicación.
4. **Errores con motivo y siguiente paso**: "El contenedor tiene un traspaleo pendiente.
   Avisa a operación", no "409 Conflict".
5. **El estado se ve igual en todas partes**: mismo nombre, mismo color, en tablas,
   tarjetas, correos y mapa.
6. **Lo del cliente es del cliente**: ve todo lo de sus contenedores y nada de los demás,
   ni siquiera su existencia.

## Roles y navegación

Hoy `guardia` y `despachador` pueden iniciar sesión, pero no tienen ninguna ruta propia.
Con este spec, cada rol tiene su pantalla de inicio y su sección en el `Sidebar`, todo
derivado del mismo `lib/rutas.ts` que usa el guard.

| Rol | Inicio | Secciones del menú | Dispositivo principal |
| --- | --- | --- | --- |
| Guardia | Portería | Portería (Ingreso, Salida), Buscar | Celular |
| Despachador | Salidas del día | Salidas, Mapa, Buscar | Celular o tableta |
| Operador de grúa (nuevo) | Por ubicar | Por ubicar, Mapa, Buscar | Celular |
| Cuadrilla (nuevo) | Servicios de hoy | Servicios de hoy, Buscar | Celular |
| Admin | Tablero | Tablero, Contenedores, Mapa, Salidas, Servicios, Reportes, Clientes, Usuarios, Patios | Escritorio |
| Cliente | Mis contenedores | Mis contenedores, Solicitar entrada, Reportes, Mi empresa | Cualquiera |

### Rol nuevo: `operador_grua`

El operador de grúa confirma la ubicación de cada contenedor que ingresa y hace las
reubicaciones (decidido el 17 nov 2026). Su pantalla de inicio, **Por ubicar**, lista los
contenedores `ingresado` del patio con la ubicación sugerida y un botón de confirmar. Se
agrega a `RolUsuario` y a las rutas de ubicar y reubicar.

### Rol nuevo: `cuadrilla`

La cuadrilla hace los servicios especiales: traspaleo, reacomodo, desempalme y empalme
(decidido el 17 nov 2026). Su pantalla **Servicios de hoy** muestra las órdenes programadas
del patio con botones grandes de **Iniciar** y **Terminar**, la cámara para las fotos que
pide el servicio y, en el traspaleo, el registro de la segunda unidad (contenedor o caja seca).

### Reglas de navegación

- Después del login se redirige al inicio del rol, no a `/`.
- En móvil, los roles operativos ven una barra inferior con 3 o 4 destinos en vez del menú lateral.
- Un usuario con varios patios elige el patio una vez arriba, en `PatioSelect`, y toda la
  app usa ese patio hasta que lo cambie.

## Componentes y lenguaje

Primero se terminan los nueve componentes pendientes del rediseño (`Button`, `Field`,
`Card`, `DataTable`, `Badge`, `EmptyState`, `Skeleton`, `Alert`, `PageHeader`). Las fases
1 a 4 necesitan, además, estos:

| Componente | Qué hace | Lo usan |
| --- | --- | --- |
| `CodeInput` | Captura PIN o número de contenedor: teclado numérico o mayúsculas automáticas, validación ISO 6346 al teclear | Portería |
| `ContenedorPicker` | Combobox de búsqueda de contenedores con filtro de estados | Movimientos, salidas, servicios |
| `UbicacionPicker` | Sugerencias primero y después la cascada carril → nivel | Portería, operador de grúa, servicios |
| `EstadoBadge` | Nombre y color fijo de cada estado (tabla abajo) | Todas |
| `Timeline` | Pasos con fecha y hora, el actual resaltado | Detalle, portal |
| `StatCard` | Número grande, etiqueta y enlace a la lista que lo explica | Tablero, portal |
| `PhotoCapture` | Cámara del celular, compresión y subida a Spaces con reintento | Portería, servicios |
| `Sheet` | Panel lateral en escritorio, hoja desde abajo en móvil | Mapa, detalle rápido |

### Nombres y colores de estado

| Estado | Etiqueta | Tono de `Badge` |
| --- | --- | --- |
| `solicitud_ingreso` | Entrada solicitada | Neutral |
| `ingresado` | Por ubicar | Informativo |
| `ubicado` | En patio | Éxito |
| `en_servicio_especial` | En servicio | Advertencia |
| `solicitud_salida` | Salida solicitada | Informativo |
| `en_porteria_salida` | Listo en puerta | Acento |
| `despachado` | Despachado | Neutral atenuado |
| `rechazado` | Rechazado | Crítico |

La tabla vive en un solo archivo, `lib/estados.ts`. Las plantillas de correo y los
reportes usan las mismas etiquetas.

### Formatos

- Fechas: "17 nov 2026, 12:45" en hora del patio; en tablas, "17/11 12:45".
- Número de contenedor en fuente monoespaciada y separado: `MSCU 123456 7`. Se guarda sin espacios.
- Días: "8 días" y "1 día", nunca "8 d".

## Tablero interno y portal del cliente

El tablero responde "¿cómo está el patio hoy y qué necesita atención?". El portal responde
"¿dónde están mis contenedores y qué puedo hacer con ellos?". Ninguno de los dos necesita
tablas nuevas: leen lo que crean las fases 1 a 4.

### Tablero del admin

- **Fila de `StatCard`**: en patio, ocupación %, entradas de hoy, salidas de hoy, servicios
  pendientes, estancias que rebasan el umbral. Cada tarjeta lleva a la lista filtrada.
- **Requiere atención**, ordenado por urgencia:
    - contenedores `ingresado` sin ubicar por más de 2 horas;
    - salidas con fecha deseada de hoy que aún no están listas en puerta;
    - servicios pendientes de contenedores con salida solicitada;
    - PIN bloqueados por intentos fallidos;
    - corte diario pendiente.
- **Actividad reciente**: los últimos 20 movimientos con quién y cuándo.

Endpoint: `GET /api/tablero?patio_id=` devuelve todo en una sola respuesta y se refresca cada 60 s.

### Portal del cliente

**Mis contenedores**

- Contadores arriba: entrada solicitada, en patio, en servicio, salida solicitada. Cada
  contador filtra la lista.
- Tarjeta por contenedor: número, `EstadoBadge`, días en patio, días libres restantes y el
  botón de la siguiente acción posible (Ver PIN, Solicitar salida o Ver PIN de salida).
- Búsqueda por número y filtro por estado; en escritorio, cambio a vista de tabla.

**Detalle del contenedor**

- `Timeline`: entrada solicitada, ingresó (con fotos de inspección), en patio, cada
  servicio, salida solicitada, listo en puerta, despachado.
- Acciones: reenviar PIN, solicitar, modificar o cancelar la salida, solicitar servicio.
- El cliente ve días y servicios, pero no la ubicación exacta en el patio (pregunta abierta).

**Mi empresa**

- Lista de usuarios de la empresa, invitar a un compañero y darlo de baja (solo el usuario
  principal del cliente).
- Preferencias de correo de cada usuario.

## Notificaciones por correo

El cliente se entera de cada cambio importante sin entrar al portal. Se usa el wrapper de
SendGrid que ya existe, con una plantilla por evento y un registro de envíos para poder
reenviar y auditar.

| Evento | Destinatario | Contenido |
| --- | --- | --- |
| Entrada solicitada | Quien solicitó | PIN de entrada, patio, instrucciones |
| Ingreso confirmado | Usuarios del cliente | Hora de ingreso, fotos de inspección |
| Salida solicitada | Quien solicitó | PIN de salida para el transportista |
| Listo en puerta | Usuarios del cliente | Que ya puede pasar el transportista |
| Despachado | Usuarios del cliente | Hora de salida y días de estancia |
| Servicio programado, terminado o rechazado | Quien lo solicitó | Fecha, fotos o motivo |
| Queda 1 día libre (opcional) | Usuarios del cliente | Contenedor y fecha desde la que se cobra |

### Datos

- Tabla `notificaciones`: evento, contenedor_id, usuario_id, correo, enviado_en, estado de
  SendGrid. Un envío fallido se reintenta desde el scheduler.
- Columna `usuarios.preferencias_correo` (jsonb) con un interruptor por evento. Los correos
  con PIN no se pueden apagar.

### Reglas

- Asunto con el número de contenedor al inicio: "MSCU 123456 7 · Listo en puerta".
- Si un mismo evento ocurre para varios contenedores del mismo cliente en 10 minutos, se
  manda un solo correo con la lista.

## Calidad, entrega y preguntas

### Accesibilidad y móvil

- Todas las pantallas funcionan a 360 px de ancho. Los objetivos táctiles miden al menos 48 px.
- Contraste AA en todo y alto contraste en portería, que se usa a pleno sol.
- Activar la paleta oscura que ya está definida, con cambio automático por preferencia del
  sistema. Ayuda al turno nocturno de portería.
- `inputmode="numeric"` en PIN, `autocapitalize="characters"` en números de contenedor y
  `autocomplete="off"` en ambos.
- El color nunca es la única señal: cada `EstadoBadge` lleva texto y el mapa imprime `n/5`.

### Medición

- Tiempo de ingreso: de abrir Portería → Ingreso a confirmar. Meta: menos de 60 s.
- Rechazos 409 por motivo, para ver qué regla frena más la operación.
- Porcentaje de salidas solicitadas desde el portal frente a las registradas por personal interno.

Se guardan en la auditoría existente y se resumen en el tablero del admin.

### Orden de entrega

1. Terminar los nueve componentes del rediseño y migrar `/login`, `/patios` y
   `/contenedores`. Investigar en el mismo paso el fallo intermitente del login, que sigue
   sin causa raíz.
2. Rutas e inicio por rol, `lib/estados.ts` y `EstadoBadge`. Con esto, guardia y
   despachador ya tienen pantalla.
3. `CodeInput`, `ContenedorPicker`, `UbicacionPicker` y `PhotoCapture`, junto con la Fase 1.
4. Portal del cliente con `Timeline` y las notificaciones.
5. Tablero del admin, cuando ya existan los datos de las fases 3 y 4.

### Pruebas

- Cada componente nuevo con Vitest y React Testing Library, incluida la navegación con teclado.
- Por rol: después del login llega a su inicio, y una ruta de otro rol muestra la pantalla explicativa.
- `lib/estados.ts` cubre los 12 valores de `EstadoContenedor`. La prueba falla si se agrega
  un estado sin etiqueta.
- Plantillas de correo: cada evento genera asunto y cuerpo con el número de contenedor.

### Preguntas abiertas

- [ ] ¿`operador_grua` es el `operador` existente? ¿"Operación" equivale a `supervisor`?
- [ ] ¿El cliente debe ver la ubicación exacta de su contenedor en el patio?
- [ ] ¿Los transportistas necesitan su propio acceso, o basta con que el cliente les reenvíe el PIN?
- [ ] ¿Quién del lado del cliente puede invitar y dar de baja usuarios?
