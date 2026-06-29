---
name: registrador-cuentas
description: Registra ingresos y gastos en cuentas diarias de {{BUSINESS_NAME}}. Consulta historial, rangos de fechas y resumen mensual. Los registros aparecen en cuentas.html con badge {{AGENT_NAME}}.
---

# Registrador de Cuentas y Base de Clientes — {{BUSINESS_NAME}}

## Cuándo usar

**Cuentas** — usar cuando:
- Un cliente confirma un pago, abono o anticipo
- Héctor informa que recibió un pago
- Héctor registra un gasto del negocio
- Alguien pregunta cuánto se recibió hoy / esta semana / este mes
- Alguien pide el balance del día o del mes

**Clientes** — usar cuando:
- Alguien pregunta por un cliente ("¿qué le hemos vendido a fulano?")
- Se completa una cotización → guardar cliente automáticamente
- Se confirma una venta → actualizar estado del pedido
- Alguien pide la lista de clientes

---

## CUENTAS — registrar_cuenta.py

### Cómo ejecutar

```powershell
$json = @'
{"accion": "...", ...}
'@
[System.IO.File]::WriteAllText("$env:TEMP\cuenta_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs-manager/scripts/registrar_cuenta.py" "$env:TEMP\cuenta_input.json"
```

### Acciones de cuentas

#### `registrar` — Registrar un ingreso o gasto

```json
{
  "accion": "registrar",
  "fecha": "hoy",
  "tipo": "ingreso",
  "descripcion": "Abono Carlos Ramírez - ventana cocina",
  "valor": 200000
}
```

- `tipo`: `"ingreso"` / `"abono"` / `"pago"` → registra como ingreso
- `tipo`: `"gasto"` / `"egreso"` / `"pago_proveedor"` → registra como gasto
- `fecha`: `"hoy"` o `"YYYY-MM-DD"`

#### `consultar` — Ver el día actual o un día específico

```json
{"accion": "consultar", "fecha": "hoy"}
```

#### `consultar_rango` — Ver un rango de fechas

```json
{
  "accion": "consultar_rango",
  "fecha_inicio": "2026-05-01",
  "fecha_fin": "2026-05-11"
}
```

#### `listar_todo` — Ver todo el historial registrado por {{AGENT_NAME}}

```json
{"accion": "listar_todo"}
```

#### `resumen_mes` — Resumen del mes actual (o un mes específico)

```json
{"accion": "resumen_mes"}
```

o para un mes específico:

```json
{"accion": "resumen_mes", "mes": 4, "anio": 2026}
```

---

## CLIENTES — base_clientes.py

### Cómo ejecutar

```powershell
$json = @'
{"action": "...", ...}
'@
[System.IO.File]::WriteAllText("$env:TEMP\cliente_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/base-clientes/scripts/base_clientes.py" "$env:TEMP\cliente_input.json"
```

### Acciones de clientes

#### `guardar` — Crear o actualizar cliente

```json
{
  "action": "guardar",
  "nombre": "CARLOS RAMÍREZ",
  "telefono": "+573001234567",
  "direccion": "Calle 15 # 8-23, Cali",
  "notas": "Prefiere vidrio templado, paga en efectivo",
  "pedido": {
    "tipo": "cotizacion",
    "total": 450000,
    "estado": "cotizado"
  }
}
```

Si el cliente ya existe (mismo teléfono) → ACTUALIZA. Si no → CREA.
El campo `pedido` es opcional.
Estados posibles: `"cotizado"`, `"confirmado"`, `"entregado"`, `"pendiente_pago"`

#### `buscar` — Buscar por teléfono o nombre

```json
{"action": "buscar", "telefono": "+573001234567"}
{"action": "buscar", "nombre": "carlos ramirez"}
```

#### `historial` — Ver historial de pedidos de un cliente

```json
{"action": "historial", "nombre": "carlos ramirez"}
```

#### `listar` — Ver todos los clientes

```json
{"action": "listar"}
```

---

## BÚSQUEDA DE FACTURAS — buscar_doc.py

Busca físicamente las cotizaciones y facturas guardadas por nombre de cliente.

```powershell
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs-manager/scripts/buscar_doc.py" "nombre cliente"
```

---

## Flujo completo: cotización → cliente → cuenta

1. Cotizar con `calculate_quote.py`
2. Guardar cliente con `base_clientes.py` (`action: "guardar"`, `estado: "cotizado"`)
3. Cuando el cliente pague → `registrar_cuenta.py` (`accion: "registrar"`, `tipo: "ingreso"`)
4. Cuando se entregue → `base_clientes.py` (`action: "guardar"`, `estado: "entregado"`)
