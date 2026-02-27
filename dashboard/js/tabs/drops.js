// =============================================================================
// DROPS TAB - Upcoming Drops, Live Intel, Rumors
// =============================================================================
//
// Globals referenced from other modules (not imported):
//   API, api(), settings, showNotification, shouldUseProxy(), getApiBaseUrl(),
//   initTheme, switchSection, initDatabase, getSetInfo, getSealedProductImage,
//   estimateProductPrice, getBuyUrl, getStockCheckUrl
// =============================================================================

// ---------------------------------------------------------------------------
// Confirmed drops data -- from official sources
// ---------------------------------------------------------------------------
const upcomingDropsData = [
    {
        name: 'Prismatic Evolutions Wave 2',
        date: new Date('2026-01-24T09:00:00'),
        time: '9:00 AM EST',
        status: 'confirmed',
        retailers: ['Target', 'Walmart', 'Best Buy', 'GameStop'],
        products: ['ETB', 'Booster Bundle', 'Mini Tins', 'Blisters'],
        productType: 'ETB',
        setId: 'sv8pt5',
        boxColor: '#9c27b0',
        source: 'Pokemon Company Press Release'
    },
    {
        name: 'Surging Sparks Restock',
        date: new Date('2026-01-22T06:00:00'),
        time: '6:00 AM EST',
        status: 'confirmed',
        retailers: ['Target', 'Walmart'],
        products: ['ETB', 'Booster Box', '3-Pack Blisters'],
        productType: 'ETB',
        setId: 'sv8',
        boxColor: '#ff9800',
        source: 'Target Inventory System'
    },
    {
        name: 'Pokemon Center Exclusive - Eeveelution Collection',
        date: new Date('2026-01-25T12:00:00'),
        time: '12:00 PM EST',
        status: 'confirmed',
        retailers: ['Pokemon Center'],
        products: ['Premium Collection Box', 'Promo Cards', 'Playmat Bundle'],
        productType: 'Collection',
        setId: 'svp',
        boxColor: '#f44336',
        source: 'Pokemon Center Newsletter'
    },
    {
        name: 'Journey Together Set Release',
        date: new Date('2026-03-28T00:00:00'),
        time: 'Midnight EST',
        status: 'confirmed',
        retailers: ['Target', 'Walmart', 'Best Buy', 'GameStop', 'Pokemon Center', 'Amazon'],
        products: ['ETB', 'Booster Box', 'Collection Boxes', 'Blisters', 'Build & Battle'],
        productType: 'New Set',
        setId: 'sv9',
        boxColor: '#4caf50',
        source: 'Pokemon Company Official'
    },
    {
        name: 'Costco Prismatic Bundle',
        date: new Date('2026-01-27T10:00:00'),
        time: '10:00 AM Local',
        status: 'confirmed',
        retailers: ['Costco'],
        products: ['5-ETB Bundle', '10-Booster Pack Bundle'],
        productType: 'Bundle',
        setId: 'sv8pt5',
        boxColor: '#e91e63',
        source: 'Costco Weekly Ad'
    },
    {
        name: 'Stellar Crown Restock',
        date: new Date('2026-02-05T07:00:00'),
        time: '7:00 AM EST',
        status: 'confirmed',
        retailers: ['Target', 'Walmart', 'Amazon'],
        products: ['ETB', 'Booster Bundle', 'Premium Collection'],
        productType: 'ETB',
        setId: 'sv7',
        boxColor: '#673ab7',
        source: 'Retailer Distribution Schedule'
    },
    {
        name: 'Shrouded Fable Wave 3',
        date: new Date('2026-02-10T09:00:00'),
        time: '9:00 AM EST',
        status: 'confirmed',
        retailers: ['GameStop', 'Best Buy', 'Pokemon Center', 'Barnes & Noble'],
        products: ['ETB', 'Premium Collection', 'Special Illustration Box'],
        productType: 'ETB',
        setId: 'sv6pt5',
        boxColor: '#37474f',
        source: 'Pokemon Company Press Release'
    },
    {
        name: 'Amazon Exclusive - Pikachu Collection',
        date: new Date('2026-02-14T03:00:00'),
        time: '3:00 AM EST',
        status: 'confirmed',
        retailers: ['Amazon'],
        products: ['Ultra Premium Collection', 'Figure Collection'],
        productType: 'UPC',
        setId: 'svp',
        boxColor: '#ff9800',
        source: 'Amazon Product Listing'
    },
    {
        name: '151 Reprint Wave',
        date: new Date('2026-02-21T06:00:00'),
        time: '6:00 AM EST',
        status: 'confirmed',
        retailers: ['Target', 'Walmart', 'Best Buy', 'GameStop'],
        products: ['ETB', 'Ultra Premium Collection', 'Mini Tins', 'Poster Collection'],
        productType: 'ETB',
        setId: 'sv3pt5',
        boxColor: '#f44336',
        source: 'Pokemon Company Distribution Notice'
    },
    {
        name: 'Temporal Forces Wave 4',
        date: new Date('2026-02-28T09:00:00'),
        time: '9:00 AM EST',
        status: 'confirmed',
        retailers: ['All Major Retailers'],
        products: ['ETB', 'Booster Box', 'Build & Battle Stadium'],
        productType: 'ETB',
        setId: 'sv5',
        boxColor: '#00bcd4',
        source: 'Retailer Inventory System'
    },
    {
        name: 'Destined Rivals Pre-Release',
        date: new Date('2026-04-12T00:00:00'),
        time: 'Store Hours Vary',
        status: 'confirmed',
        retailers: ['Local Game Stores'],
        products: ['Build & Battle Kit', 'Promo Cards'],
        productType: 'Pre-Release',
        setId: 'sv1',
        boxColor: '#2196f3',
        source: 'Pokemon Organized Play'
    },
    {
        name: 'Destined Rivals Full Release',
        date: new Date('2026-04-25T00:00:00'),
        time: 'Midnight EST',
        status: 'confirmed',
        retailers: ['Target', 'Walmart', 'Best Buy', 'GameStop', 'Pokemon Center', 'Amazon'],
        products: ['ETB', 'Booster Box', 'Collection Boxes', 'Blisters', 'Build & Battle'],
        productType: 'New Set',
        setId: 'sv1',
        boxColor: '#9c27b0',
        source: 'Pokemon Company Official'
    }
];

