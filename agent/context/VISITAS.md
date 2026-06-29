# VISITAS TECNICAS - {{BUSINESS_NAME}}

## REGLA CRITICA — EJECUCION OBLIGATORIA
NUNCA digas "voy a contactar a Steven/Hector" sin ANTES ejecutar el script con tu herramienta de shell.
El script hace la notificacion automaticamente. Si no ejecutas: la visita NO se registra y nadie se entera.
Ejecutar el script NO es opcional. Es el paso 1, siempre.

## Cuando usar este protocolo
Cliente pide visita tecnica para: medir, instalar o evaluar trabajos en sitio.
**Costo:** $20.000 en Cali (abonables al trabajo) | $50.000 fuera de Cali

---

## DATOS QUE NECESITAS (recopilar en UN solo mensaje si faltan)
- Nombre completo del cliente
- Telefono
- Direccion exacta (barrio + calle o referencia)
- Fecha y hora preferida

Si el cliente ya los dio en su mensaje, NO los vuelvas a pedir. Agenda directamente.

---

## PASO 1 ?" Crear la visita y notificar a Steven

```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"crear\",\"cliente\":\"NOMBRE\",\"telefono\":\"+57XXXXXXXXXX\",\"direccion\":\"DIRECCION\",\"fecha\":\"YYYY-MM-DDTHH:MM\",\"notas\":\"\"}"
```

El script devuelve:
- `id` ?" guardalo, lo necesitas para confirmar/completar
- `mensaje_steven` ?" envialo textual a Steven (+573176616458)

### Mensaje al cliente mientras tanto:
"Perfecto! Estoy verificando disponibilidad con nuestro tecnico, te confirmo en breve."

---

## PASO 2 ?" Steven responde

**SI confirma:** ejecutar accion `confirmar`
**Propone otra hora:** ejecutar `confirmar` con `hora_confirmada`
**NO puede:** avisar al cliente y proponer nueva fecha

```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"confirmar\",\"id\":ID}"
```

Con hora alternativa:
```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"confirmar\",\"id\":ID,\"hora_confirmada\":\"YYYY-MM-DDTHH:MM\"}"
```

El script devuelve `mensaje_cliente` ?" envialo textual al cliente.

---

## PASO 3 ?" Cerrar visita (cuando ya se realizo)

```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"completar\",\"id\":ID,\"notas\":\"Se midio. Cotizacion pendiente.\"}"
```

---

## OTRAS ACCIONES

### Cancelar
```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"cancelar\",\"id\":ID,\"motivo\":\"Cliente cancelo\"}"
```

### Ver proximas visitas (7 dias)
```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"proximas\"}"
```

### Buscar por fecha o estado
```powershell
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas/scripts/registrar_visita.py" "{\"accion\":\"consultar\",\"fecha\":\"2026-05-20\",\"estado\":\"pendiente\"}"
```

---

## REGLAS
- NUNCA confirmar sin verificar con Steven primero
- Guardar siempre el `id` de la visita para actualizarla
- Si cancela el cliente: ejecutar `cancelar` para mantener historial
- Dashboard: file:///C:/Users/USER/clawd/visitas.html

