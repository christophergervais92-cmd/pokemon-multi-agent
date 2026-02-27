// PokeAgent - App Bootstrap
// DOMContentLoaded handler, section switching, deep link support, initialization

// Section switching
function switchSection(name) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
    document.querySelector(`[data-section="${name}"]`)?.classList.add('active');
    document.getElementById(name)?.classList.add('active');

    // Sync mobile dropdown
    const mobileSelect = document.getElementById('mobileNavSelect');
    if (mobileSelect) mobileSelect.value = name;

    // Initialize drops when switching to drops section
    if (name === 'search') {
        setTimeout(() => {
            const container = document.getElementById('upcomingDrops');
            if (container && (!container.innerHTML.trim() || container.innerHTML.includes('empty'))) {
                initDrops();
            }
        }, 100);
    }

    // Initialize vending map when switching to vending section (lazy load Leaflet)
    if (name === 'vending') {
        setTimeout(async () => {
            const vendingZip = document.getElementById('vendingZip');
            if (vendingZip && !vendingZip.value) {
                vendingZip.value = settings.zip || document.getElementById('stockZip')?.value || '90210';
            }
            if (typeof window.loadLeaflet === 'function') {
                try { await window.loadLeaflet(); } catch (e) { console.warn('Failed to load Leaflet:', e); }
            }
            initVendingMap();
            if (vendingMap) vendingMap.invalidateSize();
        }, 100);
    }

    // Initialize monitors when switching to monitors section
    if (name === 'monitors') {
        setTimeout(() => { initMonitors(); }, 50);
    }
}

function switchSectionMobile(name) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
    document.querySelector(`[data-section="${name}"]`)?.classList.add('active');
    document.getElementById(name)?.classList.add('active');

    // Initialize drops when switching to drops section
    if (name === 'search') {
        setTimeout(() => {
            const container = document.getElementById('upcomingDrops');
            if (container && (!container.innerHTML.trim() || container.innerHTML.includes('empty'))) {
                initDrops();
            }
        }, 100);
    }

    // Initialize monitors when switching to monitors section
    if (name === 'monitors') {
        setTimeout(() => { initMonitors(); }, 50);
    }

    // Initialize database section
    if (name === 'database') {
        setTimeout(() => {
            const setSelector = document.getElementById('setSelector');
            const chaseGrid = document.getElementById('chaseCardsGrid');
            if (setSelector && (!setSelector.value || setSelector.value === '')) {
                if (chaseGrid && (!chaseGrid.innerHTML.trim() || chaseGrid.innerHTML.includes('empty'))) {
                    chaseGrid.innerHTML = `
                        <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">
                            <div class="empty-icon book" style="margin-bottom: 0.75rem;"></div>
                            <div style="font-weight: 600; margin-bottom: 0.5rem;">Select a set to view cards</div>
                            <div style="font-size: 0.875rem;">Choose a set from the dropdown above</div>
                        </div>
                    `;
                }
            }
            if (setSelector && typeof loadAllSets === 'function') {
                const hasOptions = setSelector.querySelectorAll('option').length > 1;
                if (!hasOptions) loadAllSets();
            }
        }, 100);
    }

    // Initialize vending map when switching to vending section (lazy load Leaflet)
    if (name === 'vending') {
        setTimeout(async () => {
            const vendingZip = document.getElementById('vendingZip');
            if (vendingZip && !vendingZip.value) {
                vendingZip.value = settings.zip || document.getElementById('stockZip')?.value || '90210';
            }
            if (typeof window.loadLeaflet === 'function') {
                try { await window.loadLeaflet(); } catch (e) { console.warn('Failed to load Leaflet:', e); }
            }
            initVendingMap();
            if (vendingMap) vendingMap.invalidateSize();
        }, 100);
    }
}