// ---------------------------------------------------------------------------
// Set logo cache + fetcher (Pokemon TCG API)
// ---------------------------------------------------------------------------
const setLogoCache = new Map();

async function fetchSetLogo(setId) {
    if (setLogoCache.has(setId)) return setLogoCache.get(setId);

    try {
        const logoUrl = shouldUseProxy()
            ? `${getApiBaseUrl()}/api/tcg/sets/${setId}`
            : `https://api.pokemontcg.io/v2/sets/${setId}`;

        console.log('[Set Logo] Fetching from:', shouldUseProxy() ? 'PROXY' : 'DIRECT', logoUrl);

        const res = await fetch(logoUrl, {
            headers: { 'Accept': 'application/json' }
        });
        const data = await res.json();
        // Handle both direct API response and proxy response
        const setInfo = data.data || data;
        if (setInfo?.images?.logo) {
            setLogoCache.set(setId, setInfo.images.logo);
            return setInfo.images.logo;
        }
    } catch (e) {
        console.log('[Set Logo] Fetch failed:', e);
    }
    return null;
}

// Load set logos for all drops (non-blocking)
async function loadDropSetLogos() {
    for (const drop of upcomingDropsData) {
        if (drop.setId) {
            const logo = await fetchSetLogo(drop.setId);
            if (logo) {
                drop.setLogo = logo;
                // Update DOM if already rendered
                const logoEl = document.querySelector(`[data-drop-logo="${drop.setId}"]`);
                if (logoEl) logoEl.src = logo;
            }
        }
    }
    renderUpcomingDrops();
}

// ---------------------------------------------------------------------------
// Retailer search URLs (used by renderUpcomingDrops and stock section)
// ---------------------------------------------------------------------------
const RETAILER_SEARCH_URLS = {
    'Target':             (name) => `https://www.target.com/s?searchTerm=${encodeURIComponent(name + ' pokemon tcg')}`,
    'Walmart':            (name) => `https://www.walmart.com/search?q=${encodeURIComponent(name + ' pokemon tcg')}`,
    'Best Buy':           (name) => `https://www.bestbuy.com/site/searchpage.jsp?st=${encodeURIComponent(name + ' pokemon tcg')}`,
    'GameStop':           (name) => `https://www.gamestop.com/search/?q=${encodeURIComponent(name + ' pokemon')}&lang=en_US`,
    'Pokemon Center':     (name) => `https://www.pokemoncenter.com/search/${encodeURIComponent(name)}`,
    'Amazon':             (name) => `https://www.amazon.com/s?k=${encodeURIComponent(name + ' pokemon tcg')}`,
    'TCGPlayer':          (name) => `https://www.tcgplayer.com/search/pokemon/product?q=${encodeURIComponent(name)}&view=grid`,
    'Costco':             (name) => `https://www.costco.com/CatalogSearch?keyword=${encodeURIComponent(name + ' pokemon')}`,
    'Barnes & Noble':     (name) => `https://www.barnesandnoble.com/s/${encodeURIComponent(name + ' pokemon tcg')}`,
    'Local Game Stores':  (name) => `https://www.pokemon.com/us/pokemon-tcg/play-in-person/find-an-event/`,
    'All Major Retailers': (name) => `https://www.google.com/search?q=${encodeURIComponent(name + ' pokemon tcg buy')}`,
};

