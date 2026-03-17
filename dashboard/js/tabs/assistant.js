// =============================================================================
// AI ASSISTANT TAB
// =============================================================================
// Depends on globals: api(), showNotification(), switchSection(),
//                     optimizedLocalStorageSet(), settings, escapeHtml()
// =============================================================================

// ---------------------------------------------------------------------------
// Alert Rules (no automated checkout)
// ---------------------------------------------------------------------------

let autoBuyRules = JSON.parse(localStorage.getItem('autoBuyRules') || '[]');

function addAutoBuyRule() {
    const product = document.getElementById('ruleProduct').value;
    const maxPrice = parseFloat(document.getElementById('ruleMaxPrice').value) || 60;
    const quantity = parseInt(document.getElementById('ruleQuantity').value) || 3;

    const productNames = {
        'any': 'Any Pokemon TCG',
        'etb': 'Elite Trainer Box',
        'booster': 'Booster Box',
        'pack': 'Booster Packs',
        'tin': 'Tins',
        'upc': 'Ultra Premium Collection',
    };

    const rule = {
        id: Date.now(),
        product: product,
        productName: productNames[product] || product,
        maxPrice,
        quantity,
        purchased: 0,
        active: true,
        created: new Date().toISOString(),
    };

    autoBuyRules.push(rule);
    localStorage.setItem('autoBuyRules', JSON.stringify(autoBuyRules));
    renderAutoBuyRules();
}

function renderAutoBuyRules() {
    const container = document.getElementById('autoBuyRules');
    if (!container) return;
    if (!autoBuyRules.length) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.875rem;">No alert rules set up yet.</p>';
        return;
    }

    container.innerHTML = autoBuyRules.map(r => `
        <div class="rule-item">
            <div class="rule-info">
                <div class="rule-name">${r.productName || r.product}</div>
                <div class="rule-details">Max $${r.maxPrice} • ${r.purchased}/${r.quantity} alerts this month</div>
            </div>
            <span class="rule-status">${r.active ? 'Active' : 'Paused'}</span>
            <button class="btn btn-outline btn-sm" onclick="deleteRule(${r.id})" style="margin-left: 0.5rem;">Remove</button>
        </div>
    `).join('');
}

function deleteRule(id) {
    autoBuyRules = autoBuyRules.filter(r => r.id !== id);
    localStorage.setItem('autoBuyRules', JSON.stringify(autoBuyRules));
    renderAutoBuyRules();
}

// ---------------------------------------------------------------------------
// Pokemon TCG Knowledge Base (client-side AI)
// ---------------------------------------------------------------------------

const TCG_KNOWLEDGE = {
    'best sets to invest': `**Sealed Investing Basics**

**What tends to hold value:**
\u2022 Sets with iconic Pokemon and strong artwork
\u2022 Products bought near MSRP (not after hype spikes)
\u2022 Widely opened sets can be more volatile than expected

**Risk checks:**
\u2022 Reprints can reset prices
\u2022 "Limited print" claims are often unverified early on
\u2022 Shipping/taxes matter for real ROI

**Practical approach:**
\u2022 Track restocks/drops and cost-average
\u2022 Diversify across a few sets and SKUs (ETB, booster box, UPC)
\u2022 Use the Stock + Drops tabs to avoid paying secondary premiums`,

    'grade or sell raw': `**Grade or Sell Raw**

**Grade if:**
\u2022 The raw value is high enough to cover fees + shipping
\u2022 Centering/corners/surface look strong (clean photos help)
\u2022 You can wait out turnaround time
\u2022 The expected 10/9 premium clears your all-in cost

**Sell raw if:**
\u2022 The card is low value or has obvious wear
\u2022 You need liquidity soon

**Tip:** Use the Flip Calculator tab to run the numbers for your exact card.`,

    'chase cards': `**Chase Cards**

**What usually matters:**
\u2022 Top rarity tiers (SIR/SAR/alt-art style cards, secret rares)
\u2022 Popular Pokemon, trainers, and iconic artwork
\u2022 Condition: small defects can destroy graded upside

**How to use this site:**
\u2022 Use the Database tab for set-specific chase lists
\u2022 Use the Cards tab to compare raw vs graded pricing`,

    'spot fake': `**Spotting Fakes (Quick Checklist)**

**Material and print:**
\u2022 Compare to a known real card from the same era
\u2022 Look for blurry text, wrong fonts, and off colors

**Light test (not perfect):**
\u2022 Many real cards have an inner layer that blocks light
\u2022 Some counterfeits transmit too much light

**Surface and texture:**
\u2022 Modern textured cards should have consistent texture
\u2022 Holo patterns should match the set/era

**Red flags:**
\u2022 Prices that are far below market
\u2022 Seller refuses back photos
\u2022 Wrong set symbol/number/rarity for the card`,

    'grading': `**Grading Overview**

**Common graders:**
\u2022 PSA (most liquid resale in many markets)
\u2022 CGC (often cheaper, different label options)
\u2022 BGS (premiums at very high grades)

**Costs and turnaround:**
\u2022 Fees and timelines change frequently; check the grader's site
\u2022 Shipping/insurance can be a big part of the all-in cost

**Tip:** Use the Flip Calculator tab to see if grading is worth it for your card.`,

    'price': `**How Card Pricing Works**

**Main drivers:**
\u2022 Rarity and demand
\u2022 Condition (NM vs LP can be a large drop)
\u2022 Supply (set print, how much the set is opened)

**Where to check:**
\u2022 TCGPlayer market/low/high for singles
\u2022 eBay sold listings for real transactions
\u2022 PriceCharting for trends (varies by item)

**Tip:** Use the Cards tab to see raw + graded prices and recent sales.`,

    'default': `I can help with:

\u2022 Investing and sealed strategy
\u2022 Grading (PSA/CGC/BGS) and ROI
\u2022 Set chase cards and what to look for
\u2022 Spotting fakes
\u2022 Price lookups and recent sales

Use the quick question buttons above to jump in.`
};

