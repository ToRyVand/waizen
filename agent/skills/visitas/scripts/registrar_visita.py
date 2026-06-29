#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} - Registrador de Visitas Tecnicas
Gestiona visitas: crear, confirmar, completar, cancelar, consultar.
Input: JSON via stdin o argv[1]
Output: JSON con resultado
"""
import json, sys, os
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_FILE = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/visitas-data.json')
STEVEN    = '+573176616458'
HECTOR    = '+573134003693'

def load():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding='utf-8-sig'))
    return {'visitas': []}

def save(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def maps_link(direccion):
    return f'https://maps.google.com/?q={quote(direccion)}'

def next_id(data):
    ids = [v.get('id', 0) for v in data['visitas']]
    return (max(ids) + 1) if ids else 1

def fmt_fecha(f):
    try:
        dt = datetime.fromisoformat(f)
        dias = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo']
        meses = ['','enero','febrero','marzo','abril','mayo','junio',
                 'julio','agosto','septiembre','octubre','noviembre','diciembre']
        return f"{dias[dt.weekday()]} {dt.day} de {meses[dt.month]} a las {dt.strftime('%H:%M')}"
    except:
        return f

def crear(cliente, telefono, direccion, fecha_hora, notas=''):
    data = load()
    vid  = next_id(data)
    link = maps_link(direccion)
    visita = {
        'id':        vid,
        'cliente':   cliente,
        'telefono':  telefono,
        'direccion': direccion,
        'maps':      link,
        'fecha':     fecha_hora,
        'notas':     notas,
        'estado':    'pendiente',
        'creada':    datetime.now().isoformat(timespec='seconds'),
        'tecnico':   'Steven',
    }
    data['visitas'].append(visita)
    save(data)

    fecha_fmt = fmt_fecha(fecha_hora)
    msg_steven = (
        f"Visita tecnica solicitada:\n"
        f"Cliente: {cliente}\n"
        f"Direccion: {direccion}\n"
        f"Fecha: {fecha_fmt}\n"
        f"Maps: {link}\n"
        f"{'Notas: ' + notas if notas else ''}\n\n"
        f"Confirma disponibilidad respondiendo SI o NO (con hora alternativa si no podes)."
    ).strip()

    return {
        'status':       'creada',
        'id':           vid,
        'cliente':      cliente,
        'fecha':        fecha_fmt,
        'maps':         link,
        'estado':       'pendiente',
        'mensaje_steven': msg_steven,
        'steven':       STEVEN,
        'nota':         f'Envia este mensaje a Steven ({STEVEN}) para confirmar disponibilidad.',
    }

def confirmar(vid, hora_confirmada=None):
    data = load()
    v = next((x for x in data['visitas'] if x['id'] == vid), None)
    if not v:
        return {'error': f'No se encontro visita ID {vid}'}
    if hora_confirmada:
        v['fecha'] = hora_confirmada
    v['estado']     = 'confirmada'
    v['confirmada'] = datetime.now().isoformat(timespec='seconds')
    save(data)

    fecha_fmt = fmt_fecha(v['fecha'])
    msg_cliente = (
        f"Confirmado! La visita tecnica de {{BUSINESS_NAME}} queda agendada para el {fecha_fmt}.\n"
        f"Direccion: {v['direccion']}\n"
        f"Nuestro tecnico Steven estara con vos. Cualquier cambio te avisamos."
    )
    return {
        'status':         'confirmada',
        'id':             vid,
        'cliente':        v['cliente'],
        'fecha':          fecha_fmt,
        'maps':           v['maps'],
        'mensaje_cliente': msg_cliente,
        'telefono_cliente': v['telefono'],
    }

def actualizar_estado(vid, estado, notas_extra=''):
    data  = load()
    v     = next((x for x in data['visitas'] if x['id'] == vid), None)
    if not v:
        return {'error': f'No se encontro visita ID {vid}'}
    v['estado'] = estado
    if notas_extra:
        v['notas'] = (v.get('notas','') + ' | ' + notas_extra).strip(' |')
    v['actualizada'] = datetime.now().isoformat(timespec='seconds')
    save(data)
    return {'status': estado, 'id': vid, 'cliente': v['cliente']}

def consultar(fecha=None, estado=None):
    data    = load()
    visitas = data['visitas']
    if fecha:
        visitas = [v for v in visitas if v['fecha'].startswith(fecha[:10])]
    if estado:
        visitas = [v for v in visitas if v['estado'] == estado]
    visitas = sorted(visitas, key=lambda v: v['fecha'])
    return {'total': len(visitas), 'visitas': visitas}

def proximas(dias=7):
    data  = load()
    hoy   = date.today()
    res   = []
    for v in data['visitas']:
        if v['estado'] in ('cancelada',):
            continue
        try:
            dt = datetime.fromisoformat(v['fecha']).date()
            diff = (dt - hoy).days
            if 0 <= diff <= dias:
                res.append({**v, 'dias_restantes': diff})
        except:
            pass
    return {'total': len(res), 'visitas': sorted(res, key=lambda v: v['fecha'])}

def main():
    try:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            data = json.load(open(arg, encoding='utf-8-sig')) if os.path.isfile(arg) else json.loads(arg)
        else:
            data = json.load(sys.stdin)

        accion = data.get('accion', '')

        if accion == 'crear':
            result = crear(
                cliente    = data['cliente'],
                telefono   = data.get('telefono', ''),
                direccion  = data['direccion'],
                fecha_hora = data['fecha'],
                notas      = data.get('notas', ''),
            )
        elif accion == 'confirmar':
            result = confirmar(int(data['id']), data.get('hora_confirmada'))
        elif accion == 'completar':
            result = actualizar_estado(int(data['id']), 'completada', data.get('notas',''))
        elif accion == 'cancelar':
            result = actualizar_estado(int(data['id']), 'cancelada', data.get('motivo',''))
        elif accion == 'consultar':
            result = consultar(data.get('fecha'), data.get('estado'))
        elif accion == 'proximas':
            result = proximas(int(data.get('dias', 7)))
        else:
            result = {'error': f'Accion desconocida: "{accion}". Opciones: crear, confirmar, completar, cancelar, consultar, proximas'}

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()
