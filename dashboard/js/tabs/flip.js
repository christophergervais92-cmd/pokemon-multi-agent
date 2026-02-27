// =============================================================================
// Flip Calculator Tab
// =============================================================================
// Calculates grading ROI for raw Pokemon cards.
// Depends on globals: debounce(), formatPrice(), getAssetImageOverride()
// DOM elements: flipCard, flipPrice, flipCompany, flipTier, flipCardGrid,
//               flipCardGridItems, flipResultCount, flipResults
// =============================================================================

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const flipCache = new Map();
let flipCardResults = [];
let selectedFlipCard = null;

// ---------------------------------------------------------------------------
// Grading cost data (2024-2025 prices)
// ---------------------------------------------------------------------------
const GRADING_COSTS = {
    PSA: {
        economy:       { cost: 25,  turnaround: '120-150 days' },
        regular:       { cost: 75,  turnaround: '65 days' },
        express:       { cost: 150, turnaround: '20 days' },
        super_express: { cost: 300, turnaround: '10 days' },
        walk_through:  { cost: 600, turnaround: '3 days' }
    },
    CGC: {
        economy:       { cost: 18,  turnaround: '100 days' },
        regular:       { cost: 40,  turnaround: '50 days' },
        express:       { cost: 80,  turnaround: '20 days' },
        super_express: { cost: 150, turnaround: '10 days' },
        walk_through:  { cost: 250, turnaround: '5 days' }
    },
    BGS: {
        economy:       { cost: 22,  turnaround: '100 days' },
        regular:       { cost: 50,  turnaround: '45 days' },
        express:       { cost: 100, turnaround: '20 days' },
        super_express: { cost: 200, turnaround: '10 days' },
        walk_through:  { cost: 400, turnaround: '5 days' }
    }
};

// Grade multipliers (how much a graded card is worth vs raw)
const GRADE_MULTIPLIERS = {
    PSA: { 10: 3.5, 9: 1.8, 8: 1.2, 7: 0.9 },
    CGC: { 10: 2.8, 9: 1.5, 8: 1.1, 7: 0.85 },
    BGS: { 10: 4.0, 9.5: 2.5, 9: 1.6, 8.5: 1.2, 8: 1.0 }
};

// Grade probabilities (chance of getting each grade for a near-mint card)
const GRADE_PROBABILITIES = {
    PSA: { 10: 0.15, 9: 0.55, 8: 0.25, 7: 0.05 },
    CGC: { 10: 0.12, 9: 0.50, 8: 0.30, 7: 0.08 },
    BGS: { 10: 0.05, 9.5: 0.15, 9: 0.45, 8.5: 0.25, 8: 0.10 }
};

// ---------------------------------------------------------------------------
// Tier dropdown options per grading company
// ---------------------------------------------------------------------------
const TIER_OPTIONS = {
    PSA: [
        { value: 'economy',       label: 'Economy ($25)' },
        { value: 'regular',       label: 'Regular ($50)' },
        { value: 'express',       label: 'Express ($100)' },
        { value: 'super_express', label: 'Super Express ($200)' },
        { value: 'walk_through',  label: 'Walk-Through ($600)' }
    ],
    CGC: [
        { value: 'economy',       label: 'Economy ($20)' },
        { value: 'standard',      label: 'Standard ($30)' },
        { value: 'express',       label: 'Express ($65)' },
        { value: 'walk_through',  label: 'Walk-Through ($150)' }
    ],
    BGS: [
        { value: 'economy',       label: 'Economy ($25)' },
        { value: 'standard',      label: 'Standard ($40)' },
        { value: 'express',       label: 'Express ($100)' },
        { value: 'premium',       label: 'Premium ($250)' }
    ]
};

