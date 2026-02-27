// PokeAgent - Portfolio Tab
// =============================================================================
// Tracks a user's Pokemon card collection with cost basis, market values,
// and profit/loss calculations.
// Depends on globals: api(), debounce(), optimizedLocalStorageSet(),
//                     optimizedLocalStorageGet(), syncToServer(), sessionToken
// DOM elements: portfolioName, portfolioType, portfolioCardType, portfolioCost,
//               portfolioQty, portfolioMarketPrice, portfolioTotal,
//               portfolioGain, portfolioROI, portfolioItems
// =============================================================================

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let portfolio = JSON.parse(localStorage.getItem('portfolio') || '[]');
let portfolioLookupTimeout = null;
let lastPortfolioLookup = { name: '', price: 0 };

// ---------------------------------------------------------------------------
// Auto-lookup price when typing card name
// ---------------------------------------------------------------------------
const lookupPortfolioPrice = debounce(async function() {
    const name = document.getElementById('portfolioName').value.trim();
    const type = document.getElementById('portfolioType').value;
    const priceDiv = document.getElementById('portfolioMarketPrice');

    if (!name || name.length < 2) {
        priceDiv.textContent = '-- Enter name --';
        priceDiv.style.color = 'var(--text-muted)';
        return;
    }

    priceDiv.textContent = 'Looking up...';
    priceDiv.style.color = 'var(--text-muted)';

    try {
        // Fetch price from Pokemon TCG API
        const res = await fetch(`https://api.pokemontcg.io/v2/cards?q=name:"${encodeURIComponent(name)}"&pageSize=1`);
        const data = await res.json();

        if (data.data?.length) {
            const card = data.data[0];
            const prices = card.tcgplayer?.prices || {};
            const rawPrice = prices.holofoil?.market || prices.normal?.market || prices.reverseHolofoil?.market || 0;

            // Calculate graded price based on type
            let finalPrice = rawPrice;
            const gradeMultipliers = {
                'card': 1,
                'psa10': 2.5,
                'psa9': 1.5,
                'psa8': 1.2,
                'cgc10': 2.0,
                'cgc95': 1.7,
                'bgs10': 3.5,
                'bgs95': 2.0,
                'sealed': 1,
            };

            finalPrice = rawPrice * (gradeMultipliers[type] || 1);

            if (finalPrice > 0) {
                priceDiv.textContent = `$${finalPrice.toFixed(2)}`;
                priceDiv.style.color = 'var(--accent)';
                lastPortfolioLookup = { name, price: finalPrice, rawPrice, cardType: card.types?.[0] || card.supertype };

                // Auto-fill card type if found
                const cardTypeSelect = document.getElementById('portfolioCardType');
                if (card.types?.[0] && cardTypeSelect) {
                    const typeOption = Array.from(cardTypeSelect.options).find(o => o.value === card.types[0]);
                    if (typeOption) cardTypeSelect.value = card.types[0];
                } else if (card.supertype && cardTypeSelect) {
                    const typeOption = Array.from(cardTypeSelect.options).find(o => o.value === card.supertype);
                    if (typeOption) cardTypeSelect.value = card.supertype;
                }
            } else {
                priceDiv.textContent = 'No price data';
                priceDiv.style.color = 'var(--text-muted)';
            }
        } else {
            priceDiv.textContent = 'Not found';
            priceDiv.style.color = 'var(--text-muted)';
        }
    } catch (e) {
        priceDiv.textContent = 'Lookup failed';
        priceDiv.style.color = 'var(--red)';
    }
}, 500);

// ---------------------------------------------------------------------------
// Add item to portfolio
// ---------------------------------------------------------------------------
async function addToPortfolio() {
    const name = document.getElementById('portfolioName').value.trim();
    const type = document.getElementById('portfolioType').value;
    const cardType = document.getElementById('portfolioCardType').value;
    const cost = parseFloat(document.getElementById('portfolioCost').value) || 0;
    const qty = parseInt(document.getElementById('portfolioQty').value) || 1;

    if (!name) {
        alert('Please enter an item name');
        return;
    }

    // Get the current market price (from lookup or cost)
    let currentValue = cost;
    if (lastPortfolioLookup.name.toLowerCase() === name.toLowerCase() && lastPortfolioLookup.price > 0) {
        currentValue = lastPortfolioLookup.price;
    }

    const item = {
        id: Date.now(),
        name,
        type,
        cardType,
        cost,
        qty,
        currentValue,
        added: new Date().toISOString(),
    };

    portfolio.push(item);
    savePortfolio();

    // Reset form
    document.getElementById('portfolioName').value = '';
    document.getElementById('portfolioCost').value = '';
    document.getElementById('portfolioQty').value = '1';
    document.getElementById('portfolioCardType').value = '';
    document.getElementById('portfolioMarketPrice').textContent = '-- Enter name --';
    document.getElementById('portfolioMarketPrice').style.color = 'var(--text-muted)';
    lastPortfolioLookup = { name: '', price: 0 };

    renderPortfolio();
}

