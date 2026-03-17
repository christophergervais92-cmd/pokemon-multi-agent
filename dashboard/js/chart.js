// PokeAgent - Canvas Price Chart Module
//
// Globals from state.js:
//   chartContext, currentChartRange, currentChartGrade,
//   priceHistoryData, allGradePrices, selectedCard

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format a price number for chart axis labels (no dollar sign).
 * Returns the numeric string only -- callers prepend '$'.
 */
function formatChartPrice(value) {
    if (value === null || value === undefined || value === '' || isNaN(value)) return '??';
    const num = parseFloat(value);
    if (isNaN(num) || num === 0) return '??';
    if (num >= 1000) return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    if (num >= 100) return num.toFixed(0);
    return num.toFixed(2);
}

// ---------------------------------------------------------------------------
// Price-history data generation
// ---------------------------------------------------------------------------

function generatePriceHistory(card) {
    // Get raw price from various sources
    const prices = card.tcgplayer?.prices || {};
    const rawPrice = allGradePrices['raw'] ||
                     prices.holofoil?.market ||
                     prices.normal?.market ||
                     prices.reverseHolofoil?.market ||
                     card.priceData?.raw?.price ||
                     10;

    // Ensure allGradePrices has at least the raw price
    if (!allGradePrices['raw'] || Object.keys(allGradePrices).length === 0) {
        const basePrice = rawPrice;
        allGradePrices = {
            'raw': basePrice,
            'PSA 10': basePrice * 2.5,
            'PSA 9': basePrice * 1.8,
            'CGC 10': basePrice * 2.0,
            'CGC 9.5': basePrice * 1.7,
            'BGS 10': basePrice * 3.5
        };
    }

    // Reset to raw and generate data
    currentChartGrade = 'raw';
    const gradeSelect = document.getElementById('gradeSelect');
    if (gradeSelect) gradeSelect.value = 'raw';

    generatePriceHistoryForGrade(rawPrice);
    console.log('Generated price history with raw price:', rawPrice);
}

function generatePriceHistoryForGrade(basePrice) {
    priceHistoryData = {
        '1M': generatePricePoints(basePrice, 30, 0.12),
        '3M': generatePricePoints(basePrice, 90, 0.20),
        '6M': generatePricePoints(basePrice, 180, 0.30),
        '1Y': generatePricePoints(basePrice, 365, 0.45),
        '2Y': generatePricePoints(basePrice, 730, 0.65),
    };
}

function generateProductPriceHistory(product) {
    const basePrice = product.price || 50;

    // Products don't have graded versions
    allGradePrices = { 'raw': basePrice };
    currentChartGrade = 'raw';
    document.getElementById('gradeSelect').value = 'raw';

    priceHistoryData = {
        '1M': generatePricePoints(basePrice, 30, 0.08),
        '3M': generatePricePoints(basePrice, 90, 0.15),
        '6M': generatePricePoints(basePrice, 180, 0.25),
        '1Y': generatePricePoints(basePrice, 365, 0.35),
        '2Y': generatePricePoints(basePrice, 730, 0.45),
    };
}

function generatePricePoints(currentPrice, days, volatility) {
    const points = [];

    // Start price: generally cards appreciate, so start lower
    const trendUp = Math.random() > 0.3; // 70% chance of uptrend
    const startMultiplier = trendUp ? (0.6 + Math.random() * 0.3) : (1.1 + Math.random() * 0.3);
    let price = currentPrice * startMultiplier;

    // Create smooth price movement with realistic patterns
    const dailyVolatility = volatility / days * 2;
    let trend = trendUp ? 0.001 : -0.001; // Slight trend direction

    for (let i = days; i >= 0; i--) {
        // Smooth random walk with mean reversion
        const noise = (Math.random() - 0.5) * 2 * dailyVolatility * currentPrice;
        const meanReversion = (currentPrice - price) * 0.01; // Pull toward current

        // Occasional jumps (releases, market events)
        const jump = Math.random() < 0.02 ? (Math.random() - 0.5) * currentPrice * 0.1 : 0;

        price += trend * currentPrice + noise + meanReversion + jump;
        price = Math.max(price, currentPrice * 0.2); // Floor at 20% of current
        price = Math.min(price, currentPrice * 3);   // Cap at 3x current

        points.push({
            date: new Date(Date.now() - i * 24 * 60 * 60 * 1000),
            price: Math.round(price * 100) / 100
        });
    }

    // Smooth approach to current price in last 5 days
    const smoothDays = Math.min(5, points.length - 1);
    for (let i = 0; i < smoothDays; i++) {
        const idx = points.length - smoothDays + i;
        const weight = (i + 1) / smoothDays;
        points[idx].price = Math.round((points[idx].price * (1 - weight) + currentPrice * weight) * 100) / 100;
    }

    // Ensure last point IS the current price
    points[points.length - 1].price = currentPrice;

    return points;
}

