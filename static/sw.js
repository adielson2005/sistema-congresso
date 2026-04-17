// Service Worker - Sistema Cadepa PWA
const CACHE_VERSION = 'v1';
const SHELL_CACHE = `cadepa-shell-${CACHE_VERSION}`;
const DATA_CACHE  = `cadepa-data-${CACHE_VERSION}`;

// Recursos do app shell para cache inicial (carregados offline)
const SHELL_ASSETS = [
    '/static/manifest.json',
    '/static/icons/icon.svg',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
];

// ─── Install ──────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_ASSETS))
    );
    self.skipWaiting();
});

// ─── Activate ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(k => k !== SHELL_CACHE && k !== DATA_CACHE)
                    .map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// ─── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignora requisições que não sejam GET ou de extensões do browser
    if (request.method !== 'GET') return;
    if (url.protocol === 'chrome-extension:') return;

    // API calls → network-first (dados sempre frescos, sem cache stale)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request, DATA_CACHE));
        return;
    }

    // Assets estáticos próprios (/static/) → cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(request, SHELL_CACHE));
        return;
    }

    // CDN (Bootstrap, Chart.js) → stale-while-revalidate
    if (url.hostname.includes('cdn.jsdelivr.net')) {
        event.respondWith(staleWhileRevalidate(request, SHELL_CACHE));
        return;
    }

    // Páginas da aplicação → network-first com fallback offline
    event.respondWith(networkFirst(request, SHELL_CACHE));
});

// ─── Estratégias de cache ─────────────────────────────────────────────────────

async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
    }
    return response;
}

async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        // Fallback offline simples para páginas HTML
        if (request.headers.get('accept')?.includes('text/html')) {
            return new Response(
                `<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sem conexão – Sistema Cadepa</title>
<style>
  body{font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;
       min-height:100vh;margin:0;background:#f4f6f8;text-align:center;}
  .card{background:#fff;padding:40px;border-radius:20px;box-shadow:0 4px 18px rgba(0,0,0,.08);max-width:400px;}
  h1{color:#2563eb;margin-bottom:8px;}p{color:#6b7280;}
  button{background:linear-gradient(90deg,#2563eb,#4f46e5);color:#fff;border:none;
         padding:12px 28px;border-radius:10px;cursor:pointer;font-size:15px;margin-top:16px;}
</style></head>
<body>
  <div class="card">
    <h1>Sistema Cadepa</h1>
    <p>Sem conexão com a internet.<br>Verifique sua rede e tente novamente.</p>
    <button onclick="location.reload()">Tentar novamente</button>
  </div>
</body></html>`,
                { status: 503, headers: { 'Content-Type': 'text/html;charset=utf-8' } }
            );
        }
        return new Response('Offline', { status: 503 });
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) cache.put(request, response.clone());
        return response;
    }).catch(() => cached);
    return cached || fetchPromise;
}