// ---------------------------------------------------------------------------
// Render portfolio list and stats
// ---------------------------------------------------------------------------
function renderPortfolio() {
    const container = document.querySelector('#portfolio .card:last-child #portfolioItems') || document.getElementById('portfolioItems');

    // Calculate totals
    let totalValue = 0;
    let totalCost = 0;

    portfolio.forEach(item => {
        totalValue += (item.currentValue || item.cost) * item.qty;
        totalCost += item.cost * item.qty;
    });

    const gain = totalValue - totalCost;
    const roi = totalCost > 0 ? ((gain / totalCost) * 100) : 0;

    // Update stats
    document.getElementById('portfolioTotal').textContent = `$${totalValue.toFixed(2)}`;
    document.getElementById('portfolioGain').textContent = `${gain >= 0 ? '+' : ''}$${gain.toFixed(2)}`;
    document.getElementById('portfolioGain').className = `stat-value ${gain >= 0 ? 'green' : 'red'}`;
    document.querySelector('#portfolio .stat:nth-child(3) .stat-value').textContent = portfolio.length;
    document.getElementById('portfolioROI').textContent = `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`;

    if (!portfolio.length) {
        container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">Your portfolio is empty. Add items above!</p>';
        return;
    }

    const typeLabels = {
        'card': 'Raw',
        'psa10': 'PSA 10',
        'psa9': 'PSA 9',
        'psa8': 'PSA 8',
        'cgc10': 'CGC 10',
        'cgc95': 'CGC 9.5',
        'bgs10': 'BGS 10',
        'bgs95': 'BGS 9.5',
        'sealed': 'Sealed',
    };

    container.innerHTML = portfolio.map(item => {
        const value = (item.currentValue || item.cost) * item.qty;
        const itemGain = value - (item.cost * item.qty);
        const itemRoi = item.cost > 0 ? ((itemGain / (item.cost * item.qty)) * 100) : 0;

        return `
                    <div class="portfolio-item">
                        <div style="min-width: 180px;">
                            <div class="portfolio-item-name">${item.name}</div>
                            <div class="portfolio-item-type">
                                ${typeLabels[item.type] || item.type}
                                ${item.cardType ? ` | ${item.cardType}` : ''}
                                ${item.qty > 1 ? ` | x${item.qty}` : ''}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.625rem; color: var(--text-muted);">Cost</div>
                            <div class="portfolio-item-value">$${(item.cost * item.qty).toFixed(2)}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.625rem; color: var(--text-muted);">Market</div>
                            <div class="portfolio-item-value" style="color: var(--accent);">$${value.toFixed(2)}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.625rem; color: var(--text-muted);">P/L</div>
                            <div class="portfolio-item-gain ${itemGain >= 0 ? 'green' : 'red'}">
                                ${itemGain >= 0 ? '+' : ''}$${itemGain.toFixed(2)}
                                <span style="font-size: 0.625rem; opacity: 0.8;">(${itemRoi >= 0 ? '+' : ''}${itemRoi.toFixed(0)}%)</span>
                            </div>
                        </div>
                        <button class="btn btn-outline btn-sm" onclick="removeFromPortfolio(${item.id})">X</button>
                    </div>
                `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Remove item from portfolio
// ---------------------------------------------------------------------------
function removeFromPortfolio(id) {
    portfolio = portfolio.filter(item => item.id !== id);
    savePortfolio();
    renderPortfolio();
}

// ---------------------------------------------------------------------------
// Save portfolio and sync to server
// ---------------------------------------------------------------------------
function savePortfolio() {
    optimizedLocalStorageSet('portfolio', portfolio);
    if (sessionToken) syncToServer('portfolio', portfolio);
}

// ---------------------------------------------------------------------------
// Refresh all portfolio prices from the API
// ---------------------------------------------------------------------------
async function refreshPortfolioPrices() {
    const btn = document.querySelector('[onclick="refreshPortfolioPrices()"]');
    btn.disabled = true;
    btn.textContent = 'Refreshing...';

    for (const item of portfolio) {
        try {
            const data = await api(`/prices/card/${encodeURIComponent(item.name)}`);
            if (data.raw?.price) {
                // Adjust based on type
                if (item.type === 'card') {
                    item.currentValue = data.raw.price;
                } else if (item.type === 'psa' && data.graded?.['PSA 10']) {
                    item.currentValue = data.graded['PSA 10'].price;
                } else if (item.type === 'cgc' && data.graded?.['CGC 10']) {
                    item.currentValue = data.graded['CGC 10'].price;
                } else if (item.type === 'bgs' && data.graded?.['BGS 10']) {
                    item.currentValue = data.graded['BGS 10'].price;
                } else {
                    item.currentValue = data.raw.price * 1.1; // Sealed premium
                }
            }
        } catch (e) {
            console.error('Failed to get price for', item.name);
        }
    }

    savePortfolio();
    renderPortfolio();

    btn.disabled = false;
    btn.textContent = 'Refresh Prices';
}
