---
name: visitas-tecnicas
description: Agenda, confirma y gestiona visitas tecnicas de {{BUSINESS_NAME}}. Notifica a Steven, genera links de Google Maps y Calendar. Consulta proximas visitas y estado del calendario tecnico.
---

# Visitas Tecnicas {{BUSINESS_NAME}}

## REGLA CRITICA — EJECUCION OBLIGATORIA
NUNCA digas "voy a contactar a Steven" o "le voy a avisar al equipo" sin EJECUTAR el script primero.
Debes correr el comando PowerShell con tu herramienta de shell. El script hace la notificacion automaticamente.
Si no ejecutas el script, la visita NO queda registrada y nadie se entera.

---

## Cuando usar
- Cliente pide visita tecnica para medicion o instalacion
- Necesitas ver el calendario de Steven
- Confirmar o cancelar una visita existente
- Ver proximas visitas de la semana

---

## CREAR visita (EJECUTAR para notificar a Steven)

```powershell
$json = @'
{
  "accion": "crear",
  "cliente": "NOMBRE CLIENTE",
  "telefono": "+57XXXXXXXXXX",
  "direccion": "Calle 15 # 8-23, barrio San Fernando, Cali",
  "fecha": "2026-05-20T15:00:00",
  "notas": "Quiere cabina de bano templado"
}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

**Output:** JSON con `id` (guardalo), `mensaje_steven` (envialo a Steven +573176616458), `maps` (link Google Maps).
**Despues de ejecutar:** envia el `mensaje_steven` a Steven. Al cliente dile: "Estoy verificando disponibilidad con nuestro tecnico, te confirmo en breve."

---

## CONFIRMAR visita (despues de que Steven dice SI)

```powershell
$json = @'
{"accion": "confirmar", "id": ID_VISITA}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

Si Steven propone hora diferente:
```powershell
$json = @'
{"accion": "confirmar", "id": ID_VISITA, "hora_confirmada": "2026-05-20T17:00:00"}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

**Output:** JSON con `mensaje_cliente` (envialo textual al cliente).

---

## COMPLETAR visita

```powershell
$json = @'
{"accion": "completar", "id": ID_VISITA, "notas": "Se realizo la visita."}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

---

## CANCELAR visita

```powershell
$json = @'
{"accion": "cancelar", "id": ID_VISITA, "motivo": "Cliente cancelo"}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

---

## VER proximas visitas (7 dias)

```powershell
$json = @'
{"accion": "proximas", "dias": 7}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

---

## CONSULTAR por fecha o estado

```powershell
$json = @'
{"accion": "consultar", "estado": "pendiente"}
'@
[System.IO.File]::WriteAllText("$env:TEMP\visita_input.json", $json, [System.Text.Encoding]::UTF8)
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "$env:TEMP\visita_input.json"
```

---

## Flujo completo
1. Cliente pide visita -> EJECUTAR `crear` -> enviar `mensaje_steven` a Steven
2. Steven confirma -> EJECUTAR `confirmar` -> enviar `mensaje_cliente` al cliente
3. Visita realizada -> EJECUTAR `completar`

Protocolo completo: ver VISITAS.md
