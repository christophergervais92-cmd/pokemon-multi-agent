// Service Worker for PokeAgent - Offline Support & Smart Caching
// UPDATED: v4 - Stale-While-Revalidate for API, optimized caching strategies
const CACHE_VERSION = 'v4';
const STATIC_CACHE = `pokeagent-static-${CACHE_VERSION}`;
const API_CACHE = `pokeagent-api-${CACHE_VERSION}`;
const IMAGE_CACHE = `pokeagent-images-${CACHE_VERSION}`;

// Cache TTLs (in milliseconds)
const CACHE_TTL = {
    api: 5 * 60 * 1000,        // 5 minutes for API data
    cards: 60 * 60 * 1000,     // 1 hour for card data
    images: 24 * 60 * 60 * 1000, // 24 hours for images
    static: 7 * 24 * 60 * 60 * 1000 // 7 days for static assets
};

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/dashboard.html',
    '/index.html'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    self.skipWaiting();
    
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => {
                console.log('Cache install failed:', err);
            });
        })
    );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (!cacheName.includes(CACHE_VERSION)) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

/**
 * Stale-While-Revalidate strategy
 * Returns cached response immediately, then updates cache in background
 */
async function staleWhileRevalidate(request, cacheName, ttl) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    // Start network fetch (don't await - background update)
    const fetchPromise = fetch(request)
        .then(response => {
            if (response.ok) {
                // Store response with timestamp
                const responseToCache = response.clone();
                cache.put(request, responseToCache);
            }
            return response;
        })
        .catch(err => {
            console.log('Background fetch failed:', err);
            return null;
        });
    
    // Return cached immediately if available
    if (cachedResponse) {
        return cachedResponse;
    }
    
    // No cache, wait for network
    return fetchPromise;
}

/**
 * Network first with cache fallback
 */
async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        throw err;
    }
}

/**
 * Cache first with network fallback
 */
async function cacheFirst(request, cacheName) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    const response = await fetch(request);
    if (response.ok) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
    }
    return response;
}

// Fetch event - smart caching strategies
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip cross-origin requests (except allowed APIs and images)
    const allowedOrigins = [
        'api.pokemontcg.io',
        'images.pokemontcg.io',
        'fonts.googleapis.com',
        'fonts.gstatic.com',
        'unpkg.com'
    ];
    
    if (url.origin !== location.origin && 
        !allowedOrigins.some(origin => url.href.includes(origin))) {
        return;
    }
    
    // HTML files: Network First (always get latest code)
    if (request.url.endsWith('.html') || 
        request.url.endsWith('/') || 
        request.destination === 'document') {
        event.respondWith(
            networkFirst(request, STATIC_CACHE)
                .catch(() => caches.match('/dashboard.html'))
        );
        return;
    }
    
    // Pokemon TCG API: Stale-While-Revalidate
    if (url.href.includes('api.pokemontcg.io')) {
        event.respondWith(
            staleWhileRevalidate(request, API_CACHE, CACHE_TTL.cards)
        );
        return;
    }
    
    // Pokemon card images: Cache First (long TTL)
    if (url.href.includes('images.pokemontcg.io')) {
        event.respondWith(
            cacheFirst(request, IMAGE_CACHE)
        );
        return;
    }
    
    // Backend API: Stale-While-Revalidate
    if (request.url.includes('/api/') || 
        request.url.includes('/scanner/') ||
        request.url.includes('/prices/') ||
        request.url.includes('/drops')) {
        event.respondWith(
            staleWhileRevalidate(request, API_CACHE, CACHE_TTL.api)
                .catch(() => {
                    return new Response(
                        JSON.stringify({ error: 'Offline - cached data unavailable' }),
                        {
                            status: 503,
                            headers: { 'Content-Type': 'application/json' }
                        }
                    );
                })
        );
        return;
    }
    
    // Fonts: Cache First (long TTL)
    if (url.href.includes('fonts.googleapis.com') || 
        url.href.includes('fonts.gstatic.com')) {
        event.respondWith(cacheFirst(request, STATIC_CACHE));
        return;
    }
    
    // Other static assets: Cache First
    event.respondWith(
        cacheFirst(request, STATIC_CACHE)
    );
});

// Message handler for cache management
self.addEventListener('message', (event) => {
    if (event.data) {
        switch (event.data.type) {
            case 'CLEAR_CACHE':
                Promise.all([
                    caches.delete(STATIC_CACHE),
                    caches.delete(API_CACHE),
                    caches.delete(IMAGE_CACHE)
                ]).then(() => {
                    if (event.ports[0]) {
                        event.ports[0].postMessage({ success: true });
                    }
                });
                break;
                
            case 'CLEAR_API_CACHE':
                caches.delete(API_CACHE).then(() => {
                    if (event.ports[0]) {
                        event.ports[0].postMessage({ success: true });
                    }
                });
                break;
                
            case 'GET_CACHE_STATS':
                Promise.all([
                    caches.open(STATIC_CACHE).then(c => c.keys()),
                    caches.open(API_CACHE).then(c => c.keys()),
                    caches.open(IMAGE_CACHE).then(c => c.keys())
                ]).then(([staticKeys, apiKeys, imageKeys]) => {
                    if (event.ports[0]) {
                        event.ports[0].postMessage({
                            static: staticKeys.length,
                            api: apiKeys.length,
                            images: imageKeys.length,
                            version: CACHE_VERSION
                        });
                    }
                });
                break;
        }
    }
});
