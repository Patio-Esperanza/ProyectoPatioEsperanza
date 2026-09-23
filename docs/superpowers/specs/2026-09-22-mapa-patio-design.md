# Mapa visual del patio

Fecha: 2026-09-22
Estado: aprobado, pendiente de plan de implementación

## Problema

No existe forma de ver el acomodo del patio. El operador que necesita colocar un
contenedor usa `/ubicaciones/sugerir`, una pantalla donde debe teclear a mano el UUID del
contenedor y el UUID de una ubicación de referencia. No hay manera de saber qué espacios
están libres ni dónde está cada contenedor sin consultar la base de datos directamente.

Faltan dos cosas para resolverlo:

1. Ningún endpoint devuelve la ocupación del patio. `app/api/routes/ubicaciones.py` solo
   expone `POST /sugerir`.
2. No hay manera de crear el layout de un patio. Los carriles, tramos, tiras y ubicaciones
   solo se crean dentro de los tests. No hay API, no hay seed y no hay interfaz de
   administración.

## Alcance

Entra en este spec:

- Un endpoint que devuelve la ocupación agregada de un patio.
- Un endpoint que devuelve el detalle de una tira.
- Una pantalla `/mapa` con vista de planta y detalle al hacer clic.
- Colocar un contenedor desde el mapa, apoyado en el algoritmo de sugerencia existente.
- Un script de seed para cargar el layout de un patio.

Queda fuera:

- Reubicar contenedores arrastrando en el mapa.
- Vista de alzado tipo bay plan.
- Editor de layout desde la interfaz.
- Actualización en vivo del mapa.

## Modelo de datos existente

La geometría del patio vive en `backend/app/models/ubicacion.py` y tiene cuatro niveles:

```
Patio
  Carril  (orden, tipo_teorico)
    Tramo  (orden)
      Tira  (orden)
        Ubicacion  (nivel 1 a 5, capacidad_peso_kg, activo)
```

La ocupación se lee de `contenedores.ubicacion_id`. El índice parcial único
`uq_contenedor_ubicacion_activa` garantiza que una ubicación tenga a lo más un contenedor.

## Diseño

### Esquema

Migración `0011_patio_punto_entrada.py`: agrega `patios.ubicacion_entrada_id`, UUID
nullable con llave foránea a `ubicaciones.id`.

Es nullable porque los patios existentes todavía no tienen layout. Cuando el valor es
nulo el mapa se muestra igual, pero la sugerencia automática queda deshabilitada y la
pantalla lo explica.

La llave foránea cierra un ciclo: `patios` apunta a `ubicaciones`, que a través de
`tiras`, `tramos` y `carriles` regresa a `patios`. Postgres acepta el ciclo cuando la
restricción se agrega con `ALTER TABLE ADD CONSTRAINT`, que es lo que hace esta migración.

### Servicio

Archivo nuevo `backend/app/services/mapa_patio.py`, con dos funciones y una consulta cada
una. Ninguna hace N+1.

`obtener_mapa(db, patio_id)` une `carriles`, `tramos`, `tiras` y `ubicaciones`, hace LEFT
JOIN con `contenedores` y agrupa por tira. Por cada tira devuelve `niveles_totales`,
`niveles_activos` y `niveles_ocupados`. El mapa nunca carga las ubicaciones individuales:
en un patio mediano son unas 7,200 filas contra unas 1,440 tiras.

`obtener_detalle_tira(db, tira_id)` devuelve los cinco niveles de una tira con el
contenedor de cada uno, o nulo si está libre.

### Endpoints

| Método | Ruta | Respuesta |
| --- | --- | --- |
| GET | `/api/patios/{patio_id}/mapa` | jerarquía de carriles, tramos y tiras con ocupación agregada, más `ubicacion_entrada_id` y un resumen |
| GET | `/api/tiras/{tira_id}` | los cinco niveles con contenedor o nulo |

Ambos exigen rol `operador`, `supervisor` o `admin`, los mismos de `_ROLES_ESCRITURA`. El
rol `cliente` no tiene acceso. Pasan por `require_roles` y por los GUC `app.rol` y
`app.patios_asignados` que `deps.py` fija con `set_config(..., true)`, así que la RLS
aplica sin cambios.

Forma de la respuesta del mapa:

