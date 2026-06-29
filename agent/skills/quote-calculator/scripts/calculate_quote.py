#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} Quote Calculator
Input: JSON via argv[1] or stdin
Output: JSON to stdout
"""
import json
import re
import sys
import os
from datetime import date

PRECIOS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'PRECIOS.md')


def parse_precios(path):
    prices = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        # Try alternate path (workspace root)
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'PRECIOS.md')
        with open(alt, 'r', encoding='utf-8') as f:
            content = f.read()

    for line in content.splitlines():
        line = line.strip()
        if not line.startswith('-'):
            continue
        m = re.match(r'^-\s+(.+?):\s+(.+)$', line)
        if not m:
            continue

        name = m.group(1).strip()
        price_info = m.group(2).strip()

        unit = 'ML' if ('Metro Lineal' in price_info or 'ML' in price_info) else 'M2'

        if '|' in price_info:
            parts = price_info.split('|')
            v = re.search(r'\$([0-9.]+)', parts[0])
            p = re.search(r'\$([0-9.]+)', parts[1])
            vidriero = int(v.group(1).replace('.', '')) if v else 0
            publico  = int(p.group(1).replace('.', '')) if p else 0
        else:
            pm = re.search(r'\$([0-9.]+)', price_info)
            price = int(pm.group(1).replace('.', '')) if pm else 0
            vidriero = publico = price

        prices[name.lower()] = {
            'name': name,
            'vidriero': vidriero,
            'publico': publico,
            'unit': unit,
        }
    return prices


def find_price(prices, query):
    q = query.lower().strip()
    if q in prices:
        return prices[q]
    # Partial / word match
    best, best_score = None, 0
    q_words = set(q.split())
    for key, data in prices.items():
        k_words = set(key.split())
        score = len(q_words & k_words)
        if score > best_score:
            best_score, best = score, data
    return best if best_score > 0 else None


def fmt(value):
    # Colombian peso format: $1.234.567
    s = f"{int(round(value)):,}".replace(',', '.')
    return f"${s}"


def calculate(items, client_type='publico', transport=0):
    prices = parse_precios(PRECIOS_PATH)
    client_type = client_type if client_type in ('vidriero', 'publico') else 'publico'

    lines = []
    not_found = []
    subtotal = 0

    for item in items:
        product  = item.get('product', '')
        width    = float(item.get('width', 0))
        height   = float(item.get('height', 0))
        qty      = int(item.get('quantity', 1))

        pd = find_price(prices, product)
        if not pd:
            not_found.append(product)
            lines.append(f"- {product}: precio no encontrado en lista")
            continue

        # GUARD: nunca cotizar $0 por falta de medidas - obligar a preguntar
        if width <= 0 or (pd['unit'] == 'M2' and height <= 0):
            not_found.append(product)
            lines.append(f"- {product}: FALTAN MEDIDAS (ancho/alto en metros). NO cotizar: preguntale al cliente las medidas exactas.")
            continue

        unit       = pd['unit']
        unit_price = pd[client_type]

        if unit == 'ML':
            measure   = width * qty
            item_total = measure * unit_price
            desc = f"{pd['name']} {width:.2f}m x{qty} und"
        else:
            area       = width * height
            measure    = area * qty
            item_total = measure * unit_price
            desc = f"{pd['name']} {width:.2f}x{height:.2f}m"

        subtotal += item_total
        lines.append(
            f"- {desc}  Und: {qty} | V.Unit: {fmt(unit_price)}/{unit} | Total: {fmt(item_total)}"
        )

    transport = float(transport)
    total = subtotal + transport

    return {
        'fecha': date.today().strftime('%d/%m/%Y'),
        'items': lines,
        'not_found': not_found,
        'subtotal': fmt(subtotal),
        'transport': fmt(transport),
        'total': fmt(total),
        'subtotal_raw': round(subtotal),
        'transport_raw': round(transport),
        'total_raw': round(total),
    }


def main():
    try:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if os.path.isfile(arg):
                with open(arg, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
            else:
                data = json.loads(arg)
        else:
            data = json.load(sys.stdin)

        result = calculate(
            items=data.get('items', []),
            client_type=data.get('client_type', 'publico'),
            transport=data.get('transport', 0),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
