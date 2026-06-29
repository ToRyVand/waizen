#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} Registrador de Cuentas - {{AGENT_NAME}}
Registra ingresos y gastos en cuentas-bot.json (fusionado con localStorage en la UI).
Input: JSON {accion, fecha, tipo, descripcion, valor} via stdin o argv[1]
Output: JSON con confirmacion y totales
"""
import json
import sys
import os
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_FILE = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/cuentas-data.json')


def fmt(v):
    return '$' + f'{int(v):,}'.replace(',', '.')


def load():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding='utf-8-sig'))
    return {}


def save(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def parse_fecha(f):
    if not f or str(f).lower() in ('hoy', 'today'):
        return date.today().isoformat()
    return str(f)


def registrar(fecha, tipo, descripcion, valor):
    fecha = parse_fecha(fecha)
    data  = load()
    if fecha not in data:
        data[fecha] = {'ingresos': [], 'gastos': []}

    entry = {
        'desc':  descripcion,
        'valor': int(valor),
        'por':   '{{AGENT_NAME}}',
        'hora':  datetime.now().strftime('%H:%M'),
    }

    tipo_lower = tipo.lower()
    if tipo_lower in ('ingreso', 'ingresos', 'abono', 'pago'):
        data[fecha]['ingresos'].append(entry)
        tipo_display = 'ingreso'
    elif tipo_lower in ('gasto', 'gastos', 'egreso', 'egresos', 'pago_proveedor'):
        data[fecha]['gastos'].append(entry)
        tipo_display = 'gasto'
    else:
        return {'error': f'tipo debe ser "ingreso" o "gasto", recibido: "{tipo}"'}

    save(data)

    # NO devolver totales/balance del dia aqui: es info PRIVADA del negocio.
    # La confirmacion de un pago de cliente NO debe incluir cuanto entro en el dia.
    return {
        'status':       'registrado',
        'fecha':        fecha,
        'tipo':         tipo_display,
        'descripcion':  descripcion,
        'valor':        fmt(valor),
        'confirmacion': f'{tipo_display.capitalize()} de {fmt(valor)} registrado en cuentas.',
        'AVISO_PRIVACIDAD': 'NUNCA compartas totales/ingresos/balance del negocio con el cliente. Solo confirma SU pago. Los totales son solo para admins via accion consultar.',
        'url':          'file:///C:/Users/USER/clawd/cuentas.html',
    }


def consultar(fecha=None):
    fecha = parse_fecha(fecha)
    data  = load()
    dia   = data.get(fecha, {'ingresos': [], 'gastos': []})
    total_ing = sum(e['valor'] for e in dia['ingresos'])
    total_gas = sum(e['valor'] for e in dia['gastos'])
    return {
        'fecha':          fecha,
        'ingresos':       dia['ingresos'],
        'gastos':         dia['gastos'],
        'total_ingresos': fmt(total_ing),
        'total_gastos':   fmt(total_gas),
        'balance':        fmt(total_ing - total_gas),
    }


def consultar_rango(fecha_inicio, fecha_fin=None):
    fecha_inicio = parse_fecha(fecha_inicio)
    fecha_fin    = parse_fecha(fecha_fin) if fecha_fin else date.today().isoformat()
    data         = load()

    total_ing = 0
    total_gas = 0
    detalle   = []

    for f in sorted(data.keys()):
        if fecha_inicio <= f <= fecha_fin:
            dia = data[f]
            ing = sum(e['valor'] for e in dia.get('ingresos', []))
            gas = sum(e['valor'] for e in dia.get('gastos', []))
            total_ing += ing
            total_gas += gas
            detalle.append({
                'fecha':    f,
                'ingresos': fmt(ing),
                'gastos':   fmt(gas),
                'balance':  fmt(ing - gas),
            })

    return {
        'rango':          f'{fecha_inicio} a {fecha_fin}',
        'dias_con_datos': len(detalle),
        'total_ingresos': fmt(total_ing),
        'total_gastos':   fmt(total_gas),
        'balance_total':  fmt(total_ing - total_gas),
        'detalle':        detalle,
    }


def listar_todo():
    data   = load()
    result = []
    for f in sorted(data.keys(), reverse=True):
        dia = data[f]
        for e in dia.get('ingresos', []):
            result.append({'fecha': f, 'tipo': 'ingreso', **e})
        for e in dia.get('gastos', []):
            result.append({'fecha': f, 'tipo': 'gasto', **e})

    total_ing = sum(e['valor'] for e in result if e['tipo'] == 'ingreso')
    total_gas = sum(e['valor'] for e in result if e['tipo'] == 'gasto')

    return {
        'total_entradas':  len(result),
        'total_ingresos':  fmt(total_ing),
        'total_gastos':    fmt(total_gas),
        'balance_general': fmt(total_ing - total_gas),
        'entradas':        result,
    }


def resumen_mes(mes=None, anio=None):
    hoy   = date.today()
    mes   = int(mes)   if mes   else hoy.month
    anio  = int(anio)  if anio  else hoy.year
    prefx = f'{anio}-{mes:02d}'
    data  = load()

    total_ing = 0
    total_gas = 0
    detalle   = []

    for f in sorted(data.keys()):
        if f.startswith(prefx):
            dia = data[f]
            ing = sum(e['valor'] for e in dia.get('ingresos', []))
            gas = sum(e['valor'] for e in dia.get('gastos', []))
            if ing or gas:
                total_ing += ing
                total_gas += gas
                detalle.append({'fecha': f, 'ingresos': fmt(ing), 'gastos': fmt(gas), 'balance': fmt(ing - gas)})

    meses = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    return {
        'mes':            f'{meses[mes]} {anio}',
        'dias_con_datos': len(detalle),
        'total_ingresos': fmt(total_ing),
        'total_gastos':   fmt(total_gas),
        'balance_mes':    fmt(total_ing - total_gas),
        'detalle':        detalle,
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

        accion = data.get('accion', 'registrar')

        if accion == 'registrar':
            result = registrar(
                fecha       = data.get('fecha', 'hoy'),
                tipo        = data.get('tipo', ''),
                descripcion = data.get('descripcion', ''),
                valor       = data.get('valor', 0),
            )
        elif accion == 'consultar':
            result = consultar(data.get('fecha', 'hoy'))
        elif accion == 'consultar_rango':
            result = consultar_rango(
                fecha_inicio = data.get('fecha_inicio', date.today().isoformat()),
                fecha_fin    = data.get('fecha_fin'),
            )
        elif accion == 'listar_todo':
            result = listar_todo()
        elif accion == 'resumen_mes':
            result = resumen_mes(data.get('mes'), data.get('anio'))
        else:
            result = {'error': f'Acción desconocida: "{accion}". Opciones: registrar, consultar, consultar_rango, listar_todo, resumen_mes'}

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()

