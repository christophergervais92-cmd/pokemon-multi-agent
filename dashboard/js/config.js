// PokeAgent - Configuration
// Auto-detect API URL, proxy settings, constants

const DEPLOYED_API = 'https://pokemon-multi-agent.onrender.com';
const LOCAL_API = 'http://127.0.0.1:5001';

// Auto-detect backend API URL and proxy usage
let BACKEND_API = LOCAL_API;
let USE_PROXY = false;

// Detect if we're on a deployed domain (Vercel, Render, etc.)
const hostname = window.location.hostname;
const isDeployed = hostname !== 'localhost' &&
                  hostname !== '127.0.0.1' &&
                  hostname !== '' &&
                  !hostname.startsWith('192.168.') &&
                  !hostname.startsWith('10.') &&
                  !hostname.startsWith('172.');

// Helper to safely get settings from localStorage (before optimizedLocalStorageGet is defined)
function _getSavedApiUrl() {
    try {
        const settings = localStorage.getItem('settings');
        if (settings) {
            return JSON.parse(settings)?.api_url;
        }
    } catch (e) {}
    return null;
}

if (isDeployed) {
    const savedApi = _getSavedApiUrl();
    if (savedApi && savedApi.startsWith('http')) {
        BACKEND_API = savedApi;
    } else {
        BACKEND_API = DEPLOYED_API;
    }
    USE_PROXY = true;
    console.log('[Config] Deployed domain detected:', hostname);
} else {
    const savedApi = _getSavedApiUrl();
    if (savedApi && savedApi.startsWith('http')) {
        BACKEND_API = savedApi;
        if (!savedApi.includes('localhost') && !savedApi.includes('127.0.0.1')) {
            USE_PROXY = true;
        }
    }
}

console.log('[Config] Backend API:', BACKEND_API, 'Use Proxy:', USE_PROXY, 'Hostname:', hostname);

// Safe Mode: Disable proxy usage
const SAFE_MODE = localStorage.getItem('tcg_safe_mode') === 'true';
if (SAFE_MODE) {
    console.log('[Config] SAFE MODE ENABLED - Proxy disabled, using direct API calls');
}

function shouldUseProxy() {
    if (SAFE_MODE) return false;
    const hn = window.location.hostname;
    const isRemote = hn !== 'localhost' &&
                     hn !== '127.0.0.1' &&
                     hn !== '' &&
                     !hn.startsWith('192.168.') &&
                     !hn.startsWith('10.') &&
                     !hn.startsWith('172.');
    return USE_PROXY || isRemote;
}

function getApiBaseUrl() {
    return shouldUseProxy() ? BACKEND_API : 'https://api.pokemontcg.io/v2';
}

function getDefaultAPI() {
    const saved = localStorage.getItem('api');
    if (saved) return saved;
    if (window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return LOCAL_API;
    }
    return DEPLOYED_API;
}

// Cache TTLs
const CACHE_TTL = 30000;         // 30s - dynamic data (stock, drops)
const CACHE_TTL_PRICES = 300000; // 5min - price data
const CACHE_TTL_CARDS = 3600000; // 1hr - card data
const CACHE_TTL_IMAGES = 86400000; // 24hr - images
const CACHE_TTL_LONG = 1800000;  // 30min - search results

// IndexedDB
const DB_NAME = 'PokeAgentDB';
const DB_VERSION = 1;
const DB_STORE = 'images';

// Debug mode
const DEBUG_MODE = true;
function debugLog(...args) {
    if (DEBUG_MODE) console.log('[DEBUG]', ...args);
}

// Global error handlers
window.onerror = function(msg, url, line, col, error) {
    console.error('GLOBAL ERROR:', msg, 'at line', line);
    return false;
};
window.onunhandledrejection = function(event) {
    console.error('UNHANDLED PROMISE:', event.reason);
};

// Set name to ID mapping
const SET_NAME_TO_ID = {
    'destined rivals': 'sv10', 'destined': 'sv10',
    'journey together': 'sv10',
    'prismatic evolutions': 'sv8pt5', 'prismatic': 'sv8pt5',
    'surging sparks': 'sv8', 'surging': 'sv8',
    'stellar crown': 'sv7', 'stellar': 'sv7',
    'shrouded fable': 'sv6pt5',
    'twilight masquerade': 'sv6',
    'temporal forces': 'sv5',
    'paldean fates': 'sv4pt5', 'paldean': 'sv4pt5',
    'paradox rift': 'sv4',
    '151': 'sv3pt5', 'pokemon 151': 'sv3pt5', 'sv 151': 'sv3pt5',
    'obsidian flames': 'sv3', 'obsidian': 'sv3',
    'paldea evolved': 'sv2',
    'scarlet violet': 'sv1', 'scarlet & violet base': 'sv1',
    'crown zenith': 'swsh12pt5',
    'silver tempest': 'swsh12',
    'lost origin': 'swsh11',
    'astral radiance': 'swsh10',
    'brilliant stars': 'swsh9',
    'fusion strike': 'swsh8',
    'evolving skies': 'swsh7',
    'chilling reign': 'swsh6',
    'battle styles': 'swsh5',
    'shining fates': 'swsh45',
    'vivid voltage': 'swsh4',
    'champions path': 'swsh35', "champion's path": 'swsh35',
};

// Asset image overrides (correct image for known cards)
const ASSET_IMAGE_OVERRIDES = {
    'umbreon vmax|evolving skies|215/203': 'https://images.pokemontcg.io/swsh7/215_hires.png',
    'umbreon vmax|evolving skies|215': 'https://images.pokemontcg.io/swsh7/215_hires.png',
    'umbreon vmax|evolving skies': 'https://images.pokemontcg.io/swsh7/215_hires.png',
    'umbreon vmax alt art|evolving skies': 'https://images.pokemontcg.io/swsh7/215_hires.png',
    'umbreon vmax (alt art)|evolving skies': 'https://images.pokemontcg.io/swsh7/215_hires.png',
};
const ASSET_IMAGE_CACHE = new Map();

function getAssetImageOverride(card) {
    if (!card) return null;
    const name = (card.name || '').trim().toLowerCase();
    const set = (card.set?.name || '').trim().toLowerCase();
    const num = card.number && card.set?.printedTotal ? `${card.number}/${card.set.printedTotal}` : (card.number || '');
    const cardNum = card.number || '';

    if (name.includes('umbreon') && name.includes('vmax') &&
        (set.includes('evolving') || set.includes('swsh7') || set.includes('swsh6')) &&
        (cardNum === '215' || num.includes('215'))) {
        if (DEBUG_MODE) console.log('[Asset Override] Direct match: Umbreon VMAX 215');
        return 'https://images.pokemontcg.io/swsh6/215_hires.png';
    }

    const key1 = `${name}|${set}|${num}`;
    const key2 = `${name}|${set}|${cardNum}`;
    const key3 = `${name}|${set}`;
    let override = ASSET_IMAGE_OVERRIDES[key1] || ASSET_IMAGE_OVERRIDES[key2] || ASSET_IMAGE_OVERRIDES[key3];

    if (!override && name.includes('umbreon') && name.includes('vmax') &&
        (set.includes('evolving') || set.includes('swsh7') || set.includes('swsh6'))) {
        override = 'https://images.pokemontcg.io/swsh7/215_hires.png';
    }

    return override || null;
}
