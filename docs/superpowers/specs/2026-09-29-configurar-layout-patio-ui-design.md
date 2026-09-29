# Configurar layout de patio desde el UI

Fecha: 2026-09-29
Estado: implementado

## Problema

Cargar el layout de un patio (carriles, tramos, tiras, niveles) solo se puede hoy
ejecutando `backend/scripts/seed_patio_layout.py` a mano en el servidor. Un administrador
que quiera dar de alta un patio nuevo, o agregar más carriles a uno existente, depende de
que alguien con acceso a shell y `DATABASE_URL` corra el script por él.

`/patios` ya es la pantalla de administración de patios (crear patio, editar anticipación
mínima). Le falta la acción de definir su layout.

## Alcance

Entra en este spec:

- Endpoint que siembra layout uniforme (mismo número de tramos/tiras/niveles en todo el
  patio) para un patio existente.
- Botón "Configurar layout" por fila en `/patios`, solo visible para admin.
- Servicio compartido entre el endpoint nuevo y `seed_patio_layout.py`, para no duplicar la
  lógica de siembra ni las reglas de idempotencia.

Queda fuera:

- Modo config variable (JSON con tramos/tiras/niveles distintos por carril). Ya existe vía
  `seed_patio_layout.py --config` y no se toca.
- Editar o borrar carriles, tramos o tiras existentes.
- Asignar `tipo_teorico` desde este formulario. Ya existe `set_tipo_teorico.py` aparte.
- Fijar `ubicacion_entrada_id` desde el UI. Sigue siendo `--entrada` en el script.
- Vista del layout actual del patio (conteos, árbol). `/mapa` ya cubre esa necesidad.

## Modelo de datos existente

Sin cambios de esquema. La jerarquía ya vive en `backend/app/models/ubicacion.py`:

```
Patio
  Carril  (patio_id, codigo unico por patio, orden, tipo_teorico)
    Tramo  (carril_id, codigo unico por carril, orden)
      Tira  (tramo_id, codigo unico por tramo, orden)
        Ubicacion  (tira_id, nivel 1 a 5 unico por tira, codigo, capacidad_peso_kg, activo)
```

## Diseño

### Servicio compartido

Archivo nuevo `backend/app/services/patio_layout.py`, con una función:

```python
async def sembrar_layout_uniforme(
    db: AsyncSession, patio: Patio, carriles: int, tramos: int, tiras: int, niveles: int
) -> tuple[int, int, int]:
    ...  # devuelve (carriles_creados, carriles_saltados, ubicaciones_creadas)
```

Es el cuerpo actual de `_sembrar_uniforme` en `seed_patio_layout.py`, sin cambios de
comportamiento: genera códigos `A{n:02d}`, `T{n:02d}`, `R{n:02d}`, `N{n}`; si un carril con
el código que le toca ya existe, lo salta completo (no le agrega tramos nuevos). No hace
`commit`, igual que hoy: quien llama decide cuándo.

`seed_patio_layout.py` pasa a importar y llamar esta función en vez de tener la lógica
inline. El modo `--config` no cambia.

### Endpoint

| Método | Ruta | Rol |
| --- | --- | --- |
| POST | `/api/patios/{patio_id}/layout` | `admin` |

Payload (`LayoutPatioCreate` en `backend/app/schemas/patio.py`):

```python
class LayoutPatioCreate(BaseModel):
    carriles: int = Field(gt=0)
    tramos: int = Field(gt=0)
    tiras: int = Field(gt=0)
    niveles: int = Field(ge=1, le=5)
```

Respuesta (`LayoutPatioOut`):

```json
{
  "carriles_creados": 4,
  "carriles_saltados": 7,
  "ubicaciones_creadas": 240
}
```

`404` si `patio_id` no existe, igual patrón que `mapa_patio` en
`backend/app/api/routes/patios.py`. La ruta llama al servicio, hace `commit`, y registra
auditoría con `registrar_auditoria` (`entidad="patios"`, `accion="configurar_layout"`,
`valor_nuevo` con los tres contadores) — mismo patrón que `crear_patio` y
`actualizar_patio`.

### Frontend

`frontend/app/patios/page.tsx`:

- Columna nueva de acciones en `DataTable`, visible solo si `esAdmin`: botón "Configurar
  layout" por fila.
- Al hacer clic, la fila expande un formulario inline (estado `patioLayoutAbierto: string |
  null` con el id del patio expandido) con cuatro `Field` numéricos: Carriles, Tramos,
  Tiras, Niveles (`min={1}`, Niveles con `max={5}`).
- Botón "Aplicar" llama `configurarLayoutPatio(token, patioId, payload)`.
- Resultado exitoso se muestra como `Alert` tono éxito dentro de la fila expandida:
  "Se crearon {ubicaciones_creadas} ubicaciones en {carriles_creados} carriles nuevos.
  {carriles_saltados} carriles ya existían y se omitieron." Si `carriles_creados` es 0, el
  mensaje deja claro que no se creó nada nuevo.
- Error usa el mismo patrón que el resto de la página: `ApiError` capturado, mensaje en
  `Alert` tono error.
- `frontend/lib/api.ts` gana `configurarLayoutPatio(token, patioId, payload):
  Promise<LayoutPatioResult>` y el tipo `LayoutPatioResult`.

## Pruebas

Backend:

- `sembrar_layout_uniforme` crea la jerarquía completa (carril, tramos, tiras, niveles) y
  devuelve los tres contadores correctos.
- Llamado dos veces con los mismos parámetros: la segunda vez `carriles_creados` es 0 y
  `carriles_saltados` es igual al número de carriles.
- Llamado con `carriles` mayor que la vez anterior: solo los carriles nuevos se crean, los
  existentes se saltan sin tocar sus tramos.
- El endpoint responde 404 con `patio_id` inexistente.
- El endpoint responde 403 a roles distintos de `admin`.
- El endpoint valida `niveles` fuera de 1..5 con 422.
- `seed_patio_layout.py --carriles/--tramos/--tiras` sigue produciendo el mismo resultado
  que antes de la extracción (test de regresión existente, si lo hay, o prueba manual).

Frontend:

- Botón "Configurar layout" no aparece para rol no admin.
- Envío exitoso muestra el mensaje con los tres contadores.
- Envío con error de API muestra `Alert` de error.
- Validación de campos: no permite enviar con algún campo vacío o menor a 1, ni niveles
  fuera de 1..5.

## Decisiones y por qué

**Solo modo uniforme en el UI.** El modo variable por JSON ya tiene su herramienta
(`--config`) para el caso poco común de un patio con tramos/tiras/niveles distintos por
carril. Construir ese formulario en el UI es trabajo considerable para un caso que hoy se
resuelve editando un archivo. Si se necesita más adelante, es un spec aparte.

**Servicio compartido en vez de duplicar la función en la ruta.** El endpoint y el script
necesitan exactamente la misma lógica de idempotencia. Duplicarla es la forma más fácil de
que un día diverjan y un carril se cree distinto según por dónde se sembró.

**Acción por fila en la tabla existente, no pantalla aparte.** El patio ya está listado en
`/patios`; agregar una ruta nueva solo para este formulario de cuatro campos es más
navegación de la que el caso amerita.

**Sin vista del layout actual antes de configurar.** `/mapa` ya muestra la ocupación real
del patio con su jerarquía completa. Repetir un resumen aquí duplicaría esa pantalla para
un caso de uso (¿cuántos carriles tengo ya?) que el admin puede resolver abriendo el mapa.