```json
{
  "patio_id": "...",
  "ubicacion_entrada_id": "...",
  "resumen": { "ubicaciones_activas": 7100, "ocupadas": 2300 },
  "carriles": [
    {
      "id": "...",
      "codigo": "A1",
      "orden": 0,
      "tipo_teorico": "lleno",
      "tramos": [
        {
          "id": "...",
          "codigo": "T1",
          "orden": 0,
          "tiras": [
            {
              "id": "...",
              "codigo": "R1",
              "orden": 0,
              "niveles_totales": 5,
              "niveles_activos": 5,
              "niveles_ocupados": 3
            }
          ]
        }
      ]
    }
  ]
}
```

Forma de la respuesta del detalle de tira:

```json
{
  "tira_id": "...",
  "codigo": "A1-T1-R1",
  "niveles": [
    {
      "nivel": 1,
      "ubicacion_id": "...",
      "codigo": "A1-T1-R1-N1",
      "activo": true,
      "capacidad_peso_kg": 30000,
      "contenedor": {
        "id": "...",
        "numero_contenedor": "CAIU1112223",
        "tipo": "lleno",
        "tamano": "40",
        "peso_kg": 28000,
        "estado": "ubicado"
      }
    }
  ]
}
```

### Filtro nuevo en contenedores

`GET /api/contenedores` filtra hoy por `estado`, `patio_id` y `cliente_id`. El panel de
pendientes necesita además `sin_ubicacion: bool`. Filtrar del lado del cliente obligaría a
traer todos los contenedores del patio para descartar casi todos.

### Seed del layout

Script nuevo `backend/scripts/seed_patio_layout.py`, con los argumentos
`--patio-codigo`, `--carriles`, `--tramos`, `--tiras`, `--niveles` y `--entrada`.

Es idempotente: si ya existe un carril con el código que va a generar, lo salta. Al
terminar marca la ubicación indicada en `patios.ubicacion_entrada_id`.

### Colocación

Se reusa `POST /api/movimientos` sin cambios. Ya bloquea la ubicación destino con
`with_for_update`, responde 409 cuando está ocupada y registra la auditoría. El mapa solo
consume ese contrato.

## Frontend

### Ruta y navegación

Ruta nueva `/mapa`. El patio se elige con el componente `PatioSelect` que ya existe, y la
selección se sincroniza al query param `?patio=<id>` para que el enlace se pueda compartir
y sobreviva a un refresco.

En `frontend/lib/rutas.ts` se agrega `"/mapa": [...ROLES_STAFF]`. El `Sidebar` gana una
entrada en la sección de operación.

### Componentes

Todos nuevos, bajo `frontend/components/mapa/`:

| Componente | Responsabilidad |
| --- | --- |
| `MapaPatio.tsx` | Dibuja la cuadrícula. Presentacional puro. |
| `CeldaTira.tsx` | Una celda: color por ocupación, texto `3/5`, estados seleccionada y sugerida. |
| `DetalleTira.tsx` | Los cinco niveles de una tira, con botón de colocar en cada nivel libre. |
| `PanelPendientes.tsx` | Contenedores del patio sin ubicación asignada, con selección única. |
| `LeyendaMapa.tsx` | Leyenda de colores. |

`frontend/app/mapa/page.tsx` es el único que hace fetch y guarda estado. Los cinco
componentes reciben props y emiten callbacks, de modo que cada uno se prueba aislado.

### Render de la cuadrícula

La cuadrícula se dibuja con CSS grid sobre DOM, sin canvas y sin virtualización. A 1,440
celdas React rinde bien y la accesibilidad no requiere trabajo extra.

El mapa agrupa un bloque por carril. Dentro del carril los tramos se separan con un
margen, y dentro de cada tramo las tiras se acomodan en columnas. Arriba del mapa hay un
filtro por carril para que el operador reduzca la vista cuando el patio es grande.

Accesibilidad:

- El mapa usa `role="grid"` con roving tabindex: un solo tab stop y navegación con flechas
  entre celdas. Exponer 1,440 tab stops haría la pantalla inutilizable con teclado.
- Cada celda lleva un `aria-label` completo, por ejemplo
  `Carril A1, tramo T1, tira R1, 3 de 5 niveles ocupados`.
- El color nunca es el único indicador. La celda siempre imprime `3/5`, la misma regla que
  ya siguen `Badge` y `Alert`.

### Flujo de colocación