// ---------------------------------------------------------------------------
// updateFlipTiers  --  populates the tier <select> when company changes
// ---------------------------------------------------------------------------
function updateFlipTiers() {
    const company = document.getElementById('flipCompany').value;
    const tierSelect = document.getElementById('flipTier');
    const currentTier = tierSelect.value;

    const tiers = TIER_OPTIONS[company] || TIER_OPTIONS.PSA;

    tierSelect.innerHTML = tiers
        .map(t => `<option value="${t.value}">${t.label}</option>`)
        .join('');

    // Try to keep the same tier if it exists, otherwise use first option
    if (tiers.some(t => t.value === currentTier)) {
        tierSelect.value = currentTier;
    } else {
        tierSelect.value = tiers[0].value;
    }
}

// ---------------------------------------------------------------------------
// calculateFlip  --  main entry point, searches for cards then calculates
// ---------------------------------------------------------------------------
async function calculateFlip() {
    console.log('[Flip] calculateFlip called');

    const cardInput    = document.getElementById('flipCard');
    const priceInput   = document.getElementById('flipPrice');
    const companyInput = document.getElementById('flipCompany');
    const tierInput    = document.getElementById('flipTier');

    if (!cardInput || !priceInput || !companyInput || !tierInput) {
        console.error('[Flip] Missing elements:', { cardInput, priceInput, companyInput, tierInput });
        alert('Flip Calculator Error: Missing form elements');
        return;
    }

    const card    = cardInput.value?.trim();
    const price   = priceInput.value;
    const company = companyInput.value;
    const tier    = tierInput.value || 'economy';

    console.log('[Flip] Inputs:', { card, price, company, tier });

    if (!card || card.length < 2) {
        document.getElementById('flipCardGrid').style.display = 'none';
        document.getElementById('flipResults').innerHTML = '';
        return;
    }

    const results = document.getElementById('flipResults');
    const grid    = document.getElementById('flipCardGrid');

    results.innerHTML = '<div class="loading"><div class="spinner"></div>Searching for cards...</div>';
    grid.style.display = 'none';

    try {
        console.log('[Flip] Fetching cards from TCG API...');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        const url = `https://api.pokemontcg.io/v2/cards?q=name:${encodeURIComponent(card)}*&pageSize=50&select=id,name,images,set,rarity,tcgplayer,number`;
        const res = await fetch(url, {
            signal: controller.signal,
            headers: { 'Accept': 'application/json' }
        });
        clearTimeout(timeoutId);

        const data = await res.json();
        const matchingCards = data.data || [];

        console.log('[Flip] Found cards:', matchingCards.length);
        flipCardResults = matchingCards;

        if (matchingCards.length === 0) {
            results.innerHTML = `<div class="empty"><div class="empty-icon"></div>No cards found for "${card}"<br><small style="color: var(--text-muted);">Try a different search term</small></div>`;
            return;
        }

        if (matchingCards.length > 1) {
            displayFlipCardGrid(matchingCards);
            results.innerHTML = '';
            return;
        }

        // Single card found -- calculate flip directly
        await calculateFlipForCard(matchingCards[0], price, company, tier);
    } catch (e) {
        console.error('Flip calculator error:', e);
        if (e.name === 'AbortError') {
            results.innerHTML = `<div class="empty">
                <div class="empty-icon timeout"></div>
                <div>Pokemon TCG API is slow - request timed out</div>
                <button class="btn" onclick="calculateFlip()" style="margin-top: 1rem;">Try Again</button>
            </div>`;
        } else {
            results.innerHTML = `<div class="empty"><div class="empty-icon error"></div>Error: ${e.message}<br>
                <button class="btn" onclick="calculateFlip()" style="margin-top: 1rem;">Try Again</button>
            </div>`;
        }
    }
}

