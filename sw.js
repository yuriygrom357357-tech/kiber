/* КІБЕР — service worker: офлайн-кеш курсу */
const CACHE = "kb-86016";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "vendor/html2pdf.bundle.min.js", "vendor/docx.min.js", "icons/emblem.png", "fonts/dela-gothic-one-cyrillic-400-normal.woff2", "fonts/dela-gothic-one-latin-400-normal.woff2", "fonts/fira-sans-condensed-cyrillic-600-normal.woff2", "fonts/fira-sans-condensed-cyrillic-700-normal.woff2", "fonts/fira-sans-condensed-latin-600-normal.woff2", "fonts/fira-sans-condensed-latin-700-normal.woff2", "fonts/ibm-plex-sans-cyrillic-400-normal.woff2", "fonts/ibm-plex-sans-cyrillic-600-normal.woff2", "fonts/ibm-plex-sans-latin-400-normal.woff2", "fonts/ibm-plex-sans-latin-600-normal.woff2", "fonts/jetbrains-mono-cyrillic-400-normal.woff2", "fonts/jetbrains-mono-cyrillic-700-normal.woff2", "fonts/jetbrains-mono-latin-400-normal.woff2", "fonts/jetbrains-mono-latin-700-normal.woff2"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith("kb-") && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
async function ranged(resp, range) {
  const buf = await resp.arrayBuffer(); const n = buf.byteLength;
  const m = /bytes=(\d*)-(\d*)/.exec(range || "");
  let s = m && m[1] ? +m[1] : 0, e = m && m[2] ? +m[2] : n - 1;
  if (m && !m[1] && m[2]) { s = Math.max(0, n - +m[2]); e = n - 1; }
  e = Math.min(e, n - 1);
  return new Response(buf.slice(s, e + 1), {status: 206, statusText: "Partial Content", headers: {
    "Content-Type": resp.headers.get("Content-Type") || "audio/mpeg", "Content-Range": `bytes ${s}-${e}/${n}`,
    "Content-Length": String(e - s + 1), "Accept-Ranges": "bytes"}});
}
self.addEventListener("fetch", e => {
  const req = e.request; const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  // сторінка: спершу мережа (щоб отримувати оновлення), без мережі — кеш
  if (req.mode === "navigate" || url.pathname.endsWith("/index.html")) {
    e.respondWith((async () => {
      try {
        const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 4000);
        const r = await fetch(req, {signal: ctrl.signal}); clearTimeout(t);
        if (r.ok) { const c = await caches.open(CACHE); c.put("index.html", r.clone()); }
        return r;
      } catch (err) {
        const c = await caches.open(CACHE);
        return (await c.match("index.html")) || (await c.match("./")) || Response.error();
      }
    })());
    return;
  }
  // аудіо та інше: спершу кеш (з підтримкою Range для плеєра)
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const hit = await c.match(req.url, {ignoreSearch: true, ignoreVary: true});
    if (hit) return req.headers.has("range") ? ranged(hit, req.headers.get("range")) : hit;
    return fetch(req);
  })());
});
