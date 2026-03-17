// PokeAgent - Product & Retail Utilities
// Shared functions for product images, prices, retailer URLs, set data

// Sealed Product Images - Set Logos and Symbols
const SET_IMAGES = {
    // Upcoming / New Sets
    'sv9': { logo: 'https://assets.pokemon.com/assets/cms2/img/trading-card-game/series/series12/series12_pokemon_logo.png', symbol: '', name: 'Destined Rivals' },
    // Scarlet & Violet Era
    'sv8': { logo: 'https://images.pokemontcg.io/sv8/logo.png', symbol: 'https://images.pokemontcg.io/sv8/symbol.png', name: 'Prismatic Evolutions' },
    'sv7': { logo: 'https://images.pokemontcg.io/sv7/logo.png', symbol: 'https://images.pokemontcg.io/sv7/symbol.png', name: 'Surging Sparks' },
    'sv6pt5': { logo: 'https://images.pokemontcg.io/sv6pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv6pt5/symbol.png', name: 'Shrouded Fable' },
    'sv6': { logo: 'https://images.pokemontcg.io/sv6/logo.png', symbol: 'https://images.pokemontcg.io/sv6/symbol.png', name: 'Twilight Masquerade' },
    'sv5': { logo: 'https://images.pokemontcg.io/sv5/logo.png', symbol: 'https://images.pokemontcg.io/sv5/symbol.png', name: 'Temporal Forces' },
    'sv4pt5': { logo: 'https://images.pokemontcg.io/sv4pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv4pt5/symbol.png', name: 'Paldean Fates' },
    'sv4': { logo: 'https://images.pokemontcg.io/sv4/logo.png', symbol: 'https://images.pokemontcg.io/sv4/symbol.png', name: 'Paradox Rift' },
    'sv3pt5': { logo: 'https://images.pokemontcg.io/sv3pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv3pt5/symbol.png', name: '151' },
    'sv3': { logo: 'https://images.pokemontcg.io/sv3/logo.png', symbol: 'https://images.pokemontcg.io/sv3/symbol.png', name: 'Obsidian Flames' },
    'sv2': { logo: 'https://images.pokemontcg.io/sv2/logo.png', symbol: 'https://images.pokemontcg.io/sv2/symbol.png', name: 'Paldea Evolved' },
    'sv1': { logo: 'https://images.pokemontcg.io/sv1/logo.png', symbol: 'https://images.pokemontcg.io/sv1/symbol.png', name: 'Scarlet & Violet' },
    // Sword & Shield Era
    'swsh12pt5': { logo: 'https://images.pokemontcg.io/swsh12pt5/logo.png', symbol: 'https://images.pokemontcg.io/swsh12pt5/symbol.png', name: 'Crown Zenith' },
    'swsh12': { logo: 'https://images.pokemontcg.io/swsh12/logo.png', symbol: 'https://images.pokemontcg.io/swsh12/symbol.png', name: 'Silver Tempest' },
    'swsh11': { logo: 'https://images.pokemontcg.io/swsh11/logo.png', symbol: 'https://images.pokemontcg.io/swsh11/symbol.png', name: 'Lost Origin' },
    'swsh10': { logo: 'https://images.pokemontcg.io/swsh10/logo.png', symbol: 'https://images.pokemontcg.io/swsh10/symbol.png', name: 'Astral Radiance' },
    'swsh9': { logo: 'https://images.pokemontcg.io/swsh9/logo.png', symbol: 'https://images.pokemontcg.io/swsh9/symbol.png', name: 'Brilliant Stars' },
    'swsh8': { logo: 'https://images.pokemontcg.io/swsh8/logo.png', symbol: 'https://images.pokemontcg.io/swsh8/symbol.png', name: 'Fusion Strike' },
    'swsh7': { logo: 'https://images.pokemontcg.io/swsh7/logo.png', symbol: 'https://images.pokemontcg.io/swsh7/symbol.png', name: 'Evolving Skies' },
    'swsh6': { logo: 'https://images.pokemontcg.io/swsh6/logo.png', symbol: 'https://images.pokemontcg.io/swsh6/symbol.png', name: 'Chilling Reign' },
    'swsh5': { logo: 'https://images.pokemontcg.io/swsh5/logo.png', symbol: 'https://images.pokemontcg.io/swsh5/symbol.png', name: 'Battle Styles' },
    'swsh45': { logo: 'https://images.pokemontcg.io/swsh45/logo.png', symbol: 'https://images.pokemontcg.io/swsh45/symbol.png', name: 'Shining Fates' },
    'swsh4': { logo: 'https://images.pokemontcg.io/swsh4/logo.png', symbol: 'https://images.pokemontcg.io/swsh4/symbol.png', name: 'Vivid Voltage' },
    'swsh35': { logo: 'https://images.pokemontcg.io/swsh35/logo.png', symbol: 'https://images.pokemontcg.io/swsh35/symbol.png', name: "Champion's Path" },
};