// ---------------------------------------------------------------------------
// Grade / range selection
// ---------------------------------------------------------------------------

function setChartGrade(grade) {
    currentChartGrade = grade;
    const price = allGradePrices[grade] || allGradePrices['raw'] || 10;
    generatePriceHistoryForGrade(price);
    drawPriceChart();

    // Update recent sales for the selected grade
    if (selectedCard) {
        displayRecentSales(selectedCard, grade);
    }
}

function setChartRange(range) {
    currentChartRange = range;
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.range === range);
    });
    drawPriceChart();
}

// ---------------------------------------------------------------------------
// Main chart drawing
// ---------------------------------------------------------------------------

function drawPriceChart() {
    const canvas = document.getElementById('priceChart');
    if (!canvas) {
        console.error('Price chart canvas not found');
        return;
    }

    const ctx = canvas.getContext('2d');
    let data = priceHistoryData[currentChartRange] || [];

    // If no data, generate fallback data based on allGradePrices
    if (!data.length) {
        console.log('No price history data for range:', currentChartRange, '- generating fallback');
        const basePrice = allGradePrices['raw'] || allGradePrices[currentChartGrade] || 10;
        const days = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730 }[currentChartRange] || 30;
        data = generatePricePoints(basePrice, days, 0.15);
        priceHistoryData[currentChartRange] = data;
    }

    if (!data.length) {
        console.error('Still no chart data after fallback');
        return;
    }

    // Set canvas size with fallback minimums
    const rect = canvas.parentElement?.getBoundingClientRect() || { width: 432, height: 232 };
    canvas.width = Math.max(rect.width - 32, 400);
    canvas.height = Math.max(rect.height - 32, 200);

    const width = canvas.width;
    const height = canvas.height;

    console.log('Drawing chart:', { width, height, dataPoints: data.length });
    const padding = { top: 20, right: 15, bottom: 25, left: 55 };

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Calculate min/max
    const prices = data.map(d => d.price);
    const minPrice = Math.min(...prices) * 0.95;
    const maxPrice = Math.max(...prices) * 1.05;

    // Scale functions
    const xScale = (i) => padding.left + (i / (data.length - 1)) * (width - padding.left - padding.right);
    const yScale = (p) => height - padding.bottom - ((p - minPrice) / (maxPrice - minPrice)) * (height - padding.top - padding.bottom);
    const isUp = data[data.length - 1].price >= data[0].price;

    // Store for hover
    chartContext = { data, xScale, yScale, padding, width, height, isUp, minPrice, maxPrice };

    // Draw gradient fill based on overall trend
    const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
    gradient.addColorStop(0, isUp ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.beginPath();
    ctx.moveTo(xScale(0), height - padding.bottom);
    data.forEach((d, i) => ctx.lineTo(xScale(i), yScale(d.price)));
    ctx.lineTo(xScale(data.length - 1), height - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line -- green if overall up, red if overall down
    ctx.beginPath();
    data.forEach((d, i) => {
        if (i === 0) ctx.moveTo(xScale(i), yScale(d.price));
        else ctx.lineTo(xScale(i), yScale(d.price));
    });
    ctx.strokeStyle = isUp ? '#22c55e' : '#ef4444';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Draw current price dot (color based on overall trend)
    const lastPoint = data[data.length - 1];
    ctx.beginPath();
    ctx.arc(xScale(data.length - 1), yScale(lastPoint.price), 6, 0, Math.PI * 2);
    ctx.fillStyle = isUp ? '#22c55e' : '#ef4444';
    ctx.fill();
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Y-axis labels
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#666';
    ctx.font = '11px Space Mono, monospace';
    ctx.textAlign = 'right';

    const ySteps = 4;
    for (let i = 0; i <= ySteps; i++) {
        const price = minPrice + (maxPrice - minPrice) * (i / ySteps);
        const y = yScale(price);
        ctx.fillText('$' + formatChartPrice(price), padding.left - 8, y + 4);

        // Grid line
        ctx.strokeStyle = 'rgba(128, 128, 128, 0.15)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // X-axis labels
    ctx.textAlign = 'center';
    const dates = [data[0].date, data[Math.floor(data.length / 2)].date, data[data.length - 1].date];
    dates.forEach((d, i) => {
        const x = xScale(i === 0 ? 0 : i === 1 ? Math.floor(data.length / 2) : data.length - 1);
        ctx.fillText(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), x, height - 5);
    });

    // Stats
    const startPrice = data[0].price;
    const endPrice = data[data.length - 1].price;
    const change = ((endPrice - startPrice) / startPrice * 100).toFixed(1);
    const high = Math.max(...prices).toFixed(2);
    const low = Math.min(...prices).toFixed(2);

    document.getElementById('chartStats').innerHTML = `
        <div style="color: ${isUp ? 'var(--green)' : 'var(--red)'}; font-weight: 600;">${isUp ? '\u2191' : '\u2193'} ${change}%</div>
        <div>H: $${high}</div>
        <div>L: $${low}</div>
    `;

    // Setup hover events (once)
    if (!canvas.hasAttribute('data-hover-setup')) {
        canvas.setAttribute('data-hover-setup', 'true');
        setupChartHover(canvas);
    }
}

// ---------------------------------------------------------------------------
// Hover / tooltip
// ---------------------------------------------------------------------------

function setupChartHover(canvas) {
    // Create tooltip element (stock-chart style)
    let tooltip = document.getElementById('chartTooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'chartTooltip';
        tooltip.style.cssText = `
            position: fixed;
            background: rgba(20, 20, 25, 0.95);
            border: 1px solid rgba(139, 92, 246, 0.5);
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 12px;
            font-family: 'Space Mono', monospace;
            pointer-events: none;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            backdrop-filter: blur(8px);
            min-width: 140px;
        `;
        document.body.appendChild(tooltip);
    }

    // Track last hover index for performance
    let lastHoverIndex = -1;

    canvas.addEventListener('mousemove', (e) => {
        const { data, xScale, yScale, padding, width, height, isUp } = chartContext;
        if (!data || !data.length || !xScale) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Check if in chart area
        if (x < padding.left || x > width - padding.right) {
            tooltip.style.display = 'none';
            if (lastHoverIndex !== -1) {
                lastHoverIndex = -1;
                drawPriceChart();
            }
            return;
        }

        // Find closest data point
        const chartWidth = width - padding.left - padding.right;
        const ratio = (x - padding.left) / chartWidth;
        const index = Math.round(ratio * (data.length - 1));
        const clampedIndex = Math.max(0, Math.min(data.length - 1, index));

        // Only redraw if index changed (performance)
        if (clampedIndex === lastHoverIndex) {
            // Just update tooltip position
            tooltip.style.left = (e.clientX + 15) + 'px';
            tooltip.style.top = (e.clientY - 60) + 'px';
            return;
        }
        lastHoverIndex = clampedIndex;

        const point = data[clampedIndex];
        const startPoint = data[0];
        const changePercent = ((point.price - startPoint.price) / startPoint.price * 100).toFixed(2);
        const changeColor = point.price >= startPoint.price ? '#22c55e' : '#ef4444';
        const changeSign = point.price >= startPoint.price ? '+' : '';

        // Update tooltip with stock-chart style info
        const dateStr = point.date.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });

        tooltip.innerHTML = `
            <div style="color: #888; font-size: 10px; margin-bottom: 6px; letter-spacing: 0.5px;">${dateStr}</div>
            <div style="font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 4px;">$${point.price.toFixed(2)}</div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="color: ${changeColor}; font-weight: 600; font-size: 13px;">${changeSign}${changePercent}%</span>
                <span style="color: #666; font-size: 11px;">from start</span>
            </div>
            <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 10px; color: #666;">
                Day ${clampedIndex + 1} of ${data.length}
            </div>
        `;
        tooltip.style.display = 'block';

        // Smart positioning -- avoid going off screen
        let left = e.clientX + 15;
        let top = e.clientY - 60;

        if (left + 160 > window.innerWidth) {
            left = e.clientX - 160;
        }
        if (top < 10) {
            top = e.clientY + 20;
        }

        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';

        // Redraw chart with hover crosshair
        drawPriceChartWithHover(clampedIndex);
    });

    canvas.addEventListener('mouseleave', () => {
        tooltip.style.display = 'none';
        lastHoverIndex = -1;
        drawPriceChart(); // Redraw without hover
    });

    // Touch support for mobile
    canvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        canvas.dispatchEvent(mouseEvent);
    });

    canvas.addEventListener('touchend', () => {
        tooltip.style.display = 'none';
        lastHoverIndex = -1;
        drawPriceChart();
    });
}

