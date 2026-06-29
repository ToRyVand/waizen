#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} Media Reader
Reads images and PDFs sent by WhatsApp clients via Gemini API (stdlib only).
Input: file path as argv[1]
Output: JSON with extracted content, measurements, context
"""
import json
import sys
import os
import base64
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load API key from env or .clawdbot/.env
API_KEY = os.environ.get('GOOGLE_API_KEY', '')
if not API_KEY:
    for env_path in [Path.home()/'clientes'/'{{WHATSAPP_ACCOUNT}}'/'.env', Path.home()/'.openclaw'/'.env']:
        try:
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if line.startswith('GOOGLE_API_KEY='):
                    API_KEY = line.split('=', 1)[1].strip()
                    break
            if API_KEY:
                break
        except Exception:
            pass

MODEL   = 'gemini-2.5-flash'
API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}'

PROMPT = """Eres asistente de {{BUSINESS_NAME}} (vidrios y espejos, Cali, Colombia).

Analiza este archivo enviado por un cliente de WhatsApp y extrae TODA la información útil.

Busca:
1. MEDIDAS visibles (cm, mm, m, pulgadas) — convertir TODO a metros decimales
2. PRODUCTOS identificables (espejo, vidrio templado, ventana, puerta vidrio, cabina baño, fachada, etc.)
3. CANTIDAD de piezas si hay varias iguales
4. TEXTO legible (listas, presupuestos, planos con etiquetas)
5. CONTEXTO: qué quiere hacer el cliente

Reglas de conversión:
- 60 cm → 0.60 m  |  120 cm → 1.20 m  |  250 cm → 2.50 m
- 600 mm → 0.60 m  |  1200 mm → 1.20 m
- 2 ft → 0.61 m  |  6 ft → 1.83 m

Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{
  "tipo": "foto_espacio|plano|lista_items|cotizacion_externa|foto_producto|documento|otro",
  "tiene_medidas": true,
  "items": [
    {
      "producto": "nombre descriptivo (ej: espejo, vidrio 6mm incoloro, ventana corrediza, cabina ducha)",
      "ancho_m": 0.80,
      "alto_m": 1.20,
      "cantidad": 1,
      "notas": "cualquier detalle adicional visible"
    }
  ],
  "texto_extraido": "texto relevante del documento si aplica (lista de items, medidas escritas, etc.)",
  "contexto": "resumen de qué necesita el cliente según el archivo",
  "observaciones": "cualquier info adicional que ayude a cotizar"
}

Si no hay medidas visibles, items = [].
Si hay texto pero no medidas estructuradas, colócalo en texto_extraido."""

SUPPORTED = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png',  '.webp': 'image/webp',
    '.gif': 'image/gif',  '.pdf': 'application/pdf',
}


def read_file(path):
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED:
        return None, None
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8'), SUPPORTED[suffix]


def call_gemini(file_path):
    data, mime = read_file(file_path)
    if data is None:
        return {
            'tipo': 'no_soportado',
            'tiene_medidas': False,
            'items': [],
            'texto_extraido': '',
            'contexto': f'Formato {Path(file_path).suffix} no soportado para análisis visual',
            'observaciones': ''
        }

    payload = {
        'contents': [{'parts': [
            {'text': PROMPT},
            {'inline_data': {'mime_type': mime, 'data': data}},
        ]}],
        'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 8192, 'responseMimeType': 'application/json'},
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=45) as resp:
        response = json.loads(resp.read().decode('utf-8'))

    raw = response['candidates'][0]['content']['parts'][0]['text'].strip()

    # Strip markdown code fences if present
    if '```' in raw:
        parts = raw.split('```')
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()

    # Fix literal newlines inside JSON strings (common Gemini output issue)
    raw = _sanitize_json(raw)

    return json.loads(raw)


def _sanitize_json(text):
    """Replace literal newlines/tabs inside JSON string values with escape sequences."""
    result = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == '\\':
            result.append(ch)
            escaped = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch == '\n':
            result.append('\\n')
        elif in_string and ch == '\r':
            pass  # skip CR
        elif in_string and ch == '\t':
            result.append('\\t')
        else:
            result.append(ch)
    return ''.join(result)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Uso: read_media.py <ruta_archivo>'}))
        sys.exit(1)

    file_path = sys.argv[1].strip('"').strip("'")

    if not os.path.exists(file_path):
        print(json.dumps({
            'error': f'Archivo no encontrado: {file_path}',
            'items': [],
            'tiene_medidas': False,
            'contexto': ''
        }))
        sys.exit(1)

    try:
        result = call_gemini(file_path)
        result['archivo'] = os.path.basename(file_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        print(json.dumps({'error': f'API HTTP {e.code}: {body}', 'items': []}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': str(e), 'items': []}))
        sys.exit(1)


if __name__ == '__main__':
    main()
