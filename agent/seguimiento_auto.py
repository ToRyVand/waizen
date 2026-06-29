#!/usr/bin/env python3
"""
Seguimiento automatico de cotizaciones {{BUSINESS_NAME}} (Fase 2).
Recorre clientes-db.json: pedidos en estado 'cotizado' con contacto previo,
sin respuesta hace >= 4 dias -> envia seguimiento por WhatsApp via API /seguimiento.
Frenos: max 3 seguimientos por pedido, max 5 envios por corrida,
salta convertida/no_interesado, salta leads sin fecha o viejos sin contacto previo.
Uso: python seguimiento_auto.py [--dry-run]
"""
import json, sys, urllib.request
from datetime import date, datetime
from pathlib import Path

DB   = Path(r"/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/clientes-db.json")
LOG  = Path(r"/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/seguimiento-auto.log")
API  = "http://localhost:18788/seguimiento"
DIAS_ESPERA   = 12
MAX_SEGS      = 3
MAX_POR_DIA   = 5
DRY = "--dry-run" in sys.argv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def parse_fecha(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def log(line):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{line}\n")

def main():
    db = json.loads(DB.read_text(encoding="utf-8-sig"))
    hoy = date.today()
    candidatos = []

    for c in db.get("clientes", []):
        tel = (c.get("telefono") or "").strip()
        if not tel:
            continue
        for p in c.get("pedidos", []):
            if p.get("estado") != "cotizado":
                continue
            se = p.get("seguimiento_estado", "")
            if se in ("convertida", "no_interesado"):
                continue
            segs = p.get("seguimientos") or []
            if len(segs) >= MAX_SEGS:
                continue
            ultimo = p.get("ultimo_seguimiento") or p.get("ultimo_envio_cotizacion")
            if ultimo:
                last = parse_fecha(ultimo)
            else:
                # sin contacto previo registrado: solo si la cotizacion es reciente (<30 dias)
                f = parse_fecha(p.get("fecha_pedido") or p.get("fecha"))
                if not f or (hoy - f).days > 30:
                    continue
                last = f
            if not last or (hoy - last).days < DIAS_ESPERA:
                continue
            candidatos.append((c, p, (hoy - last).days))

    candidatos.sort(key=lambda x: -x[2])  # los mas olvidados primero
    candidatos = candidatos[:MAX_POR_DIA]

    if not candidatos:
        print(json.dumps({"enviados": 0, "nota": "sin candidatos hoy"}))
        log("SKIP sin candidatos")
        return

    enviados = []
    for c, p, dias in candidatos:
        nombre = (c.get("nombre") or "").split()[0].title() or "cliente"
        desc = (p.get("descripcion") or "tu cotizacion")[:80]
        msg = (f"Hola {nombre}! Te saludamos de {{BUSINESS_NAME}}. "
               f"Hace unos dias te compartimos la cotizacion de {desc}. "
               f"Quedamos atentos a cualquier duda o ajuste que necesites. Con gusto te ayudamos!")
        if DRY:
            enviados.append({"cliente": c.get("nombre"), "tel": c.get("telefono"), "dias_sin_contacto": dias, "msg": msg})
            continue
        body = json.dumps({"telefono": c.get("telefono"), "mensaje": msg}).encode("utf-8")
        req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            ok = json.loads(resp.read().decode()).get("ok", False)
        except Exception as e:
            log(f"ERROR {c.get('nombre')} {e}")
            continue
        if ok:
            stamp = datetime.now().isoformat(timespec="seconds")
            p.setdefault("seguimientos", []).append({"fecha": stamp, "tipo": "auto"})
            p["ultimo_seguimiento"] = stamp
            if not p.get("seguimiento_estado"):
                p["seguimiento_estado"] = "sin_respuesta"
            enviados.append({"cliente": c.get("nombre"), "tel": c.get("telefono"), "dias": dias})
            log(f"ENVIADO {c.get('nombre')} ({c.get('telefono')}) {dias}d")

    if not DRY and enviados:
        DB.write_text(json.dumps(db, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(json.dumps({"dry_run": DRY, "enviados": len(enviados), "detalle": enviados}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