// ---------------------------------------------------------------------------
// Chart with hover crosshair overlay
// ---------------------------------------------------------------------------

function drawPriceChartWithHover(hoverIndex) {
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');
    const { data, xScale, yScale, padding, width, height, isUp, minPrice, maxPrice } = chartContext;

    if (!data || !data.length) return;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Draw gradient fill based on overall trend
    const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
    gradient.addColorStop(0, isUp ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.beginPath();
    ctx.moveTo(xScale(0), height - padding.bottom);
    data.forEach((d, i) => ctx.lineTo(xScale(i), yScale(d.price)));
    ctx.lineTo(xScale(data.length - 1), height - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw line -- green if overall up, red if overall down
    ctx.beginPath();
    data.forEach((d, i) => {
        if (i === 0) ctx.moveTo(xScale(i), yScale(d.price));
        else ctx.lineTo(xScale(i), yScale(d.price));
    });
    ctx.strokeStyle = isUp ? '#22c55e' : '#ef4444';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Get hover point coordinates
    const hoverX = xScale(hoverIndex);
    const hoverY = yScale(data[hoverIndex].price);
    const hoverPrice = data[hoverIndex].price;

    // Draw vertical crosshair line (full height, semi-transparent)
    ctx.strokeStyle = 'rgba(139, 92, 246, 0.4)';
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(hoverX, padding.top);
    ctx.lineTo(hoverX, height - padding.bottom);
    ctx.stroke();

    // Draw horizontal crosshair line at price level
    ctx.strokeStyle = 'rgba(139, 92, 246, 0.4)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padding.left, hoverY);
    ctx.lineTo(width - padding.right, hoverY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw price label on Y-axis
    ctx.fillStyle = '#8b5cf6';
    const priceLabel = '$' + hoverPrice.toFixed(2);
    ctx.fillRect(0, hoverY - 10, padding.left - 4, 20);
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px Space Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText(priceLabel, padding.left - 8, hoverY + 4);

    // Draw hover dot with glow effect (color based on overall trend)
    ctx.shadowColor = isUp ? '#22c55e' : '#ef4444';
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(hoverX, hoverY, 8, 0, Math.PI * 2);
    ctx.fillStyle = isUp ? '#22c55e' : '#ef4444';
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Draw current price dot (smaller when not hovered)
    if (hoverIndex !== data.length - 1) {
        ctx.beginPath();
        ctx.arc(xScale(data.length - 1), yScale(data[data.length - 1].price), 5, 0, Math.PI * 2);
        ctx.fillStyle = isUp ? '#22c55e' : '#ef4444';
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    // Y-axis labels
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#666';
    ctx.font = '11px Space Mono, monospace';
    ctx.textAlign = 'right';

    const ySteps = 4;
    for (let i = 0; i <= ySteps; i++) {
        const price = minPrice + (maxPrice - minPrice) * (i / ySteps);
        const y = yScale(price);
        ctx.fillText('$' + formatChartPrice(price), padding.left - 8, y + 4);

        // Grid line
        ctx.strokeStyle = 'rgba(128, 128, 128, 0.15)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // X-axis labels
    ctx.textAlign = 'center';
    const dates = [data[0].date, data[Math.floor(data.length / 2)].date, data[data.length - 1].date];
    dates.forEach((d, i) => {
        const x = xScale(i === 0 ? 0 : i === 1 ? Math.floor(data.length / 2) : data.length - 1);
        ctx.fillText(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), x, height - 5);
    });
}

// ---------------------------------------------------------------------------
// Fallback chart initialisation
// ---------------------------------------------------------------------------

function initFallbackChart(card) {
    const chartCanvas = document.getElementById('priceChart');
    if (!chartCanvas) return;

    requestAnimationFrame(() => {
        const rect = chartCanvas.parentElement.getBoundingClientRect();
        chartCanvas.width = rect.width - 32 || 400;
        chartCanvas.height = rect.height - 32 || 168;

        const ctx = chartCanvas.getContext('2d');
        const prices = card.tcgplayer?.prices || {};
        const marketPrice = prices.holofoil?.market || prices.normal?.market || 0;

        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#666';
        ctx.font = '14px sans-serif';
        ctx.textAlign = 'center';

        if (marketPrice > 0) {
            ctx.fillText(`Market: $${marketPrice.toFixed(2)}`, chartCanvas.width / 2, chartCanvas.height / 2);
        } else {
            ctx.fillText('Price history loading...', chartCanvas.width / 2, chartCanvas.height / 2);
        }
    });
}
