const CACHE_NAME = 'rhythmic-static-v1';
const STATIC_ASSETS = [
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/offline.html'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  // Never cache HTML pages or authenticated/API responses: keep account sessions private and fresh.
  if (url.pathname.startsWith('/api/') || request.mode === 'navigate') {
    if (request.mode === 'navigate') {
      event.respondWith(fetch(request).catch(() => caches.match('/static/offline.html')));
    }
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) { const copy = response.clone(); caches.open(CACHE_NAME).then(cache => cache.put(request, copy)); }
      return response;
    })));
  }
});