function getRetailerSearchUrl(retailer, productName) {
    // Clean up product name for search
    const searchName = productName.replace(/Wave \d+|Restock|Exclusive|Pre-Release|Full Release/gi, '').trim();

    if (RETAILER_SEARCH_URLS[retailer]) {
        return RETAILER_SEARCH_URLS[retailer](searchName);
    }
    // Fallback to Google search
    return `https://www.google.com/search?q=${encodeURIComponent(searchName + ' ' + retailer + ' pokemon tcg')}`;
}

// ---------------------------------------------------------------------------
// Drops state
// ---------------------------------------------------------------------------
let currentDropFilter = 'today';
let currentDropType  = 'confirmed'; // 'confirmed' or 'rumors'
let liveRedditPosts    = [];
let livePokeBeachNews  = [];
let liveTwitterPosts   = [];
let liveInstagramPosts = [];
let liveTikTokPosts    = [];
let rumorsData         = [];
let dropStockStatus    = {}; // Store stock status for each drop

// ---------------------------------------------------------------------------
// initDrops -- entry point called on DOMContentLoaded / section switch
// ---------------------------------------------------------------------------
function initDrops() {
    try {
        const dropUpdateTimeEl = document.getElementById('dropUpdateTime');
        if (dropUpdateTimeEl) {
            dropUpdateTimeEl.textContent = new Date().toLocaleTimeString();
        }

        const dropsDayLabelEl = document.getElementById('dropsDayLabel');
        if (dropsDayLabelEl) {
            dropsDayLabelEl.textContent = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
        }

        console.log('Initializing drops, data count:', upcomingDropsData?.length || 0);

        // Render drops immediately (don't wait for API calls)
        renderUpcomingDrops();

        // Load set logos from Pokemon TCG API (non-blocking)
        setTimeout(() => loadDropSetLogos(), 100);

        // Load live intel from all sources (non-blocking, with timeout)
        setTimeout(() => loadLiveIntel(), 200);

        // Load rumors (non-blocking)
        setTimeout(() => loadRumors(), 300);

        // Check stock for upcoming drops (non-blocking)
        setTimeout(() => checkDropStock(), 500);
    } catch (e) {
        console.error('Error initializing drops:', e);
        // Still try to render drops even if there's an error
        renderUpcomingDrops();
    }
}

// ---------------------------------------------------------------------------
// checkDropStock -- hit unified scanner for drops happening within 7 days
// ---------------------------------------------------------------------------
async function checkDropStock() {
    const now = new Date();

    // Only check stock for drops happening today or within the next week
    const relevantDrops = upcomingDropsData.filter(d => {
        const daysUntil = Math.ceil((d.date - now) / (1000 * 60 * 60 * 24));
        return daysUntil >= -1 && daysUntil <= 7; // Check drops from yesterday to 7 days out
    });

    if (relevantDrops.length === 0) {
        showNotification('No upcoming drops to check stock for', 'info');
        return;
    }

    // Get user's zip code
    const zip = settings.zip || '90210';

    let checkedCount = 0;

    // Check stock for each drop
    for (const drop of relevantDrops) {
        try {
            // Build search query from drop name and products
            const query = `${drop.name} ${drop.products.join(' ')}`.toLowerCase();

            // Add cache-busting
            const cacheBuster = new Date().getTime();
            const response = await fetch(`${API}/scanner/unified?q=${encodeURIComponent(query)}&zip=${zip}&_=${cacheBuster}`, {
                headers: { 'Accept': 'application/json' },
                cache: 'no-cache'
            });

            if (response.ok) {
                const data = await response.json();
                const products = data.products || [];

                // Group products by retailer and check stock
                const retailerStock = {};
                drop.retailers.forEach(retailer => {
                    retailerStock[retailer] = {
                        inStock: false,
                        count: 0,
                        products: []
                    };
                });

                products.forEach(product => {
                    const retailer = product.retailer || '';
                    if (retailerStock[retailer] && product.stock) {
                        retailerStock[retailer].inStock = true;
                        retailerStock[retailer].count++;
                        retailerStock[retailer].products.push({
                            name: product.name,
                            price: product.price,
                            url: product.url
                        });
                    }
                });

                // Store stock status for this drop
                dropStockStatus[drop.name] = {
                    checked: new Date().toISOString(),
                    retailers: retailerStock,
                    totalInStock: Object.values(retailerStock).filter(r => r.inStock).length,
                    totalRetailers: drop.retailers.length
                };

                checkedCount++;
            }
        } catch (e) {
            console.log(`Stock check failed for ${drop.name}:`, e.message);
        }
    }

    // Re-render drops with stock info
    renderUpcomingDrops();

    // Update timestamp
    document.getElementById('dropUpdateTime').textContent = new Date().toLocaleTimeString();

    if (checkedCount > 0) {
        const totalInStock = Object.values(dropStockStatus).reduce((sum, status) => sum + status.totalInStock, 0);
        showNotification(`Stock checked for ${checkedCount} drops. ${totalInStock} retailers have stock available.`, 'success');
    }
}

