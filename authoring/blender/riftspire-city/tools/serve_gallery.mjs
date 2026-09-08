/** Serve only the exported review images, without exposing the workspace. */
import http from 'node:http';
import { createReadStream, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const host = process.argv.find(a => a.startsWith('--host='))?.slice(7) ?? '127.0.0.1';
const port = Number(process.argv.find(a => a.startsWith('--port='))?.slice(7) ?? 8088);
const images = new Map([
  ['city-district-market.png', 'Blackvein market stalls'],
  ['city-district-crown.png', 'Riftspire Crown monuments'],
  ['city-district-works.png', 'Drowned Works machinery'],
  ['city-district-warrens.png', 'Hollowwall daily life'],
  ['city-district-commons.png', 'Chainwake cooking and haulage'],
  ['city-district-ashgate.png', 'Ashgate military stores'],
  ['city-neighborhood.png', 'Varied cliff neighborhoods'],
  ['city-rim.png', 'Crater overview'],
  ['city-commons.png', 'Suspended settlement'],
  ['city-palace.png', 'Palace interior'],
]);
const html = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Riftspire screenshots</title>'
  + '<style>body{padding:24px;background:#11131a;color:#e9e3d6;font:17px system-ui;max-width:1600px;margin:auto}h1{font-size:28px}figure{margin:32px 0}img{width:100%;height:auto;border-radius:8px}figcaption{margin:10px 0}a{color:#d8c491}</style>'
  + '<h1>Riftspire Citadel</h1><p>District life and Riftbound architecture · exported-model renders</p>'
  + [...images].map(([file,title]) => `<figure><figcaption>${title}</figcaption><a href="/${file}"><img src="/${file}" alt="${title}"></a></figure>`).join('') + '</html>';
http.createServer((req,res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405); return res.end(); }
  const pathname = new URL(req.url, 'http://localhost').pathname;
  if (pathname === '/') {
    res.writeHead(200, {'Content-Type':'text/html; charset=utf-8'});
    return res.end(req.method === 'HEAD' ? '' : html);
  }
  const name = pathname.slice(1);
  if (!images.has(name)) { res.writeHead(404); return res.end('Not found'); }
  const file = fileURLToPath(new URL(`../review/${name}`, import.meta.url));
  try {
    res.writeHead(200, {'Content-Type':'image/png', 'Content-Length':statSync(file).size});
    if (req.method === 'HEAD') return res.end();
    createReadStream(file).on('error', () => res.destroy()).pipe(res);
  } catch { res.writeHead(404); res.end('Preview unavailable'); }
}).listen(port, host, () => console.log(`Riftspire screenshots: http://${host}:${port}/`));
