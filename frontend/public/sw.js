/* SlimLight — PWA service worker.
 * Strategy: always show the LATEST version on every visit.
 *   - index.html / navigations → network-first (fresh on every load)
 *   - JS/CSS/static assets     → network-first with cache fallback (fresh when online)
 *   - API / TTS / external     → never cached (pass-through)
 *   - Shell fallback           → cached for offline use only
 */
const CACHE = 'miro-shell-v3';
const SHELL = ['/', '/index.html', '/manifest.json', '/icon-192.png', '/icon-512.png', '/favicon.ico'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => null));
  self.skipWaiting();
});

self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // API / TTS / external — never cached
  if (url.pathname.startsWith('/api/') || url.hostname.includes('fonts.g') || url.hostname.includes('openrouter')) {
    return;
  }

  // Navigation (HTML) — always fresh, offline fallback to cached index.html
  if (req.mode === 'navigate' || req.destination === 'document') {
    e.respondWith(
      fetch(req).then((resp) => {
        if (resp && resp.ok) {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put('/index.html', copy));
        }
        return resp;
      }).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Static assets (JS/CSS/images) — network-first, cache fallback
  e.respondWith(
    fetch(req).then((resp) => {
      if (resp && resp.ok && resp.type === 'basic') {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return resp;
    }).catch(() => caches.match(req))
  );
});