1. El operador elige el patio. El mapa y los pendientes se cargan en paralelo.
2. Elige un contenedor del panel de pendientes.
3. El frontend llama `POST /api/ubicaciones/sugerir` usando
   `punto_referencia_ubicacion_id = ubicacion_entrada_id` del patio. Si el patio no tiene
   punto de entrada, este paso se omite y se muestra un `Alert` que lo explica.
4. El mapa marca la tira sugerida con un contorno distinto y la etiqueta `Sugerido`.
5. El operador abre cualquier tira y elige un nivel libre.
6. Si el nivel elegido no es el sugerido, se pide un motivo en un `Field` obligatorio y se
   envía `override_manual: true` junto con `motivo_override`. Si coincide con la
   sugerencia, se envía `override_manual: false`.
7. Se llama `POST /api/movimientos` con `tipo: "ingreso"`, `score_sugerido` y
   `score_elegido`.
8. Al terminar se recargan el mapa y los pendientes.

### Datos desfasados

El mapa puede quedar viejo si otro operador coloca un contenedor mientras tanto. No habrá
polling ni websockets.

El backend ya responde 409 con el mensaje `Ubicación ya ocupada`. El frontend lo muestra en
un `Alert` y recarga el mapa. Además, el encabezado lleva un botón `Actualizar` manual.

### Cliente de API

En `frontend/lib/api.ts` se agregan `obtenerMapaPatio` y `obtenerDetalleTira`, y el
parámetro `sin_ubicacion` en `listarContenedores`. `crearMovimiento` ya existe pero su tipo
de payload no acepta `score_sugerido` ni `score_elegido`, aunque el backend sí los recibe;
hay que agregarlos.

`sugerirUbicacion` ya existe. Su respuesta devuelve `ubicacion_id`, `codigo` y `costo`,
pero no dice a qué tira pertenece la ubicación sugerida, y el mapa necesita esa tira para
resaltarla. `SugerenciaUbicacionResponse` gana dos campos: `tira_id` y `nivel`.

## Pruebas

Backend:

- `obtener_mapa` agrega correctamente los tres contadores por tira.
- Las ubicaciones con `activo = false` cuentan en `niveles_totales` pero no en
  `niveles_activos`, y nunca en `niveles_ocupados`.
- `obtener_detalle_tira` devuelve los cinco niveles, con contenedor y sin contenedor.
- Los dos endpoints rechazan al rol `cliente` con 403.
- La RLS limita el mapa a los patios asignados del usuario.
- `GET /api/contenedores?sin_ubicacion=true` excluye a los que ya tienen ubicación.

Frontend:

- `CeldaTira`: los cuatro estados (vacía, parcial, llena, inactiva), el texto `n/5` y el
  `aria-label`.
- `MapaPatio`: agrupación por carril y tramo, navegación con flechas, filtro por carril.
- `DetalleTira`: nivel libre contra nivel ocupado, y botón de colocar deshabilitado cuando
  no hay contenedor seleccionado.
- `PanelPendientes`: lista, estado vacío y selección.
- `app/mapa/page.tsx`: colocación exitosa, respuesta 409 con recarga, motivo obligatorio al
  desviarse de la sugerencia, y patio sin punto de entrada.

## Decisiones y por qué

**Vista de planta con detalle al hacer clic, en lugar de alzado tipo bay plan.** La planta
da el panorama del patio de un vistazo, que es lo que el operador necesita para decidir
dónde colocar. El alzado sirve para planear estiba, un problema distinto que este spec no
resuelve.

**Agregado por tira en el endpoint del mapa, no ubicación por ubicación.** Reduce la
respuesta de unas 7,200 filas a unas 1,440. El detalle se pide solo de la tira abierta.

**Punto de entrada guardado en el patio, no elegido por el operador.** Refleja la operación
real: el contenedor llega por la portería, y el costo del algoritmo se mide desde ahí. Si
cada operador eligiera su propia referencia, las sugerencias dejarían de ser comparables.

**Seed en lugar de editor de layout.** Un CRUD completo de carriles, tramos, tiras y
ubicaciones es un proyecto aparte. El seed desbloquea esta pantalla hoy.

**Sin actualización en vivo.** El 409 del backend ya evita la colocación doble, que es el
único error que importa. Websockets serían infraestructura nueva para un problema que ya
está cubierto.
