# BASE DE CLIENTES - {{BUSINESS_NAME}}

## Cuándo usar

- Alguien pregunta por un cliente ("¿qué le vendimos a Carlos?", "¿tiene historial fulano?")
- Se completa una cotización → guardar cliente automáticamente
- Cliente confirma un pedido → actualizar estado a "en_fabricacion"
- Pedido listo en taller → actualizar estado a "listo"
- Se entrega el pedido → actualizar estado a "entregado"
- Se recibe imagen o PDF de una factura → extraer datos del cliente y guardar
- Alguien pide la lista de clientes del negocio

## Cómo ejecutar

```powershell
$json = @'
{"action": "...", ...}
'@
[System.IO.File]::WriteAllText("$env:TEMP\cliente_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/base-clientes/scripts/base_clientes.py" "$env:TEMP\cliente_input.json"
```

---

## Estados de pedido

| Estado | Significado |
|---|---|
| `cotizado` | Se envió cotización, sin confirmar |
| `en_fabricacion` | Pedido confirmado, en producción |
| `listo` | Terminado, listo para entregar |
| `entregado` | Entregado al cliente |

---

## Acciones disponibles

### `guardar` — Crear o actualizar cliente

```json
{
  "action": "guardar",
  "nombre": "CARLOS RAMIREZ",
  "telefono": "+573001234567",
  "direccion": "Calle 15 # 8-23, Cali",
  "cedula_nit": "12345678",
  "notas": "Prefiere vidrio templado 6mm, paga en efectivo",
  "pedido": {
    "descripcion": "Espejo biselado 0.80x1.20m x2",
    "total": 450000,
    "estado": "cotizado",
    "fecha_entrega_est": "2026-05-20"
  }
}
```

- Si ya existe (mismo teléfono o nombre similar) → **actualiza** la ficha
- Si es nuevo → **crea** una ficha
- El campo `pedido` es OPCIONAL — solo incluirlo cuando hay pedido concreto
- El pedido recibe un `id` UUID automático para poder referenciarlo luego

### `actualizar_orden` — Cambiar estado de un pedido

```json
{
  "action": "actualizar_orden",
  "telefono": "+573001234567",
  "pedido_desc": "espejo biselado",
  "estado": "listo"
}
```

Identificar el pedido con UNO de estos campos:
- `pedido_id` — UUID exacto del pedido (más preciso)
- `pedido_desc` — descripción parcial (búsqueda fuzzy)
- `pedido_idx` — número de posición en la lista (0 = más reciente)

Si el cliente solo tiene **un pedido**, no hace falta especificar cuál.

Cuando `estado` es `"entregado"`, se registra automáticamente `fecha_entrega_real`.
Podés pasarla manualmente: `"fecha_entrega": "2026-05-15"`.

### `buscar` — Buscar un cliente

```json
{"action": "buscar", "telefono": "+573001234567"}
```
```json
{"action": "buscar", "nombre": "carlos ramirez"}
```

Retorna datos del cliente + último pedido.

### `historial` — Historial completo de pedidos

```json
{"action": "historial", "nombre": "carlos ramirez"}
```

Retorna todos los pedidos, valor histórico total, fecha desde que es cliente.

### `listar` — Listar todos los clientes

```json
{"action": "listar"}
```

Retorna lista ordenada por último contacto.

---

## Flujo completo: Cotización → Entrega

1. Calculá el precio con `calculate_quote.py`
2. **Guardá el cliente** con `guardar` + `pedido` con `estado: "cotizado"`
3. Cliente confirma → `actualizar_orden` con `estado: "en_fabricacion"`
4. Sale del taller → `actualizar_orden` con `estado: "listo"`
5. Se entrega → `actualizar_orden` con `estado: "entregado"`

## Flujo: Factura PDF → Guardar cliente

1. Leé el archivo con `read_media.py` → obtenés texto con nombre, teléfono, dirección
2. Extraé esos datos y guardá con `action: "guardar"`

## Datos importantes a guardar

- `nombre`: nombre completo
- `telefono`: número de WhatsApp (identificador principal)
- `direccion`: dirección de entrega o instalación
- `cedula_nit`: cédula o NIT (para facturas formales)
- `notas`: preferencias, zona, forma de pago habitual