// Retailer search URL builders
const RETAILER_SEARCH_URLS = {
    'Target': (name) => `https://www.target.com/s?searchTerm=${encodeURIComponent(name + ' pokemon tcg')}`,
    'Walmart': (name) => `https://www.walmart.com/search?q=${encodeURIComponent(name + ' pokemon tcg')}`,
    'Best Buy': (name) => `https://www.bestbuy.com/site/searchpage.jsp?st=${encodeURIComponent(name + ' pokemon tcg')}`,
    'GameStop': (name) => `https://www.gamestop.com/search/?q=${encodeURIComponent(name + ' pokemon')}&lang=en_US`,
    'Pokemon Center': (name) => `https://www.pokemoncenter.com/search/${encodeURIComponent(name)}`,
    'Amazon': (name) => `https://www.amazon.com/s?k=${encodeURIComponent(name + ' pokemon tcg')}`,
    'TCGPlayer': (name) => `https://www.tcgplayer.com/search/pokemon/product?q=${encodeURIComponent(name)}&view=grid`,
    'Costco': (name) => `https://www.costco.com/CatalogSearch?keyword=${encodeURIComponent(name + ' pokemon')}`,
    'Barnes & Noble': (name) => `https://www.barnesandnoble.com/s/${encodeURIComponent(name + ' pokemon tcg')}`,
    'Local Game Stores': (name) => `https://www.pokemon.com/us/pokemon-tcg/play-in-person/find-an-event/`,
    'All Major Retailers': (name) => `https://www.google.com/search?q=${encodeURIComponent(name + ' pokemon tcg buy')}`,
};

// Get retailer search URL
function getRetailerSearchUrl(retailer, productName) {
    const searchName = productName.replace(/Wave \d+|Restock|Exclusive|Pre-Release|Full Release/gi, '').trim();
    if (RETAILER_SEARCH_URLS[retailer]) {
        return RETAILER_SEARCH_URLS[retailer](searchName);
    }
    return `https://www.google.com/search?q=${encodeURIComponent(searchName + ' ' + retailer + ' pokemon tcg')}`;
}

// Get sealed product image by matching product name to set
function getSealedProductImage(name) {
    const n = (name || '').toLowerCase();
    if (n.includes('destined rivals')) return 'https://images.pokemontcg.io/sv1/logo.png';
    if (n.includes('prismatic evolution')) return 'https://images.pokemontcg.io/sv8pt5/logo.png';
    if (n.includes('surging spark')) return 'https://images.pokemontcg.io/sv8/logo.png';
    if (n.includes('stellar crown')) return 'https://images.pokemontcg.io/sv7/logo.png';
    if (n.includes('shrouded fable')) return 'https://images.pokemontcg.io/sv6pt5/logo.png';
    if (n.includes('twilight masquerade')) return 'https://images.pokemontcg.io/sv6/logo.png';
    if (n.includes('temporal force')) return 'https://images.pokemontcg.io/sv5/logo.png';
    if (n.includes('paldean fates')) return 'https://images.pokemontcg.io/sv4pt5/logo.png';
    if (n.includes('paradox rift')) return 'https://images.pokemontcg.io/sv4/logo.png';
    if (n.includes('151')) return 'https://images.pokemontcg.io/sv3pt5/logo.png';
    if (n.includes('obsidian flame')) return 'https://images.pokemontcg.io/sv3/logo.png';
    if (n.includes('paldea evolved')) return 'https://images.pokemontcg.io/sv2/logo.png';
    if (n.includes('scarlet') && n.includes('violet')) return 'https://images.pokemontcg.io/sv1/logo.png';
    if (n.includes('crown zenith')) return 'https://images.pokemontcg.io/swsh12pt5/logo.png';
    if (n.includes('silver tempest')) return 'https://images.pokemontcg.io/swsh12/logo.png';
    if (n.includes('lost origin')) return 'https://images.pokemontcg.io/swsh11/logo.png';
    if (n.includes('evolving sk')) return 'https://images.pokemontcg.io/swsh7/logo.png';
    if (n.includes('brilliant star')) return 'https://images.pokemontcg.io/swsh9/logo.png';
    if (n.includes('fusion strike')) return 'https://images.pokemontcg.io/swsh8/logo.png';
    return 'https://images.pokemontcg.io/sv1/logo.png';
}

