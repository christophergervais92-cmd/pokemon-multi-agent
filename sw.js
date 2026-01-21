// Service Worker for PokeAgent - Offline Support & Caching
const CACHE_NAME = 'pokeagent-v1';
const STATIC_CACHE = 'pokeagent-static-v1';
const API_CACHE = 'pokeagent-api-v1';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/dashboard.html',
    '/index.html'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => {
                console.log('Cache install failed:', err);
            });
        })
    );
    self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME && 
                        cacheName !== STATIC_CACHE && 
                        cacheName !== API_CACHE) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    if (request.method !== 'GET') return;
    if (url.origin !== location.origin && !url.href.includes('api.pokemontcg.io')) return;
    
    if (request.url.includes('/api/') || request.url.includes('api.pokemontcg.io')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(API_CACHE).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    return caches.match(request).then((cachedResponse) => {
                        return cachedResponse || new Response(
                            JSON.stringify({ error: 'Offline - using cached data' }),
                            { status: 200, headers: { 'Content-Type': 'application/json' } }
                        );
                    });
                })
        );
    } else {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                return cachedResponse || fetch(request).then((response) => {
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(STATIC_CACHE).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                });
            })
        );
    }
});

self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'CLEAR_CACHE') {
        caches.delete(API_CACHE).then(() => {
            event.ports[0].postMessage({ success: true });
        });
    }
});
