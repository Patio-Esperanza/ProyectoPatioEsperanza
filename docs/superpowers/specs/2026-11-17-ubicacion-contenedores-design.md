# Ubicación de contenedores: buscador, selectores y mapa del patio

Fecha: 2026-11-17
Estado: propuesto; debe conciliarse con `2026-09-22-mapa-patio-design.md` antes del plan
Versión editable: https://claude.ai/artifact/QD5xfvVXFiM7EBz2Cu3Ngb

## Relación con el spec del mapa (2026-09-22)

Este spec se escribió sin conocer `2026-09-22-mapa-patio-design.md`. Ese spec ya cubre
parte de lo que aquí se propone. La regla para el plan: **reusar lo que ya existe y agregar
solo lo nuevo**.

| Pieza | Estado | Qué hacer |
| --- | --- | --- |
| `GET /api/patios/{id}/mapa` agregado por tira | Ya existe | Extender la respuesta con los valores de los modos de color (cliente dominante, días máximos, lleno/vacío, servicio pendiente) |
| Detalle de tira | Ya existe como `GET /api/tiras/{id}` | Usarlo; no crear `/api/tiras/{id}/posiciones`. Agregar `remanejos` y días en patio por nivel |
| Pantalla `/mapa` con CSS grid, panel de pendientes y colocación | Ya existe | Mantener CSS grid (no SVG). Agregar el selector de modo de color y el botón **Reubicar** en el detalle |
| Códigos `A01-T04-R02-N1` | Ya existen | Usarlos como etiqueta corta en lugar de `B-03-2-1` |
| Filtro `sin_ubicacion` en contenedores | Ya existe | Es la base de la lista **Por ubicar** del operador de grúa |
| Buscador global, `ContenedorPicker`, `UbicacionPicker` | Nuevo | Como se describe abajo |
| Reglas de estiba y remanejos | Nuevo | Como se describe abajo |
| `POST /api/contenedores/{id}/reubicar` | Nuevo | Como se describe abajo |
| Roles | Conciliar | El mapa usa `operador`, `supervisor`, `admin`. Decidir si `operador_grua` es nuevo o es `operador` |

## Resumen

Encontrar un contenedor debe tomar un solo paso, y ubicarlo o reubicarlo nunca debe pedir
un UUID. Este spec agrega un buscador global, dos selectores reutilizables, modos de color
en el mapa y el conteo de remanejos. Corresponde a la Fase 2 de
`2026-11-17-mejoras-operativas-patio-design.md`.

| Meta | Cómo se mide |
| --- | --- |
| Ubicar un contenedor por número | Con 4 caracteres el buscador muestra carril, tramo, tira y nivel |
| Cero UUID en formularios | Ningún campo de texto libre recibe `contenedor_id` ni `ubicacion_id` |
| Ver la ocupación del patio | El mapa carga un patio completo en menos de 1 s |
| Despachar con menos remanejos | La cola de salidas muestra cuántos contenedores hay encima de cada uno |

## Modelo y reglas de estiba

No hace falta ninguna tabla nueva. Se agregan una etiqueta legible, un límite de altura por
tira y tres reglas que el backend valida en cada ubicación o reubicación.

### Etiqueta legible

Función única `etiqueta_ubicacion(ubicacion)` en `app/core/ubicaciones.py` con dos formas:

- Corta, para tablas y la grúa: el código existente, por ejemplo `A01-T04-R02-N1`.
- Larga, para tarjetas y correos: "Carril A01 · Tramo T04 · Tira R02 · Nivel 1".

Todas las respuestas de la API que incluyen una ubicación traen `ubicacion_etiqueta` junto
al id. El frontend nunca arma la etiqueta.

### Cambios de datos

- `tiras.max_niveles` (entero, por defecto el mayor nivel existente en la tira).
- Índice sobre la columna de número de contenedor con `text_pattern_ops`, para que la
  búsqueda por prefijo use el índice.

### Reglas al ubicar o reubicar

1. **Sin contenedores flotantes**: solo se puede ocupar el nivel n si el nivel n−1 de la
   misma tira está ocupado.
2. **Altura máxima**: el nivel no puede pasar de `tiras.max_niveles`.
3. **No sacar de abajo**: solo se reubica o despacha el contenedor de arriba de su tira. Si
   hay contenedores encima, la API responde 409 con la lista de los que hay que mover primero.

Estas reglas se suman al locking de slot actual de `POST /api/movimientos`, dentro de la
misma transacción.

