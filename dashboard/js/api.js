// PokeAgent - API Layer
// Supports both Flask backend and OpenClaw Gateway

// Backend mode: 'flask' or 'openclaw'
const BACKEND_MODE = 'flask'; // Toggle to 'openclaw' when ready

// OpenClaw Gateway WebSocket URL
const OPENCLAW_GATEWAY = 'ws://127.0.0.1:18789';

// OpenClaw agent routing map - maps Flask endpoints to agent+tool pairs
const OPENCLAW_ROUTES = {
    '/scanner/unified':     { agent: 'scanner', tool: 'unified_search' },
    '/scanner/target':      { agent: 'scanner', tool: 'search_target' },
    '/scanner/walmart':     { agent: 'scanner', tool: 'search_walmart' },
    '/scanner/bestbuy':     { agent: 'scanner', tool: 'search_bestbuy' },
    '/scanner/gamestop':    { agent: 'scanner', tool: 'search_gamestop' },
    '/scanner/pokemoncenter': { agent: 'scanner', tool: 'search_pokemoncenter' },
    '/scanner/amazon':      { agent: 'scanner', tool: 'search_amazon' },
    '/scanner/costco':      { agent: 'scanner', tool: 'search_costco' },
    '/scanner/tcgplayer':   { agent: 'scanner', tool: 'search_tcgplayer' },
    '/prices/card':         { agent: 'price', tool: 'lookup_card_price' },
    '/prices/history':      { agent: 'price', tool: 'price_history' },
    '/prices/graded':       { agent: 'price', tool: 'graded_prices' },
    '/market/flip':         { agent: 'market', tool: 'calculate_flip' },
    '/market/orderbook':    { agent: 'market', tool: 'orderbook' },
    '/grade/analyze':       { agent: 'grading', tool: 'grade_card' },
    '/vision/identify':     { agent: 'vision', tool: 'identify_card' },
    '/drops/upcoming':      { agent: 'drops', tool: 'get_upcoming' },
    '/drops/intel':         { agent: 'drops', tool: 'get_live_intel' },
    '/drops/rumors':        { agent: 'drops', tool: 'get_rumors' },
    '/assistant/chat':      { agent: 'assistant', tool: 'chat' },
    '/api/tcg/cards':       { agent: 'tcg-proxy', tool: 'search_cards' },
    '/api/tcg/sets':        { agent: 'tcg-proxy', tool: 'get_sets' },
    '/health':              { agent: null, tool: null }, // Direct check
};

// API with caching, request deduplication, and timeout
async function api(endpoint, options = {}) {
    const key = endpoint + JSON.stringify(options);

    function getTTL(ep) {
        if (ep.includes('/prices')) return CACHE_TTL_PRICES;
        if (ep.includes('/market/orderbook')) return CACHE_TTL_PRICES;
        if (ep.includes('/cards') || ep.includes('/sets')) return CACHE_TTL_CARDS;
        if (ep.includes('/images') || ep.includes('image')) return CACHE_TTL_IMAGES;
        if (ep.includes('/search')) return CACHE_TTL_LONG;
        return CACHE_TTL;
    }

    // Check memory cache
    const cached = cache.get(key);
    const ttl = options.ttl || getTTL(endpoint);
    if (cached && Date.now() - cached.time < ttl) {
        return cached.data;
    }

    // Check IndexedDB for large responses
    if (endpoint.includes('/cards') || endpoint.includes('/prices') || options.longCache) {
        const dbCached = await getAPICache(key);
        if (dbCached) {
            cache.set(key, { data: dbCached, time: Date.now() });
            return dbCached;
        }
    }

    // Deduplicate in-flight requests
    if (pendingRequests.has(key)) {
        return pendingRequests.get(key);
    }

    const requestPromise = (async () => {
        try {
            // Route through OpenClaw if enabled
            if (BACKEND_MODE === 'openclaw') {
                return await apiViaOpenClaw(endpoint, options);
            }

            const controller = new AbortController();
            const timeout = options.timeout || 30000;
            const timeoutId = setTimeout(() => controller.abort(), timeout);

            const authHeaders = {};
            if (sessionToken && !(options.headers && options.headers['Authorization'])) {
                authHeaders['Authorization'] = `Bearer ${sessionToken}`;
            }

            const res = await fetch(`${API}${endpoint}`, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders,
                    ...options.headers
                }
            });

            clearTimeout(timeoutId);

            if (!res.ok) {
                throw new Error(`API error: ${res.status} ${res.statusText}`);
            }

            const data = await res.json();
            cache.set(key, { data, time: Date.now() });

            if (endpoint.includes('/cards') || endpoint.includes('/prices') || options.longCache) {
                await storeAPICache(key, data, ttl);
            }

            pendingRequests.delete(key);
            return data;
        } catch (e) {
            pendingRequests.delete(key);
            if (e.name === 'AbortError') {
                console.warn('API request timeout:', endpoint);
                return { error: 'Request timeout' };
            } else {
                console.log('API error:', endpoint, e.message);
                return { error: 'Connection failed. Is the server running?' };
            }
        }
    })();

    pendingRequests.set(key, requestPromise);
    return requestPromise;
}

// Route API call through OpenClaw Gateway
async function apiViaOpenClaw(endpoint, options = {}) {
    // Find matching route
    const basePath = endpoint.split('?')[0];
    const route = OPENCLAW_ROUTES[basePath];

    if (!route || !route.agent) {
        // Fallback to direct Flask call
        return apiFallbackFlask(endpoint, options);
    }

    // Parse query params into tool arguments
    const url = new URL(endpoint, 'http://localhost');
    const args = {};
    url.searchParams.forEach((val, key) => { args[key] = val; });

    // Add body params if present
    if (options.body) {
        try {
            Object.assign(args, JSON.parse(options.body));
        } catch {}
    }

    // Send to OpenClaw Gateway via HTTP bridge
    try {
        const res = await fetch(`http://127.0.0.1:18789/api/invoke`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent: route.agent,
                tool: route.tool,
                args
            })
        });

        if (!res.ok) throw new Error(`OpenClaw error: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn('OpenClaw call failed, falling back to Flask:', e.message);
        return apiFallbackFlask(endpoint, options);
    }
}

// Fallback to Flask backend
async function apiFallbackFlask(endpoint, options = {}) {
    const controller = new AbortController();
    const timeout = options.timeout || 30000;
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const res = await fetch(`${API}${endpoint}`, {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        clearTimeout(timeoutId);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return await res.json();
    } catch (e) {
        clearTimeout(timeoutId);
        return { error: e.message };
    }
}

// Intersection Observer for lazy loading images
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    }, { rootMargin: '50px' });

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('img[data-src]').forEach(img => imageObserver.observe(img));
    });
}