// Estimate price based on product type
function estimateProductPrice(name) {
    const n = (name || '').toLowerCase();
    if (n.includes('ultra premium') || n.includes('upc')) return 119.99;
    if (n.includes('booster box') || n.includes('36 pack')) return 143.99;
    if (n.includes('elite trainer') || n.includes('etb')) return 49.99;
    if (n.includes('collection box') || n.includes('premium')) return 39.99;
    if (n.includes('bundle') || n.includes('6 pack')) return 24.99;
    if (n.includes('mini tin')) return 7.99;
    if (n.includes('blister') || n.includes('3 pack')) return 14.99;
    if (n.includes('booster pack') || n.includes('single pack')) return 4.49;
    if (n.includes('tin')) return 24.99;
    if (n.includes('binder')) return 19.99;
    return 29.99;
}

// Get product image from set name
function getProductImage(productName) {
    const nameLower = (productName || '').toLowerCase();
    if (nameLower.includes('journey together')) return 'https://images.pokemontcg.io/sv10/logo.png';
    if (nameLower.includes('destined rivals')) return 'https://images.pokemontcg.io/sv10/logo.png';
    if (nameLower.includes('prismatic evolution')) return 'https://images.pokemontcg.io/sv8pt5/logo.png';
    if (nameLower.includes('surging spark')) return 'https://images.pokemontcg.io/sv8/logo.png';
    if (nameLower.includes('stellar crown')) return 'https://images.pokemontcg.io/sv7/logo.png';
    if (nameLower.includes('shrouded fable')) return 'https://images.pokemontcg.io/sv6pt5/logo.png';
    if (nameLower.includes('twilight masquerade')) return 'https://images.pokemontcg.io/sv6/logo.png';
    if (nameLower.includes('temporal force')) return 'https://images.pokemontcg.io/sv5/logo.png';
    if (nameLower.includes('paldean fates')) return 'https://images.pokemontcg.io/sv4pt5/logo.png';
    if (nameLower.includes('paradox rift')) return 'https://images.pokemontcg.io/sv4/logo.png';
    if (nameLower.includes('151')) return 'https://images.pokemontcg.io/sv3pt5/logo.png';
    if (nameLower.includes('obsidian flame')) return 'https://images.pokemontcg.io/sv3/logo.png';
    if (nameLower.includes('paldea evolved')) return 'https://images.pokemontcg.io/sv2/logo.png';
    if (nameLower.includes('scarlet') && nameLower.includes('violet')) return 'https://images.pokemontcg.io/sv1/logo.png';
    if (nameLower.includes('crown zenith')) return 'https://images.pokemontcg.io/swsh12pt5/logo.png';
    if (nameLower.includes('silver tempest')) return 'https://images.pokemontcg.io/swsh12/logo.png';
    if (nameLower.includes('lost origin')) return 'https://images.pokemontcg.io/swsh11/logo.png';
    if (nameLower.includes('brilliant star')) return 'https://images.pokemontcg.io/swsh9/logo.png';
    if (nameLower.includes('fusion strike')) return 'https://images.pokemontcg.io/swsh8/logo.png';
    if (nameLower.includes('evolving sk')) return 'https://images.pokemontcg.io/swsh7/logo.png';
    // Try SET_NAME_TO_ID mapping
    for (const [setName, setId] of Object.entries(SET_NAME_TO_ID)) {
        if (nameLower.includes(setName)) {
            return `https://images.pokemontcg.io/${setId}/logo.png`;
        }
    }
    return 'https://images.pokemontcg.io/sv1/logo.png';
}

