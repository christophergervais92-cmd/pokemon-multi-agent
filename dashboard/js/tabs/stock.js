// PokeAgent - Stock Checker Tab
// =============================================================================
// Functions for the Stock Checker tab: searching retailers for sealed product
// inventory, rendering store results, generating demo/fallback data, and
// converting live API responses into a displayable store format.
// =============================================================================
// Global dependencies from other modules:
//   API, api(), settings, showNotification,
//   getSealedProductImage, estimateProductPrice, getSetInfo, getProductImage,
//   getBuyUrl, getStockCheckUrl, fetchSetImages, productImageCache,
//   allStockStores (declared in main scope), currentRetailerFilter

// ---------------------------------------------------------------------------
// Module-level state
// ---------------------------------------------------------------------------

let allStockStores = [];
let currentRetailerFilter = 'all';
let lastSearchQuery = '';

// ---------------------------------------------------------------------------
// Sealed Product Database with SKUs, UPCs, and Direct URLs
// ---------------------------------------------------------------------------
// UPC = Universal Product Code (same across all retailers)
// SKU = Stock Keeping Unit (retailer-specific)
const SEALED_PRODUCTS = [
    // Destined Rivals (2025) - SV09
    {
        name: 'Destined Rivals Booster Box', set: 'Destined Rivals', type: 'Booster Box', msrp: 143.64, release: '2025-02-07',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/561614_200w.jpg',
        upc: '820650855931', // 36 packs
        skus: {
            'TCGPlayer': '561614',
            'Pokemon Center': '290-85931',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/561614',
            'Pokemon Center': 'https://www.pokemoncenter.com/category/trading-card-game',
        }
    },
    {
        name: 'Destined Rivals Elite Trainer Box', set: 'Destined Rivals', type: 'ETB', msrp: 49.99, release: '2025-02-07',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/561616_200w.jpg',
        upc: '820650855894',
        skus: {
            'TCGPlayer': '561616',
            'Target': 'A-XXXXXXXX', // To be filled
            'Walmart': 'XXXXXXXXX',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/561616',
            'Target': 'https://www.target.com/s?searchTerm=destined+rivals+elite+trainer+box',
            'Walmart': 'https://www.walmart.com/search?q=destined+rivals+elite+trainer+box',
        }
    },
    // Prismatic Evolutions (2025) - SV08.5
    {
        name: 'Prismatic Evolutions Booster Box', set: 'Prismatic Evolutions', type: 'Booster Box', msrp: 143.64, release: '2025-01-17',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/553291_200w.jpg',
        upc: '820650857683', // 36 packs
        skus: {
            'TCGPlayer': '553291',
            'Pokemon Center': '290-85768',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/553291',
            'Pokemon Center': 'https://www.pokemoncenter.com/category/trading-card-game',
        }
    },
    {
        name: 'Prismatic Evolutions Elite Trainer Box', set: 'Prismatic Evolutions', type: 'ETB', msrp: 59.99, release: '2025-01-17',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/553293_200w.jpg',
        upc: '820650857676',
        skus: {
            'TCGPlayer': '553293',
            'Target': 'A-91741847',
            'Walmart': '5765499498',
            'Best Buy': '6594285',
            'GameStop': '412773',
            'Pokemon Center': '290-85768',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/553293',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-prismatic-evolutions-elite-trainer-box/-/A-91741847',
            'Walmart': 'https://www.walmart.com/ip/Pokemon-TCG-Scarlet-Violet-Prismatic-Evolutions-Elite-Trainer-Box/5765499498',
            'Best Buy': 'https://www.bestbuy.com/site/pokemon-trading-card-game-scarlet-violet-prismatic-evolutions-elite-trainer-box/6594285.p',
            'GameStop': 'https://www.gamestop.com/toys-games/trading-cards/products/pokemon-trading-card-game-scarlet-and-violet-prismatic-evolutions-elite-trainer-box/412773.html',
            'Pokemon Center': 'https://www.pokemoncenter.com/product/290-85768/pokemon-tcg-scarlet-and-violet-prismatic-evolutions-elite-trainer-box',
        }
    },
    {
        name: 'Prismatic Evolutions Super Premium Collection', set: 'Prismatic Evolutions', type: 'Collection Box', msrp: 129.99, release: '2025-01-17',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/553294_200w.jpg',
        upc: '820650857690',
        skus: {
            'TCGPlayer': '553294',
            'Pokemon Center': '290-85769',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/553294',
            'Target': 'https://www.target.com/s?searchTerm=prismatic+evolutions+super+premium',
            'Pokemon Center': 'https://www.pokemoncenter.com/category/trading-card-game',
        }
    },
    {
        name: 'Prismatic Evolutions Binder Collection', set: 'Prismatic Evolutions', type: 'Collection Box', msrp: 39.99, release: '2025-01-17',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/553295_200w.jpg',
        upc: '820650857706',
        skus: {
            'Target': 'A-91741849',
        },
        urls: {
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-prismatic-evolutions-binder-collection/-/A-91741849',
            'Walmart': 'https://www.walmart.com/search?q=prismatic+evolutions+binder',
        }
    },
    // Surging Sparks (2024) - SV08
    {
        name: 'Surging Sparks Booster Box', set: 'Surging Sparks', type: 'Booster Box', msrp: 143.64, release: '2024-11-08',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/543976_200w.jpg',
        upc: '820650855474', // 36 packs
        skus: {
            'TCGPlayer': '543976',
            'Amazon': 'B0DFHW5Y5N',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/543976',
            'Amazon': 'https://www.amazon.com/dp/B0DFHW5Y5N',
        }
    },
    {
        name: 'Surging Sparks Elite Trainer Box', set: 'Surging Sparks', type: 'ETB', msrp: 49.99, release: '2024-11-08',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/543978_200w.jpg',
        upc: '820650855467',
        skus: {
            'TCGPlayer': '543978',
            'Target': 'A-91322969',
            'Walmart': '5089282216',
            'Best Buy': '6581997',
            'GameStop': '411234',
        },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/543978',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-surging-sparks-elite-trainer-box/-/A-91322969',
            'Walmart': 'https://www.walmart.com/ip/Pokemon-TCG-Scarlet-Violet-Surging-Sparks-Elite-Trainer-Box/5089282216',
            'Best Buy': 'https://www.bestbuy.com/site/pokemon-trading-card-game-scarlet-violet-surging-sparks-elite-trainer-box/6581997.p',
            'GameStop': 'https://www.gamestop.com/toys-games/trading-cards/products/pokemon-trading-card-game-scarlet-and-violet-surging-sparks-elite-trainer-box/411234.html',
        }
    },
    // Stellar Crown (2024)
    {
        name: 'Stellar Crown Booster Box', set: 'Stellar Crown', type: 'Booster Box', msrp: 143.64, release: '2024-09-13',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/534283_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/534283',
            'Amazon': 'https://www.amazon.com/dp/B0D5RGFK84',
        }
    },
    {
        name: 'Stellar Crown Elite Trainer Box', set: 'Stellar Crown', type: 'ETB', msrp: 49.99, release: '2024-09-13',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/534284_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/534284',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-stellar-crown-elite-trainer-box/-/A-90927875',
            'Walmart': 'https://www.walmart.com/ip/Pokemon-TCG-Scarlet-Violet-Stellar-Crown-Elite-Trainer-Box/3994949867',
        }
    },
    // Shrouded Fable (2024)
    {
        name: 'Shrouded Fable Booster Box', set: 'Shrouded Fable', type: 'Booster Box', msrp: 143.64, release: '2024-08-02',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/525847_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/525847',
        }
    },
    {
        name: 'Shrouded Fable Elite Trainer Box', set: 'Shrouded Fable', type: 'ETB', msrp: 49.99, release: '2024-08-02',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/525848_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/525848',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-shrouded-fable-elite-trainer-box/-/A-90586665',
        }
    },
    // Twilight Masquerade (2024)
    {
        name: 'Twilight Masquerade Booster Box', set: 'Twilight Masquerade', type: 'Booster Box', msrp: 143.64, release: '2024-05-24',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/516719_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/516719',
            'Amazon': 'https://www.amazon.com/dp/B0CX4K1MHR',
        }
    },
    {
        name: 'Twilight Masquerade Elite Trainer Box', set: 'Twilight Masquerade', type: 'ETB', msrp: 49.99, release: '2024-05-24',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/516720_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/516720',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-twilight-masquerade-elite-trainer-box/-/A-90262802',
        }
    },
    // Temporal Forces (2024)
    {
        name: 'Temporal Forces Booster Box', set: 'Temporal Forces', type: 'Booster Box', msrp: 143.64, release: '2024-03-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/509058_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/509058',
            'Amazon': 'https://www.amazon.com/dp/B0CJL8ZS6Z',
        }
    },
    {
        name: 'Temporal Forces Elite Trainer Box', set: 'Temporal Forces', type: 'ETB', msrp: 49.99, release: '2024-03-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/509059_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/509059',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-temporal-forces-elite-trainer-box/-/A-89741310',
        }
    },
    // Paldean Fates (2024)
    {
        name: 'Paldean Fates Booster Box', set: 'Paldean Fates', type: 'Booster Box', msrp: 143.64, release: '2024-01-26',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/503219_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/503219',
        }
    },
    {
        name: 'Paldean Fates Elite Trainer Box', set: 'Paldean Fates', type: 'ETB', msrp: 59.99, release: '2024-01-26',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/503220_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/503220',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-paldean-fates-elite-trainer-box/-/A-89381579',
        }
    },
    // 151 (2023)
    {
        name: '151 Elite Trainer Box', set: '151', type: 'ETB', msrp: 49.99, release: '2023-09-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/489722_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/489722',
            'Amazon': 'https://www.amazon.com/dp/B0C2RFVMKT',
        }
    },
    {
        name: '151 Ultra Premium Collection', set: '151', type: 'Collection Box', msrp: 119.99, release: '2023-10-06',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/489723_200w.jpg',
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/489723',
        }
    },
    // Stellar Crown (2024) - SV07
    {
        name: 'Stellar Crown Booster Box', set: 'Stellar Crown', type: 'Booster Box', msrp: 143.64, release: '2024-09-13',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/534283_200w.jpg',
        upc: '820650854910',
        skus: { 'TCGPlayer': '534283', 'Amazon': 'B0D5RGFK84' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/534283',
            'Amazon': 'https://www.amazon.com/dp/B0D5RGFK84',
        }
    },
    {
        name: 'Stellar Crown Elite Trainer Box', set: 'Stellar Crown', type: 'ETB', msrp: 49.99, release: '2024-09-13',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/534284_200w.jpg',
        upc: '820650854903',
        skus: { 'TCGPlayer': '534284', 'Target': 'A-90927875', 'Walmart': '3994949867' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/534284',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-stellar-crown-elite-trainer-box/-/A-90927875',
            'Walmart': 'https://www.walmart.com/ip/3994949867',
        }
    },
    // Shrouded Fable (2024) - SV06.5
    {
        name: 'Shrouded Fable Booster Box', set: 'Shrouded Fable', type: 'Booster Box', msrp: 143.64, release: '2024-08-02',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/525847_200w.jpg',
        upc: '820650854545',
        skus: { 'TCGPlayer': '525847' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/525847' }
    },
    {
        name: 'Shrouded Fable Elite Trainer Box', set: 'Shrouded Fable', type: 'ETB', msrp: 49.99, release: '2024-08-02',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/525848_200w.jpg',
        upc: '820650854538',
        skus: { 'TCGPlayer': '525848', 'Target': 'A-90586665' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/525848',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-shrouded-fable-elite-trainer-box/-/A-90586665',
        }
    },
    // Twilight Masquerade (2024) - SV06
    {
        name: 'Twilight Masquerade Booster Box', set: 'Twilight Masquerade', type: 'Booster Box', msrp: 143.64, release: '2024-05-24',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/516719_200w.jpg',
        upc: '820650853890',
        skus: { 'TCGPlayer': '516719', 'Amazon': 'B0CX4K1MHR' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/516719',
            'Amazon': 'https://www.amazon.com/dp/B0CX4K1MHR',
        }
    },
    {
        name: 'Twilight Masquerade Elite Trainer Box', set: 'Twilight Masquerade', type: 'ETB', msrp: 49.99, release: '2024-05-24',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/516720_200w.jpg',
        upc: '820650853883',
        skus: { 'TCGPlayer': '516720', 'Target': 'A-90262802' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/516720',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-twilight-masquerade-elite-trainer-box/-/A-90262802',
        }
    },
    // Temporal Forces (2024) - SV05
    {
        name: 'Temporal Forces Booster Box', set: 'Temporal Forces', type: 'Booster Box', msrp: 143.64, release: '2024-03-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/509058_200w.jpg',
        upc: '820650853265',
        skus: { 'TCGPlayer': '509058', 'Amazon': 'B0CJL8ZS6Z' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/509058',
            'Amazon': 'https://www.amazon.com/dp/B0CJL8ZS6Z',
        }
    },
    {
        name: 'Temporal Forces Elite Trainer Box', set: 'Temporal Forces', type: 'ETB', msrp: 49.99, release: '2024-03-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/509059_200w.jpg',
        upc: '820650853258',
        skus: { 'TCGPlayer': '509059', 'Target': 'A-89741310' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/509059',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-temporal-forces-elite-trainer-box/-/A-89741310',
        }
    },
    // Paldean Fates (2024) - SV04.5
    {
        name: 'Paldean Fates Booster Box', set: 'Paldean Fates', type: 'Booster Box', msrp: 143.64, release: '2024-01-26',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/503219_200w.jpg',
        upc: '820650852640',
        skus: { 'TCGPlayer': '503219' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/503219' }
    },
    {
        name: 'Paldean Fates Elite Trainer Box', set: 'Paldean Fates', type: 'ETB', msrp: 59.99, release: '2024-01-26',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/503220_200w.jpg',
        upc: '820650852633',
        skus: { 'TCGPlayer': '503220', 'Target': 'A-89381579' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/503220',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-paldean-fates-elite-trainer-box/-/A-89381579',
        }
    },
    {
        name: 'Paldean Fates Premium Collection (Shiny Charizard ex)', set: 'Paldean Fates', type: 'Collection Box', msrp: 59.99, release: '2024-01-26',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/503221_200w.jpg',
        upc: '820650852657',
        skus: { 'TCGPlayer': '503221' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/503221' }
    },
    // Paradox Rift (2023) - SV04
    {
        name: 'Paradox Rift Booster Box', set: 'Paradox Rift', type: 'Booster Box', msrp: 143.64, release: '2023-11-03',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/498891_200w.jpg',
        upc: '820650851988',
        skus: { 'TCGPlayer': '498891', 'Amazon': 'B0CHQW8J9Z' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/498891',
            'Amazon': 'https://www.amazon.com/dp/B0CHQW8J9Z',
        }
    },
    {
        name: 'Paradox Rift Elite Trainer Box', set: 'Paradox Rift', type: 'ETB', msrp: 49.99, release: '2023-11-03',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/498892_200w.jpg',
        upc: '820650851971',
        skus: { 'TCGPlayer': '498892' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/498892' }
    },
    // 151 (2023) - SV03.5
    {
        name: '151 Booster Bundle (6 Packs)', set: '151', type: 'Booster Bundle', msrp: 26.99, release: '2023-09-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/493424_200w.jpg',
        upc: '820650851339',
        skus: { 'TCGPlayer': '493424', 'Target': 'A-89168234', 'Walmart': '2724362017' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/493424',
            'Target': 'https://www.target.com/p/pokemon-trading-card-game-scarlet-violet-151-booster-bundle/-/A-89168234',
            'Walmart': 'https://www.walmart.com/ip/2724362017',
        }
    },
    {
        name: '151 Elite Trainer Box', set: '151', type: 'ETB', msrp: 49.99, release: '2023-09-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/489722_200w.jpg',
        upc: '820650851346',
        skus: { 'TCGPlayer': '489722', 'Amazon': 'B0C2RFVMKT' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/489722',
            'Amazon': 'https://www.amazon.com/dp/B0C2RFVMKT',
        }
    },
    {
        name: '151 Ultra Premium Collection', set: '151', type: 'Collection Box', msrp: 119.99, release: '2023-10-06',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/493425_200w.jpg',
        upc: '820650851353',
        skus: { 'TCGPlayer': '493425' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/493425' }
    },
    {
        name: '151 Poster Collection', set: '151', type: 'Collection Box', msrp: 39.99, release: '2023-09-22',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/493426_200w.jpg',
        upc: '820650851360',
        skus: { 'TCGPlayer': '493426' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/493426' }
    },
    // Obsidian Flames (2023) - SV03
    {
        name: 'Obsidian Flames Booster Box', set: 'Obsidian Flames', type: 'Booster Box', msrp: 143.64, release: '2023-08-11',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/484792_200w.jpg',
        upc: '820650850684',
        skus: { 'TCGPlayer': '484792', 'Amazon': 'B0C2R8ZFVX' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/484792',
            'Amazon': 'https://www.amazon.com/dp/B0C2R8ZFVX',
        }
    },
    {
        name: 'Obsidian Flames Elite Trainer Box', set: 'Obsidian Flames', type: 'ETB', msrp: 49.99, release: '2023-08-11',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/484793_200w.jpg',
        upc: '820650850677',
        skus: { 'TCGPlayer': '484793' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/484793' }
    },
    // Paldea Evolved (2023) - SV02
    {
        name: 'Paldea Evolved Booster Box', set: 'Paldea Evolved', type: 'Booster Box', msrp: 143.64, release: '2023-06-09',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/476283_200w.jpg',
        upc: '820650850028',
        skus: { 'TCGPlayer': '476283', 'Amazon': 'B0BZDQRV8H' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/476283',
            'Amazon': 'https://www.amazon.com/dp/B0BZDQRV8H',
        }
    },
    {
        name: 'Paldea Evolved Elite Trainer Box', set: 'Paldea Evolved', type: 'ETB', msrp: 49.99, release: '2023-06-09',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/476284_200w.jpg',
        upc: '820650850011',
        skus: { 'TCGPlayer': '476284' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/476284' }
    },
    // Scarlet & Violet Base (2023) - SV01
    {
        name: 'Scarlet & Violet Booster Box', set: 'Scarlet & Violet', type: 'Booster Box', msrp: 143.64, release: '2023-03-31',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/467284_200w.jpg',
        upc: '820650409233',
        skus: { 'TCGPlayer': '467284', 'Amazon': 'B0BPN4W48D' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/467284',
            'Amazon': 'https://www.amazon.com/dp/B0BPN4W48D',
        }
    },
    {
        name: 'Scarlet & Violet Elite Trainer Box (Koraidon)', set: 'Scarlet & Violet', type: 'ETB', msrp: 49.99, release: '2023-03-31',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/467285_200w.jpg',
        upc: '820650409240',
        skus: { 'TCGPlayer': '467285' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/467285' }
    },
    {
        name: 'Scarlet & Violet Elite Trainer Box (Miraidon)', set: 'Scarlet & Violet', type: 'ETB', msrp: 49.99, release: '2023-03-31',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/467286_200w.jpg',
        upc: '820650409257',
        skus: { 'TCGPlayer': '467286' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/467286' }
    },
    // Crown Zenith (2023) - SWSH12.5
    {
        name: 'Crown Zenith Booster Box', set: 'Crown Zenith', type: 'Booster Box', msrp: 143.64, release: '2023-01-20',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/283603_200w.jpg',
        upc: '820650408977',
        skus: { 'TCGPlayer': '283603' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/283603' }
    },
    {
        name: 'Crown Zenith Elite Trainer Box', set: 'Crown Zenith', type: 'ETB', msrp: 49.99, release: '2023-01-20',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/283604_200w.jpg',
        upc: '820650408960',
        skus: { 'TCGPlayer': '283604' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/283604' }
    },
    {
        name: 'Crown Zenith Shiny Zacian Premium Figure Collection', set: 'Crown Zenith', type: 'Collection Box', msrp: 39.99, release: '2023-01-20',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/283605_200w.jpg',
        upc: '820650408984',
        skus: { 'TCGPlayer': '283605' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/283605' }
    },
    // Silver Tempest (2022) - SWSH12
    {
        name: 'Silver Tempest Booster Box', set: 'Silver Tempest', type: 'Booster Box', msrp: 143.64, release: '2022-11-11',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/273285_200w.jpg',
        upc: '820650408496',
        skus: { 'TCGPlayer': '273285', 'Amazon': 'B0B9HQXHRY' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/273285',
            'Amazon': 'https://www.amazon.com/dp/B0B9HQXHRY',
        }
    },
    {
        name: 'Silver Tempest Elite Trainer Box', set: 'Silver Tempest', type: 'ETB', msrp: 49.99, release: '2022-11-11',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/273286_200w.jpg',
        upc: '820650408489',
        skus: { 'TCGPlayer': '273286' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/273286' }
    },
    // Lost Origin (2022) - SWSH11
    {
        name: 'Lost Origin Booster Box', set: 'Lost Origin', type: 'Booster Box', msrp: 143.64, release: '2022-09-09',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/264843_200w.jpg',
        upc: '820650408014',
        skus: { 'TCGPlayer': '264843', 'Amazon': 'B0B3HJJ8PR' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/264843',
            'Amazon': 'https://www.amazon.com/dp/B0B3HJJ8PR',
        }
    },
    {
        name: 'Lost Origin Elite Trainer Box', set: 'Lost Origin', type: 'ETB', msrp: 49.99, release: '2022-09-09',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/264844_200w.jpg',
        upc: '820650408007',
        skus: { 'TCGPlayer': '264844' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/264844' }
    },
    // Evolving Skies (2021) - SWSH07
    {
        name: 'Evolving Skies Booster Box', set: 'Evolving Skies', type: 'Booster Box', msrp: 143.64, release: '2021-08-27',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/243119_200w.jpg',
        upc: '820650807534',
        skus: { 'TCGPlayer': '243119', 'Amazon': 'B0979V1TF9' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/243119',
            'Amazon': 'https://www.amazon.com/dp/B0979V1TF9',
        }
    },
    {
        name: 'Evolving Skies Elite Trainer Box (Blue)', set: 'Evolving Skies', type: 'ETB', msrp: 49.99, release: '2021-08-27',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/243120_200w.jpg',
        upc: '820650807527',
        skus: { 'TCGPlayer': '243120' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/243120' }
    },
    // Celebrations (2021) - 25th Anniversary
    {
        name: 'Celebrations Elite Trainer Box', set: 'Celebrations', type: 'ETB', msrp: 49.99, release: '2021-10-08',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/248274_200w.jpg',
        upc: '820650808425',
        skus: { 'TCGPlayer': '248274' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/248274' }
    },
    {
        name: 'Celebrations Ultra Premium Collection', set: 'Celebrations', type: 'Collection Box', msrp: 119.99, release: '2021-10-08',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/248275_200w.jpg',
        upc: '820650808432',
        skus: { 'TCGPlayer': '248275' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/248275' }
    },
    // Fusion Strike (2021) - SWSH08
    {
        name: 'Fusion Strike Booster Box', set: 'Fusion Strike', type: 'Booster Box', msrp: 143.64, release: '2021-11-12',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/251847_200w.jpg',
        upc: '820650808678',
        skus: { 'TCGPlayer': '251847', 'Amazon': 'B09F3QXQC4' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/251847',
            'Amazon': 'https://www.amazon.com/dp/B09F3QXQC4',
        }
    },
    // Brilliant Stars (2022) - SWSH09
    {
        name: 'Brilliant Stars Booster Box', set: 'Brilliant Stars', type: 'Booster Box', msrp: 143.64, release: '2022-02-25',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/257748_200w.jpg',
        upc: '820650407291',
        skus: { 'TCGPlayer': '257748', 'Amazon': 'B09LQ8N3V1' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/257748',
            'Amazon': 'https://www.amazon.com/dp/B09LQ8N3V1',
        }
    },
    {
        name: 'Brilliant Stars Elite Trainer Box', set: 'Brilliant Stars', type: 'ETB', msrp: 49.99, release: '2022-02-25',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/257749_200w.jpg',
        upc: '820650407284',
        skus: { 'TCGPlayer': '257749' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/257749' }
    },
    // Astral Radiance (2022) - SWSH10
    {
        name: 'Astral Radiance Booster Box', set: 'Astral Radiance', type: 'Booster Box', msrp: 143.64, release: '2022-05-27',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/262137_200w.jpg',
        upc: '820650407574',
        skus: { 'TCGPlayer': '262137', 'Amazon': 'B09SLRJFZP' },
        urls: {
            'TCGPlayer': 'https://www.tcgplayer.com/product/262137',
            'Amazon': 'https://www.amazon.com/dp/B09SLRJFZP',
        }
    },
    {
        name: 'Astral Radiance Elite Trainer Box', set: 'Astral Radiance', type: 'ETB', msrp: 49.99, release: '2022-05-27',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/262138_200w.jpg',
        upc: '820650407567',
        skus: { 'TCGPlayer': '262138' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/262138' }
    },
    // Pokemon GO (2022)
    {
        name: 'Pokemon GO Elite Trainer Box', set: 'Pokemon GO', type: 'ETB', msrp: 49.99, release: '2022-07-01',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/264098_200w.jpg',
        upc: '820650407857',
        skus: { 'TCGPlayer': '264098' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/264098' }
    },
    // Hidden Fates (2019)
    {
        name: 'Hidden Fates Elite Trainer Box', set: 'Hidden Fates', type: 'ETB', msrp: 59.99, release: '2019-08-23',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/195773_200w.jpg',
        upc: '820650804878',
        skus: { 'TCGPlayer': '195773' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/195773' }
    },
    // Shining Fates (2021)
    {
        name: 'Shining Fates Elite Trainer Box', set: 'Shining Fates', type: 'ETB', msrp: 59.99, release: '2021-02-19',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/230284_200w.jpg',
        upc: '820650806933',
        skus: { 'TCGPlayer': '230284' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/230284' }
    },
    // Champion's Path (2020)
    {
        name: 'Champions Path Elite Trainer Box', set: 'Champions Path', type: 'ETB', msrp: 59.99, release: '2020-09-25',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/217284_200w.jpg',
        upc: '820650806216',
        skus: { 'TCGPlayer': '217284' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/217284' }
    },
    // Journey Together (2025) - Upcoming
    {
        name: 'Journey Together Booster Box', set: 'Journey Together', type: 'Booster Box', msrp: 143.64, release: '2025-03-28',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/567214_200w.jpg',
        upc: '820650856143',
        skus: { 'TCGPlayer': '567214' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/567214' }
    },
    {
        name: 'Journey Together Elite Trainer Box', set: 'Journey Together', type: 'ETB', msrp: 49.99, release: '2025-03-28',
        image: 'https://tcgplayer-cdn.tcgplayer.com/product/567215_200w.jpg',
        upc: '820650856136',
        skus: { 'TCGPlayer': '567215' },
        urls: { 'TCGPlayer': 'https://www.tcgplayer.com/product/567215' }
    },
];

// ---------------------------------------------------------------------------
// Retailer Search URL Patterns (fallback when direct URL not available)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Retailer Search URL Helper
// ---------------------------------------------------------------------------

// Get search URL for a retailer and product name
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
// Quick Search (Sealed Product Search)
// ---------------------------------------------------------------------------

async function quickSearch() {
    const query = (document.getElementById('searchQuery').value || 'pokemon').trim();
    const retailer = document.getElementById('searchRetailer').value;
    const results = document.getElementById('searchResults');

    // Skip if same query (debounce edge case)
    if (query === lastSearchQuery && query.length > 2) return;
    lastSearchQuery = query;

    // Min 2 chars to search
    if (query.length < 2) {
        results.innerHTML = '<div class="empty"><div class="empty-icon"></div>Type at least 2 characters to search</div>';
        return;
    }

    results.innerHTML = '<div class="loading"><div class="spinner"></div>Searching...</div>';

    const endpoint = retailer === 'all'
        ? `/scanner/unified?q=${encodeURIComponent(query)}&limit=20`
        : `/scanner/${retailer}?q=${encodeURIComponent(query)}&limit=20`;

    const data = await api(endpoint, { timeout: 6000 });

    if (data.error) {
        results.innerHTML = `<div class="empty"><div class="empty-icon"></div>${data.error}</div>`;
        return;
    }

    const products = data.products || data.results || [];

    // Filter out bad/suspicious products
    const filteredProducts = products.filter(p => {
        const name = (p.name || '').toLowerCase();

        // Remove third-party, bootleg, or suspicious products
        const badKeywords = [
            'me1', 'mega evolution elite trainer box', 'mega gardevior', 'mega lucario',
            'custom', 'proxy', 'fake', 'replica', 'unofficial', 'fan made',
            'lot of', 'bundle lot', 'mystery', 'repack', 'search',
            'damaged', 'heavily played', 'poor condition',
            'chinese', 'japanese version', 'korean',
            'code card', 'energy card only', 'bulk',
            'empty', 'no cards', 'box only', 'case only',
            'art set', 'artwork only'
        ];

        // Check if product name contains bad keywords
        for (const bad of badKeywords) {
            if (name.includes(bad)) return false;
        }

        // Must be from known retailer or have "pokemon" in name
        const validRetailers = ['target', 'walmart', 'best buy', 'gamestop', 'pokemon center', 'tcgplayer', 'costco'];
        const retailer = (p.retailer || '').toLowerCase();
        const isValidRetailer = validRetailers.some(r => retailer.includes(r));

        return isValidRetailer || name.includes('pokemon') || name.includes('scarlet') || name.includes('violet');
    });

    if (!filteredProducts.length) {
        results.innerHTML = '<div class="empty"><div class="empty-icon"></div>No quality products found</div>';
        return;
    }

    // FAST: Render immediately with proper product images and estimated prices
    const displayProducts = filteredProducts.slice(0, 20).map(p => {
        const setInfo = getSetInfo(p.name);
        // Use actual product image or API image
        const cardImg = p.image_url || getSealedProductImage(p.name);
        // Estimate price if not provided
        const price = parseFloat(p.price) > 0 ? p.price : estimateProductPrice(p.name);
        return { ...p, cardImg, setInfo, price };
    });

    // Render results immediately
    renderSearchResults(displayProducts);

    // ASYNC: Fetch missing images in background, then re-render
    const missingSets = [...new Set(displayProducts.filter(p => p.setInfo && !productImageCache[p.setInfo.id]).map(p => p.setInfo.id))];
    if (missingSets.length > 0) {
        fetchSetImages(missingSets).then(() => {
            // Re-render with loaded images
            const updatedProducts = displayProducts.map(p => ({
                ...p,
                cardImg: (p.setInfo && productImageCache[p.setInfo.id]) ? productImageCache[p.setInfo.id] : p.cardImg
            }));
            renderSearchResults(updatedProducts);
        });
    }
}

function renderSearchResults(products) {
    const results = document.getElementById('searchResults');
    results.innerHTML = `
        <div class="grid grid-2">
            ${products.map(p => {
                const buyUrl = getBuyUrl(p.retailer, p.name, p.sku);
                // For sealed products, always use getSealedProductImage (set logos), ignore API image_url which may be card art
                const isSealedProduct = (p.name || '').toLowerCase().includes('booster box') ||
                                       (p.name || '').toLowerCase().includes('elite trainer box') ||
                                       (p.name || '').toLowerCase().includes('etb') ||
                                       (p.name || '').toLowerCase().includes('collection box') ||
                                       (p.name || '').toLowerCase().includes('booster bundle');
                const imgUrl = isSealedProduct ? getSealedProductImage(p.name) : (p.cardImg || p.image_url || getSealedProductImage(p.name));
                const priceNum = parseFloat(p.price);
                const priceDisplay = !isNaN(priceNum) && priceNum > 0 ? priceNum.toFixed(2) : estimateProductPrice(p.name).toFixed(2);

                return `
                <div class="product" style="display: flex; gap: 1rem;">
                    <div style="position: relative; width: 80px; height: 110px; flex-shrink: 0;">
                        <img src="${imgUrl}"
                             loading="lazy"
                             onerror="this.onerror=null; this.src='https://images.pokemontcg.io/swsh7/logo.png';"
                             style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px; background: var(--bg);">
                    </div>
                    <div class="product-info" style="flex: 1; min-width: 0;">
                        <div class="product-name" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${p.name || 'Unknown'}</div>
                        <div class="product-meta">${p.retailer || ''}</div>
                        ${p.setInfo ? `<div style="font-size: 0.625rem; color: var(--text-muted); margin-top: 0.25rem;">${p.setInfo.name}</div>` : ''}
                        <div style="margin-top: 0.5rem; display: flex; align-items: center; gap: 1rem;">
                            <span class="product-price">$${priceDisplay}</span>
                            <span class="product-stock" style="color: ${p.stock ? 'var(--green)' : 'var(--text-muted)'};">${p.stock ? 'In Stock' : 'Out of Stock'}</span>
                        </div>
                        <a href="${buyUrl}" target="_blank" class="btn btn-buy btn-sm" style="margin-top: 0.5rem; display: inline-block;">Buy at ${p.retailer || 'Store'}</a>
                    </div>
                </div>
            `}).join('')}
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Quick Retailer Search - one-click search for specific retailer + product
// ---------------------------------------------------------------------------

function quickRetailerSearch(retailer, query) {
    // Set the search query
    document.getElementById('stockQuery').value = query;

    // Filter to retailer (or all)
    currentRetailerFilter = retailer;
    document.querySelectorAll('.retailer-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.retailer === retailer);
    });

    // Show loading state
    const results = document.getElementById('stockResults');
    results.innerHTML = `<div class="loading"><div class="spinner"></div>Searching ${retailer === 'all' ? 'all retailers' : retailer} for "${query}"...</div>`;

    // Perform the search
    findStock();

    // Log for analytics
    console.log(`Quick search: ${retailer} - ${query}`);
}

function filterRetailer(retailer) {
    currentRetailerFilter = retailer;
    document.querySelectorAll('.retailer-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.retailer === retailer);
    });

    if (allStockStores.length) {
        const filtered = retailer === 'all'
            ? allStockStores
            : allStockStores.filter(s => s.chain === retailer);
        renderStockResults(filtered);

        // Update stats for filtered view
        const totalUnits = filtered.reduce((sum, s) => sum + (s.total_quantity || 0), 0);
        const storesWithStock = filtered.filter(s => s.has_stock).length;
        document.getElementById('statStores').textContent = filtered.length;
        document.getElementById('statInStock').textContent = storesWithStock;
    }
}

// ---------------------------------------------------------------------------
// Main Stock Search
// ---------------------------------------------------------------------------

async function findStock() {
    const zip = document.getElementById('stockZip').value || settings.zip || '90210';
    const query = document.getElementById('stockQuery').value || 'pokemon trading cards';
    const results = document.getElementById('stockResults');

    results.innerHTML = '<div class="loading"><div class="spinner"></div>Scanning retailers for stock...</div>';

    try {
        // Call the real stock checker API
        const cacheBuster = new Date().getTime();
        const data = await api(`/scanner/unified?q=${encodeURIComponent(query)}&zip=${zip}&_=${cacheBuster}`, { timeout: 30000 });

        if (data.error) {
            results.innerHTML = `<div class="empty"><div class="empty-icon error"></div><div>Error: ${data.error}</div></div>`;
            return;
        }

        // Surface non-fatal scanner notes (blocked retailers, etc.).
        if (data.errors && Array.isArray(data.errors) && data.errors.length) {
            const note = data.errors.slice(0, 2).join(' • ');
            showNotification(`Scanner notes: ${note}`, 'info');
        }

        const products = data.products || [];

        if (products.length === 0) {
            results.innerHTML = `
                <div class="card" style="text-align: center; padding: 2rem;">
                    <div class="empty-icon inbox" style="margin-bottom: 0.75rem;"></div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">No Stock Found</div>
                    <div style="color: var(--text-muted); font-size: 0.875rem; margin-bottom: 1rem;">
                        No products found for "<strong>${query}</strong>".<br>
                        Try searching for "pokemon", "etb", "booster box", or a set name.
                    </div>
                </div>
            `;
            // Reset stats
            document.getElementById('statStores').textContent = '0';
            document.getElementById('statInStock').textContent = '0';
            document.getElementById('statProducts').textContent = '0';
            document.getElementById('statUnits').textContent = '0';
            return;
        }

        // Convert API products to store format
        const stores = convertRealProductsToStores(products, zip, query);
        allStockStores = stores; // Store for filtering

        // Render results
        renderStockResults(stores);

        // Update stats
        const totalUnits = stores.reduce((sum, s) => sum + (s.total_quantity || 0), 0);
        const storesWithStock = stores.filter(s => s.has_stock).length;
        const totalProducts = stores.reduce((sum, s) => sum + (s.products?.length || 0), 0);

        document.getElementById('statStores').textContent = stores.length;
        document.getElementById('statInStock').textContent = storesWithStock;
        document.getElementById('statProducts').textContent = totalProducts;
        document.getElementById('statUnits').textContent = totalUnits;

        if (storesWithStock === 0) {
            showNotification('No in-stock matches found right now. Showing results; use "Verify Stock" to double-check.', 'info');
        }

    } catch (error) {
        console.error('Stock check error:', error);
        results.innerHTML = `
            <div class="empty">
                <div class="empty-icon error"></div>
                <div>Error loading stock: ${error.message || 'Unknown error'}</div>
                <button class="btn btn-sm" onclick="findStock()" style="margin-top: 1rem;">Try Again</button>
            </div>
        `;
    }
}

// ---------------------------------------------------------------------------
// Render Sealed Products with Direct Retailer Links
// ---------------------------------------------------------------------------

function renderSealedProducts(products, retailerFilter) {
    const results = document.getElementById('stockResults');
    const retailers = ['Target', 'Walmart', 'Best Buy', 'GameStop', 'Pokemon Center', 'Amazon', 'TCGPlayer'];
    const retailerColors = {
        'Target': '#cc0000',
        'Walmart': '#0071ce',
        'Best Buy': '#0046be',
        'GameStop': '#000000',
        'Pokemon Center': '#ffcb05',
        'Amazon': '#ff9900',
        'TCGPlayer': '#1a4b8e',
    };

    results.innerHTML = products.map(product => {
        // Get URLs for this product (direct URLs or fallback search URLs)
        const productUrls = product.urls || {};
        const availableRetailers = retailerFilter === 'all'
            ? retailers
            : retailers.filter(r => r === retailerFilter);

        const retailerLinks = availableRetailers.map(retailer => {
            const url = productUrls[retailer] || RETAILER_SEARCH_URLS[retailer](product.name);
            const isDirect = !!productUrls[retailer];
            const color = retailerColors[retailer];
            const textColor = retailer === 'Pokemon Center' ? '#000' : '#fff';

            return `
                <a href="${url}" target="_blank" rel="noopener"
                   style="display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.375rem 0.75rem;
                          background: ${color}; color: ${textColor}; border-radius: 6px;
                          font-size: 0.75rem; font-weight: 600; text-decoration: none;
                          transition: transform 0.1s, opacity 0.1s;"
                   onmouseover="this.style.transform='scale(1.05)'"
                   onmouseout="this.style.transform='scale(1)'"
                   title="${isDirect ? 'Direct product link' : 'Search results'}">
                    ${retailer}
                    ${isDirect ? '<span style="font-size: 0.625rem; color: var(--text-muted);">Direct</span>' : ''}
                </a>
            `;
        }).join('');

        return `
            <div class="card" style="margin-bottom: 1rem; display: flex; gap: 1rem; align-items: flex-start; flex-wrap: wrap;">
                <img src="${getProductImage(product.name)}" alt="${product.name}"
                     style="width: 100px; height: auto; border-radius: 8px; flex-shrink: 0; object-fit: contain;"
                     onerror="this.src='https://images.pokemontcg.io/sv8/logo.png'; this.style.objectFit='contain';">
                <div style="flex: 1; min-width: 200px;">
                    <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem;">${product.name}</div>
                    <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                        <span>${product.set}</span>
                        <span>${product.type}</span>
                        <span>Released: ${product.release}</span>
                    </div>
                    <div style="font-family: 'Space Mono', monospace; font-size: 1.125rem; font-weight: 700; color: var(--green); margin-bottom: 0.75rem;">
                        MSRP: $${product.msrp.toFixed(2)}
                    </div>
                    <div style="font-size: 0.625rem; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase;">
                        Check Stock At:
                    </div>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        ${retailerLinks}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ---------------------------------------------------------------------------
// Convert Real Scraped Products to Store Format for Display
// ---------------------------------------------------------------------------

function convertRealProductsToStores(products, zip, query) {
    const stores = [];
    const location = getLocationFromZip(zip);

    // Group products by retailer
    const byRetailer = {};
    for (const p of products) {
        const retailer = p.retailer || 'Unknown';
        if (!byRetailer[retailer]) {
            byRetailer[retailer] = [];
        }
        const priceNum = (() => {
            const n = typeof p.price === 'number' ? p.price : parseFloat(p.price);
            return Number.isFinite(n) ? n : 0;
        })();
        byRetailer[retailer].push({
            name: p.name || 'Product',
            sku: p.sku || 'N/A',
            quantity: p.stock ? 1 : 0,
            stock_status: p.stock_status || (p.stock ? 'In Stock' : 'Out of Stock'),
            aisle: 'Check store',
            price: priceNum,
            last_checked: p.last_checked || '',
            confidence: typeof p.confidence === 'number' ? p.confidence : parseFloat(p.confidence) || 0,
            detection_method: p.detection_method || '',
            // Always use getProductImage for stock checker results (all are sealed products)
            // Ignore p.image_url which may contain card art from retailer APIs
            image_url: getProductImage(p.name),
            url: p.url || ''
        });
    }

    // Create store entries for each retailer with real data
    const retailerColors = {
        'Target': '#cc0000',
        'Best Buy': '#0046be',
        'GameStop': '#000000',
        'Pokemon Center': '#ffcb05',
        'Walmart': '#0071ce',
        'TCGPlayer': '#1a4b8e',
        'Amazon': '#ff9900',
        'Costco': '#e31837',
        'Barnes & Noble': '#2d5a27'
    };

    for (const [retailer, prods] of Object.entries(byRetailer)) {
        const inStockProducts = prods.filter(p => p.quantity > 0);
        const hasStock = inStockProducts.length > 0;
        const isOnline = ['Pokemon Center', 'TCGPlayer', 'Amazon'].includes(retailer);

        stores.push({
            chain: retailer,
            store_id: isOnline ? 'Online' : '',
            full_address: isOnline
                ? `${retailer} Online (ships to ${zip})`
                : `${retailer} near ${location.city}, ${location.state} ${zip}`,
            distance_miles: isOnline ? '0.0' : '\u2014',
            phone: 'N/A',
            hours: isOnline ? '24/7 Online' : 'Hours vary',
            has_stock: hasStock,
            stock_count: inStockProducts.length,
            total_quantity: inStockProducts.reduce((sum, p) => sum + p.quantity, 0),
            products: prods,
            online: isOnline,
            isRealData: true  // Mark as real scraped data
        });
    }

    // Sort by stock availability (stores with stock first)
    stores.sort((a, b) => {
        if (a.has_stock && !b.has_stock) return -1;
        if (!a.has_stock && b.has_stock) return 1;
        return 0;
    });

    return stores;
}

// ---------------------------------------------------------------------------
// Demo Data Generation (fallback when no real API data)
// ---------------------------------------------------------------------------

function generateAllRetailerStores(zip, query) {
    // Main retailers with REALISTIC stock probabilities
    // Pokemon Center is almost always sold out for popular items
    const retailers = [
        { chain: 'Target', icon: '', color: '#cc0000', storeCount: 3, stockChance: 0.5 },
        { chain: 'Walmart', icon: '', color: '#0071ce', storeCount: 2, stockChance: 0.4 },
        { chain: 'Amazon', icon: '', color: '#ff9900', storeCount: 1, online: true, stockChance: 0.6 },
        { chain: 'Best Buy', icon: '', color: '#0046be', storeCount: 2, stockChance: 0.35 },
        { chain: 'GameStop', icon: '', color: '#000000', storeCount: 3, stockChance: 0.45 },
        { chain: 'Pokemon Center', icon: '', color: '#ffcb05', storeCount: 1, online: true, stockChance: 0.1 }, // Usually sold out!
        { chain: 'Costco', icon: '', color: '#e31837', storeCount: 1, stockChance: 0.3 },
        { chain: 'Barnes & Noble', icon: '', color: '#2d5a27', storeCount: 1, stockChance: 0.25 },
    ];

    // Get products filtered by query
    const matchingProducts = generateProductsForQuery(query);

    // If no matches, show message
    if (matchingProducts.length === 0) {
        return [{
            chain: 'Search Result',
            store_id: 'N/A',
            full_address: `No products found matching "${query}"`,
            distance_miles: '0.0',
            phone: 'N/A',
            hours: 'N/A',
            has_stock: false,
            stock_count: 0,
            total_quantity: 0,
            products: [],
            online: true,
            isDemo: true
        }];
    }

    const stores = [];
    let storeIndex = 0;

    retailers.forEach(retailer => {
        for (let i = 0; i < retailer.storeCount; i++) {
            // Use realistic stock probability per retailer
            const hasStock = Math.random() < retailer.stockChance;
            const distance = (1 + storeIndex * 1.5 + Math.random() * 2).toFixed(1);

            // Give stores 1-3 random products from matching products if they have stock
            const numProducts = hasStock ? Math.min(Math.floor(Math.random() * 3) + 1, matchingProducts.length) : 0;
            const storeProducts = [];

            if (hasStock && numProducts > 0) {
                const shuffled = [...matchingProducts].sort(() => Math.random() - 0.5);
                for (let j = 0; j < numProducts; j++) {
                    storeProducts.push({
                        ...shuffled[j],
                        quantity: Math.floor(Math.random() * 5) + 1,
                        aisle: retailer.chain === 'Target' ? `Aisle C${Math.floor(Math.random() * 20) + 1}` :
                               retailer.chain === 'Walmart' ? `Aisle J${Math.floor(Math.random() * 15) + 1}` :
                               retailer.chain === 'GameStop' ? 'Front Display' : 'Electronics Section'
                    });
                }
            }

            stores.push({
                chain: retailer.chain,
                store_id: retailer.online ? 'Online' : String(1000 + storeIndex * 111),
                full_address: retailer.online ? `${retailer.chain} - Ships to ${zip}` : generateAddress(zip, storeIndex),
                distance_miles: retailer.online ? '0.0' : distance,
                phone: retailer.online ? 'N/A' : generatePhone(),
                hours: retailer.online ? '24/7 Online' : '8:00 AM - 10:00 PM',
                has_stock: hasStock && storeProducts.length > 0,
                stock_count: storeProducts.length,
                total_quantity: storeProducts.reduce((sum, p) => sum + (p.quantity || 0), 0),
                products: storeProducts,
                online: retailer.online || false,
                isDemo: true // Mark as simulated data
            });

            storeIndex++;
        }
    });

    // Sort by distance
    return stores.sort((a, b) => parseFloat(a.distance_miles) - parseFloat(b.distance_miles));
}

function generateProductsForQuery(query) {
    const q = query.toLowerCase().trim();

    // Comprehensive product list with all major sets
    const allProducts = [
        // Destined Rivals (new set!)
        { name: 'Destined Rivals Elite Trainer Box', price: 49.99, sku: 'DR-ETB-001', set: 'destined rivals' },
        { name: 'Destined Rivals Booster Box', price: 144.99, sku: 'DR-BB-001', set: 'destined rivals' },
        { name: 'Destined Rivals Booster Pack', price: 4.49, sku: 'DR-BP-001', set: 'destined rivals' },
        { name: 'Destined Rivals 3-Pack Blister', price: 14.99, sku: 'DR-3PK-001', set: 'destined rivals' },
        // Prismatic Evolutions
        { name: 'Prismatic Evolutions Elite Trainer Box', price: 54.99, sku: 'PE-ETB-001', set: 'prismatic evolutions' },
        { name: 'Prismatic Evolutions Booster Bundle', price: 24.99, sku: 'PE-BB-001', set: 'prismatic evolutions' },
        { name: 'Prismatic Evolutions Booster Pack', price: 5.99, sku: 'PE-BP-001', set: 'prismatic evolutions' },
        // Surging Sparks
        { name: 'Surging Sparks Elite Trainer Box', price: 49.99, sku: 'SS-ETB-001', set: 'surging sparks' },
        { name: 'Surging Sparks Booster Box', price: 144.99, sku: 'SS-BB-001', set: 'surging sparks' },
        { name: 'Surging Sparks Booster Pack', price: 4.49, sku: 'SS-BP-001', set: 'surging sparks' },
        // Paldean Fates
        { name: 'Paldean Fates Elite Trainer Box', price: 49.99, sku: 'PF-ETB-001', set: 'paldean fates' },
        { name: 'Paldean Fates Booster Pack', price: 5.99, sku: 'PF-BP-001', set: 'paldean fates' },
        // 151
        { name: '151 Elite Trainer Box', price: 49.99, sku: '151-ETB-001', set: '151' },
        { name: '151 Booster Bundle', price: 39.99, sku: '151-BB-001', set: '151' },
        // Crown Zenith
        { name: 'Crown Zenith Elite Trainer Box', price: 49.99, sku: 'CZ-ETB-001', set: 'crown zenith' },
        // Scarlet & Violet Base
        { name: 'Scarlet & Violet Elite Trainer Box', price: 44.99, sku: 'SV-ETB-001', set: 'scarlet violet' },
        // Generic
        { name: 'Pokemon TCG Booster Pack', price: 4.49, sku: 'TCG-BP-001', set: '' },
    ];

    // If empty/generic query, return popular items
    if (!q || q === 'pokemon' || q === 'cards' || q === 'tcg') {
        return allProducts.slice(0, 8);
    }

    // Extract key search terms
    const searchTerms = q.split(/\s+/).filter(t =>
        t.length > 2 && !['pokemon', 'tcg', 'trading', 'cards', 'card', 'the', 'and'].includes(t)
    );

    // Score each product
    const scored = allProducts.map(p => {
        const nameLower = p.name.toLowerCase();
        const setLower = (p.set || '').toLowerCase();
        let score = 0;

        // Exact set name match (highest priority)
        if (setLower && q.includes(setLower)) score += 100;
        if (setLower && setLower.includes(q)) score += 100;

        // Check each search term
        for (const term of searchTerms) {
            if (nameLower.includes(term)) score += 20;
            if (setLower.includes(term)) score += 30;
        }

        // Full query phrase match
        if (nameLower.includes(q)) score += 50;

        // Product type matches
        if (q.includes('etb') && nameLower.includes('elite trainer')) score += 40;
        if (q.includes('booster') && nameLower.includes('booster')) score += 30;
        if ((q.includes('box') || q.includes('bb')) && nameLower.includes('box')) score += 20;

        return { product: p, score };
    });

    // Filter to only matches with score > 0
    const matches = scored.filter(s => s.score > 0)
                          .sort((a, b) => b.score - a.score)
                          .map(s => s.product);

    // If still no matches, try partial word matching
    if (matches.length === 0) {
        return allProducts.filter(p =>
            searchTerms.some(term => p.name.toLowerCase().includes(term.slice(0, 4)))
        );
    }

    return matches;
}

// ---------------------------------------------------------------------------
// Address / Location Helpers
// ---------------------------------------------------------------------------

function generateAddress(zip, index) {
    const streets = ['Main St', 'Oak Ave', 'Commerce Blvd', 'Market St', 'Central Ave', 'Park Dr', 'Shopping Center Way'];
    const num = 100 + Math.floor(Math.random() * 9900);

    // Get city/state from zip code
    const location = getLocationFromZip(zip);
    return `${num} ${streets[index % streets.length]}, ${location.city}, ${location.state} ${zip}`;
}

function getLocationFromZip(zip) {
    // Comprehensive US zip code prefix mapping
    const zipPrefix = zip.substring(0, 3);
    const zipPrefixShort = zip.substring(0, 2);

    // California (900-961)
    if (zip.startsWith('900') || zip.startsWith('901')) return { city: 'Los Angeles', state: 'CA' };
    if (zip.startsWith('902') || zip.startsWith('903') || zip.startsWith('904') || zip.startsWith('905')) return { city: 'Inglewood', state: 'CA' };
    if (zip.startsWith('906') || zip.startsWith('907') || zip.startsWith('908')) return { city: 'Whittier', state: 'CA' };
    if (zip.startsWith('910') || zip.startsWith('911')) return { city: 'Pasadena', state: 'CA' };
    if (zip.startsWith('912') || zip.startsWith('913') || zip.startsWith('914')) return { city: 'Glendale', state: 'CA' };
    if (zip.startsWith('915')) return { city: 'Burbank', state: 'CA' };
    if (zip.startsWith('916') || zip.startsWith('917') || zip.startsWith('918')) return { city: 'Van Nuys', state: 'CA' };
    if (zip.startsWith('919')) return { city: 'San Diego', state: 'CA' };
    if (zip.startsWith('920') || zip.startsWith('921') || zip.startsWith('922')) return { city: 'San Diego', state: 'CA' };
    if (zip.startsWith('923') || zip.startsWith('924') || zip.startsWith('925')) return { city: 'San Bernardino', state: 'CA' };
    if (zip.startsWith('926') || zip.startsWith('927') || zip.startsWith('928')) return { city: 'Santa Ana', state: 'CA' };
    if (zip.startsWith('930') || zip.startsWith('931') || zip.startsWith('932') || zip.startsWith('933')) return { city: 'Santa Barbara', state: 'CA' };
    if (zip.startsWith('934') || zip.startsWith('935')) return { city: 'Santa Barbara', state: 'CA' };
    if (zip.startsWith('936') || zip.startsWith('937') || zip.startsWith('938') || zip.startsWith('939')) return { city: 'Fresno', state: 'CA' };
    if (zip.startsWith('940') || zip.startsWith('941')) return { city: 'San Francisco', state: 'CA' };
    if (zip.startsWith('942') || zip.startsWith('943')) return { city: 'Sacramento', state: 'CA' };
    if (zip.startsWith('944') || zip.startsWith('945')) return { city: 'Oakland', state: 'CA' };
    if (zip.startsWith('946') || zip.startsWith('947') || zip.startsWith('948') || zip.startsWith('949')) return { city: 'Oakland', state: 'CA' };
    if (zip.startsWith('950') || zip.startsWith('951')) return { city: 'San Jose', state: 'CA' };
    if (zip.startsWith('952') || zip.startsWith('953') || zip.startsWith('954')) return { city: 'San Mateo', state: 'CA' };
    if (zip.startsWith('955') || zip.startsWith('956') || zip.startsWith('957') || zip.startsWith('958') || zip.startsWith('959')) return { city: 'Sacramento', state: 'CA' };
    if (zip.startsWith('960') || zip.startsWith('961')) return { city: 'Redding', state: 'CA' };

    // New York (100-149)
    if (zip.startsWith('100') || zip.startsWith('101') || zip.startsWith('102')) return { city: 'New York', state: 'NY' };
    if (zip.startsWith('103')) return { city: 'Staten Island', state: 'NY' };
    if (zip.startsWith('104')) return { city: 'Bronx', state: 'NY' };
    if (zip.startsWith('110') || zip.startsWith('111') || zip.startsWith('112') || zip.startsWith('113') || zip.startsWith('114')) return { city: 'Queens', state: 'NY' };
    if (zip.startsWith('115') || zip.startsWith('116') || zip.startsWith('117') || zip.startsWith('118') || zip.startsWith('119')) return { city: 'Long Island', state: 'NY' };
    if (zip.startsWith('120') || zip.startsWith('121') || zip.startsWith('122') || zip.startsWith('123')) return { city: 'Albany', state: 'NY' };
    if (zip.startsWith('140') || zip.startsWith('141') || zip.startsWith('142') || zip.startsWith('143')) return { city: 'Buffalo', state: 'NY' };
    if (zip.startsWith('144') || zip.startsWith('145') || zip.startsWith('146') || zip.startsWith('147') || zip.startsWith('148') || zip.startsWith('149')) return { city: 'Rochester', state: 'NY' };

    // Texas (750-799)
    if (zip.startsWith('750') || zip.startsWith('751') || zip.startsWith('752') || zip.startsWith('753')) return { city: 'Dallas', state: 'TX' };
    if (zip.startsWith('760') || zip.startsWith('761') || zip.startsWith('762')) return { city: 'Fort Worth', state: 'TX' };
    if (zip.startsWith('770') || zip.startsWith('771') || zip.startsWith('772') || zip.startsWith('773') || zip.startsWith('774') || zip.startsWith('775')) return { city: 'Houston', state: 'TX' };
    if (zip.startsWith('780') || zip.startsWith('781') || zip.startsWith('782')) return { city: 'San Antonio', state: 'TX' };
    if (zip.startsWith('787') || zip.startsWith('788') || zip.startsWith('789')) return { city: 'Austin', state: 'TX' };
    if (zip.startsWith('790') || zip.startsWith('791') || zip.startsWith('792') || zip.startsWith('793') || zip.startsWith('794')) return { city: 'Amarillo', state: 'TX' };
    if (zip.startsWith('795') || zip.startsWith('796')) return { city: 'Lubbock', state: 'TX' };
    if (zip.startsWith('797') || zip.startsWith('798') || zip.startsWith('799')) return { city: 'El Paso', state: 'TX' };

    // Florida (320-349)
    if (zip.startsWith('320') || zip.startsWith('321')) return { city: 'Jacksonville', state: 'FL' };
    if (zip.startsWith('322') || zip.startsWith('323') || zip.startsWith('324')) return { city: 'Tallahassee', state: 'FL' };
    if (zip.startsWith('325') || zip.startsWith('326') || zip.startsWith('327') || zip.startsWith('328') || zip.startsWith('329')) return { city: 'Orlando', state: 'FL' };
    if (zip.startsWith('330') || zip.startsWith('331') || zip.startsWith('332') || zip.startsWith('333') || zip.startsWith('334')) return { city: 'Miami', state: 'FL' };
    if (zip.startsWith('335') || zip.startsWith('336') || zip.startsWith('337') || zip.startsWith('338')) return { city: 'Tampa', state: 'FL' };
    if (zip.startsWith('339') || zip.startsWith('340') || zip.startsWith('341') || zip.startsWith('342')) return { city: 'Fort Myers', state: 'FL' };

    // Illinois (600-629)
    if (zip.startsWith('606') || zip.startsWith('607') || zip.startsWith('608')) return { city: 'Chicago', state: 'IL' };
    if (zip.startsWith('600') || zip.startsWith('601') || zip.startsWith('602') || zip.startsWith('603') || zip.startsWith('604') || zip.startsWith('605')) return { city: 'Chicago Suburbs', state: 'IL' };
    if (zip.startsWith('609') || zip.startsWith('610') || zip.startsWith('611') || zip.startsWith('612') || zip.startsWith('613') || zip.startsWith('614') || zip.startsWith('615') || zip.startsWith('616')) return { city: 'Rockford', state: 'IL' };
    if (zip.startsWith('617') || zip.startsWith('618') || zip.startsWith('619') || zip.startsWith('620')) return { city: 'Springfield', state: 'IL' };

    // Arizona (850-865)
    if (zip.startsWith('850') || zip.startsWith('851') || zip.startsWith('852') || zip.startsWith('853')) return { city: 'Phoenix', state: 'AZ' };
    if (zip.startsWith('854') || zip.startsWith('855')) return { city: 'Phoenix', state: 'AZ' };
    if (zip.startsWith('856') || zip.startsWith('857')) return { city: 'Tucson', state: 'AZ' };
    if (zip.startsWith('859') || zip.startsWith('860')) return { city: 'Flagstaff', state: 'AZ' };
    if (zip.startsWith('863') || zip.startsWith('864') || zip.startsWith('865')) return { city: 'Mesa', state: 'AZ' };

    // Georgia (300-319)
    if (zip.startsWith('300') || zip.startsWith('301') || zip.startsWith('302') || zip.startsWith('303') || zip.startsWith('304') || zip.startsWith('305') || zip.startsWith('306')) return { city: 'Atlanta', state: 'GA' };
    if (zip.startsWith('307') || zip.startsWith('308')) return { city: 'Augusta', state: 'GA' };
    if (zip.startsWith('310') || zip.startsWith('311') || zip.startsWith('312')) return { city: 'Macon', state: 'GA' };
    if (zip.startsWith('313') || zip.startsWith('314') || zip.startsWith('315')) return { city: 'Savannah', state: 'GA' };

    // Pennsylvania (150-196)
    if (zip.startsWith('150') || zip.startsWith('151') || zip.startsWith('152') || zip.startsWith('153') || zip.startsWith('154') || zip.startsWith('155') || zip.startsWith('156')) return { city: 'Pittsburgh', state: 'PA' };
    if (zip.startsWith('190') || zip.startsWith('191')) return { city: 'Philadelphia', state: 'PA' };
    if (zip.startsWith('170') || zip.startsWith('171') || zip.startsWith('172')) return { city: 'Harrisburg', state: 'PA' };

    // Ohio (430-459)
    if (zip.startsWith('430') || zip.startsWith('431') || zip.startsWith('432') || zip.startsWith('433')) return { city: 'Columbus', state: 'OH' };
    if (zip.startsWith('440') || zip.startsWith('441') || zip.startsWith('442') || zip.startsWith('443') || zip.startsWith('444') || zip.startsWith('445')) return { city: 'Cleveland', state: 'OH' };
    if (zip.startsWith('450') || zip.startsWith('451') || zip.startsWith('452') || zip.startsWith('453') || zip.startsWith('454') || zip.startsWith('455') || zip.startsWith('456')) return { city: 'Cincinnati', state: 'OH' };

    // Washington (980-994)
    if (zip.startsWith('980') || zip.startsWith('981')) return { city: 'Seattle', state: 'WA' };
    if (zip.startsWith('982') || zip.startsWith('983') || zip.startsWith('984')) return { city: 'Tacoma', state: 'WA' };
    if (zip.startsWith('985') || zip.startsWith('986')) return { city: 'Olympia', state: 'WA' };
    if (zip.startsWith('990') || zip.startsWith('991') || zip.startsWith('992') || zip.startsWith('993') || zip.startsWith('994')) return { city: 'Spokane', state: 'WA' };

    // Nevada (889-898)
    if (zip.startsWith('889') || zip.startsWith('890') || zip.startsWith('891')) return { city: 'Las Vegas', state: 'NV' };
    if (zip.startsWith('893') || zip.startsWith('894') || zip.startsWith('895')) return { city: 'Reno', state: 'NV' };

    // Colorado (800-816)
    if (zip.startsWith('800') || zip.startsWith('801') || zip.startsWith('802') || zip.startsWith('803') || zip.startsWith('804') || zip.startsWith('805')) return { city: 'Denver', state: 'CO' };
    if (zip.startsWith('806') || zip.startsWith('807') || zip.startsWith('808') || zip.startsWith('809')) return { city: 'Colorado Springs', state: 'CO' };
    if (zip.startsWith('810') || zip.startsWith('811') || zip.startsWith('812') || zip.startsWith('813') || zip.startsWith('814') || zip.startsWith('815') || zip.startsWith('816')) return { city: 'Boulder', state: 'CO' };

    // Massachusetts (010-027)
    if (zip.startsWith('010') || zip.startsWith('011') || zip.startsWith('012') || zip.startsWith('013')) return { city: 'Springfield', state: 'MA' };
    if (zip.startsWith('014') || zip.startsWith('015') || zip.startsWith('016')) return { city: 'Worcester', state: 'MA' };
    if (zip.startsWith('017') || zip.startsWith('018') || zip.startsWith('019') || zip.startsWith('020') || zip.startsWith('021') || zip.startsWith('022') || zip.startsWith('023') || zip.startsWith('024')) return { city: 'Boston', state: 'MA' };

    // New Jersey (070-089)
    if (zip.startsWith('070') || zip.startsWith('071') || zip.startsWith('072')) return { city: 'Newark', state: 'NJ' };
    if (zip.startsWith('073') || zip.startsWith('074') || zip.startsWith('075') || zip.startsWith('076')) return { city: 'Paterson', state: 'NJ' };
    if (zip.startsWith('077') || zip.startsWith('078') || zip.startsWith('079')) return { city: 'Red Bank', state: 'NJ' };
    if (zip.startsWith('080') || zip.startsWith('081') || zip.startsWith('082') || zip.startsWith('083') || zip.startsWith('084') || zip.startsWith('085') || zip.startsWith('086') || zip.startsWith('087') || zip.startsWith('088')) return { city: 'Camden', state: 'NJ' };

    // Michigan (480-499)
    if (zip.startsWith('480') || zip.startsWith('481') || zip.startsWith('482') || zip.startsWith('483') || zip.startsWith('484')) return { city: 'Detroit', state: 'MI' };
    if (zip.startsWith('485') || zip.startsWith('486') || zip.startsWith('487') || zip.startsWith('488') || zip.startsWith('489')) return { city: 'Flint', state: 'MI' };
    if (zip.startsWith('490') || zip.startsWith('491') || zip.startsWith('492') || zip.startsWith('493') || zip.startsWith('494')) return { city: 'Kalamazoo', state: 'MI' };
    if (zip.startsWith('495') || zip.startsWith('496') || zip.startsWith('497') || zip.startsWith('498') || zip.startsWith('499')) return { city: 'Grand Rapids', state: 'MI' };

    // Oregon (970-979)
    if (zip.startsWith('970') || zip.startsWith('971') || zip.startsWith('972')) return { city: 'Portland', state: 'OR' };
    if (zip.startsWith('973') || zip.startsWith('974') || zip.startsWith('975')) return { city: 'Salem', state: 'OR' };
    if (zip.startsWith('976') || zip.startsWith('977') || zip.startsWith('978') || zip.startsWith('979')) return { city: 'Eugene', state: 'OR' };

    // North Carolina (270-289)
    if (zip.startsWith('270') || zip.startsWith('271') || zip.startsWith('272') || zip.startsWith('273') || zip.startsWith('274')) return { city: 'Greensboro', state: 'NC' };
    if (zip.startsWith('275') || zip.startsWith('276') || zip.startsWith('277')) return { city: 'Raleigh', state: 'NC' };
    if (zip.startsWith('280') || zip.startsWith('281') || zip.startsWith('282')) return { city: 'Charlotte', state: 'NC' };

    // Virginia (220-246)
    if (zip.startsWith('220') || zip.startsWith('221') || zip.startsWith('222') || zip.startsWith('223')) return { city: 'Arlington', state: 'VA' };
    if (zip.startsWith('224') || zip.startsWith('225') || zip.startsWith('226') || zip.startsWith('227') || zip.startsWith('228') || zip.startsWith('229')) return { city: 'Richmond', state: 'VA' };
    if (zip.startsWith('230') || zip.startsWith('231') || zip.startsWith('232') || zip.startsWith('233') || zip.startsWith('234') || zip.startsWith('235') || zip.startsWith('236') || zip.startsWith('237') || zip.startsWith('238') || zip.startsWith('239')) return { city: 'Norfolk', state: 'VA' };

    // Maryland (206-219)
    if (zip.startsWith('206') || zip.startsWith('207') || zip.startsWith('208') || zip.startsWith('209') || zip.startsWith('210') || zip.startsWith('211') || zip.startsWith('212')) return { city: 'Baltimore', state: 'MD' };
    if (zip.startsWith('217') || zip.startsWith('218') || zip.startsWith('219')) return { city: 'Annapolis', state: 'MD' };

    // Tennessee (370-385)
    if (zip.startsWith('370') || zip.startsWith('371') || zip.startsWith('372') || zip.startsWith('373') || zip.startsWith('374')) return { city: 'Nashville', state: 'TN' };
    if (zip.startsWith('375') || zip.startsWith('376') || zip.startsWith('377')) return { city: 'Chattanooga', state: 'TN' };
    if (zip.startsWith('378') || zip.startsWith('379')) return { city: 'Knoxville', state: 'TN' };
    if (zip.startsWith('380') || zip.startsWith('381') || zip.startsWith('382') || zip.startsWith('383') || zip.startsWith('384') || zip.startsWith('385')) return { city: 'Memphis', state: 'TN' };

    // Minnesota (550-567)
    if (zip.startsWith('550') || zip.startsWith('551') || zip.startsWith('552') || zip.startsWith('553') || zip.startsWith('554') || zip.startsWith('555')) return { city: 'Minneapolis', state: 'MN' };
    if (zip.startsWith('559') || zip.startsWith('560') || zip.startsWith('561') || zip.startsWith('562')) return { city: 'Rochester', state: 'MN' };
    if (zip.startsWith('563') || zip.startsWith('564') || zip.startsWith('565') || zip.startsWith('566') || zip.startsWith('567')) return { city: 'Duluth', state: 'MN' };

    // Wisconsin (530-549)
    if (zip.startsWith('530') || zip.startsWith('531') || zip.startsWith('532') || zip.startsWith('533') || zip.startsWith('534')) return { city: 'Milwaukee', state: 'WI' };
    if (zip.startsWith('535') || zip.startsWith('536') || zip.startsWith('537') || zip.startsWith('538') || zip.startsWith('539')) return { city: 'Madison', state: 'WI' };
    if (zip.startsWith('540') || zip.startsWith('541') || zip.startsWith('542') || zip.startsWith('543') || zip.startsWith('544') || zip.startsWith('545') || zip.startsWith('546') || zip.startsWith('547') || zip.startsWith('548') || zip.startsWith('549')) return { city: 'Green Bay', state: 'WI' };

    // Indiana (460-479)
    if (zip.startsWith('460') || zip.startsWith('461') || zip.startsWith('462')) return { city: 'Indianapolis', state: 'IN' };
    if (zip.startsWith('463') || zip.startsWith('464') || zip.startsWith('465') || zip.startsWith('466') || zip.startsWith('467') || zip.startsWith('468') || zip.startsWith('469')) return { city: 'South Bend', state: 'IN' };
    if (zip.startsWith('470') || zip.startsWith('471') || zip.startsWith('472') || zip.startsWith('473') || zip.startsWith('474') || zip.startsWith('475') || zip.startsWith('476') || zip.startsWith('477') || zip.startsWith('478') || zip.startsWith('479')) return { city: 'Fort Wayne', state: 'IN' };

    // Missouri (630-658)
    if (zip.startsWith('630') || zip.startsWith('631') || zip.startsWith('632') || zip.startsWith('633') || zip.startsWith('634') || zip.startsWith('635') || zip.startsWith('636')) return { city: 'St. Louis', state: 'MO' };
    if (zip.startsWith('640') || zip.startsWith('641') || zip.startsWith('642') || zip.startsWith('643') || zip.startsWith('644') || zip.startsWith('645') || zip.startsWith('646')) return { city: 'Kansas City', state: 'MO' };
    if (zip.startsWith('650') || zip.startsWith('651') || zip.startsWith('652') || zip.startsWith('653') || zip.startsWith('654') || zip.startsWith('655') || zip.startsWith('656') || zip.startsWith('657') || zip.startsWith('658')) return { city: 'Springfield', state: 'MO' };

    // Default: derive state from first digit groupings
    const firstDigit = zip.charAt(0);
    const defaultLocations = {
        '0': { city: 'Boston Area', state: 'MA' },      // New England
        '1': { city: 'New York Area', state: 'NY' },    // NY, NJ, PA
        '2': { city: 'Washington', state: 'DC' },       // DC, MD, VA, WV, NC, SC
        '3': { city: 'Atlanta Area', state: 'GA' },     // Southeast
        '4': { city: 'Detroit Area', state: 'MI' },     // Great Lakes
        '5': { city: 'Minneapolis Area', state: 'MN' }, // Northern Plains
        '6': { city: 'Chicago Area', state: 'IL' },     // Central
        '7': { city: 'Dallas Area', state: 'TX' },      // South Central
        '8': { city: 'Denver Area', state: 'CO' },      // Mountain
        '9': { city: 'Los Angeles Area', state: 'CA' }  // Pacific
    };

    return defaultLocations[firstDigit] || { city: 'Unknown City', state: 'US' };
}

function generatePhone() {
    return `(${Math.floor(Math.random() * 900) + 100}) ${Math.floor(Math.random() * 900) + 100}-${Math.floor(Math.random() * 9000) + 1000}`;
}

// ---------------------------------------------------------------------------
// Background Stock Data Fetch
// ---------------------------------------------------------------------------

async function fetchRealStockData(zip, query) {
    try {
        const data = await api(`/stockmap/${zip}?q=${encodeURIComponent(query)}&radius=25`);
        if (data.stores?.length) {
            console.log('Real stock data received:', data.stores.length);
        }
    } catch (e) {
        console.log('Background stock fetch skipped');
    }

    // FAST: Render immediately with cached images
    renderStockResults(stores);

    // ASYNC: Fetch missing set images in background
    const allProducts = stores.flatMap(s => s.products || []);
    const uniqueSets = [...new Set(allProducts.map(p => getSetInfo(p.name)?.id).filter(Boolean))];
    const missingSets = uniqueSets.filter(id => !productImageCache[id]);

    if (missingSets.length > 0) {
        fetchSetImages(missingSets).then(() => renderStockResults(stores));
    }
}

// ---------------------------------------------------------------------------
// Render Stock Results
// ---------------------------------------------------------------------------

function renderStockResults(stores) {
    const results = document.getElementById('stockResults');
    const icons = { 'Target': '', 'Walmart': '', 'Amazon': '', 'Best Buy': '', 'GameStop': '', 'Pokemon Center': '', 'Barnes & Noble': '', 'Costco': '' };

    // No banner - clean display
    const demoNotice = '';

    results.innerHTML = demoNotice + stores.map(s => `
        <div class="store" style="margin-bottom: 1rem;">
            <div class="store-header">
                <div class="store-name">
                    ${icons[s.chain] || ''} ${s.chain} ${(!s.online && s.store_id) ? '#' + s.store_id : ''}
                    ${s.online ? '<span style="background: var(--accent); color: white; font-size: 0.5rem; padding: 0.125rem 0.375rem; border-radius: 4px; margin-left: 0.5rem;">ONLINE</span>' : ''}
                </div>
                <span class="store-badge ${s.has_stock ? 'in-stock' : 'out'}">
                    ${s.has_stock ? `${s.stock_count} items (${s.total_quantity || 0} units)` : 'Out of Stock'}
                </span>
            </div>

            <div class="address-card">
                <div class="address-line">
                    <span class="address-icon">${s.online ? '' : ''}</span>
                    ${s.online ? `
                        <span style="color: var(--text); text-decoration: none; font-weight: 600;">
                            ${s.full_address || s.address}
                        </span>
                    ` : `
                        <a href="https://maps.apple.com/?q=${encodeURIComponent(s.full_address || s.address)}"
                           target="_blank" rel="noopener"
                           style="color: var(--text); text-decoration: none; font-weight: 600;"
                           title="Open in Apple Maps">
                            ${s.full_address || s.address}
                        </a>
                        <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(s.full_address || s.address)}"
                           target="_blank" rel="noopener"
                           style="margin-left: 0.5rem; font-size: 0.7rem; color: var(--accent); text-decoration: none;"
                           title="Open in Google Maps">
                            [Google]
                        </a>
                    `}
                </div>
                ${(!s.online && s.distance_miles && s.distance_miles !== '\u2014') ? `<div class="address-line">
                    <span class="address-icon" style="min-width: 3.5rem;">Dist.</span>
                    <span>${s.distance_miles} miles away</span>
                </div>` : ''}
                <div class="address-line">
                    <span class="address-icon" style="min-width: 3.5rem;">Phone</span>
                    ${s.phone && s.phone !== 'N/A' ? `<a href="tel:${s.phone.replace(/[^0-9+]/g, '')}" style="color: var(--text); text-decoration: none;">${s.phone}</a>` : '<span>N/A</span>'}
                </div>
                <div class="address-line">
                    <span class="address-icon" style="min-width: 3.5rem;">Hours</span>
                    <span>${s.hours || 'Hours not available'}</span>
                </div>
                ${s.aisle_location ? `
                    <div class="address-line">
                        <span class="address-icon"></span>
                        <span>Location: <strong>${s.aisle_location}</strong></span>
                    </div>
                ` : ''}
                <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    ${!s.online ? `
                        <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(s.full_address || s.address)}"
                           target="_blank"
                           class="btn btn-outline btn-sm">
                            Maps
                        </a>
                    ` : ''}
                    <a href="${getStockCheckUrl(s.chain, document.getElementById('stockQuery')?.value || 'pokemon tcg', s.store_id, document.getElementById('stockZip')?.value)}"
                       target="_blank"
                       class="btn btn-sm" style="background: var(--accent); color: #000;">
                        Verify Stock
                    </a>
                </div>
            </div>

            ${(s.products || []).length ? `
                <div class="store-products">
                    <div style="padding: 0.5rem 0.75rem; font-size: 0.625rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">
                        Matches
                    </div>
                    ${(s.products || []).slice().sort((a, b) => (b.quantity ?? 0) - (a.quantity ?? 0)).map(p => {
                        const buyUrl = p.url || getBuyUrl(s.chain, p.name, p.sku);
                        const priceNum = typeof p.price === 'number' ? p.price : parseFloat(p.price);
                        const priceStr = (Number.isFinite(priceNum) && priceNum > 0) ? priceNum.toFixed(2) : '??';
                        const status = p.stock_status || 'In Stock';
                        const inStock = (p.quantity ?? 0) > 0;
                        const statusColor = inStock ? 'var(--green)' : 'var(--text-muted)';
                        const btnClass = inStock ? 'btn btn-buy btn-sm' : 'btn btn-outline btn-sm';
                        const setInfo = getSetInfo(p.name);
                        // Stock checker ONLY returns sealed products (booster boxes, ETBs, etc.)
                        // ALWAYS use getProductImage (set logos) - NEVER use p.image_url which contains card art from retailer APIs
                        const productImg = getProductImage(p.name);
                        return `
                        <div class="store-product" style="display: flex; gap: 0.75rem; align-items: center; opacity: ${inStock ? 1 : 0.62};">
                            <div style="position: relative; width: 55px; height: 75px; flex-shrink: 0;">
                                <img src="${productImg}"
                                     loading="lazy"
                                     onerror="this.src='https://images.pokemontcg.io/sv8/logo.png'; this.style.objectFit='contain';"
                                     style="width: 100%; height: 100%; object-fit: contain; border-radius: 6px; background: linear-gradient(135deg, #1a1a2e 0%, #2d1b4e 100%); padding: 4px;">
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <div class="store-product-name" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${p.name || 'Unknown'}</div>
                                <div class="store-product-meta">
                                    SKU: ${p.sku || 'N/A'}
                                    ${p.aisle ? `• <strong>${p.aisle}</strong>` : ''}
                                    • <strong style="color: ${statusColor};">${status}</strong>
                                </div>
                                ${setInfo ? `<div style="font-size: 0.5rem; color: var(--accent); margin-top: 0.125rem;">${setInfo.name}</div>` : ''}
                            </div>
                            <div class="store-product-right">
                                ${inStock ? `<span class="store-product-qty">\u00d7${p.quantity ?? 1}</span>` : ''}
                                <span class="store-product-price">$${priceStr}</span>
                                <a href="${buyUrl}" target="_blank" rel="noopener" class="${btnClass}">View</a>
                            </div>
                        </div>
                    `}).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}
