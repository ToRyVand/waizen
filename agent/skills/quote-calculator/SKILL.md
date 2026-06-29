---
name: quote-calculator
description: Calcula precios reales de productos {{BUSINESS_NAME}} (M2 o metro lineal) con valores EXACTOS de PRECIOS.md. USAR SIEMPRE que el cliente tenga producto + medidas + cantidad y pida precio o cotizacion. NUNCA calcular precios a mano ni escalar a Hector para precios que esta skill puede calcular.
---

# Cotizador {{BUSINESS_NAME}}

## CUANDO USAR (OBLIGATORIO)

Apenas tengas del cliente: **producto + medidas (ancho x alto) + cantidad**, EJECUTA esta skill.
NO calcules el precio mentalmente. NO digas "consultare con Hector" para un precio que el cotizador puede dar.
Solo escalas a Hector si el producto NO aparece en PRECIOS.md (el cotizador te lo dice en "not_found").

## COMO EJECUTAR (2 pasos, metodo a prueba de errores)

NO inventes flags como --items o --client_type. El script NO los acepta.
El metodo correcto es: escribir el JSON a un archivo, luego ejecutar el script con la RUTA del archivo.

### Paso 1: escribir el JSON con la herramienta write
Archivo: `/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/_cotizacion.json`
Contenido (ejemplo para 1 espejo 4mm de 1.20x1.20 que el cliente recoge):
```json
{"items":[{"product":"espejo 4mm","width":1.20,"height":1.20,"quantity":1}],"client_type":"publico","transport":0}
```

### Paso 2: ejecutar con exec
```
python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/quote-calculator/scripts/calculate_quote.py" "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/_cotizacion.json"
```

## ESTRUCTURA DEL JSON

```json
{
  "items": [
    { "product": "espejo 4mm", "width": 1.20, "height": 1.20, "quantity": 1 },
    { "product": "biselado",   "width": 1.20, "height": 0,    "quantity": 4 }
  ],
  "client_type": "publico",
  "transport": 0
}
```

- `product`: nombre del producto (el script hace fuzzy match con PRECIOS.md). Ej: "espejo 4mm", "6mm incoloro", "ventaneria 744", "biselado".
- `width`: ancho en metros (numero). Para servicios lineales como biselado/pulido, es el LARGO.
- `height`: alto en metros (numero). Para servicios de Metro Lineal poner 0.
- `quantity`: cantidad (numero entero).
- `client_type`: "publico" por defecto. "vidriero" SOLO si memory/clientes/<num>.md dice que es vidriero/aluminio.
- `transport`: 0 si el cliente recoge | 20000 visita en Cali | 50000 municipios (Jamundi, Yumbo, Palmira).

## OUTPUT (lo que devuelve el script)

```json
{
  "fecha": "10/06/2026",
  "items": ["- 4mm espejo 1.20x1.20m  Und: 1 | V.Unit: $110.000/M2 | Total: $158.400"],
  "not_found": [],
  "subtotal": "$158.400",
  "transport": "$0",
  "total": "$158.400"
}
```

Si `not_found` tiene productos -> NO enviar cotizacion, preguntar el nombre exacto o escalar a Hector solo por esos.

## MENSAJE DE COTIZACION PARA WHATSAPP

Cuando tengas nombre, telefono, direccion y CC/NIT del cliente, arma el mensaje:

```
*COTIZACION {{BUSINESS_NAME}}*
Fecha: [fecha]

*Datos del cliente*
Nombre: [nombre]
Tel: [telefono]
Direccion: [direccion]
CC/NIT: [cc_nit]

*Detalle del pedido*
[pegar cada linea de items del output]

*Resumen*
Subtotal: [subtotal]
Transporte: [transport]
*TOTAL: [total]*

_Cotizacion valida 3 dias habiles._
_{{BUSINESS_NAME}} - Cali, Colombia - +57 302 865 4189_
```

## REGLAS

- Producto + medidas + cantidad presentes -> EJECUTAR el cotizador, no escalar.
- Visita Cali: transport 20000 | Municipios: transport 50000 | Cliente retira: transport 0.
- Si el cliente da el precio el mismo ("me lo dejan en X"), respetar lo de SOUL.md (aceptar su dato).


## DESPUES DE COTIZAR: GUARDA TODO (CRITICO)
Cuando terminas una cotizacion ya tenes TODOS los datos del cliente. NO los pierdas. Guardar = parte del cotizar:
1. Guarda el cliente + pedido en el CRM -> write a `/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/_cliente.json`:
   {"action":"guardar","nombre":"...","telefono":"...","direccion":"...","cedula_nit":"...","pedido":{"descripcion":"<producto+medidas>","total":<total_raw>,"estado":"cotizado"}}
   exec: python "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/base-clientes/scripts/base_clientes.py" "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/_cliente.json"
2. Actualiza memory/clientes/<telefono>.md con info RICA: nombre, telefono, direccion, cedula/nit, producto+medidas, total cotizado ($), estado=cotizado, fecha.
Usa el campo `total_raw` (numero) del output del cotizador para el "total" del pedido.
Asi, si el cliente vuelve a escribir mas tarde, retomas con todo el contexto aunque la sesion se haya rotado.