### Remanejos

`remanejos` = cuántos contenedores hay en la misma tira en un nivel mayor. Se calcula en la
consulta, no se guarda, y aparece en el detalle del contenedor, en el buscador, en el
detalle de tira y en la cola de salidas.

## API

| Método | Ruta | Respuesta | Roles |
| --- | --- | --- | --- |
| GET | `/api/buscar?q=&patio_id=` | Hasta 10 contenedores cuyo número empieza o contiene `q` (mínimo 4 caracteres): número, cliente, estado, `ubicacion_etiqueta`, días en patio, remanejos | Internos; cliente solo los suyos |
| GET | `/api/patios/{id}/arbol` | Carriles → tramos → tiras con ocupados y capacidad por tira, para el selector en cascada (puede reutilizar la consulta de `obtener_mapa`) | Internos |
| GET | `/api/patios/{id}/mapa?modo=` | Extensión del endpoint existente: agrega el valor del modo por tira | Internos |
| POST | `/api/contenedores/{id}/reubicar` | Body `{ubicacion_destino_id, motivo}`. Aplica las reglas de estiba, crea el movimiento de reubicación y devuelve el contenedor con su nueva etiqueta | Admin, operador de grúa |

`POST /api/ubicaciones/sugerir` se mantiene. El selector de ubicación lo llama para poner
las sugeridas al principio.

## Pantallas

### Buscador global

- Vive en la barra superior del `AppShell`. En escritorio se abre con Ctrl+K; en móvil es
  un botón de lupa que abre la búsqueda a pantalla completa.
- Acepta el número con o sin espacios y en minúsculas. Muestra resultados desde el cuarto carácter.
- Cada resultado es una tarjeta: número, cliente, estado, etiqueta de ubicación, días en
  patio y remanejos. Al tocarla abre el detalle con el botón **Ver en mapa** (`/mapa?patio=…`
  con la tira seleccionada).

### Selectores

- `ContenedorPicker`: combobox con la misma búsqueda. Acepta un filtro de estados (por
  ejemplo, solo `en_porteria_salida` en la pantalla de salida).
- `UbicacionPicker`: primero muestra las 3 sugerencias del algoritmo; después, la cascada
  carril → tramo → tira → nivel, con solo las posiciones que cumplen las reglas de estiba.
- Reemplazan los campos de UUID en `/movimientos`, `/ubicaciones/sugerir` y en las
  pantallas de portería de la Fase 1.

### Mapa del patio (`/mapa`, extensión)

- **Modos de color**: cliente (un color por cliente, con leyenda), días en patio (más tono,
  más días), lleno o vacío, y servicio pendiente. La celda sigue imprimiendo `3/5`, así el
  color nunca es la única señal.
- **Detalle de tira**: muestra por nivel número, cliente, días y remanejos, y un botón
  **Reubicar** que abre `UbicacionPicker`. En móvil se abre como hoja desde abajo.
- Sigue sin arrastrar y soltar.

## Pruebas (TDD)

**Backend**

- Ubicar en nivel 2 con el nivel 1 vacío: 409 "posición flotante".
- Ubicar por encima de `max_niveles`: 409.
- Reubicar un contenedor con dos encima: 409 con los dos números en la respuesta.
- `remanejos` correcto para niveles 1, 2 y el de arriba.
- `/api/buscar` con 3 caracteres: 422. Con minúsculas y espacios: encuentra el contenedor.
- Un cliente busca un número de otro cliente: lista vacía.
- `/api/patios/{id}/mapa?modo=dias` de un patio no asignado: 404.

**Frontend**

- `UbicacionPicker` muestra primero las sugerencias y no ofrece posiciones flotantes.
- `ContenedorPicker` respeta el filtro de estados.
- El mapa cambia de modo de color sin perder la tira seleccionada.

## Fuera de alcance

Arrastrar y soltar en el mapa, vista 3D, geocercas, actualización en tiempo real por
WebSocket y lectura de números por cámara.

## Decisiones tomadas (17 nov 2026)

- El operador de grúa confirma ubicaciones y reubica.

## Preguntas abiertas

- [ ] ¿Un contenedor de 40 pies ocupa una tira o dos? Si ocupa dos, el modelo de posiciones necesita cambiar.
- [ ] ¿Cuál es la altura máxima real por tira, y cambia entre llenos y vacíos?
- [ ] ¿`operador_grua` es un rol nuevo o el `operador` que ya existe?
