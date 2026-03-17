// PokeAgent - Utility Functions

// Debounce
function debounce(fn, delay = 300) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}

// Throttle
function throttle(fn, limit = 1000) {
    let inThrottle;
    return (...args) => {
        if (!inThrottle) {
            fn(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 400px;
        font-size: 0.875rem;
        color: var(--text);
        ${type === 'success' ? 'border-left: 4px solid var(--green);' : ''}
        ${type === 'error' ? 'border-left: 4px solid var(--red);' : ''}
        ${type === 'warning' ? 'border-left: 4px solid var(--yellow);' : ''}
        ${type === 'info' ? 'border-left: 4px solid var(--purple);' : ''}
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// HTML escaping
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Price formatting (returns number string without $, callers prepend $ in templates)
function formatPrice(value) {
    if (value === null || value === undefined || value === '' || isNaN(value)) return '??';
    const num = parseFloat(value);
    if (isNaN(num) || num === 0) return '??';
    if (num >= 1000) return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    if (num >= 100) return num.toFixed(0);
    if (num >= 10) return num.toFixed(2);
    return num.toFixed(2);
}

// Type emoji helper (stub - returns empty for all types)
function getTypeEmoji(type) {
    return '';
}

// Set images helper
function fetchSetImages(setIds) {
    setIds.forEach(setId => {
        if (!productImageCache[setId]) {
            productImageCache[setId] = `https://images.pokemontcg.io/${setId}/logo.png`;
        }
    });
}

// Optimized localStorage - Batch writes to reduce I/O
let localStorageQueue = new Map();
let localStorageTimeout = null;
const LS_BATCH_DELAY = 50;

function optimizedLocalStorageSet(key, value) {
    const str = typeof value === 'string' ? value : JSON.stringify(value);
    localStorageQueue.set(key, str);
    if (localStorageTimeout) clearTimeout(localStorageTimeout);
    localStorageTimeout = setTimeout(() => {
        localStorageQueue.forEach((value, key) => {
            try {
                localStorage.setItem(key, value);
            } catch (e) {
                if (e.name === 'QuotaExceededError') {
                    console.warn('localStorage quota exceeded, clearing old cache');
                    Object.keys(localStorage).forEach(k => {
                        if (k.startsWith('cache_') || k.startsWith('temp_') || k === 'api') {
                            localStorage.removeItem(k);
                        }
                    });
                    try {
                        localStorage.setItem(key, value);
                    } catch (e2) {
                        console.error('Failed to save to localStorage:', key, e2);
                    }
                }
            }
        });
        localStorageQueue.clear();
    }, LS_BATCH_DELAY);
}

function optimizedLocalStorageGet(key, defaultValue = null) {
    try {
        const value = localStorage.getItem(key);
        if (value === null) return defaultValue;
        try {
            return JSON.parse(value);
        } catch {
            return value;
        }
    } catch (e) {
        return defaultValue;
    }
}

// Diagnostic tool
window.runDiagnostics = async function() {
    console.log('=== RUNNING DIAGNOSTICS ===');
    const results = [];

    console.log('1. Checking global variables...');
    results.push({ test: 'allSetsData', pass: Array.isArray(allSetsData), value: allSetsData?.length });
    results.push({ test: 'currentSetCards', pass: Array.isArray(currentSetCards), value: currentSetCards?.length });
    results.push({ test: 'showChaseCardDetail', pass: typeof showChaseCardDetail === 'function' });
    results.push({ test: 'searchCards', pass: typeof searchCards === 'function' });
    results.push({ test: 'displayCardGrid', pass: typeof displayCardGrid === 'function' });

    console.log('2. Checking DOM elements...');
    results.push({ test: 'cardName input', pass: !!document.getElementById('cardName') });
    results.push({ test: 'cardResults div', pass: !!document.getElementById('cardResults') });
    results.push({ test: 'chaseCardsGrid', pass: !!document.getElementById('chaseCardsGrid') });
    results.push({ test: 'setSelector', pass: !!document.getElementById('setSelector') });

    console.log('3. Testing Pokemon TCG API...');
    try {
        const testUrl = shouldUseProxy()
            ? `${getApiBaseUrl()}/api/tcg/cards?q=name:pikachu&pageSize=1`
            : 'https://api.pokemontcg.io/v2/cards?q=name:pikachu&pageSize=1';
        const testRes = await fetch(testUrl);
        const testData = await testRes.json();
        results.push({ test: 'Pokemon TCG API', pass: testData.data?.length > 0, value: testRes.status });
    } catch (e) {
        results.push({ test: 'Pokemon TCG API', pass: false, error: e.message });
    }

    console.log('4. Checking sessionStorage...');
    const cacheKeys = Object.keys(sessionStorage).filter(k => k.startsWith('set_cards_'));
    results.push({ test: 'Cached sets', pass: true, value: cacheKeys.length + ' sets cached' });

    console.log('=== DIAGNOSTIC RESULTS ===');
    results.forEach(r => {
        const status = r.pass ? 'PASS' : 'FAIL';
        console.log(`${status} ${r.test}: ${r.value || r.error || (r.pass ? 'OK' : 'FAIL')}`);
    });
    console.log(`\n${results.filter(r => r.pass).length}/${results.length} tests passed`);
    return results;
};

console.log('TIP: Run runDiagnostics() in console to test the site');
