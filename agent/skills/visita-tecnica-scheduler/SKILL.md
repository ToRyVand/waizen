---
name: visita-tecnica-scheduler
description: Agenda visitas técnicas de {{BUSINESS_NAME}}. Crea una ficha estructurada con toda la info del cliente, genera link de Google Maps y link para agregar el evento a Google Calendar. Notifica a Héctor por WhatsApp. Usar cuando el cliente solicite o acepte una visita técnica.
---

# Agendador de Visitas Técnicas

## Cuándo usar esta skill

Usar cuando el cliente:
- Pregunta por una visita técnica o inspección
- Acepta el costo de la visita y quiere agendarla
- Pide que alguien vaya a medir o revisar el trabajo

## Datos a recopilar (en orden, uno por uno)

1. **Dirección completa** — calle, número, barrio, referencia (ej: "frente a la panadería")
2. **Motivo de la visita** — qué quiere hacer/revisar (ej: "cambio de ventana", "medir para cabina ducha")
3. **Fecha sugerida** — dd/mm/yyyy
4. **Hora aproximada** — mañana (8:30–12:00) o tarde (2:00–5:00)
5. **Zona** — Cali (costo $20.000) o municipio —Jamundí/Yumbo/Palmira— (costo $50.000)

El nombre y teléfono ya los tenés del chat o de `memory/clientes/[numero].md`.

## Verificar disponibilidad antes de confirmar

Antes de crear, verificar si ya hay visitas ese día. Escribir un archivo JSON temporal y ejecutar:

```powershell
[System.IO.File]::WriteAllText("$env:TEMP\visit_input.json", '{"action":"list"}', [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visita-tecnica-scheduler/scripts/schedule_visit.py" "$env:TEMP\visit_input.json"
```

⚠️ Usar SIEMPRE `[System.IO.File]::WriteAllText(...)` para escribir el JSON de entrada. NO usar `Out-File -Encoding utf8NoBOM` — esta caja corre PowerShell 5.1 y ese encoding NO existe ahí (falla y el script re-lee input viejo).

Si hay 2 o más visitas el mismo día, sugerirle al cliente otra fecha.

## Crear la visita — Comando

**Paso 1:** Escribir el JSON al archivo temporal (esto preserva todos los caracteres especiales):

```powershell
$json = @'
{
  "action": "create",
  "tipo": "visita",
  "client_name": "Carlos Ruiz",
  "phone": "+573164239059",
  "address": "Calle 30N #6A-22, Barrio Versalles, Cali",
  "reason": "Medir para cabina de baño en vidrio templado 8mm",
  "date": "2026-05-15",
  "time": "10:00",
  "duration_hours": 1,
  "zone": "cali",
  "technician": "Por confirmar",
  "notes": "Piso 3, tocar intercomunicador"
}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visit_input.json", $json, [System.Text.Encoding]::UTF8)
```

**`tipo`**: `"visita"` (toma de medidas / inspección, cobra costo de visita) o `"instalacion"` (instalar el trabajo en lo del cliente, sin cobro de visita). Ambas aparecen como card en `visitas.html` con su badge.

**Paso 2:** Ejecutar el script pasando la ruta del archivo:

```powershell
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visita-tecnica-scheduler/scripts/schedule_visit.py" "$env:TEMP\visit_input.json"
```

Campos del JSON:
- `date`: formato YYYY-MM-DD
- `time`: formato HH:MM (24h)
- `zone`: `"cali"` o `"municipio"`
- `technician`: nombre si ya está asignado, o `"Por confirmar"`
- `notes`: cualquier detalle extra del acceso o del trabajo

## Output del script

Además de la ficha `.md`, la skill crea automáticamente la **card en el dashboard de Visitas Técnicas** (`visitas-data.json` → `visitas.html`), con `tipo: "visita"`, `estado: "pendiente"`. El `card_id` del output es el id de esa card.

```json
{
  "status": "created",
  "filename": "Carlos_Ruiz_2026-05-15.md",
  "card_id": 11,
  "client_name": "Carlos Ruiz",
  "date": "Jueves 15 de mayo de 2026",
  "time": "10:00 AM – 11:00 AM",
  "address": "Calle 30N #6A-22, Barrio Versalles, Cali",
  "maps_url": "https://www.google.com/maps/search/?api=1&query=...",
  "calendar_url": "https://calendar.google.com/calendar/render?...",
  "cost": "$20.000 COP (abonables al trabajo final)",
  "technician": "Por confirmar",
  "conflicts": []
}
```

Si `conflicts` no está vacío → notificar a Héctor para coordinar horarios.

## Mensajes a enviar después de crear la visita

### 1. Al cliente (WhatsApp):
```
Listo! Tu visita técnica quedó agendada 📅

📍 Dirección: [address]
📆 Fecha: [date]
⏰ Hora: [time]
🔧 Motivo: [reason]
💰 Costo: [cost]

Nuestro técnico llegará en ese horario. Cualquier cambio te avisamos con anticipación.
```

### 2. A Héctor (+573134003693) — siempre notificar:
```
Nueva visita técnica agendada 🔧

Cliente: [client_name] — [phone]
📍 [address]
📆 [date] a las [time]
Motivo: [reason]

📍 Maps: [maps_url]
📅 Calendar: [calendar_url]
```

## Reglas

- La visita NO está confirmada por el equipo — decirle al cliente "agendada", no "confirmada"
- SIEMPRE notificar a Héctor después de crear la visita
- El costo se abona al trabajo final — mencionarlo al cliente
- No agendar fuera de horario laboral (L-V 8:30–17:30, S 8:30–13:00)
- Si piden fuera de horario → ofrecer el próximo día hábil disponible
- Si el cliente ya tiene un archivo en `memory/clientes/[numero].md`, actualizar con la fecha de visita agendada