// Quick search from header
async function quickSearchFromHeader() {
    const query = document.getElementById('quickSearch')?.value?.trim();
    if (!query || query.length < 2) {
        document.getElementById('quickSearchResults').style.display = 'none';
        return;
    }

    const results = document.getElementById('quickSearchResults');
    results.style.display = 'block';
    results.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-muted);"><div class="spinner" style="margin: 0 auto;"></div>Searching...</div>';

    try {
        const cards = await fetchAllCardsFromTCG(query);
        if (cards.length > 0) {
            results.innerHTML = `
                <div style="padding: 0.5rem; border-bottom: 1px solid var(--border); font-size: 0.75rem; color: var(--text-muted); font-weight: 600;">
                    Cards (${cards.length})
                </div>
                <div style="max-height: 300px; overflow-y: auto;">
                    ${cards.slice(0, 5).map((card) => {
                        const price = card.tcgplayer?.prices?.holofoil?.market || card.tcgplayer?.prices?.normal?.market || 0;
                        return `
                            <div onclick="selectCardFromQuickSearch('${card.name.replace(/'/g, "\\'")}')"
                                 style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.2s;"
                                 onmouseover="this.style.background='var(--bg)'"
                                 onmouseout="this.style.background='transparent'">
                                <img src="${getAssetImageOverride(card) || card.images?.small || ''}"
                                     style="width: 50px; height: 70px; object-fit: contain; border-radius: 4px;"
                                     onerror="this.style.display='none'">
                                <div style="flex: 1; min-width: 0;">
                                    <div style="font-weight: 500; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${card.name}</div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted);">${card.set?.name || ''}</div>
                                    ${price > 0 ? `<div style="font-size: 0.75rem; color: var(--green); font-weight: 600;">$${price.toFixed(2)}</div>` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
                    ${cards.length > 5 ? `
                        <div onclick="goToCardLookup('${query.replace(/'/g, "\\'")}')"
                             style="padding: 0.75rem; text-align: center; cursor: pointer; color: var(--accent); font-size: 0.875rem; font-weight: 500; border-top: 1px solid var(--border);"
                             onmouseover="this.style.background='var(--bg)'"
                             onmouseout="this.style.background='transparent'">
                            View all ${cards.length} results
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            results.innerHTML = `
                <div style="padding: 1rem; text-align: center; color: var(--text-muted);">
                    No cards found. <a href="#" onclick="goToStockSearch('${query.replace(/'/g, "\\'")}'); return false;" style="color: var(--accent);">Search products instead</a>
                </div>
            `;
        }
    } catch (e) {
        results.innerHTML = `<div style="padding: 1rem; text-align: center; color: var(--text-muted);">Search error: ${e.message}</div>`;
    }
}

function selectCardFromQuickSearch(cardName) {
    document.getElementById('quickSearch').value = cardName;
    document.getElementById('quickSearchResults').style.display = 'none';
    switchSection('card');
    setTimeout(() => {
        document.getElementById('cardName').value = cardName;
        searchCardsOrProducts();
    }, 100);
}

function goToCardLookup(query) {
    document.getElementById('quickSearchResults').style.display = 'none';
    switchSection('card');
    setTimeout(() => {
        document.getElementById('cardName').value = query;
        searchCardsOrProducts();
    }, 100);
}

function goToStockSearch(query) {
    document.getElementById('quickSearchResults').style.display = 'none';
    switchSection('stock');
    setTimeout(() => {
        document.getElementById('stockQuery').value = query;
        findStock();
    }, 100);
}

// Prefetch (disabled to reduce API load)
async function prefetchCommonData() {
    console.log('Prefetch disabled to reduce API load');
}

// Safe mode toggle
function toggleSafeMode() {
    const checkbox = document.getElementById('safeModeToggle');
    const enabled = checkbox.checked;
    localStorage.setItem('tcg_safe_mode', enabled ? 'true' : 'false');
    if (enabled) {
        showNotification('Safe Mode enabled - Proxy disabled. Page will reload.', 'warning');
        setTimeout(() => window.location.reload(), 1500);
    } else {
        showNotification('Safe Mode disabled - Proxy enabled. Page will reload.', 'info');
        setTimeout(() => window.location.reload(), 1500);
    }
}

// Main initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Cache version management
    const CACHE_VERSION = 'v3';
    const storedVersion = localStorage.getItem('setCacheVersion');
    if (storedVersion !== CACHE_VERSION) {
        console.log('Cache version changed, clearing all set caches...');
        Object.keys(sessionStorage).forEach(key => {
            if (key.startsWith('set_cards_')) {
                sessionStorage.removeItem(key);
            }
        });
        localStorage.setItem('setCacheVersion', CACHE_VERSION);
    }

    // Initialize IndexedDB
    try {
        await initIndexedDB();
        const lastClean = localStorage.getItem('lastIndexedDBClean');
        if (!lastClean || Date.now() - parseInt(lastClean) > 24 * 60 * 60 * 1000) {
            await cleanIndexedDB();
            localStorage.setItem('lastIndexedDBClean', Date.now().toString());
        }
    } catch (e) {
        console.warn('IndexedDB initialization failed:', e);
    }

    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('./sw.js', { scope: './' }).then(reg => {
            console.log('Service worker registered:', reg.scope);
        }).catch(e => {
            console.warn('Service worker registration failed:', e);
        });
    }

    // Core initialization
    loadSettings();
    checkConnection();
    connectLive();
    prefetchCommonData();
    initAuth();

    // Nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => switchSection(btn.dataset.section));
    });

    // Debounced search inputs
    const debouncedSearch = debounce(quickSearch, 300);
    const debouncedCardLookup = debounce(lookupCard, 300);
    const debouncedFlip = debounce(calculateFlip, 400);
    const debouncedQuickSearch = debounce(quickSearchFromHeader, 300);
    const debouncedStock = debounce(findStock, 400);

    // Quick search in header
    const quickSearchInput = document.getElementById('quickSearch');
    if (quickSearchInput) {
        quickSearchInput.addEventListener('input', () => {
            const query = quickSearchInput.value.trim();
            if (query.length >= 2) {
                debouncedQuickSearch();
            } else {
                document.getElementById('quickSearchResults').style.display = 'none';
            }
        });
        document.addEventListener('click', (e) => {
            const results = document.getElementById('quickSearchResults');
            if (results && !quickSearchInput.contains(e.target) && !results.contains(e.target)) {
                results.style.display = 'none';
            }
        });
    }

    // Search input bindings
    document.getElementById('searchQuery')?.addEventListener('input', debouncedSearch);
    document.getElementById('cardName')?.addEventListener('input', debouncedCardLookup);
    document.getElementById('flipCard')?.addEventListener('input', debouncedFlip);
    document.getElementById('stockQuery')?.addEventListener('input', debouncedStock);

    // Initialize flip calculator tiers
    if (typeof updateFlipTiers === 'function') updateFlipTiers();

    // Enter key for immediate search
    document.getElementById('searchQuery')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') { e.preventDefault(); quickSearch(); }
    });
    document.getElementById('cardName')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') { e.preventDefault(); searchCardsOrProducts(); }
    });
    document.getElementById('flipCard')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') { e.preventDefault(); calculateFlip(); }
    });
    document.getElementById('stockQuery')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') { e.preventDefault(); findStock(); }
    });

    // Request notification permission
    if ('Notification' in window) Notification.requestPermission();

    // Deep link support: ?section=stock, ?section=cards, etc.
    try {
        const initialSection = new URLSearchParams(window.location.search).get('section');
        if (initialSection && document.getElementById(initialSection)) {
            switchSection(initialSection);
        }
    } catch {}
});