// Get set info from product name
function getSetInfo(productName) {
    const nameLower = (productName || '').toLowerCase();
    for (const [setName, setId] of Object.entries(SET_NAME_TO_ID)) {
        if (nameLower.includes(setName)) {
            return { id: setId, ...SET_IMAGES[setId] };
        }
    }
    return null;
}

// Cached product images from TCG API
async function getProductImageWithCard(productName) {
    if (productImageCache[productName]) return productImageCache[productName];
    const cached = await getAPICache(`product_${productName}`);
    if (cached) {
        productImageCache[productName] = cached;
        return cached;
    }
    const setInfo = getSetInfo(productName);
    if (!setInfo) return getProductImage(productName);
    try {
        const res = await fetch(`https://api.pokemontcg.io/v2/cards?q=set.id:${setInfo.id}&pageSize=1&orderBy=-tcgplayer.prices.holofoil.market`);
        const data = await res.json();
        if (data.data?.[0]?.images?.small) {
            const imageUrl = data.data[0].images.small;
            productImageCache[productName] = imageUrl;
            await storeAPICache(`product_${productName}`, imageUrl, CACHE_TTL_IMAGES);
            return imageUrl;
        }
    } catch (e) {
        console.log('Could not fetch card image for product:', e);
    }
    return setInfo.logo;
}

// Build buy URL for a retailer
function getBuyUrl(retailer, productName, sku) {
    const q = encodeURIComponent(productName);
    const urls = {
        'Target': `https://www.target.com/s?searchTerm=${q}`,
        'Walmart': `https://www.walmart.com/search?q=${q}`,
        'Amazon': `https://www.amazon.com/s?k=${q}&rh=p_6%3AATVPDKIKX0DER`,
        'Best Buy': `https://www.bestbuy.com/site/searchpage.jsp?st=${q}`,
        'GameStop': `https://www.gamestop.com/search/?q=${q}&lang=en`,
        'Pokemon Center': `https://www.pokemoncenter.com/search/${q}`,
        'Barnes & Noble': `https://www.barnesandnoble.com/s/${q}`,
        'Costco': `https://www.costco.com/CatalogSearch?dept=All&keyword=${q}`,
    };
    return urls[retailer] || `https://www.google.com/search?q=${q}+buy`;
}

// Get stock check URL for in-store availability
function getStockCheckUrl(retailer, productName, storeId, zip) {
    const q = encodeURIComponent(productName || 'pokemon tcg');
    const urls = {
        'Target': `https://www.target.com/s?searchTerm=${q}&facetedValue=at_store`,
        'Walmart': `https://www.walmart.com/search?q=${q}&facet=fulfillment_method%3AIn-store`,
        'Best Buy': `https://www.bestbuy.com/site/searchpage.jsp?st=${q}&qp=storepickupstores_facet%3DStore%20Pickup%20At~My%20Local%20Store`,
        'GameStop': `https://www.gamestop.com/search/?q=${q}&prefn1=availability&prefv1=inStock`,
        'Pokemon Center': `https://www.pokemoncenter.com/search/${q}?inStockOnly=true`,
        'Amazon': `https://www.amazon.com/s?k=${q}&rh=p_6%3AATVPDKIKX0DER%2Cp_85%3A2470955011`,
        'Barnes & Noble': `https://www.barnesandnoble.com/s/${q}?Ns=P_Ship_Availability`,
        'Costco': `https://www.costco.com/CatalogSearch?keyword=${q}`,
    };
    return urls[retailer] || getBuyUrl(retailer, productName, '');
}
