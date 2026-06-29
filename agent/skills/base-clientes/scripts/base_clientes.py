#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} - Base de Datos de Clientes
Storage: clientes-db.json in clawd workspace
Input: JSON via stdin or argv[1] (file path or raw JSON string)
Output: JSON
"""
import json, sys, os, re, uuid, unicodedata
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/clientes-db.json')

ESTADOS_VALIDOS = ('cotizado', 'en_fabricacion', 'listo', 'entregado')


def normalize(text):
    if not text:
        return ''
    text = str(text).lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9\s]', '', text).strip()


def clean_phone(p):
    return re.sub(r'[^0-9]', '', str(p or ''))


def fmt_cop(v):
    try:
        return '$' + f'{int(v):,}'.replace(',', '.')
    except Exception:
        return str(v)


def load_db():
    if DB_PATH.exists():
        with open(DB_PATH, encoding='utf-8-sig') as f:
            return json.load(f)
    return {'clientes': []}


def save_db(db):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def find_client(db, telefono=None, nombre=None):
    if telefono:
        tel = clean_phone(telefono)
        for i, c in enumerate(db['clientes']):
            if clean_phone(c.get('telefono', '')) == tel:
                return i, c
    if nombre:
        words = set(normalize(nombre).split())
        best = (-1, None, 0)
        for i, c in enumerate(db['clientes']):
            cwords = set(normalize(c.get('nombre', '')).split())
            overlap = len(words & cwords)
            if overlap > best[2]:
                best = (i, c, overlap)
        if best[2] >= 1:
            return best[0], best[1]
    return -1, None


def find_pedido(pedidos, pedido_id=None, pedido_desc=None, pedido_idx=None):
    """Returns (index, pedido) or (-1, None)."""
    if pedido_id:
        for i, p in enumerate(pedidos):
            if p.get('id') == pedido_id:
                return i, p
    if pedido_desc:
        words = set(normalize(pedido_desc).split())
        best = (-1, None, 0)
        for i, p in enumerate(pedidos):
            pwords = set(normalize(p.get('descripcion', '')).split())
            overlap = len(words & pwords)
            if overlap > best[2]:
                best = (i, p, overlap)
        if best[2] >= 1:
            return best[0], best[1]
    if pedido_idx is not None:
        idx = int(pedido_idx)
        if 0 <= idx < len(pedidos):
            return idx, pedidos[idx]
    return -1, None


def do_guardar(data):
    db = load_db()
    telefono = data.get('telefono', '')
    nombre   = data.get('nombre', '')
    now      = datetime.now().strftime('%Y-%m-%d')
    pedido   = data.get('pedido')

    if pedido:
        pedido.setdefault('id', str(uuid.uuid4()))
        pedido.setdefault('fecha', now)
        # Normalizar estado si viene en formato viejo
        estado_map = {'confirmado': 'en_fabricacion', 'pendiente_pago': 'en_fabricacion', 'pendiente': 'cotizado'}
        pedido['estado'] = estado_map.get(pedido.get('estado', ''), pedido.get('estado', 'cotizado'))

    idx, c = find_client(db, telefono=telefono, nombre=nombre if not telefono else None)

    if idx >= 0:
        if nombre:                      c['nombre']    = nombre
        if data.get('direccion'):       c['direccion'] = data['direccion']
        if data.get('cedula_nit'):      c['cedula_nit']= data['cedula_nit']
        if telefono:                    c['telefono']  = telefono
        if data.get('notas'):           c['notas']     = data['notas']
        c['ultima_vez'] = now
        if pedido:
            c.setdefault('pedidos', []).insert(0, pedido)
        save_db(db)
        return {
            'status':  'actualizado',
            'nombre':  c['nombre'],
            'mensaje': f"Cliente {c['nombre']} actualizado." + (f" Pedido agregado: {pedido.get('descripcion','')}." if pedido else ''),
        }
    else:
        c = {
            'id':          str(uuid.uuid4()),
            'nombre':      nombre or 'Sin nombre',
            'telefono':    telefono,
            'direccion':   data.get('direccion', ''),
            'cedula_nit':  data.get('cedula_nit', ''),
            'notas':       data.get('notas', ''),
            'pedidos':     [pedido] if pedido else [],
            'primera_vez': now,
            'ultima_vez':  now,
        }
        db['clientes'].append(c)
        save_db(db)
        return {
            'status':  'creado',
            'nombre':  c['nombre'],
            'mensaje': f"Cliente {c['nombre']} registrado en la base de datos.",
        }


def do_actualizar_orden(data):
    db = load_db()
    idx, c = find_client(db, telefono=data.get('telefono'), nombre=data.get('nombre'))
    if not c:
        return {'error': 'Cliente no encontrado. Buscalo por telefono o nombre.'}

    pedidos = c.get('pedidos', [])
    if not pedidos:
        return {'error': f"El cliente {c['nombre']} no tiene pedidos registrados."}

    pidx, pedido = find_pedido(
        pedidos,
        pedido_id   = data.get('pedido_id'),
        pedido_desc = data.get('pedido_desc'),
        pedido_idx  = data.get('pedido_idx'),
    )

    if pidx < 0:
        # Si solo hay un pedido, usarlo directamente
        if len(pedidos) == 1:
            pidx, pedido = 0, pedidos[0]
        else:
            lista = [f"  [{i}] {p.get('descripcion','?')} — {p.get('estado','?')} ({p.get('fecha','?')})" for i, p in enumerate(pedidos)]
            return {
                'error': 'No pude identificar el pedido. Especificá pedido_id, pedido_desc o pedido_idx.',
                'pedidos_disponibles': lista,
            }

    nuevo_estado = data.get('estado', '')
    if nuevo_estado not in ESTADOS_VALIDOS:
        return {'error': f'Estado inválido: "{nuevo_estado}". Válidos: {", ".join(ESTADOS_VALIDOS)}'}

    estado_anterior = pedido.get('estado', '?')
    pedido['estado'] = nuevo_estado

    now = datetime.now().strftime('%Y-%m-%d')
    if nuevo_estado == 'entregado':
        pedido['fecha_entrega_real'] = data.get('fecha_entrega', now)

    c['ultima_vez'] = now
    save_db(db)

    return {
        'status':   'actualizado',
        'cliente':  c['nombre'],
        'pedido':   pedido.get('descripcion', f'Pedido #{pidx}'),
        'estado_anterior': estado_anterior,
        'estado_nuevo':    nuevo_estado,
        'mensaje': f"Pedido de {c['nombre']} actualizado: {estado_anterior} → {nuevo_estado}." + (
            " Marcado como entregado." if nuevo_estado == 'entregado' else
            " Listo para entregar — recordá notificar al cliente." if nuevo_estado == 'listo' else ''
        ),
    }


def do_buscar(data):
    db = load_db()
    idx, c = find_client(db, telefono=data.get('telefono'), nombre=data.get('nombre'))
    if not c:
        return {'encontrado': False, 'mensaje': 'No hay registros de este cliente en la base de datos.'}
    pedidos = c.get('pedidos', [])
    ultimo  = sorted(pedidos, key=lambda x: x.get('fecha', ''))[-1] if pedidos else None
    return {
        'encontrado':    True,
        'nombre':        c.get('nombre'),
        'telefono':      c.get('telefono'),
        'direccion':     c.get('direccion'),
        'notas':         c.get('notas'),
        'total_pedidos': len(pedidos),
        'ultimo_pedido': ultimo,
    }


def do_listar(data):
    db = load_db()
    clientes = [{
        'nombre':     c.get('nombre', ''),
        'telefono':   c.get('telefono', ''),
        'ultima_vez': c.get('ultima_vez', ''),
        'pedidos':    len(c.get('pedidos', [])),
    } for c in db['clientes']]
    clientes.sort(key=lambda x: x.get('ultima_vez', ''), reverse=True)
    return {'total': len(clientes), 'clientes': clientes}


def do_historial(data):
    db = load_db()
    idx, c = find_client(db, telefono=data.get('telefono'), nombre=data.get('nombre'))
    if not c:
        return {'encontrado': False, 'mensaje': 'Cliente no encontrado.'}
    pedidos     = sorted(c.get('pedidos', []), key=lambda x: x.get('fecha', ''), reverse=True)
    total_valor = sum(p.get('total', 0) for p in pedidos if isinstance(p.get('total'), (int, float)))
    return {
        'encontrado':      True,
        'nombre':          c.get('nombre'),
        'telefono':        c.get('telefono'),
        'direccion':       c.get('direccion'),
        'notas':           c.get('notas'),
        'cliente_desde':   c.get('primera_vez'),
        'total_pedidos':   len(pedidos),
        'valor_historico': fmt_cop(total_valor),
        'pedidos':         pedidos[:10],
    }


def main():
    try:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if os.path.isfile(arg):
                with open(arg, encoding='utf-8-sig') as f:
                    data = json.load(f)
            else:
                data = json.loads(arg)
        else:
            data = json.load(sys.stdin)

        action   = data.get('action', 'buscar')
        dispatch = {
            'guardar':          do_guardar,
            'actualizar_orden': do_actualizar_orden,
            'buscar':           do_buscar,
            'listar':           do_listar,
            'historial':        do_historial,
        }

        if action not in dispatch:
            print(json.dumps({
                'error': f'Accion desconocida: "{action}". Opciones: guardar, actualizar_orden, buscar, listar, historial'
            }, ensure_ascii=False))
            sys.exit(1)

        print(json.dumps(dispatch[action](data), ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