// ---------------------------------------------------------------------------
// displayFlipCardGrid  --  renders card selection grid when multiple matches
// ---------------------------------------------------------------------------
function displayFlipCardGrid(cards) {
    const grid        = document.getElementById('flipCardGrid');
    const gridItems   = document.getElementById('flipCardGridItems');
    const resultCount = document.getElementById('flipResultCount');

    grid.style.display = 'block';
    resultCount.textContent = `(${cards.length} results)`;

    gridItems.innerHTML = cards.map((card, i) => {
        const price = card.tcgplayer?.prices?.holofoil?.market
                   || card.tcgplayer?.prices?.normal?.market
                   || card.tcgplayer?.prices?.reverseHolofoil?.market
                   || 0;
        return `
            <div class="card-grid-item" onclick="selectFlipCard(${i})" style="cursor: pointer;">
                <img src="${getAssetImageOverride(card) || card.images?.small || ''}"
                     alt="${card.name}"
                     style="width: 100%; height: 160px; object-fit: contain;"
                     loading="lazy"
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22160%22><rect fill=%22%23171717%22 width=%22120%22 height=%22160%22/><text x=%2260%22 y=%2285%22 fill=%22%23525252%22 text-anchor=%22middle%22 font-size=%2232%22></text></svg>'">
                <div class="card-title">${card.name}</div>
                <div class="card-set">${card.set?.name || ''}</div>
                <div class="card-price">${price > 0 ? '$' + price.toFixed(2) : ''}</div>
            </div>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// selectFlipCard  --  user picks a card from the grid
// ---------------------------------------------------------------------------
async function selectFlipCard(index) {
    selectedFlipCard = flipCardResults[index];
    document.getElementById('flipCard').value = selectedFlipCard.name;
    document.getElementById('flipCardGrid').style.display = 'none';

    const price   = document.getElementById('flipPrice').value;
    const company = document.getElementById('flipCompany').value;
    const tier    = document.getElementById('flipTier')?.value || 'economy';

    await calculateFlipForCard(selectedFlipCard, price, company, tier);
}

// ---------------------------------------------------------------------------
// calculateFlipForCard  --  runs the ROI math for a single card
// ---------------------------------------------------------------------------
async function calculateFlipForCard(card, price, company, tier) {
    console.log('[Flip] calculateFlipForCard called:', { card: card?.name || card, price, company, tier });

    const results  = document.getElementById('flipResults');
    const cacheKey = `${card.id || card.name}-${price}-${company}-${tier}`;

    // Check cache
    if (flipCache.has(cacheKey)) {
        console.log('[Flip] Using cached data');
        renderFlipResults(flipCache.get(cacheKey));
        return;
    }

    results.innerHTML = '<div class="loading"><div class="spinner"></div>Calculating ROI...</div>';

    try {
        // Get raw price from TCGPlayer data on the card, or use user input
        let rawPrice = parseFloat(price) || 0;

        if (!rawPrice && card.tcgplayer?.prices) {
            const prices = card.tcgplayer.prices;
            for (const variant of Object.values(prices)) {
                if (variant.market) { rawPrice = variant.market; break; }
                if (variant.mid)    { rawPrice = variant.mid; break; }
            }
        }

        if (!rawPrice) {
            rawPrice = 20; // Default estimate
        }

        // Get grading cost
        const gradingInfo  = GRADING_COSTS[company]?.[tier] || GRADING_COSTS.PSA.economy;
        const gradingCost  = gradingInfo.cost;
        const turnaround   = gradingInfo.turnaround;
        const shippingCost = 15; // Estimated shipping both ways

        const totalCost = rawPrice + gradingCost + shippingCost;

        // Calculate scenarios for each grade
        const multipliers   = GRADE_MULTIPLIERS[company]   || GRADE_MULTIPLIERS.PSA;
        const probabilities = GRADE_PROBABILITIES[company] || GRADE_PROBABILITIES.PSA;

        const scenarios = Object.entries(multipliers).map(([grade, mult]) => {
            const gradedValue  = Math.round(rawPrice * mult * 100) / 100;
            const profit       = Math.round((gradedValue - totalCost) * 100) / 100;
            const roi          = Math.round((profit / totalCost) * 1000) / 10;
            const probability  = probabilities[grade] || 0.1;

            return {
                grade:        grade.toString(),
                graded_value: gradedValue,
                profit:       profit,
                roi_percent:  roi,
                probability:  Math.round(probability * 100)
            };
        }).sort((a, b) => parseFloat(b.grade) - parseFloat(a.grade));

        // Calculate expected value
        let expectedValue = 0;
        for (const s of scenarios) {
            const prob = (s.probability || 10) / 100;
            expectedValue += s.graded_value * prob;
        }
        const expectedProfit = expectedValue - totalCost;
        const expectedRoi    = (expectedProfit / totalCost) * 100;

        // Build flip data
        const flipData = {
            card_name:            card.name,
            card_image:           card.images?.large || card.images?.small,
            card_set:             card.set?.name || '',
            card_number:          card.number || '',
            card_rarity:          card.rarity || '',
            company:              company,
            tier:                 tier,
            raw_price:            rawPrice,
            grading_cost:         gradingCost,
            shipping_cost:        shippingCost,
            total_cost:           Math.round(totalCost * 100) / 100,
            expected_graded_value: Math.round(expectedValue * 100) / 100,
            expected_profit:      Math.round(expectedProfit * 100) / 100,
            expected_roi:         Math.round(expectedRoi * 10) / 10,
            turnaround:           turnaround,
            scenarios:            scenarios,
            recommendation:       expectedRoi > 30  ? 'RECOMMENDED - Good flip potential'
                                : expectedRoi > 0   ? 'MARGINAL - Small profit potential'
                                :                     'NOT RECOMMENDED - Likely to lose money'
        };

        flipCache.set(cacheKey, flipData);
        renderFlipResults(flipData);

    } catch (e) {
        console.error('[Flip] calculateFlipForCard error:', e);
        results.innerHTML = `<div class="empty"><div class="empty-icon error"></div>Error calculating flip: ${e.message}</div>`;
    }
}

// ---------------------------------------------------------------------------
// renderFlipResults  --  renders the full results panel
// ---------------------------------------------------------------------------
function renderFlipResults(data) {
    const results = document.getElementById('flipResults');

    if (data.error) {
        results.innerHTML = `<div class="empty"><div class="empty-icon"></div>${data.error}</div>`;
        return;
    }

    const roi      = data.expected_roi || 0;
    const roiClass = roi > 50 ? 'green' : roi > 0 ? '' : 'red';
    const hasRealPrices = data.real_graded_prices && Object.keys(data.real_graded_prices).length > 0;

    // Update scenarios with real prices if available
    let scenarios = data.scenarios || [];
    if (hasRealPrices) {
        scenarios = scenarios.map(s => {
            const realPrice = data.real_graded_prices[s.grade]?.price;
            if (realPrice) {
                const profit = realPrice - data.total_cost;
                const newRoi = (profit / data.total_cost) * 100;
                return {
                    ...s,
                    graded_value:  realPrice,
                    profit:        Math.round(profit * 100) / 100,
                    roi_percent:   Math.round(newRoi * 10) / 10,
                    is_real_price: true
                };
            }
            return s;
        });
    }

    results.innerHTML = `
        <div class="card" style="margin-bottom: 1rem;">
            <div style="display: grid; grid-template-columns: 200px 1fr; gap: 1.5rem; align-items: start;">
                <!-- Card Image Preview -->
                ${data.card_image ? `
                    <div style="text-align: center; position: sticky; top: 1rem;">
                        <img src="${data.card_image}" alt="${data.card_name}"
                            style="width: 100%; max-width: 180px; height: auto; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);">
                        <div style="text-align: center; margin-top: 0.75rem;">
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.25rem;">${data.card_set || ''}</div>
                            ${data.card_number ? `<div style="font-size: 0.625rem; color: var(--text-secondary);">${data.card_number}</div>` : ''}
                            ${data.card_rarity ? `<div style="font-size: 0.625rem; color: var(--accent); margin-top: 0.25rem; font-weight: 500;">${data.card_rarity}</div>` : ''}
                        </div>
                    </div>
                ` : ''}

                <!-- Stats Grid -->
                <div>
                    <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 0.5rem;">${data.card_name || 'Card Analysis'}</h2>
                    ${data.card_set ? `<div style="color: var(--text-secondary); margin-bottom: 1rem;">${data.card_set}</div>` : ''}
                    <div class="grid grid-2" style="gap: 0.75rem; margin-bottom: 1rem;">
                        <div class="stat" style="padding: 0.75rem;">
                            <div class="stat-value" style="font-size: 1.5rem;">$${formatPrice(data.raw_price || 0)}</div>
                            <div class="stat-label">Raw Price</div>
                        </div>
                        <div class="stat" style="padding: 0.75rem;">
                            <div class="stat-value" style="font-size: 1.5rem;">$${formatPrice(data.total_cost || 0)}</div>
                            <div class="stat-label">Total Cost</div>
                        </div>
                        <div class="stat" style="padding: 0.75rem;">
                            <div class="stat-value ${roiClass}" style="font-size: 1.5rem;">$${formatPrice(data.expected_profit || 0)}</div>
                            <div class="stat-label">Expected Profit</div>
                        </div>
                        <div class="stat" style="padding: 0.75rem;">
                            <div class="stat-value ${roiClass}" style="font-size: 1.5rem;">${roi.toFixed(1)}%</div>
                            <div class="stat-label">Expected ROI</div>
                        </div>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); padding: 0.5rem; background: var(--bg); border-radius: 6px;">
                        <strong>Grading:</strong> ${data.company || data.grading_company || 'PSA'} ${data.tier || data.grading_tier || 'economy'} ($${data.grading_cost || 0})<br>
                        <strong>Shipping:</strong> $${data.shipping_cost || 0} • <strong>Turnaround:</strong> ${data.turnaround || 'N/A'}
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <h2 style="margin: 0;">Grade Scenarios</h2>
                ${hasRealPrices ? '<span style="font-size: 0.625rem; background: var(--green); color: white; padding: 0.125rem 0.375rem; border-radius: 4px;">REAL PRICES</span>' : '<span style="font-size: 0.625rem; background: var(--gold); color: black; padding: 0.125rem 0.375rem; border-radius: 4px;">ESTIMATED</span>'}
            </div>
            ${scenarios.map(s => `
                <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border); align-items: center;">
                    <span style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-weight: 600; font-size: 1.1rem;">${s.grade}</span>
                        ${s.probability ? `<span style="font-size: 0.625rem; background: var(--bg); padding: 0.125rem 0.375rem; border-radius: 4px; color: var(--text-muted);">${s.probability}% chance</span>` : ''}
                    </span>
                    <span style="font-family: 'Space Mono', monospace; text-align: right;">
                        <span style="color: var(--text-muted);">$${s.graded_value}</span> →
                        <span class="${s.profit >= 0 ? 'green' : 'red'}" style="font-weight: 600;">${s.profit >= 0 ? '+' : ''}$${s.profit}</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">(${s.roi_percent}%)</span>
                    </span>
                </div>
            `).join('')}
        </div>

        <div class="card" style="background: ${roi > 20 ? 'rgba(34, 197, 94, 0.1)' : roi > 0 ? 'var(--bg-card)' : 'rgba(239, 68, 68, 0.1)'};">
            <div style="font-weight: 600; margin-bottom: 0.5rem;">${data.recommendation || 'Analysis complete'}</div>
            <div style="font-size: 0.875rem; color: var(--text-secondary);">
                Break-even: ${data.break_even_grade || 'N/A'} • Confidence: ${data.confidence || 'N/A'}
            </div>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// initFlipTab  --  wire up event listeners (call once on DOMContentLoaded)
// ---------------------------------------------------------------------------
function initFlipTab() {
    const debouncedFlip = debounce(calculateFlip, 400);

    document.getElementById('flipCard')?.addEventListener('input', debouncedFlip);
    document.getElementById('flipCard')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') { e.preventDefault(); calculateFlip(); }
    });

    updateFlipTiers();
}
