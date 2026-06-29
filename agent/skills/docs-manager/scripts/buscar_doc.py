#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} Document Finder
Busca la cotizacion / orden / factura de un cliente por nombre.
Busca RECURSIVO en todas las carpetas de documentos y usa matching ESTRICTO
(todas las palabras significativas del nombre deben estar) para no traer docs de otros clientes.
Input: nombre (argv[1]) o JSON {"nombre": "...", "tipo": "todos"}
Output: JSON con archivos encontrados y rutas (mas reciente primero)
"""
import json
import sys
import os
import re
import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Carpetas raiz donde viven los documentos (se buscan RECURSIVO)
ROOTS = [
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/COTIZACIONES'),
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/PENDIENTES'),
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/FACTURAS ELECTRONICAS'),
]

EXTS = {'.pdf', '.png', '.jpg', '.jpeg'}


def normalizar(texto):
    """minusculas, sin acentos, sin puntuacion."""
    texto = str(texto).lower().strip()
    texto = texto.translate(str.maketrans('aeiouun', 'aeiouun'))  # placeholder, acentos abajo
    for a, b in (('a','a'),):
        pass
    # Reemplazo de acentos por unicode-safe
    acentos = {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ü':'u','ñ':'n'}
    for k, v in acentos.items():
        texto = texto.replace(k, v)
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    return ' '.join(texto.split())


def palabras_sig(nombre_norm):
    """Palabras significativas: >=3 letras (descarta de, la, el, ii, etc)."""
    return {w for w in nombre_norm.split() if len(w) >= 3}


def tipo_desde_ruta(ruta):
    r = ruta.lower()
    if 'cotizaciones' in r:
        return 'cotizacion'
    if 'facturas electronicas' in r or 'facturas' in r:
        return 'factura'
    if 'x cobrar' in r:
        return 'orden_por_cobrar'
    if 'x entregar' in r:
        return 'orden_lista'
    if 'x fabricar' in r:
        return 'orden_en_fabricacion'
    if 'x instalar' in r:
        return 'orden_por_instalar'
    if 'entregado' in r:
        return 'orden_entregada'
    return 'documento'


def buscar(nombre, tipo='todos'):
    palabras = palabras_sig(normalizar(nombre))
    resultados = []
    if not palabras:
        return resultados

    for root in ROOTS:
        if not root.exists():
            continue
        for f in root.rglob('*'):
            if not f.is_file() or f.suffix.lower() not in EXTS:
                continue
            palabras_archivo = set(normalizar(f.stem).split())
            # ESTRICTO: todas las palabras significativas del nombre deben estar en el archivo
            if palabras.issubset(palabras_archivo):
                resultados.append({
                    'tipo':   tipo_desde_ruta(str(f)),
                    'nombre': f.name,
                    'ruta':   str(f),
                    'carpeta': str(f.parent),
                    'fecha':  f.stat().st_mtime,
                })

    # mas reciente primero
    resultados.sort(key=lambda x: x['fecha'], reverse=True)
    for r in resultados:
        r['fecha'] = datetime.datetime.fromtimestamp(r['fecha']).strftime('%d/%m/%Y')
    return resultados


def main():
    try:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if os.path.isfile(arg):
                with open(arg, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                nombre = data.get('nombre', '')
                tipo   = data.get('tipo', 'todos')
            else:
                nombre = arg
                tipo   = sys.argv[2] if len(sys.argv) > 2 else 'todos'
        else:
            data   = json.load(sys.stdin)
            nombre = data.get('nombre', '')
            tipo   = data.get('tipo', 'todos')

        if not nombre:
            print(json.dumps({'error': 'Proporcionar nombre del cliente', 'resultados': []}))
            sys.exit(1)

        encontrados = buscar(nombre, tipo)
        print(json.dumps({
            'busqueda':   nombre,
            'total':      len(encontrados),
            'resultados': encontrados,
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e), 'resultados': []}))
        sys.exit(1)


if __name__ == '__main__':
    main()
