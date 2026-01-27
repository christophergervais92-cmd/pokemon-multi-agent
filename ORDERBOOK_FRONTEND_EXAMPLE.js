/**
 * Frontend Example: How to call the orderbook API with asset_id
 * 
 * This shows how to update your frontend (preview.html) to use the new asset_id parameter
 * for fetching orderbook data, which automatically includes set_name for proper filtering.
 */

// =============================================================================
// OPTION 1: Use asset_id (RECOMMENDED - automatically includes set_name)
// =============================================================================

async function fetchOrderBook(assetId) {
    try {
        const response = await fetch(
            `http://localhost:5001/market/orderbook?asset_id=${encodeURIComponent(assetId)}`
        );
        const data = await response.json();
        
        if (data.success && data.sources) {
            // Find eBay source with transactions
            const ebaySource = data.sources.find(s => s.source === 'eBay' && s.transactions);
            if (ebaySource && ebaySource.transactions) {
                return ebaySource.transactions; // Array of {price, date, title}
            }
        }
        return [];
    } catch (error) {
        console.error('Orderbook fetch error:', error);
        return [];
    }
}

// Example usage:
// const transactions = await fetchOrderBook('charizard-base-psa10');
// renderRecentSold(transactions);

// =============================================================================
// OPTION 2: Get asset metadata first, then use explicit params
// =============================================================================

async function getAssetMetadata(assetId) {
    try {
        const response = await fetch(
            `http://localhost:5001/market/asset/${encodeURIComponent(assetId)}`
        );
        const data = await response.json();
        return data.success ? data : null;
    } catch (error) {
        console.error('Asset metadata fetch error:', error);
        return null;
    }
}

async function fetchOrderBookWithMetadata(assetId) {
    const metadata = await getAssetMetadata(assetId);
    if (!metadata) return [];
    
    // Build query params from metadata
    const params = new URLSearchParams();
    if (metadata.card_name) params.append('card_name', metadata.card_name);
    if (metadata.set_name) params.append('set_name', metadata.set_name);
    if (metadata.category) params.append('category', metadata.category);
    if (metadata.grade) params.append('grade', metadata.grade);
    if (metadata.product_name) params.append('product_name', metadata.product_name);
    
    try {
        const response = await fetch(
            `http://localhost:5001/market/orderbook?${params.toString()}`
        );
        const data = await response.json();
        
        if (data.success && data.sources) {
            const ebaySource = data.sources.find(s => s.source === 'eBay' && s.transactions);
            if (ebaySource && ebaySource.transactions) {
                return ebaySource.transactions;
            }
        }
        return [];
    } catch (error) {
        console.error('Orderbook fetch error:', error);
        return [];
    }
}

// =============================================================================
// EXAMPLE: Update your existing fetchOrderBook function in preview.html
// =============================================================================

/*
// BEFORE (old way - missing set_name):
async function fetchOrderBook(assetId) {
    const market = markets.find(m => m.asset_id === assetId);
    if (!market) return [];
    
    const params = new URLSearchParams({
        card_name: market.name.split(' ')[0], // Just "Charizard" - WRONG!
        category: 'slabs',
        grade: 'PSA 10'
    });
    // Missing set_name, so Celebrations Charizard matches!
}

// AFTER (new way - uses asset_id):
async function fetchOrderBook(assetId) {
    try {
        const response = await fetch(
            `${ORACLE_URL}/market/orderbook?asset_id=${encodeURIComponent(assetId)}`
        );
        const data = await response.json();
        
        if (data.success && data.sources) {
            const ebaySource = data.sources.find(s => s.source === 'eBay' && s.transactions);
            return ebaySource?.transactions || [];
        }
        return [];
    } catch (error) {
        console.error('Orderbook error:', error);
        return [];
    }
}
*/

// =============================================================================
// ASSET ID MAPPING (for reference)
// =============================================================================

const ASSET_IDS = {
    'charizard-base-psa10': {
        card_name: 'Charizard',
        set_name: 'Base Set',  // ← This is now included automatically!
        category: 'slabs',
        grade: 'PSA 10'
    },
    'umbreon-vmax-alt-psa10': {
        card_name: 'Umbreon VMAX',
        set_name: 'Evolving Skies',
        category: 'slabs',
        grade: 'PSA 10'
    },
    // ... etc
};
