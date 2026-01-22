// Service Worker for PokeAgent - Offline Support & Caching
// UPDATED: v3 - Network First for HTML to fix caching issues
const CACHE_NAME = 'pokeagent-v3';
const STATIC_CACHE = 'pokeagent-static-v3';
const API_CACHE = 'pokeagent-api-v3';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/dashboard.html',
    '/index.html'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    // Skip waiting - activate immediately
    self.skipWaiting();
    
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => {
                console.log('Cache install failed:', err);
            });
        })
    );
});

// Activate event - clean ALL old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    // Delete ALL old caches (v1, v2, etc)
                    if (!cacheName.includes('v3')) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    // Take control of all clients immediately
    return self.clients.claim();
});

// Fetch event - NETWORK FIRST for HTML, cache first for other static assets
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip cross-origin requests (except our API and images)
    if (url.origin !== location.origin && 
        !url.href.includes('api.pokemontcg.io') &&
        !url.href.includes('images.pokemontcg.io')) {
        return;
    }
    
    // HTML files: ALWAYS Network First (to get latest code)
    if (request.url.endsWith('.html') || request.url.endsWith('/') || request.destination === 'document') {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cache the fresh response
                    if (response.ok) {
                        const responseClone = response.clone();
                        caches.open(STATIC_CACHE).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Network failed, use cache as fallback
                    return caches.match(request);
                })
        );
        return;
    }
    
    // API: Network First with cache fallback
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
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        return new Response(
                            JSON.stringify({ error: 'Offline - using cached data' }),
                            {
                                status: 200,
                                headers: { 'Content-Type': 'application/json' }
                            }
                        );
                    });
                })
        );
        return;
    }
    
    // Other static assets (images, fonts, etc): Cache First
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(request).then((response) => {
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
});

// Message handler for cache management
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'CLEAR_CACHE') {
        Promise.all([
            caches.delete(STATIC_CACHE),
            caches.delete(API_CACHE),
            caches.delete(CACHE_NAME)
        ]).then(() => {
            event.ports[0].postMessage({ success: true });
        });
    }
});
