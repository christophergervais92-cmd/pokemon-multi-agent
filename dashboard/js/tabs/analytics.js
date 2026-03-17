// PokeAgent - Analytics Tab
// =============================================================================
// Purchase tracking, stock-check accuracy verification, spending summaries,
// and backtesting across retailers.
// Depends on globals: api(), autoBuyRules, renderAutoBuyRules(), renderPortfolio()
// DOM elements: purchaseProduct, purchaseRetailer, purchasePrice, purchaseQty,
//               purchaseHistory, verifyStore, verifySystemSaid, analyticsScans,
//               analyticsHits, analyticsAccuracy, analyticsPurchases,
//               spendToday, spendWeek, spendMonth, spendTotal,
//               retailerAccuracy, rulePerformance, backtestOutput
// =============================================================================

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let purchases = JSON.parse(localStorage.getItem('purchases') || '[]');
let stockVerifications = JSON.parse(localStorage.getItem('stockVerifications') || '[]');
let scanHistory = JSON.parse(localStorage.getItem('scanHistory') || '[]');

// ---------------------------------------------------------------------------
// Purchase Tracking
// ---------------------------------------------------------------------------

function logPurchase() {
    const product = document.getElementById('purchaseProduct').value.trim();
    const retailer = document.getElementById('purchaseRetailer').value;
    const price = parseFloat(document.getElementById('purchasePrice').value) || 0;
    const qty = parseInt(document.getElementById('purchaseQty').value) || 1;

    if (!product || !price) {
        alert('Please enter product and price');
        return;
    }

    const purchase = {
        id: Date.now(),
        product,
        retailer,
        price,
        qty,
        total: price * qty,
        date: new Date().toISOString(),
        fromRule: null, // Will be set if matched to an auto-buy rule
    };

    // Check if this matches any auto-buy rules
    for (const rule of autoBuyRules) {
        if (rule.active && price <= rule.maxPrice) {
            const productLower = product.toLowerCase();
            const ruleMatch = (
                rule.product === 'any' ||
                (rule.product === 'etb' && productLower.includes('elite trainer')) ||
                (rule.product === 'booster' && productLower.includes('booster box')) ||
                (rule.product === 'pack' && productLower.includes('pack')) ||
                (rule.product === 'tin' && productLower.includes('tin')) ||
                (rule.product === 'upc' && productLower.includes('ultra premium'))
            );

            if (ruleMatch && rule.purchased < rule.quantity) {
                rule.purchased++;
                purchase.fromRule = rule.id;
                localStorage.setItem('autoBuyRules', JSON.stringify(autoBuyRules));
                break;
            }
        }
    }

    purchases.push(purchase);
    localStorage.setItem('purchases', JSON.stringify(purchases));

    // Clear inputs
    document.getElementById('purchaseProduct').value = '';
    document.getElementById('purchasePrice').value = '';
    document.getElementById('purchaseQty').value = '1';

    renderPurchaseHistory();
    renderAnalyticsStats();
    renderAutoBuyRules();
}