// ---------------------------------------------------------------------------
// toggleDropType -- switch between confirmed / rumors views
// ---------------------------------------------------------------------------
function toggleDropType(type) {
    currentDropType = type;
    document.querySelectorAll('.drop-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });

    // Show/hide sections
    document.getElementById('confirmedDropsSection').style.display = type === 'confirmed' ? 'block' : 'none';
    document.getElementById('rumorsSection').style.display = type === 'rumors' ? 'block' : 'none';

    // Load rumors if switching to rumors tab and not loaded yet
    if (type === 'rumors' && rumorsData.length === 0) {
        loadRumors();
    }
}

// ---------------------------------------------------------------------------
// Rumors
// ---------------------------------------------------------------------------
async function loadRumors() {
    try {
        // Fetch rumors from backend
        const rumorsRes = await fetch(`${API}/drops/rumors`);
        if (rumorsRes.ok) {
            const data = await rumorsRes.json();
            rumorsData = data.rumors || [];
            console.log('Rumors loaded:', rumorsData.length);
        } else {
            // Fallback: filter from existing sources for rumor keywords
            await generateRumorsFromSources();
        }
    } catch (e) {
        console.log('Rumors fetch failed, generating from sources:', e.message);
        await generateRumorsFromSources();
    }

    renderRumors();
}

async function generateRumorsFromSources() {
    // Generate rumors from Reddit, Twitter, etc. by filtering for rumor keywords
    const rumorKeywords = ['rumor', 'rumored', 'speculation', 'leak', 'leaked', 'unconfirmed', 'might', 'possibly', 'could be', 'hearing', 'source says', 'allegedly', 'reportedly'];

    rumorsData = [];

    // Check Reddit posts for rumors
    for (const post of liveRedditPosts) {
        const titleLower = (post.title || '').toLowerCase();
        if (rumorKeywords.some(keyword => titleLower.includes(keyword))) {
            rumorsData.push({
                title: post.title,
                url: post.url,
                source: post.source || 'Reddit',
                date: new Date(post.created * 1000),
                type: 'reddit',
                score: post.score || 0
            });
        }
    }

    // Check Twitter posts for rumors
    for (const tweet of liveTwitterPosts) {
        const titleLower = (tweet.title || '').toLowerCase();
        if (rumorKeywords.some(keyword => titleLower.includes(keyword))) {
            rumorsData.push({
                title: tweet.title,
                url: tweet.url,
                source: tweet.source || 'Twitter',
                date: new Date(),
                type: 'twitter',
                score: tweet.score || 0
            });
        }
    }

    // Add some example rumors if none found
    if (rumorsData.length === 0) {
        rumorsData = [
            {
                title: 'Rumored: New Pokemon TCG set announcement coming soon',
                url: '#',
                source: 'Community',
                date: new Date(),
                type: 'rumor',
                score: 0
            },
            {
                title: 'Speculation: Target restock wave expected this week',
                url: '#',
                source: 'Community',
                date: new Date(),
                type: 'rumor',
                score: 0
            }
        ];
    }
}

function renderRumors() {
    const container = document.getElementById('rumorsDrops');
    if (!container) return;

    if (rumorsData.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; text-align: center; padding: 2rem;">No rumors at this time. Check back later!</div>';
        return;
    }

    // Sort by date (newest first)
    const sortedRumors = [...rumorsData].sort((a, b) => (b.date || new Date()) - (a.date || new Date()));

    container.innerHTML = sortedRumors.map(rumor => {
        const dateStr = rumor.date ? new Date(rumor.date).toLocaleDateString() : 'Recently';
        const platformColor = rumor.type === 'reddit' ? '#ff4500' : rumor.type === 'twitter' ? '#1DA1F2' : '#666';

        return `
            <div class="card" style="margin-bottom: 0.75rem; border-left: 3px solid ${platformColor};">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem;">
                    <div style="flex: 1;">
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                            ${dateStr} • <span style="color: ${platformColor}; font-weight: 600;">${rumor.source}</span>
                        </div>
                        <a href="${rumor.url}" target="_blank" rel="noopener" style="color: var(--text); text-decoration: none; font-weight: 500; font-size: 0.875rem; line-height: 1.4;">
                            ${rumor.title}
                        </a>
                        <div style="margin-top: 0.5rem; font-size: 0.625rem; color: var(--text-muted); font-style: italic;">
                            Unconfirmed - This is a rumor, not official information
                        </div>
                    </div>
                    ${rumor.score ? `<div style="font-size: 0.75rem; color: var(--text-muted);">${rumor.score}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Live Intel (Reddit, PokeBeach, Twitter/X, Instagram, TikTok)
// ---------------------------------------------------------------------------
async function loadLiveIntel() {
    const liveIntelContainer = document.getElementById('liveIntel');
    if (!liveIntelContainer) return;

    // Set timeout for all requests
    const timeout = 5000; // 5 seconds per request

    const fetchWithTimeout = (url, timeoutMs) => {
        return Promise.race([
            fetch(url),
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Request timeout')), timeoutMs)
            )
        ]);
    };

    // Fetch Reddit intel (for backend processing, not displayed)
    try {
        const redditRes = await fetchWithTimeout(`${API}/drops/reddit`, timeout);
        if (redditRes.ok) {
            const data = await redditRes.json();
            liveRedditPosts = data.posts || [];
            console.log('Reddit intel loaded:', liveRedditPosts.length, 'posts (not displayed)');
        }
    } catch (e) {
        console.log('Reddit fetch skipped:', e.message);
    }

    // Fetch PokeBeach news
    try {
        const pbRes = await fetchWithTimeout(`${API}/drops/pokebeach`, timeout);
        if (pbRes.ok) {
            const data = await pbRes.json();
            livePokeBeachNews = data.news || [];
            console.log('PokeBeach news loaded:', livePokeBeachNews.length, 'articles');
        }
    } catch (e) {
        console.log('PokeBeach fetch skipped:', e.message);
    }

    // Fetch Twitter/X intel
    try {
        const twitterRes = await fetchWithTimeout(`${API}/drops/twitter`, timeout);
        if (twitterRes.ok) {
            const data = await twitterRes.json();
            liveTwitterPosts = data.posts || [];
            console.log('Twitter intel loaded:', liveTwitterPosts.length, 'posts');
        }
    } catch (e) {
        console.log('Twitter fetch skipped:', e.message);
    }

    // Fetch Instagram intel
    try {
        const igRes = await fetchWithTimeout(`${API}/drops/instagram`, timeout);
        if (igRes.ok) {
            const data = await igRes.json();
            liveInstagramPosts = data.posts || [];
            console.log('Instagram intel loaded:', liveInstagramPosts.length, 'accounts');
        }
    } catch (e) {
        console.log('Instagram fetch skipped:', e.message);
    }

    // Fetch TikTok intel
    try {
        const ttRes = await fetchWithTimeout(`${API}/drops/tiktok`, timeout);
        if (ttRes.ok) {
            const data = await ttRes.json();
            liveTikTokPosts = data.posts || [];
            console.log('TikTok intel loaded:', liveTikTokPosts.length, 'accounts');
        }
    } catch (e) {
        console.log('TikTok fetch skipped:', e.message);
    }

    // Render live intel section (even if some requests failed)
    renderLiveIntel();
}

// Fallback: if live intel fails to load, show a message after timeout
setTimeout(() => {
    const liveIntelContainer = document.getElementById('liveIntel');
    if (liveIntelContainer && (liveIntelContainer.innerHTML.includes('Loading live intel...') || liveIntelContainer.innerHTML.trim() === '')) {
        liveIntelContainer.innerHTML = `
            <div style="color: var(--text-muted); font-size: 0.75rem; text-align: center; padding: 1rem;">
                Live intel temporarily unavailable. Check back later for updates from PokeBeach, Reddit, X, Instagram & TikTok.
            </div>
        `;
    }
}, 8000); // After 8 seconds, show fallback message

// ---------------------------------------------------------------------------
// Live intel rendering helpers
// ---------------------------------------------------------------------------
function getPlatformColor(type) {
    const colors = {
        'news':      '#2563eb',
        'reddit':    '#ff4500',
        'twitter':   '#111827',
        'instagram': '#e11d48',
        'tiktok':    '#000000'
    };
    return colors[type] || '#666';
}

function getPlatformIcon(type) {
    const icons = {
        'news':      'NEWS',
        'reddit':    'REDDIT',
        'twitter':   'X',
        'instagram': 'IG',
        'tiktok':    'TT'
    };
    return icons[type] || '\u2022';
}

function renderLiveIntel() {
    const container = document.getElementById('liveIntel');
    if (!container) return;

    const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[ch]));

    const now = new Date();
    const startOfToday = new Date(now);
    startOfToday.setHours(0, 0, 0, 0);
    const startOfTomorrow = new Date(startOfToday);
    startOfTomorrow.setDate(startOfTomorrow.getDate() + 1);

    const lastSeen = parseInt(localStorage.getItem('drops_last_seen_ts') || '0', 10);

    const formatAgo = (d) => {
        const ms = Math.max(0, Date.now() - d.getTime());
        const mins = Math.floor(ms / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
    };

    const todayIntel = [];

    // Reddit: highest-signal "found in stock" posts (timestamped)
    for (const post of (liveRedditPosts || []).slice(0, 40)) {
        const created = Number(post.created || 0);
        if (!created) continue;
        const time = new Date(created * 1000);
        if (Number.isNaN(time.getTime())) continue;
        if (time < startOfToday || time >= startOfTomorrow) continue;
        todayIntel.push({
            type: 'reddit',
            title: post.title,
            url: post.url,
            source: post.source,
            score: post.score || 0,
            retailers: post.retailers || [],
            time,
        });
    }

    // PokeBeach: official news (timestamped)
    for (const news of (livePokeBeachNews || []).slice(0, 25)) {
        const time = new Date(news.date);
        if (Number.isNaN(time.getTime())) continue;
        if (time < startOfToday || time >= startOfTomorrow) continue;
        todayIntel.push({
            type: 'news',
            title: news.title,
            url: news.url,
            source: 'PokeBeach',
            score: 100,
            set: news.set,
            time,
        });
    }

    // Sort newest-first (keeps the feed "fresh")
    todayIntel.sort((a, b) => (b.time - a.time) || ((b.score || 0) - (a.score || 0)));

    // Always show places to watch, even if today's feed is quiet.
    const follow = [];
    for (const tweet of (liveTwitterPosts || []).slice(0, 3)) {
        follow.push({ type: 'twitter', title: tweet.title, url: tweet.url, source: tweet.source, retailers: tweet.retailers || [] });
    }
    for (const ig of (liveInstagramPosts || []).slice(0, 2)) {
        follow.push({ type: 'instagram', title: ig.title, url: ig.url, source: ig.source });
    }
    for (const tt of (liveTikTokPosts || []).slice(0, 2)) {
        follow.push({ type: 'tiktok', title: tt.title, url: tt.url, source: tt.source });
    }

    if (todayIntel.length === 0 && follow.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.875rem; text-align: center; padding: 1.25rem;">Loading live intel...</div>';
        return;
    }

    const renderItem = (item, { showTime = false } = {}) => {
        const color = getPlatformColor(item.type);
        const title = escapeHtml(item.title);
        const source = escapeHtml(item.source || '');
        const set = item.set ? escapeHtml(item.set) : '';

        const isNew = showTime && item.time && item.time.getTime() > lastSeen;
        const newBadge = isNew ? `<span class="badge badge-new">New</span>` : '';
        const timeChip = (showTime && item.time) ? `<span class="chip">${formatAgo(item.time)}</span>` : '';

        const retailerChips = (item.retailers || []).slice(0, 3).map(r => `<span class="chip">${escapeHtml(r)}</span>`).join('');
        const setChip = set ? `<span class="chip" style="border-color: rgba(255, 77, 46, 0.30); background: rgba(255, 77, 46, 0.12); color: var(--text);">${set}</span>` : '';

        return `
            <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener" class="intel-item" style="margin-bottom: 0.55rem;">
                <div class="intel-title">${title}</div>
                <div class="intel-meta">
                    <span class="badge" style="background: ${color}; border-color: ${color}; color: white;">${escapeHtml(getPlatformIcon(item.type))}</span>
                    ${newBadge}
                    <span class="chip" style="border-color: ${color}55; color: ${color};">${source}</span>
                    ${timeChip}
                    ${retailerChips}
                    ${setChip}
                </div>
            </a>
        `;
    };

    let html = '';
    if (todayIntel.length) {
        html += todayIntel.slice(0, 10).map(item => renderItem(item, { showTime: true })).join('');
    } else {
        html += `
            <div style="color: var(--text-secondary); font-size: 0.875rem; text-align: center; padding: 1.25rem; border: 1px dashed var(--border); border-radius: 14px; background: var(--bg-card-elevated);">
                No drop intel yet for today. Try refreshing in a bit, or check the sources below.
            </div>
        `;
    }

    if (follow.length) {
        html += `
            <div style="margin-top: 0.85rem; padding-top: 0.75rem; border-top: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
                    <div style="font-size: 0.75rem; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-muted);">Watch Sources</div>
                    <span class="chip">always</span>
                </div>
                ${follow.map(item => renderItem(item, { showTime: false })).join('')}
            </div>
        `;
    }

    container.innerHTML = html;

    // Persist last-seen timestamp so the "New" badge only means "since you last looked".
    localStorage.setItem('drops_last_seen_ts', String(Date.now()));
}

// ---------------------------------------------------------------------------
// filterDrops / renderUpcomingDrops
// ---------------------------------------------------------------------------
function filterDrops(filter) {
    currentDropFilter = filter;
    document.querySelectorAll('[data-filter]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    renderUpcomingDrops();
}

function renderUpcomingDrops() {
    const container = document.getElementById('upcomingDrops');
    if (!container) {
        console.error('upcomingDrops container not found');
        return;
    }

    const now = new Date();
    const startOfToday = new Date(now);
    startOfToday.setHours(0, 0, 0, 0);
    const startOfTomorrow = new Date(startOfToday);
    startOfTomorrow.setDate(startOfTomorrow.getDate() + 1);
    const startOfNext7 = new Date(startOfToday);
    startOfNext7.setDate(startOfNext7.getDate() + 7);

    if (!upcomingDropsData || upcomingDropsData.length === 0) {
        container.innerHTML = `
            <div class="empty">
                <div class="empty-icon"></div>
                <div>No drops data available</div>
            </div>
        `;
        return;
    }

    let drops = [...upcomingDropsData].sort((a, b) => a.date - b.date);

    // Apply filter
    if (currentDropFilter === 'today') {
        drops = drops.filter(d => d.date >= startOfToday && d.date < startOfTomorrow);
    } else if (currentDropFilter === 'next7') {
        drops = drops.filter(d => d.date >= startOfToday && d.date < startOfNext7);
    } else if (currentDropFilter === 'schedule') {
        // Schedule = all upcoming, but never show past days (keeps the page "fresh")
        drops = drops.filter(d => d.date >= startOfToday);
    }

    if (!drops.length) {
        const msg = currentDropFilter === 'today'
            ? "No scheduled drops today. Live intel below will still surface restocks and posts from today."
            : "No drops matching this filter";
        container.innerHTML = `
            <div class="empty">
                <div class="empty-icon"></div>
                <div>${msg}</div>
            </div>
        `;
        return;
    }

    container.innerHTML = drops.map(drop => {
        const msPerDay = 24 * 60 * 60 * 1000;
        const dropDayStart = new Date(drop.date);
        dropDayStart.setHours(0, 0, 0, 0);
        const dayDiff = Math.round((dropDayStart - startOfToday) / msPerDay);
        const isToday = dayDiff === 0;
        const isTomorrow = dayDiff === 1;
        const isDropped = drop.date <= now;

        const timeLabel = isToday
            ? (isDropped ? 'Dropped' : 'Today')
            : isTomorrow
                ? 'Tomorrow'
                : `${dayDiff} days`;
        // All drops are confirmed - show green badge
        const statusBadge = '<span style="background: var(--green); color: white; padding: 0.125rem 0.375rem; border-radius: 4px; font-size: 0.625rem;">CONFIRMED</span>';


        // Create ETB box with set logo
        const boxColor = drop.boxColor || '#3466af';
        const setLogo = drop.setLogo || null;

        return `
            <div class="card" style="margin-bottom: 0.75rem; ${isToday ? 'border: 2px solid var(--green);' : ''} ${isDropped && isToday ? 'opacity: 0.92;' : ''}">
                <div style="display: flex; gap: 1rem;">
                    <!-- ETB/BB Box with Set Logo -->
                    <div style="width: 80px; height: 80px; flex-shrink: 0; border-radius: 8px; overflow: hidden;
                        background: linear-gradient(145deg, ${boxColor}, ${boxColor}dd, ${boxColor}99);
                        box-shadow: 0 4px 15px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.3);
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        position: relative; border: 2px solid rgba(255,255,255,0.2);">
                        <!-- Pokemon TCG branding -->
                        <div style="position: absolute; top: 4px; font-size: 0.35rem; color: white; font-weight: 800; text-shadow: 0 1px 2px rgba(0,0,0,0.5); letter-spacing: 0.5px;">POK\u00c9MON</div>
                        <!-- Set Logo -->
                        ${setLogo ? `
                            <img src="${setLogo}" data-drop-logo="${drop.setId}" alt="${drop.name}"
                                style="max-width: 60px; max-height: 35px; object-fit: contain; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.4)); margin-top: 8px;"
                                onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <span style="display:none; font-size: 1.5rem;"></span>
                        ` : `
                            <img src="" data-drop-logo="${drop.setId}" alt="${drop.name}"
                                style="max-width: 60px; max-height: 35px; object-fit: contain; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.4)); margin-top: 8px; display: none;">
                            <span style="font-size: 1.5rem; margin-top: 8px;"></span>
                        `}
                        <!-- Product type badge -->
                        <div style="position: absolute; bottom: 4px; background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 3px;">
                            <span style="font-size: 0.35rem; color: white; font-weight: 700; letter-spacing: 0.5px;">${drop.productType}</span>
                        </div>
                        <!-- Shine effect -->
                        <div style="position: absolute; top: 0; left: 0; right: 0; height: 40%; background: linear-gradient(180deg, rgba(255,255,255,0.2) 0%, transparent 100%); border-radius: 6px 6px 0 0;"></div>
                    </div>
                    <div style="flex: 1; min-width: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.25rem; flex-wrap: wrap; gap: 0.25rem;">
                            <div>
                                <div style="font-weight: 600;">${drop.name}</div>
                                <div style="font-size: 0.75rem; color: var(--text-muted);">
                                    ${drop.date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                                    ${drop.time ? ` \u2022 <span style="color: var(--accent); font-weight: 600;">${drop.time}</span>` : ''}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-weight: 700; color: ${isToday ? 'var(--green)' : 'var(--text)'}; font-size: 0.875rem;">${timeLabel}</div>
                                ${statusBadge}
                            </div>
                        </div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0; align-items: center;">
                            ${drop.retailers.map(r => {
                                const stockInfo = dropStockStatus[drop.name]?.retailers[r];
                                const hasStock = stockInfo?.inStock;
                                const stockCount = stockInfo?.count || 0;
                                const retailerUrl = getRetailerSearchUrl(r, drop.name);
                                return `<a href="${retailerUrl}" target="_blank" style="text-decoration: none; font-size: 0.875rem; padding: 0.25rem 0.5rem; background: ${hasStock ? 'var(--green)' : 'var(--bg)'}; color: ${hasStock ? 'white' : 'var(--text)'}; border-radius: 6px; font-weight: 500; border: ${hasStock ? '1px solid var(--green)' : '1px solid var(--border)'}; cursor: pointer; transition: transform 0.1s, box-shadow 0.1s;"
                                    onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 2px 8px rgba(0,0,0,0.2)';"
                                    onmouseout="this.style.transform='';this.style.boxShadow='';">
                                    ${r}${hasStock ? ` <span style="font-size: 0.7rem; opacity: 0.9;">${stockCount}</span>` : ''}
                                </a>`;
                            }).join('')}
                        </div>
                        ${dropStockStatus[drop.name] ? `
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin: 0.5rem 0; padding: 0.5rem; background: ${dropStockStatus[drop.name].totalInStock > 0 ? 'rgba(16, 185, 129, 0.1)' : 'var(--bg)'}; border-radius: 6px; border-left: 3px solid ${dropStockStatus[drop.name].totalInStock > 0 ? 'var(--green)' : 'var(--border)'};">
                                <span style="font-size: 0.75rem; font-weight: 600; color: ${dropStockStatus[drop.name].totalInStock > 0 ? 'var(--green)' : 'var(--text-muted)'};">
                                    ${dropStockStatus[drop.name].totalInStock > 0
                                        ? `${dropStockStatus[drop.name].totalInStock}/${dropStockStatus[drop.name].totalRetailers} retailers have stock`
                                        : 'Checking stock...'}
                                </span>
                                <span style="font-size: 0.625rem; color: var(--text-muted); margin-left: auto;">
                                    Updated: ${new Date(dropStockStatus[drop.name].checked).toLocaleTimeString()}
                                </span>
                            </div>
                        ` : `
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin: 0.5rem 0; padding: 0.5rem; background: var(--bg); border-radius: 6px;">
                                <span style="opacity: 0.7;">Stock check pending...</span>
                            </div>
                        `}
                        <div style="font-size: 0.8125rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                            ${drop.products.join(', ')}
                        </div>
                        ${drop.source ? `<div style="font-size: 0.625rem; color: var(--text-muted); opacity: 0.7;">Source: ${drop.source}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Bootstrap: DOMContentLoaded + section-switch hooks
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme first (global)
    initTheme();

    console.log('DOM loaded, initializing drops...');
    console.log('upcomingDropsData length:', upcomingDropsData?.length || 0);

    // Wait a bit for DOM to be fully ready
    setTimeout(() => {
        initDrops();
    }, 100);

    // Auto-load stock zip when switching to stock tab
    setTimeout(() => {
        if (document.getElementById('stockZip')) {
            document.getElementById('stockZip').value = settings.zip || '90210';
        }
    }, 200);

    // Auto-refresh drop stock every 5 minutes if drops section is visible
    setInterval(() => {
        const dropsSection = document.getElementById('search');
        if (dropsSection && dropsSection.classList.contains('active')) {
            checkDropStock();
        }
    }, 5 * 60 * 1000); // 5 minutes
});

// Also initialize when drops section becomes visible
const originalSwitchSection = window.switchSection;
if (typeof originalSwitchSection === 'function') {
    window.switchSection = function(name) {
        originalSwitchSection(name);
        if (name === 'search') {
            setTimeout(() => {
                const container = document.getElementById('upcomingDrops');
                if (container && (!container.innerHTML.trim() || container.innerHTML.includes('empty'))) {
                    console.log('Drops section shown but empty, re-initializing...');
                    initDrops();
                }
            }, 100);
        }
        // Initialize database when switching to database section
        if (name === 'database') {
            setTimeout(() => {
                initDatabase();
            }, 100);
        }
    };
}