// ---------------------------------------------------------------------------
// AI Response (knowledge-base lookup)
// ---------------------------------------------------------------------------

function getAIResponse(question) {
    const q = question.toLowerCase();

    if (q.includes('invest') || q.includes('best set') || q.includes('buy now') || q.includes('worth buying')) {
        return TCG_KNOWLEDGE['best sets to invest'];
    }
    if (q.includes('grade') && (q.includes('sell') || q.includes('raw') || q.includes('should'))) {
        return TCG_KNOWLEDGE['grade or sell raw'];
    }
    if (q.includes('chase') || q.includes('valuable card') || q.includes('look for') || q.includes('pull')) {
        return TCG_KNOWLEDGE['chase cards'];
    }
    if (q.includes('fake') || q.includes('counterfeit') || q.includes('spot') || q.includes('real') || q.includes('authentic')) {
        return TCG_KNOWLEDGE['spot fake'];
    }
    if (q.includes('grading') || q.includes('psa') || q.includes('cgc') || q.includes('bgs') || q.includes('grade cost')) {
        return TCG_KNOWLEDGE['grading'];
    }
    if (q.includes('price') || q.includes('worth') || q.includes('value') || q.includes('cost')) {
        return TCG_KNOWLEDGE['price'];
    }

    return TCG_KNOWLEDGE['default'];
}

// ---------------------------------------------------------------------------
// Chat UI
// ---------------------------------------------------------------------------

async function sendAIChat() {
    const input = document.getElementById('aiChatInput');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    askAI(message);
}

async function askAI(question) {
    const chatMessages = document.getElementById('aiChatMessages');

    // Add user message
    chatMessages.innerHTML += `
        <div class="user-message" style="margin-bottom: 1rem; padding: 0.75rem; background: var(--accent); color: white; border-radius: 8px; margin-left: 2rem;">
            <div style="font-size: 0.7rem; opacity: 0.8; margin-bottom: 0.25rem;">You</div>
            <div>${escapeHtml(question)}</div>
        </div>
    `;

    // Add loading indicator
    const loadingId = 'ai-loading-' + Date.now();
    chatMessages.innerHTML += `
        <div id="${loadingId}" class="ai-message" style="margin-bottom: 1rem; padding: 0.75rem; background: var(--bg-card); border-radius: 8px;">
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">AI Assistant</div>
            <div class="loading"><div class="spinner" style="width: 16px; height: 16px;"></div> Thinking...</div>
        </div>
    `;
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate thinking delay for natural feel
    await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 500));

    // Get response from knowledge base
    const response = getAIResponse(question);

    // Remove loading indicator
    document.getElementById(loadingId)?.remove();

    // Convert markdown-style formatting to HTML
    const formattedResponse = response
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/\u2022 /g, '&nbsp;&nbsp;\u2022 ');

    // Add AI response
    chatMessages.innerHTML += `
        <div class="ai-message" style="margin-bottom: 1rem; padding: 0.75rem; background: var(--bg-card); border-radius: 8px;">
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.25rem;">AI Assistant</div>
            <div style="line-height: 1.6;">${formattedResponse}</div>
        </div>
    `;
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ---------------------------------------------------------------------------
// Auto-Buy / Alert Settings
// ---------------------------------------------------------------------------

function saveAutoBuySettings() {
    const settings = {
        budget: parseFloat(document.getElementById('autoBuyBudget').value) || 500,
        maxPrice: parseFloat(document.getElementById('autoBuyMaxPrice').value) || 100,
        buyETBs: document.getElementById('buyETBs').checked,
        buyBoosters: document.getElementById('buyBoosters').checked,
        buyCollections: document.getElementById('buyCollections').checked
    };
    localStorage.setItem('autoBuySettings', JSON.stringify(settings));
    showNotification('Alert settings saved.', 'success');
}

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

async function initAIAssistant() {
    // Check AI status from backend
    try {
        const status = await api('/ai/status');
        const statusEl = document.getElementById('aiKeyStatus');
        if (status.available) {
            statusEl.textContent = 'Active';
            statusEl.style.background = 'var(--green)';
        } else {
            statusEl.textContent = 'Unavailable';
            statusEl.style.background = 'var(--red)';
        }
    } catch (e) {
        console.log('AI status check failed:', e);
    }

    // Load auto-buy settings
    const autoBuySettings = JSON.parse(localStorage.getItem('autoBuySettings') || '{}');
    if (autoBuySettings.budget) document.getElementById('autoBuyBudget').value = autoBuySettings.budget;
    if (autoBuySettings.maxPrice) document.getElementById('autoBuyMaxPrice').value = autoBuySettings.maxPrice;
    if (autoBuySettings.buyETBs !== undefined) document.getElementById('buyETBs').checked = autoBuySettings.buyETBs;
    if (autoBuySettings.buyBoosters !== undefined) document.getElementById('buyBoosters').checked = autoBuySettings.buyBoosters;
    if (autoBuySettings.buyCollections !== undefined) document.getElementById('buyCollections').checked = autoBuySettings.buyCollections;
}

// Initialize AI Assistant when section is shown
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initAIAssistant, 100);
});
