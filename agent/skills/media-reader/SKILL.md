---
name: media-reader
description: Lee y analiza CUALQUIER archivo adjunto enviado por un cliente de WhatsApp (imágenes, PDFs, planos, listas). Extrae medidas, productos, cantidades y contexto. USAR SIEMPRE cuando aparezca [media attached: ...] en el chat, ANTES de responder.
---

# Media Reader — Lector Universal de Archivos

## REGLA CRÍTICA — ACTIVACIÓN AUTOMÁTICA

**Cada vez que el mensaje del cliente contenga `[media attached: ruta\archivo]`, ejecutá este script INMEDIATAMENTE antes de responder.**

No preguntes si querés que lo lea. No respondas sin leerlo primero. Léelo siempre.

## Comando

```
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/media-reader/scripts/read_media.py" "ruta_completa_del_archivo"
```

La ruta viene en el mensaje exactamente así:
```
[media attached: /home/ubuntu/.openclaw/media/inbound/uuid.jpg]
```

Extraé la ruta entre los corchetes y pasásela al script.

## Archivos soportados

| Extensión | Qué hace |
|---|---|
| `.jpg`, `.jpeg`, `.png`, `.webp` | Analiza la imagen con visión IA |
| `.pdf` | Extrae texto, tablas, medidas |
| `.gif` | Analiza contenido visual |
| `.ogg`, `.mp3` | No soportado (el audio ya lo transcribe Clawdbot) |
| `.xlsx`, `.xls`, `.doc` | No soportado — leer directamente con la herramienta `read` |

## Output del script

```json
{
  "tipo": "lista_items",
  "tiene_medidas": true,
  "items": [
    { "producto": "espejo", "ancho_m": 0.80, "alto_m": 1.20, "cantidad": 2, "notas": "" },
    { "producto": "vidrio 6mm incoloro", "ancho_m": 1.50, "alto_m": 2.10, "cantidad": 4, "notas": "para ventanas" }
  ],
  "texto_extraido": "...",
  "contexto": "Cliente necesita espejos para baño y vidrios para ventanas",
  "observaciones": "Medidas en centímetros en el documento, convertidas a metros"
}
```

## Qué hacer con el output

### Si tiene_medidas = true
1. Confirmá con el cliente las medidas extraídas (UNA sola pregunta si algo no está claro)
2. Si están bien → pedí datos del cliente y corré el cotizador automático
3. No preguntes por medidas que ya extrajiste del archivo

### Si tiene_medidas = false pero tiene texto_extraido
1. Usá el texto como contexto para entender qué necesita el cliente
2. Respondé naturalmente sin mencionar que leíste un archivo

### Si tipo = "cotizacion_externa"
1. Usá el texto para entender el pedido
2. Cotizá los mismos ítems con precios {{BUSINESS_NAME}}

### Si tipo = "no_soportado"
1. No menciones el error técnico
2. Preguntale al cliente qué necesita directamente

## Reglas

- NUNCA le digas al cliente "leí tu archivo" o "analicé tu imagen" — simplemente usá la info
- NUNCA inventes medidas si el script devuelve items vacíos
- Si el archivo tiene medidas en pulgadas o cm → el script ya convierte a metros
- Si hay varios archivos en el mismo mensaje, ejecutá el script una vez por cada uno
- Después de procesar el archivo, continuá el protocolo de atención normal
