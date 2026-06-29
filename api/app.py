#!/usr/bin/env python3
"""
{{BUSINESS_NAME}} Local Data API
Bridges browser HTML tools and Python scripts using shared JSON files.
Port: 18788 (localhost only)

Endpoints:
  GET/POST  /cuentas.json      -> cuentas-data.json
  GET/POST  /clientes.json     -> clientes-db.json
  GET/POST  /facturas.json     -> facturas-data.json
  GET       /pdf/<filename>    -> serves PDF/PNG/JPG from PENDIENTES & COTIZACIONES dirs
  POST      /ai-proxy          -> proxies to {{AGENT_NAME}} at localhost:18789 (CORS bridge)
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import base64, json, re, sys, unicodedata, urllib.request, urllib.error, subprocess, shutil
from pathlib import Path
from urllib.parse import unquote

BASE = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}')

# clawdbot ({{AGENT_NAME}}) para envío de seguimientos por WhatsApp
NODE = shutil.which('node') or r'node'
OPENCLAW = shutil.which('openclaw') or 'openclaw'
{{BUSINESS_NAME}}_ACCOUNT = '{{WHATSAPP_ACCOUNT}}'  # cuenta WhatsApp de OpenClaw para este agente
CLAWDBOT_ENTRY = r'C:\Users\USER\AppData\Roaming\npm\node_modules\clawdbot\dist\entry.js'


def to_e164(raw):
    """Normaliza un teléfono colombiano a E.164 (+57...). Devuelve None si no es válido."""
    d = re.sub(r'\D', '', str(raw or ''))
    if not d:
        return None
    if d.startswith('57') and len(d) == 12:   # ya trae código país
        return '+' + d
    if len(d) == 10 and d.startswith('3'):     # celular local
        return '+57' + d
    if len(d) >= 11:                            # algo con código país u otro
        return '+' + d
    return None

ROUTES = {
    '/cuentas.json':  (BASE / 'cuentas-data.json',  '{}'),
    '/clientes.json': (BASE / 'clientes-db.json',   '{"clientes": []}'),
    '/facturas.json': (BASE / 'facturas-data.json',  '{"facturas": []}'),
    '/visitas.json':  (BASE / 'visitas-data.json',  '{"visitas": []}'),
    '/productos.json': (BASE / 'productos-db.json',  '{"productos": []}'),
}

PDF_DIRS = [
    # Carpeta prioritaria: documentos activos / por entregar
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/PENDIENTES/X ENTREGAR'),
]
PDF_ROOTS = [
    # Búsqueda recursiva (histórico por año/mes) como fallback
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/PENDIENTES'),
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/COTIZACIONES'),
    Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/FACTURAS ELECTRONICAS'),
]
PDF_EXTS = ['.pdf', '.png', '.jpg', '.jpeg']
MIME = {
    '.pdf':  'application/pdf',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
}

ALBY_URL  = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
ALBY_AUTH = 'Bearer ' + os.environ.get('GOOGLE_API_KEY', '')

PORT = 18788


def _norm(s):
    s = str(s).upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()   # colapsa espacios dobles (clave para matchear)


def _mime_for(f):
    return MIME.get(f.suffix.lower(), 'application/octet-stream')


def find_pdf(name):
    """Busca <name> por nombre de cliente. Primero carpeta prioritaria,
    luego recursivo sobre PDF_ROOTS. Devuelve (Path, mime) o (None, None)."""
    name_norm = _norm(name)

    # 1) Carpeta(s) prioritaria(s): nombre exacto, luego stem normalizado
    for d in PDF_DIRS:
        if not d.exists():
            continue
        for ext in PDF_EXTS:
            f = d / (name + ext)
            if f.exists():
                return f, MIME[ext]
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() in PDF_EXTS and _norm(f.stem) == name_norm:
                return f, _mime_for(f)

    # 2) Fallback recursivo: junta todos los matches y prioriza
    #    'X ENTREGAR' (activo) y, en empate, el más reciente.
    matches = []
    for root in PDF_ROOTS:
        if not root.exists():
            continue
        for f in root.rglob('*'):
            if f.is_file() and f.suffix.lower() in PDF_EXTS and _norm(f.stem) == name_norm:
                matches.append(f)
    if matches:
        def rank(f):
            pri = 0 if 'X ENTREGAR' in str(f).upper() else 1
            try:
                mt = f.stat().st_mtime
            except OSError:
                mt = 0
            return (pri, -mt)
        matches.sort(key=rank)
        return matches[0], _mime_for(matches[0])

    return None, None


# ── Sincronización estado de orden → carpeta física ──────────────────
PEND_BASE = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/docs/PENDIENTES')
MES_ES = ['', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
          'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
MOVE_LOG = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/mover-doc.log')


def target_folder(estado, saldo, fecha_entrega_real):
    """Carpeta destino según el estado de la orden (y saldo para entregado)."""
    e = (estado or '').lower().strip()
    if e == 'cotizado':       return PEND_BASE / 'COTIZACIONES'
    if e == 'en_fabricacion': return PEND_BASE / 'X FABRICAR'
    if e == 'instalacion':    return PEND_BASE / 'X INSTALAR'
    if e == 'listo':          return PEND_BASE / 'X ENTREGAR'
    if e == 'entregado':
        try:
            s = float(str(saldo).replace(',', '').replace('$', '') or 0)
        except ValueError:
            s = 0
        if s > 0:
            return PEND_BASE / 'X COBRAR'
        f = str(fecha_entrega_real or '')
        try:
            y, m = f[:4], int(f[5:7])
            return PEND_BASE / 'ENTREGADO' / y / MES_ES[m]
        except (ValueError, IndexError):
            from datetime import datetime as _dt
            now = _dt.now()
            return PEND_BASE / 'ENTREGADO' / str(now.year) / MES_ES[now.month]
    return None


def find_all_docs(name):
    """Todos los archivos (pdf/img) cuyo nombre coincide con el cliente, en todas las raíces."""
    name_norm = _norm(name)
    seen, out = set(), []
    roots = list(PDF_DIRS) + list(PDF_ROOTS)
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob('*'):
            if (f.is_file() and f.suffix.lower() in PDF_EXTS
                    and _norm(f.stem) == name_norm and str(f) not in seen):
                seen.add(str(f))
                out.append(f)
    return out


def move_client_docs(name, target, dry_run=False):
    """Mueve los docs del cliente a la carpeta destino. NUNCA pisa ni borra.
    Devuelve lista de movimientos {from,to} o {skip,reason}."""
    import shutil
    results = []
    for f in find_all_docs(name):
        if f.parent.resolve() == target.resolve():
            results.append({'skip': f.name, 'reason': 'ya_en_destino'})
            continue
        dest = target / f.name
        if dest.exists():
            results.append({'skip': f.name, 'reason': 'destino_ocupado'})
            continue
        if dry_run:
            results.append({'from': str(f), 'to': str(dest), 'dry_run': True})
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            results.append({'from': str(f), 'to': str(dest)})
            try:
                from datetime import datetime as _dt
                with open(MOVE_LOG, 'a', encoding='utf-8') as lg:
                    lg.write(f"{_dt.now().isoformat()}\t{name}\t{f}\t-> {dest}\n")
            except OSError:
                pass
        except OSError as ex:
            results.append({'skip': f.name, 'reason': str(ex)})
    return results


import hmac as _hmac, hashlib as _hashlib, time as _time, secrets as _secrets
try:
    import bcrypt as _bcrypt
except Exception:
    _bcrypt = None
_AUTH_HASH_FILE = Path("/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/.auth_hash")
_AUTH_SECRET_FILE = Path("/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/.auth_secret")
_SESSION_DAYS = 30


def _auth_secret():
    try:
        return _AUTH_SECRET_FILE.read_bytes()
    except Exception:
        import os as _os
        sec = _secrets.token_bytes(32)
        try:
            _AUTH_SECRET_FILE.write_bytes(sec)
            _os.chmod(_AUTH_SECRET_FILE, 0o600)
        except Exception:
            pass
        return sec


def _auth_hash():
    try:
        return _AUTH_HASH_FILE.read_text().strip().encode()
    except Exception:
        return b""


def _make_session():
    exp = str(int(_time.time()) + _SESSION_DAYS * 86400)
    sig = _hmac.new(_auth_secret(), exp.encode(), _hashlib.sha256).hexdigest()
    return exp + "." + sig


def _valid_session(tok):
    try:
        exp, sig = (tok or "").split(".", 1)
        good = _hmac.new(_auth_secret(), exp.encode(), _hashlib.sha256).hexdigest()
        return _hmac.compare_digest(sig, good) and int(exp) > int(_time.time())
    except Exception:
        return False


class ARKHandler(BaseHTTPRequestHandler):
    timeout = 10

    def _cookie_tok(self):
        for part in (self.headers.get("Cookie", "") or "").split(";"):
            part = part.strip()
            if part.startswith("ark_session="):
                return part[len("ark_session="):]
        return ""

    def _authed(self):
        return self.client_address[0] in ("127.0.0.1", "::1") or _valid_session(self._cookie_tok())

    def _deny(self):
        self.send_response(401)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_HEAD(self):
        if not self._authed():
            return self._deny()
        if not self.path.startswith('/pdf/'):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        try:
            raw_name = unquote(self.path[5:])
            file_path, mime = find_pdf(raw_name)
            if not file_path:
                self.send_response(404)
                self._cors()
                self.end_headers()
                return
            size = file_path.stat().st_size
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(size))
            self.send_header('Content-Disposition', f'inline; filename="{file_path.name}"')
            self._cors()
            self.end_headers()
        except Exception:
            self.send_response(500)
            self._cors()
            self.end_headers()

    def do_GET(self):
        _p = self.path.split('?', 1)[0]
        if _p == '/auth/check':
            if _valid_session(self._cookie_tok()):
                self.send_response(200); self._cors(); self.end_headers()
            else:
                self.send_response(302)
                self.send_header('Location', '/login.html')
                self._cors(); self.end_headers()
            return
        if not self._authed():
            return self._deny()
        route = ROUTES.get(self.path)
        if route:
            file_path, default = route
            body = (file_path.read_text(encoding='utf-8')
                    if file_path.exists() else default).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith('/pdf/'):
            self._serve_pdf(head_only=False)
            return

        # Servir las herramientas HTML del workspace en el MISMO origen (evita file:// + bloqueo de POST a localhost)
        if self.path.endswith('.html'):
            name = unquote(self.path.lstrip('/'))
            try:
                html_file = (BASE / name).resolve()
            except Exception:
                html_file = None
            if html_file and html_file.exists() and html_file.suffix.lower() == '.html' and BASE.resolve() in html_file.parents:
                body = html_file.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._cors()
                self.end_headers()
                self.wfile.write(body)
                return

        self.send_response(404)
        self._cors()
        self.end_headers()

    def _serve_pdf(self, head_only=False):
        raw_name = unquote(self.path[5:])
        file_path, mime = find_pdf(raw_name)
        if not file_path:
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        size = file_path.stat().st_size
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Disposition', 'inline')
        self._cors()
        self.end_headers()
        if not head_only:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        _p = self.path.split('?', 1)[0]
        if _p == '/login':
            length = int(self.headers.get('Content-Length', 0))
            try:
                data = json.loads(self.rfile.read(length) or b'{}')
            except Exception:
                data = {}
            pw = (data.get('password') or '').encode()
            h = _auth_hash()
            ok = bool(_bcrypt and h and _bcrypt.checkpw(pw, h))
            if ok:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Set-Cookie', 'ark_session=%s; HttpOnly; Path=/; Max-Age=%d; SameSite=Lax' % (_make_session(), _SESSION_DAYS * 86400))
                self._cors(); self.end_headers()
                self.wfile.write(b'{"ok": true}')
            else:
                self._json(401, {'ok': False, 'error': 'Clave incorrecta'})
            return
        if _p == '/logout':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Set-Cookie', 'ark_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax')
            self._cors(); self.end_headers()
            self.wfile.write(b'{"ok": true}')
            return
        if not self._authed():
            return self._deny()
        # AI proxy - bridges file:// CORS to {{AGENT_NAME}} on 18789
        if self.path == '/ai-proxy':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                # Map model names for OpenRouter
                req_body = json.loads(body)
                if req_body.get('model') in ('clawdbot', None, ''):
                    req_body['model'] = 'gemini-2.5-flash-lite'
                body = json.dumps(req_body).encode()
                req = urllib.request.Request(
                    ALBY_URL,
                    data=body,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': ALBY_AUTH,
                        'X-Title': '{{BUSINESS_NAME}} Facturas IA',
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp_body = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp_body)))
                self._cors()
                self.end_headers()
                self.wfile.write(resp_body)
            except Exception as e:
                err = json.dumps({'error': str(e)}).encode()
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self._cors()
                self.end_headers()
                self.wfile.write(err)
            return

        # Seguimiento de cotizaciones: envía WhatsApp vía {{AGENT_NAME}} (clawdbot)
        if self.path == '/seguimiento':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
            except Exception:
                return self._json(400, {'ok': False, 'error': 'JSON inválido'})
            tel = to_e164(data.get('telefono', ''))
            msg = (data.get('mensaje') or '').strip()
            if not tel:
                return self._json(400, {'ok': False, 'error': 'Teléfono inválido (se esperaba celular colombiano)'})
            if not msg:
                return self._json(400, {'ok': False, 'error': 'Mensaje vacío'})
            cmd = [OPENCLAW, 'message', 'send', '--account', {{BUSINESS_NAME}}_ACCOUNT,
                   '--target', tel, '--channel', 'whatsapp', '--message', msg, '--json']
            # Adjuntar el documento del cliente (recibo) si se pide y existe
            adjunto = None
            if data.get('adjuntar_doc') and data.get('cliente'):
                fp, _m = find_pdf(data['cliente'])
                if fp:
                    cmd += ['--media', str(fp)]
                    adjunto = fp.name
            # Adjuntar la tarjeta de presentacion de {{BUSINESS_NAME}} (bienvenida)
            if data.get('adjuntar_tarjeta'):
                tarjeta = Path(r'/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/assets/{{BUSINESS_NAME}} TARJETA.jpeg')
                if tarjeta.exists():
                    cmd += ['--media', str(tarjeta)]
                    adjunto = tarjeta.name
            if data.get('dry_run'):
                cmd.append('--dry-run')
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    return self._json(200, {'ok': True, 'target': tel,
                                            'dry_run': bool(data.get('dry_run')),
                                            'adjunto': adjunto,
                                            'out': (res.stdout or '')[-600:]})
                return self._json(502, {'ok': False, 'target': tel,
                                        'error': (res.stderr or res.stdout or 'fallo desconocido')[-600:]})
            except subprocess.TimeoutExpired:
                return self._json(504, {'ok': False, 'error': 'Timeout enviando por {{AGENT_NAME}}'})
            except Exception as e:
                return self._json(502, {'ok': False, 'error': str(e)})

        # Sincroniza el documento del cliente con la carpeta del estado de la orden
        if self.path == '/mover-doc':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
            except Exception:
                return self._json(400, {'ok': False, 'error': 'JSON inválido'})
            cliente = (data.get('cliente') or '').strip()
            estado  = data.get('estado')
            target  = target_folder(estado, data.get('saldo', 0), data.get('fecha_entrega_real'))
            if not cliente or target is None:
                return self._json(400, {'ok': False, 'error': 'faltan cliente o estado válido'})
            try:
                moves = move_client_docs(cliente, target, dry_run=bool(data.get('dry_run')))
                actual = [m for m in moves if 'from' in m]
                return self._json(200, {'ok': True, 'target': str(target),
                                        'moved': len(actual), 'detail': moves})
            except Exception as e:
                return self._json(500, {'ok': False, 'error': str(e)})

        # Save PDF from quotation generator (POST from facturas-v2.html)
        if self.path == '/save-pdf':
            length = int(self.headers.get('Content-Length', 0))
            try:
                data = json.loads(self.rfile.read(length))
            except Exception:
                return self._json(400, {'ok': False, 'error': 'JSON invalido'})
            cliente = (data.get('cliente') or 'DOCUMENTO').strip()
            estado  = data.get('estado') or 'en_fabricacion'
            pdf_b64 = data.get('pdf') or ''
            try:
                open('/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/save-pdf.log','a').write('RECIBIDO cliente=%r estado=%r bytes=%d\n' % (cliente, estado, len(pdf_b64)))
            except Exception:
                pass
            if not pdf_b64:
                return self._json(400, {'ok': False, 'error': 'falta pdf'})
            folder = target_folder(estado, data.get('saldo', 0),
                                   data.get('fecha_entrega_real')) or (PEND_BASE / 'X FABRICAR')
            try:
                folder.mkdir(parents=True, exist_ok=True)
                safe = cliente.replace('/', '-').replace(chr(92), '-').strip().upper() or 'DOCUMENTO'
                dest = folder / (safe + '.pdf')
                raw = pdf_b64.split(',', 1)[-1]
                dest.write_bytes(base64.b64decode(raw))
                try:
                    open('/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}/save-pdf.log','a').write('OK ' + str(dest) + '\n')
                except Exception:
                    pass
                return self._json(200, {'ok': True, 'ruta': str(dest), 'carpeta': folder.name})
            except Exception as e:
                return self._json(500, {'ok': False, 'error': str(e)})

        if _p == '/regen-pdf':
            length = int(self.headers.get('Content-Length', 0))
            try:
                data = json.loads(self.rfile.read(length) or b'{}')
            except Exception:
                return self._json(400, {'ok': False, 'error': 'JSON invalido'})
            cliente = (data.get('cliente') or '').strip()
            if not cliente:
                return self._json(400, {'ok': False, 'error': 'falta cliente'})
            try:
                node = shutil.which('node') or '/usr/bin/node'
                res = subprocess.run([node, '{{PDFGEN_DIR}}/generate_pdfs.js', cliente],
                                     capture_output=True, text=True, timeout=150,
                                     cwd='{{PDFGEN_DIR}}')
                out = (res.stdout or '') + (res.stderr or '')
                ok = ('OK ' in out)
                return self._json(200 if ok else 500, {'ok': ok, 'out': out[-400:]})
            except subprocess.TimeoutExpired:
                return self._json(504, {'ok': False, 'error': 'timeout regenerando PDF'})
            except Exception as e:
                return self._json(500, {'ok': False, 'error': str(e)})

        route = ROUTES.get(self.path)
        if not route:
            self.send_response(404)
            self.end_headers()
            return

        file_path, _ = route
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)

        try:
            json.loads(body)
        except json.JSONDecodeError as e:
            resp = json.dumps({'ok': False, 'error': str(e)}).encode()
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(resp)
            return

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(body)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def handle_error(self, request, client_address):
        pass

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), ARKHandler)  # loopback + Tailscale (firewall restringe el resto)
    print(f'ARK API listening on http://127.0.0.1:{PORT}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopped.')
        sys.exit(0)