function renderPurchaseHistory() {
    const container = document.getElementById('purchaseHistory');
    const recent = purchases.slice(-10).reverse();

    if (!recent.length) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.875rem;">No purchases logged yet.</p>';
        return;
    }

    container.innerHTML = recent.map(p => {
        const date = new Date(p.date).toLocaleDateString();
        return `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--bg); border-radius: 6px; margin-bottom: 0.5rem;">
                <div>
                    <div style="font-weight: 500;">${p.product}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        ${p.retailer} • ${date} ${p.fromRule ? '• Auto-buy rule' : ''}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-family: 'Space Mono', monospace; font-weight: 600;">$${p.total.toFixed(2)}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">x${p.qty}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Stock Verification
// ---------------------------------------------------------------------------

function verifyStock(wasCorrect) {
    const store = document.getElementById('verifyStore').value.trim();
    const systemSaid = document.getElementById('verifySystemSaid').value;

    if (!store) {
        alert('Please enter the store/product');
        return;
    }

    const verification = {
        id: Date.now(),
        store,
        systemSaid,
        wasCorrect,
        date: new Date().toISOString(),
    };

    stockVerifications.push(verification);
    localStorage.setItem('stockVerifications', JSON.stringify(stockVerifications));

    document.getElementById('verifyStore').value = '';

    renderAnalyticsStats();
    renderBacktestResults();
}

// ---------------------------------------------------------------------------
// Analytics Stats
// ---------------------------------------------------------------------------

function renderAnalyticsStats() {
    // Total scans (from scan history)
    document.getElementById('analyticsScans').textContent = scanHistory.length || purchases.length;

    // Stock found
    const stockHits = stockVerifications.filter(v => v.systemSaid === 'in_stock').length;
    document.getElementById('analyticsHits').textContent = stockHits;

    // Accuracy
    const correct = stockVerifications.filter(v => v.wasCorrect).length;
    const accuracy = stockVerifications.length > 0
        ? Math.round((correct / stockVerifications.length) * 100)
        : 0;
    document.getElementById('analyticsAccuracy').textContent = accuracy + '%';

    // Purchases
    document.getElementById('analyticsPurchases').textContent = purchases.length;

    // Spending summary
    const now = new Date();
    const today = now.toDateString();
    const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);
    const monthAgo = new Date(now - 30 * 24 * 60 * 60 * 1000);

    const spendToday = purchases
        .filter(p => new Date(p.date).toDateString() === today)
        .reduce((sum, p) => sum + p.total, 0);
    const spendWeek = purchases
        .filter(p => new Date(p.date) >= weekAgo)
        .reduce((sum, p) => sum + p.total, 0);
    const spendMonth = purchases
        .filter(p => new Date(p.date) >= monthAgo)
        .reduce((sum, p) => sum + p.total, 0);
    const spendTotal = purchases.reduce((sum, p) => sum + p.total, 0);

    document.getElementById('spendToday').textContent = '$' + spendToday.toFixed(2);
    document.getElementById('spendWeek').textContent = '$' + spendWeek.toFixed(2);
    document.getElementById('spendMonth').textContent = '$' + spendMonth.toFixed(2);
    document.getElementById('spendTotal').textContent = '$' + spendTotal.toFixed(2);
}

// ---------------------------------------------------------------------------
// Backtest Results
// ---------------------------------------------------------------------------

function renderBacktestResults() {
    // Accuracy by retailer
    const retailerStats = {};
    const retailers = ['Target', 'Walmart', 'Best Buy', 'GameStop', 'Pokemon Center'];

    retailers.forEach(r => {
        const checks = stockVerifications.filter(v => v.store.includes(r));
        const correct = checks.filter(v => v.wasCorrect).length;
        retailerStats[r] = {
            total: checks.length,
            correct,
            accuracy: checks.length > 0 ? Math.round((correct / checks.length) * 100) : null
        };
    });

    const retailerHtml = retailers.map(r => {
        const stat = retailerStats[r];
        if (stat.total === 0) return '';
        return `
            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                <span>${r}</span>
                <span style="font-weight: 600; color: ${stat.accuracy >= 80 ? 'var(--green)' : stat.accuracy >= 50 ? 'var(--text-secondary)' : 'var(--red)'};">
                    ${stat.accuracy}% (${stat.correct}/${stat.total})
                </span>
            </div>
        `;
    }).filter(Boolean).join('') || '<p style="color: var(--text-muted); font-size: 0.875rem;">No data yet. Verify some stock checks!</p>';

    document.getElementById('retailerAccuracy').innerHTML = retailerHtml;

    // Rule performance
    const ruleHtml = autoBuyRules.map(r => {
        const rulePurchases = purchases.filter(p => p.fromRule === r.id);
        const totalSpent = rulePurchases.reduce((sum, p) => sum + p.total, 0);
        return `
            <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                <span>${r.productName || r.product}</span>
                <span style="font-weight: 600;">
                    ${r.purchased}/${r.quantity} ($${totalSpent.toFixed(2)})
                </span>
            </div>
        `;
    }).join('') || '<p style="color: var(--text-muted); font-size: 0.875rem;">No alert rules set up.</p>';

    document.getElementById('rulePerformance').innerHTML = ruleHtml;
}

// ---------------------------------------------------------------------------
// Run Backtest
// ---------------------------------------------------------------------------

async function runBacktest() {
    const output = document.getElementById('backtestOutput');
    output.innerHTML = '<div class="loading"><div class="spinner"></div>Running backtest...</div>';

    const results = {
        retailers: {},
        totalChecks: 0,
        inStock: 0,
        outOfStock: 0,
        errors: 0,
    };

    const retailers = [
        { name: 'Target', endpoint: '/scanner/target' },
        { name: 'Walmart', endpoint: '/scanner/walmart' },
        { name: 'Best Buy', endpoint: '/scanner/bestbuy' },
        { name: 'GameStop', endpoint: '/scanner/gamestop' },
    ];

    const testProducts = ['pokemon etb', 'pokemon booster', 'pokemon cards'];

    for (const retailer of retailers) {
        results.retailers[retailer.name] = { checks: 0, inStock: 0, errors: 0, products: [] };

        for (const product of testProducts) {
            try {
                const data = await api(`${retailer.endpoint}?q=${encodeURIComponent(product)}`);
                results.totalChecks++;
                results.retailers[retailer.name].checks++;

                if (data.error) {
                    results.errors++;
                    results.retailers[retailer.name].errors++;
                } else {
                    const products = data.products || data.results || [];
                    const inStockCount = products.filter(p => p.stock).length;

                    if (inStockCount > 0) {
                        results.inStock++;
                        results.retailers[retailer.name].inStock++;
                        results.retailers[retailer.name].products.push(...products.filter(p => p.stock).slice(0, 2));
                    } else {
                        results.outOfStock++;
                    }
                }

                // Log to scan history
                scanHistory.push({
                    retailer: retailer.name,
                    query: product,
                    date: new Date().toISOString(),
                    found: (data.products || []).filter(p => p.stock).length,
                });
            } catch (e) {
                results.errors++;
                results.retailers[retailer.name].errors++;
            }
        }
    }

    localStorage.setItem('scanHistory', JSON.stringify(scanHistory));
    renderAnalyticsStats();

    output.innerHTML = `
        <div style="padding: 1rem; background: var(--bg); border-radius: 8px;">
            <div style="font-weight: 600; margin-bottom: 1rem;">Backtest Complete</div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;">
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700;">${results.totalChecks}</div>
                    <div style="font-size: 0.625rem; color: var(--text-muted);">Total Checks</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--green);">${results.inStock}</div>
                    <div style="font-size: 0.625rem; color: var(--text-muted);">In Stock</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700;">${results.outOfStock}</div>
                    <div style="font-size: 0.625rem; color: var(--text-muted);">Out of Stock</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--red);">${results.errors}</div>
                    <div style="font-size: 0.625rem; color: var(--text-muted);">Errors</div>
                </div>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">
                ${Object.entries(results.retailers).map(([name, data]) =>
                    `<div style="margin-bottom: 0.25rem;">
                        <strong>${name}:</strong> ${data.inStock}/${data.checks} found stock
                        ${data.errors > 0 ? `<span style="color: var(--red);">(${data.errors} errors)</span>` : ''}
                    </div>`
                ).join('')}
            </div>
            <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 1rem;">
                Note: Results show API responses. Visit stores to verify actual accuracy and log verifications above.
            </p>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        renderPurchaseHistory();
        renderAnalyticsStats();
        renderBacktestResults();
    }, 100);
});
