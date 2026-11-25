# API de socios: solicitud de entrada desde el transportista (Kasu)

Fecha: 2026-11-24 (revisado el mismo día con las respuestas de Tony)
Estado: propuesto, con preguntas abiertas al final
Specs relacionados:
- `BitacoraKasu`: `docs/superpowers/specs/2026-11-24-integracion-patio-esperanza-v2-design.md`
- `Proyecto_HAL9MIL`: `docs/superpowers/specs/2026-11-24-aviso-cruce-avc-y-expediente-design.md`
  y `docs/superpowers/specs/2026-11-24-datos-para-patio-esperanza-design.md`

## Flujo completo

```
HAL9MIL (Loginco)            BitacoraKasu (transporte)            Patio Esperanza
-----------------            -------------------------            ---------------
Expediente DODA + AVC
  -> push por contenedor ->  Modulación
                             Destino = Patio Esperanza
                             Unidad + operador -> ASIGNADO
                               -> POST /api/socios/v1/solicitudes-ingreso   (este spec)
                                                                  Contenedor solicitud_ingreso + PIN
                               <- 201 {id, pin, ...}
                             PIN en el programa de despacho
                             ... extracción, semáforo aduanal ...
                                                                  Portería: PIN, placas y
                                                                  operador esperados -> ingresado
                               <- webhook contenedor.ingresado
  <- evento patio.ingreso   -> EN_PATIO_ESPERANZA
                                                                  ubicado, estancia, servicios
                                                                  despachado
                               <- webhook contenedor.despachado
  <- evento patio.salida
```

Este spec cubre solo el lado de Patio Esperanza: recibir la solicitud, autenticar al socio,
ligar el contenedor a su cliente, avisar de vuelta y corregir dos defectos que hoy impiden
cualquier integración.

## Estado actual (verificado en el código)

1. **No existe API para sistemas externos.** `POST /api/contenedores/solicitar` exige rol
   `cliente` y `POST /api/contenedores` exige staff. Ambos necesitan un JWT de usuario que
   caduca a los 240 minutos (`jwt_expires_minutes`).
2. **Kasu apunta a una ruta que no existe** (`POST /api/v1/contenedores`, con un token fijo).
3. **El alta interna crea contenedores que no pueden entrar.** `POST /api/contenedores` deja
   el contenedor en `solicitud_ingreso` sin PIN y sin `cliente_id`; `verificar-pin` y
   `POST /api/porteria/ingresos` exigen PIN.
4. **Un duplicado responde 500.** Nadie atrapa el `IntegrityError` de `uq_contenedor_activo`.
5. `TipoCliente` tiene `agencia_aduanal`, `importador_exportador`, `transportista` y
   `socio_api`, pero **no `naviera`**.

## Decisiones propuestas

### 1. Credenciales de socio con API key

Tabla nueva `credenciales_socio`: `id`, `nombre`, `cliente_id` (el socio como empresa, tipo
`transportista`), `prefijo` (único, 8 caracteres), `secreto_hash` (bcrypt),
`patios_permitidos` (uuid[]), `webhook_url`, `webhook_secreto`, `activo`, `ultimo_uso_en`.

- Encabezado: `Authorization: ApiKey <prefijo>.<secreto>`.
- Dependencia `get_socio`: busca por prefijo, verifica el hash, exige `activo` y fija en
  cada request los GUC de RLS (`app.rol = 'socio'`,
  `app.patios_asignados = patios_permitidos`). La política RLS existente filtra por patio sin
  cambios.
- Alta y revocación por script de administración (`python -m app.scripts.crear_credencial_socio`).

### 2. El cliente del contenedor

El cliente del patio puede ser el **importador**, la **agencia aduanal** o la **naviera**; lo
decide Kasu por contenedor y lo manda en la solicitud.

- Se agrega `naviera` a `TipoCliente` (migración del enum).
- El contenedor se liga a `Cliente` por **RFC**. Si el RFC no existe, se crea el `Cliente`
  con `razon_social` y `tipo` recibidos, `dias_libres = 0` y una marca
  `alta_por_socio = true`, para que el admin complete días libres y usuarios. No se rechaza
  la solicitud: el contenedor tiene que poder entrar aunque el cliente sea nuevo.
- Se guarda `cliente_id` en el contenedor. Con eso los reportes, los días libres y el portal
  del cliente funcionan igual que con un contenedor pedido desde el portal.

### 3. Endpoint de solicitud de entrada

`POST /api/socios/v1/solicitudes-ingreso`

```json
{
  "idempotency_key": "kasu:modulacion:1234",
  "referencia_externa": "MOD-20261124-007",
  "patio_id": "<uuid>",
  "numero_contenedor": "MSCU1234567",
  "tipo": "lleno",
  "tamano": "40",
  "tipo_iso": "40HC",
  "peso_kg": 18500,
  "sellos": null,
  "cliente": {"tipo": "importador_exportador", "rfc": "IMM210702NL7", "nombre": "Importadora X"},
  "aduana": {"agencia": "LOGINCO", "num_refe": "LCLF0353/26", "num_pedimento": "...",
             "num_doda": "...", "acuse_avc": "AVC5104...", "terminal": "LCTPC"},
  "transporte": {"operador": "Juan Pérez", "telefono": "3311223344",
                 "placas": "12AB3C", "numero_economico": "21"},
  "fecha_estimada_llegada": "2026-11-25T09:00:00-06:00"
}
```

