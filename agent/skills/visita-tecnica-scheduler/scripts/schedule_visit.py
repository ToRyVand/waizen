#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} Visit Scheduler — FUENTE ÚNICA
Crea / lista visitas técnicas en visitas-data.json (el mismo archivo que lee
visitas.html vía API /visitas.json). Genera links de Google Maps
y Google Calendar. Input: JSON via stdin o argv[1].
"""
import json
import sys
import os
import re
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# Force UTF-8 so emojis/acentos no crashen en Windows cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

# Fuente única: los mismos archivos que leen los dashboards (vía API)
_CLAWD = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
DASHBOARD_FILE = _CLAWD / 'visitas-data.json'
CLIENTS_FILE   = _CLAWD / 'clientes-db.json'
VISIT_COST = {'cali': 20000, 'municipio': 50000}


def _digits(s):
    return re.sub(r'\D', '', str(s or ''))


def upsert_client(name, phone, address):
    """Crea o actualiza el cliente (tercero) en clientes-db.json a partir de la visita.
    Devuelve 'creado' | 'actualizado' | None (si falla)."""
    try:
        if CLIENTS_FILE.exists():
            cdb = json.loads(CLIENTS_FILE.read_text(encoding='utf-8-sig'))
        else:
            cdb = {'clientes': []}
        if not isinstance(cdb.get('clientes'), list):
            cdb['clientes'] = []
        ph = _digits(phone)[-10:]
        nm = (name or '').strip().lower()
        found = None
        for c in cdb['clientes']:
            if ph and _digits(c.get('telefono'))[-10:] == ph:
                found = c; break
            if nm and (c.get('nombre', '') or '').strip().lower() == nm:
                found = c; break
        today = datetime.now().strftime('%Y-%m-%d')
        if found:
            if not found.get('direccion') and address:
                found['direccion'] = address
            found['ultima_vez'] = today
            result = 'actualizado'
        else:
            cdb['clientes'].insert(0, {
                'nombre':      (name or '').strip().upper(),
                'telefono':    phone or '',
                'direccion':   address or '',
                'cedula_nit':  '',
                'notas':       'Alta automática desde visita técnica',
                'pedidos':     [],
                'primera_vez': today,
                'ultima_vez':  today,
            })
            result = 'creado'
        CLIENTS_FILE.write_text(json.dumps(cdb, ensure_ascii=False), encoding='utf-8')
        return result
    except Exception:
        return None

WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MONTHS   = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def maps_url(address):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(address)


def calendar_url(title, address, start_dt, duration_hours, description):
    end_dt = start_dt + timedelta(hours=duration_hours)
    fmt = '%Y%m%dT%H%M%S'
    params = {
        'action':   'TEMPLATE',
        'text':     title,
        'dates':    f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}",
        'details':  description,
        'location': address,
        'trp':      'false',
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)


def load_db():
    if DASHBOARD_FILE.exists():
        try:
            db = json.loads(DASHBOARD_FILE.read_text(encoding='utf-8-sig'))
        except Exception:
            db = {'visitas': []}
    else:
        db = {'visitas': []}
    if not isinstance(db.get('visitas'), list):
        db['visitas'] = []
    return db


def save_db(db):
    DASHBOARD_FILE.write_text(json.dumps(db, ensure_ascii=False), encoding='utf-8')


def check_conflicts(date_str, db):
    """Clientes ya agendados ese día (excluye canceladas)."""
    return [v.get('cliente', '?') for v in db['visitas']
            if str(v.get('fecha', '')).startswith(date_str) and v.get('estado') != 'cancelada']


def create_visit(data):
    name       = data['client_name']
    date_str   = data['date']          # YYYY-MM-DD
    time_str   = data.get('time', '09:00')
    phone      = data.get('phone', '')
    address    = data.get('address', '')
    reason     = data.get('reason', '')
    duration   = float(data.get('duration_hours', 1))
    zone       = data.get('zone', 'cali').lower()
    technician = data.get('technician', 'Por confirmar')
    notes      = data.get('notes', '')
    tipo       = data.get('tipo', 'visita').lower()
    if tipo not in ('visita', 'instalacion'):
        tipo = 'visita'
    es_inst = tipo == 'instalacion'
    label   = 'Instalación' if es_inst else 'Visita Técnica'

    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    end_dt   = start_dt + timedelta(hours=duration)

    fecha_display = (f"{WEEKDAYS[start_dt.weekday()]} {start_dt.day} de "
                     f"{MONTHS[start_dt.month - 1]} de {start_dt.year}")
    hora_display = f"{start_dt.strftime('%I:%M %p')} – {end_dt.strftime('%I:%M %p')}"

    # Las instalaciones no cobran visita (van dentro del trabajo); las visitas técnicas sí
    cost         = 0 if es_inst else VISIT_COST.get(zone, VISIT_COST['cali'])
    cost_display = ('Incluida en el trabajo' if es_inst
                    else f"${cost:,.0f}".replace(',', '.') + " COP (abonables al trabajo final)")

    g_maps = maps_url(address)
    cal_desc = (f"Cliente: {name}\nTeléfono: {phone}\nMotivo: {reason}\n"
                f"Técnico: {technician}\nCosto: {cost_display}")
    g_cal = calendar_url(
        title          = f"{label} {{BUSINESS_NAME}} — {name}",
        address        = address,
        start_dt       = start_dt,
        duration_hours = duration,
        description    = cal_desc,
    )

    db = load_db()
    conflicts = check_conflicts(date_str, db)

    notas = reason or ''
    if notes:
        notas = (notas + ' — ' + notes) if notas else notes

    next_id = max([v.get('id', 0) for v in db['visitas']], default=0) + 1
    db['visitas'].append({
        'id':           next_id,
        'tipo':         tipo,
        'cliente':      name,
        'cliente_ref':  name,
        'telefono':     phone,
        'direccion':    address,
        'maps':         g_maps,
        'fecha':        start_dt.strftime('%Y-%m-%dT%H:%M:00'),
        'notas':        notas,
        'estado':       'pendiente',
        'creada':       datetime.now().isoformat(),
        'tecnico':      technician,
        'zona':         zone,
        'costo_visita': cost,
    })
    save_db(db)

    # Alta/actualización automática del cliente (tercero) en el CRM
    cliente_status = upsert_client(name, phone, address)

    return {
        'status':       'created',
        'tipo':         tipo,
        'card_id':      next_id,
        'cliente_crm':  cliente_status,   # 'creado' | 'actualizado'
        'client_name':  name,
        'date':         fecha_display,
        'time':         hora_display,
        'address':      address,
        'maps_url':     g_maps,
        'calendar_url': g_cal,
        'cost':         cost_display,
        'technician':   technician,
        'conflicts':    conflicts,
    }


def list_visits():
    """Lista todas las visitas del JSON, ordenadas por fecha."""
    db = load_db()
    out = []
    for v in sorted(db['visitas'], key=lambda x: str(x.get('fecha', ''))):
        out.append({
            'id':      v.get('id'),
            'name':    v.get('cliente', '?'),
            'date':    v.get('fecha', '—'),
            'estado':  v.get('estado', '—'),
            'tipo':    v.get('tipo', 'visita'),
            'tecnico': v.get('tecnico', ''),
        })
    return out


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

        action = data.get('action', 'create')
        if action == 'list':
            print(json.dumps({'visits': list_visits()}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(create_visit(data), ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
