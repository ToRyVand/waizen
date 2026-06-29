# DOCS.md - Documentos y Acceso a Sistemas {{BUSINESS_NAME}}

## Carpetas de documentos

| Tipo | Ruta | Formatos |
|---|---|---|
| **Cotizaciones** | `C:\Users\USER\Downloads\COTIZACIONES\` | PDF, PNG, JPG |
| **Facturas / Recibos** | `C:\Users\USER\Desktop\PENDIENTES\X ENTREGAR\` | PDF, PNG |

Los archivos se nombran con el nombre del cliente: `CARLOS RUIZ.pdf`.

## Buscar documentos de un cliente

```
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs-manager/scripts/buscar_doc.py" "Nombre del cliente"
```

Con tipo especifico (cotizacion o factura):
```
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs-manager/scripts/buscar_doc.py" "Carlos Ruiz" cotizacion
```

Output: JSON con `resultados[].ruta` - usar esa ruta para enviar el archivo con la herramienta de archivos.

Para leer el contenido de un PDF encontrado:
```
python3 "/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/media-reader/scripts/read_media.py" "ruta_del_archivo"
```

## Registro de ingresos y gastos (cuentas diarias)

Ver skill `docs-manager\SKILL.md` para registrar entradas.
Los datos se guardan en `/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/cuentas-data.json` via ARK API (localhost:18788).
La UI de cuentas es LOCAL: `file:///C:/Users/USER/clawd/cuentas.html`
Los registros de {{AGENT_NAME}} aparecen con badge "{{AGENT_NAME}}".

## Generador de facturas

UI LOCAL: `file:///C:/Users/USER/clawd/facturas.html`
Las facturas generadas se guardan manualmente en `Desktop\PENDIENTES\X ENTREGAR\`.

## Reglas

- Nunca menciones rutas de carpetas al cliente - simplemente envia el archivo o da la informacion.
- Si buscas un documento y no aparece, pregunta el nombre completo o avisa a Hector.
- Enviar siempre el archivo mas reciente si hay varios para el mismo cliente.
## Visitas Tecnicas

Ver skill `visitas\SKILL.md` para agendar, confirmar y consultar visitas.
La UI esta en: `file:///C:/Users/USER/clawd/visitas.html`