Reglas:

- `numero_contenedor` pasa la validación ISO 6346.
- `sellos` es opcional para el socio; lo captura el guardia en portería.
- `peso_kg` en kilos. Acepta 0 y en ese caso marca `peso_por_confirmar = true`.
- `patio_id` fuera de `patios_permitidos`: 403.
- Crea el contenedor en `solicitud_ingreso` con PIN de 4 dígitos (mismo generador que
  `/solicitar`), `origen = 'socio'`, `cliente_id` (punto 2) y los datos de `aduana` y
  `transporte`.
- Respuesta 201: `{id, estado, pin, patio: {id, nombre}, cliente_id, referencia_externa}`. El
  PIN se devuelve al socio porque Kasu lo publica en su programa de despacho. No se manda
  correo.
- **Idempotencia:** misma `idempotency_key` y mismo socio, 200 con el mismo cuerpo. Número ya
  activo con otra llave, 409 con `{"detail": "...", "contenedor_id": "<uuid>"}`.

Columnas nuevas en `contenedores`: `origen` (`portal`, `interno`, `socio`),
`credencial_socio_id`, `idempotency_key` (único junto con la credencial),
`referencia_externa`, `datos_aduana` jsonb, `transporte_esperado` jsonb,
`peso_por_confirmar`. En `clientes`: `alta_por_socio`.

### 4. Modificar, cancelar y consultar

- `PATCH .../solicitudes-ingreso/{id}`: solo `transporte` y `fecha_estimada_llegada`, solo en
  `solicitud_ingreso`. El PIN no cambia.
- `POST .../solicitudes-ingreso/{id}/cancelar` con `{motivo}`: a `rechazado` solo desde
  `solicitud_ingreso`; si no, 409. Kasu lo usa al cambiar el destino.
- `GET /api/socios/v1/contenedores/{id}`: estado, fechas de ingreso y salida, días de
  estancia. Respaldo si un webhook se pierde.

### 5. Portería muestra el transporte esperado

`GET /api/porteria/buscar` devuelve `transporte_esperado` y la pantalla de ingreso lo
muestra. Si las placas capturadas no coinciden, el ingreso **no se bloquea** (puede haber
cambio de unidad de último momento), pero queda `placas_coinciden = false` en la inspección
y viaja en el evento.

### 6. Eventos de vuelta al socio (webhooks)

Tabla `eventos_socio` como bandeja de salida (outbox): `credencial_socio_id`,
`contenedor_id`, `tipo`, `payload`, `estado`, `intentos`, `siguiente_intento_en`,
`ultimo_error`.

- Se inserta en la **misma transacción** que el cambio de estado.
- `app/scheduler.py` envía los pendientes cada minuto con reintento exponencial (hasta
  24 h).
- Encabezados: `X-Esperanza-Firma: sha256=<hmac>` y `X-Esperanza-Evento-Id`.

| Evento | Cuándo | Datos |
| --- | --- | --- |
| `contenedor.ingresado` | Portería confirma el ingreso | fecha, placas, `placas_coinciden`, sellos, fotos |
| `contenedor.rechazado` | Cancelación o rechazo en portería | motivo |
| `contenedor.despachado` | Sale del patio | fecha, días de estancia |

Kasu reenvía `ingresado` y `despachado` a HAL9MIL para el correo al ejecutivo; Esperanza no
llama a HAL9MIL directamente en esta fase.

### 7. Correcciones independientes de la integración

- `POST /api/contenedores` (alta interna) genera PIN igual que `/solicitar`, o crea directo en
  `en_porteria`. **Pregunta abierta.**
- `IntegrityError` de `uq_contenedor_activo` → 409 "Ese contenedor ya está activo en el patio"
  en todos los endpoints que crean contenedores.

## Fuera de alcance

- Pantalla de administración de credenciales de socio.
- Solicitud de salida por API (el cliente la pide en el portal).
- Webhooks directos a HAL9MIL.

## Pruebas

- Llave válida crea la solicitud con PIN; revocada, 401; patio no permitido, 403.
- RFC existente liga al `Cliente`; RFC nuevo crea uno con `alta_por_socio`; tipo `naviera`
  aceptado.
- Misma `idempotency_key` dos veces: 201 y 200 con el mismo PIN, un solo contenedor.
- Número activo con otra llave: 409 con `contenedor_id`.
- `peso_kg = 0` marca `peso_por_confirmar`.
- PATCH y cancelar fuera de `solicitud_ingreso`: 409.
- El ingreso en portería inserta `contenedor.ingresado` en la misma transacción; si falla, no
  hay evento. La salida inserta `contenedor.despachado` con días de estancia.
- Los webhooks se firman bien, se reintentan ante 5xx y no ante 2xx.
- RLS: un socio no ve contenedores fuera de `patios_permitidos`.

## Preguntas abiertas

- [ ] ¿Un solo patio para Kasu o Kasu elige entre varios?
- [ ] Alta interna sin PIN: ¿generar PIN o crear directo en portería?
- [ ] Clientes creados por el socio: ¿quedan activos de inmediato (la propuesta) o en espera
  de que el admin los apruebe?
- [ ] ¿Cuántos días libres tiene por omisión un cliente nuevo: 0, o un valor por tipo
  (naviera, agencia, importador)?
