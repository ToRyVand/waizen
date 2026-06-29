const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = '/home/ubuntu/clientes/{{WHATSAPP_ACCOUNT}}';
const DASH = '/home/ubuntu/projects/{{WHATSAPP_ACCOUNT}}-dashboard';
const HTMLFILE = 'file://' + DASH + '/facturas.html';
const PEND = BASE + '/docs/PENDIENTES';

const MES = ['', 'ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'];
function fmtFecha(s){ const m=/(\d{4})-(\d{2})-(\d{2})/.exec(s||''); return m ? `${MES[+m[2]]} ${+m[3]} DE ${m[1]}` : (s||''); }
function targetFolder(estado){
  const e=(estado||'').toLowerCase();
  if(e==='cotizado') return PEND+'/COTIZACIONES';
  if(e==='en_fabricacion') return PEND+'/X FABRICAR';
  if(e==='listo') return PEND+'/X ENTREGAR';
  if(e==='instalacion') return PEND+'/X INSTALAR';
  return PEND+'/X FABRICAR';
}
function safeName(s){ return (s||'DOCUMENTO').toUpperCase().replace(/[<>:"/\\|?*]/g,' ').replace(/\s+/g,' ').trim() || 'DOCUMENTO'; }

// Optional batch list of client names to (re)generate. Usually you pass a single
// client name as an argument: `node generate_pdfs.js "CLIENT NAME"`.
const MISSING = [];

const filter = process.argv[2] || null; // optional: only this client (test)

const data = JSON.parse(fs.readFileSync(BASE+'/clientes-db.json','utf8'));
const targets = [];
for (const c of data.clientes) {
  if (filter) { if (c.nombre !== filter) continue; }
  else if (!MISSING.includes(c.nombre)) continue;
  const orders = (c.pedidos||[]).filter(p => ['cotizado','en_fabricacion','listo','instalacion'].includes((p.estado||'').toLowerCase()));
  let best = null;
  for (const p of orders) if ((p.items||[]).length && (!best || p.items.length > (best.items||[]).length)) best = p;
  if (!best) { for (const p of orders) if (p.total) { best = {...p, items:[{qty:1, desc:(p.descripcion||c.nombre), price:p.total}]}; break; } }
  if (!best) continue;
  targets.push({
    cliente: c.nombre, dir: c.direccion||'', tel: c.telefono||'', nit: c.cedula_nit||'',
    fecha: fmtFecha(best.fecha_pedido), items: best.items, total: best.total||0, abono: best.abono||0,
    estado: best.estado, notas: best.notas||''
  });
}
console.log('targets:', targets.length, targets.map(t=>t.cliente).join(' | '));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 1200 } });
  await page.goto(HTMLFILE, { waitUntil: 'load' });
  await page.waitForTimeout(1000);
  const libs = await page.evaluate(() => ({ h2c: !!window.html2canvas, jspdf: !!window.jspdf, render: typeof renderPreview }));
  console.log('libs:', JSON.stringify(libs));

  let ok=0, fail=0;
  for (const t of targets) {
    try {
      const docType = (t.estado||'').toLowerCase()==='cotizado' ? 'cotizacion' : 'recibo';
      const nm = (t.notas||'').match(/#\s*0*(\d+)/); const docNum = nm ? nm[1] : '1';
      await page.evaluate((a) => {
        document.getElementById('f-cliente').value = a.t.cliente;
        document.getElementById('f-dir').value = a.t.dir;
        document.getElementById('f-tel').value = a.t.tel;
        document.getElementById('f-nit').value = a.t.nit;
        document.getElementById('f-fecha').value = a.t.fecha;
        document.getElementById('f-total').value = a.t.total;
        document.getElementById('f-abono').value = a.t.abono || '';
        // assign GLOBAL lexical bindings used by renderPreview (no local shadowing)
        items = a.t.items.map(it => ({ qty: it.qty || 1, desc: it.desc || '', price: it.price || 0 }));
        docType = a.dt;
        localStorage.setItem(a.dt === 'recibo' ? 'ark_recibo_num' : 'ark_cotizacion_num', a.docNum);
        renderPreview();
      }, { t, dt: docType, docNum });
      await page.waitForTimeout(350);
      const b64 = await page.evaluate(async () => {
        const el = document.getElementById('invoice-print');
        const canvas = await html2canvas(el, { scale: 2, useCORS: true, backgroundColor: '#ffffff' });
        const img = canvas.toDataURL('image/jpeg', 0.96);
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('l', 'mm', 'a4');
        const pw = pdf.internal.pageSize.getWidth(), ph = pdf.internal.pageSize.getHeight();
        const imgH = canvas.height * pw / canvas.width;
        let left = imgH, pos = 0;
        pdf.addImage(img, 'JPEG', 0, pos, pw, imgH); left -= ph;
        while (left > 0) { pos -= ph; pdf.addPage(); pdf.addImage(img, 'JPEG', 0, pos, pw, imgH); left -= ph; }
        return pdf.output('datauristring').split(',')[1];
      });
      const folder = targetFolder(t.estado);
      fs.mkdirSync(folder, { recursive: true });
      const dest = path.join(folder, safeName(t.cliente) + '.pdf');
      fs.writeFileSync(dest, Buffer.from(b64, 'base64'));
      console.log('OK  ', (Buffer.from(b64,'base64').length/1024|0)+'KB', dest);
      ok++;
    } catch (e) {
      console.log('FAIL', t.cliente, e.message);
      fail++;
    }
  }
  await browser.close();
  console.log(`\nDONE ok=${ok} fail=${fail}`);
})();
