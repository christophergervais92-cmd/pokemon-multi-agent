// =============================================================================
// SET DATABASE TAB - Pokemon TCG sets, chase cards, pull odds, set stats
// =============================================================================
//
// Globals from other modules (do NOT import):
//   state.js   : allSetsData, currentSetCards, currentSetId, productImageCache,
//                pendingRequests, allCardResults, selectedCard, allVariations,
//                cardDetailRequestSeq
//   config.js  : shouldUseProxy(), getApiBaseUrl(), getAssetImageOverride(),
//                DEBUG_MODE, debugLog(), API (via state.js)
//   api.js     : api()
//   utils.js   : fetchSetImages()
//   (dashboard.html inline): switchSection(), displayCardDetail(),
//                             searchCardsOrProducts(), quickCardSearch()

// ---- Pull rates by era / set type (approximate odds per pack) ---------------

const PULL_RATES = {
    // Scarlet & Violet era (2023+)
    'scarlet-violet': {
        'Illustration Rare': { odds: '1:18', pct: 5.5 },
        'Special Art Rare': { odds: '1:45', pct: 2.2 },
        'Ultra Rare': { odds: '1:36', pct: 2.8 },
        'Hyper Rare': { odds: '1:180', pct: 0.55 },
        'Holo Rare': { odds: '1:3', pct: 33 },
        'Double Rare': { odds: '1:9', pct: 11 },
    },
    // Sword & Shield era (2020-2023)
    'sword-shield': {
        'Alternate Art': { odds: '1:60', pct: 1.67 },
        'Secret Rare': { odds: '1:72', pct: 1.4 },
        'Full Art': { odds: '1:36', pct: 2.8 },
        'VMAX': { odds: '1:24', pct: 4.2 },
        'V': { odds: '1:9', pct: 11 },
        'Holo Rare': { odds: '1:3', pct: 33 },
    },
    // Sun & Moon era (2017-2020)
    'sun-moon': {
        'Rainbow Rare': { odds: '1:72', pct: 1.4 },
        'Secret Rare': { odds: '1:60', pct: 1.67 },
        'Full Art': { odds: '1:36', pct: 2.8 },
        'GX': { odds: '1:9', pct: 11 },
        'Holo Rare': { odds: '1:3', pct: 33 },
    },
    // XY era (2014-2017)
    'xy': {
        'Secret Rare': { odds: '1:72', pct: 1.4 },
        'Full Art': { odds: '1:36', pct: 2.8 },
        'EX': { odds: '1:12', pct: 8.3 },
        'Holo Rare': { odds: '1:4', pct: 25 },
    },
    // Black & White era (2011-2014)
    'black-white': {
        'Secret Rare': { odds: '1:72', pct: 1.4 },
        'Full Art': { odds: '1:36', pct: 2.8 },
        'EX': { odds: '1:12', pct: 8.3 },
        'Holo Rare': { odds: '1:4', pct: 25 },
    },
    // Vintage (WOTC era)
    'base': {
        'Holo Rare': { odds: '1:3', pct: 33 },
        'Rare': { odds: '1:1', pct: 100 },
    },
    // Default for unknown sets
    'default': {
        'Ultra Rare': { odds: '1:36', pct: 2.8 },
        'Holo Rare': { odds: '1:3', pct: 33 },
        'Rare': { odds: '1:1', pct: 100 },
    }
};

// ---- Map series ID to era for pull rates ------------------------------------

function getSetEra(seriesId) {
    const seriesLower = (seriesId || '').toLowerCase();
    if (seriesLower.includes('scarlet') || seriesLower.includes('violet')) return 'scarlet-violet';
    if (seriesLower.includes('sword') || seriesLower.includes('shield')) return 'sword-shield';
    if (seriesLower.includes('sun') || seriesLower.includes('moon')) return 'sun-moon';
    if (seriesLower.includes('xy')) return 'xy';
    if (seriesLower.includes('black') || seriesLower.includes('white')) return 'black-white';
    if (seriesLower.includes('base') || seriesLower.includes('jungle') || seriesLower.includes('fossil') ||
        seriesLower.includes('rocket') || seriesLower.includes('gym') || seriesLower.includes('neo')) return 'base';
    return 'default';
}

// ---- Fallback set data for when API is slow ---------------------------------

const FALLBACK_SETS = [
    { id: 'sv8', name: 'Surging Sparks', series: 'Scarlet & Violet', releaseDate: '2024-11-08', total: 191, images: { logo: 'https://images.pokemontcg.io/sv8/logo.png' } },
    { id: 'sv7', name: 'Stellar Crown', series: 'Scarlet & Violet', releaseDate: '2024-09-13', total: 175, images: { logo: 'https://images.pokemontcg.io/sv7/logo.png' } },
    { id: 'sv6pt5', name: 'Shrouded Fable', series: 'Scarlet & Violet', releaseDate: '2024-08-02', total: 99, images: { logo: 'https://images.pokemontcg.io/sv6pt5/logo.png' } },
    { id: 'sv6', name: 'Twilight Masquerade', series: 'Scarlet & Violet', releaseDate: '2024-05-24', total: 226, images: { logo: 'https://images.pokemontcg.io/sv6/logo.png' } },
    { id: 'sv5', name: 'Temporal Forces', series: 'Scarlet & Violet', releaseDate: '2024-03-22', total: 218, images: { logo: 'https://images.pokemontcg.io/sv5/logo.png' } },
    { id: 'sv4pt5', name: 'Paldean Fates', series: 'Scarlet & Violet', releaseDate: '2024-01-26', total: 245, images: { logo: 'https://images.pokemontcg.io/sv4pt5/logo.png' } },
    { id: 'sv4', name: 'Paradox Rift', series: 'Scarlet & Violet', releaseDate: '2023-11-03', total: 266, images: { logo: 'https://images.pokemontcg.io/sv4/logo.png' } },
    { id: 'sv3pt5', name: '151', series: 'Scarlet & Violet', releaseDate: '2023-09-22', total: 207, images: { logo: 'https://images.pokemontcg.io/sv3pt5/logo.png' } },
    { id: 'sv3', name: 'Obsidian Flames', series: 'Scarlet & Violet', releaseDate: '2023-08-11', total: 230, images: { logo: 'https://images.pokemontcg.io/sv3/logo.png' } },
    { id: 'sv2', name: 'Paldea Evolved', series: 'Scarlet & Violet', releaseDate: '2023-06-09', total: 279, images: { logo: 'https://images.pokemontcg.io/sv2/logo.png' } },
    { id: 'sv1', name: 'Scarlet & Violet', series: 'Scarlet & Violet', releaseDate: '2023-03-31', total: 258, images: { logo: 'https://images.pokemontcg.io/sv1/logo.png' } },
    { id: 'swsh12pt5', name: 'Crown Zenith', series: 'Sword & Shield', releaseDate: '2023-01-20', total: 230, images: { logo: 'https://images.pokemontcg.io/swsh12pt5/logo.png' } },
    { id: 'swsh12', name: 'Silver Tempest', series: 'Sword & Shield', releaseDate: '2022-11-11', total: 245, images: { logo: 'https://images.pokemontcg.io/swsh12/logo.png' } },
    { id: 'swsh11', name: 'Lost Origin', series: 'Sword & Shield', releaseDate: '2022-09-09', total: 247, images: { logo: 'https://images.pokemontcg.io/swsh11/logo.png' } },
    { id: 'swsh10', name: 'Astral Radiance', series: 'Sword & Shield', releaseDate: '2022-05-27', total: 246, images: { logo: 'https://images.pokemontcg.io/swsh10/logo.png' } },
    { id: 'swsh9', name: 'Brilliant Stars', series: 'Sword & Shield', releaseDate: '2022-02-25', total: 216, images: { logo: 'https://images.pokemontcg.io/swsh9/logo.png' } },
    { id: 'swsh8', name: 'Fusion Strike', series: 'Sword & Shield', releaseDate: '2021-11-12', total: 284, images: { logo: 'https://images.pokemontcg.io/swsh8/logo.png' } },
    { id: 'swsh7', name: 'Evolving Skies', series: 'Sword & Shield', releaseDate: '2021-08-27', total: 237, images: { logo: 'https://images.pokemontcg.io/swsh7/logo.png' } },
    { id: 'swsh6', name: 'Chilling Reign', series: 'Sword & Shield', releaseDate: '2021-06-18', total: 233, images: { logo: 'https://images.pokemontcg.io/swsh6/logo.png' } },
    { id: 'swsh5', name: 'Battle Styles', series: 'Sword & Shield', releaseDate: '2021-03-19', total: 183, images: { logo: 'https://images.pokemontcg.io/swsh5/logo.png' } },
    { id: 'swsh45sv', name: 'Shining Fates', series: 'Sword & Shield', releaseDate: '2021-02-19', total: 195, images: { logo: 'https://images.pokemontcg.io/swsh45sv/logo.png' } },
    { id: 'swsh4', name: 'Vivid Voltage', series: 'Sword & Shield', releaseDate: '2020-11-13', total: 203, images: { logo: 'https://images.pokemontcg.io/swsh4/logo.png' } },
    { id: 'swsh35', name: "Champion's Path", series: 'Sword & Shield', releaseDate: '2020-09-25', total: 80, images: { logo: 'https://images.pokemontcg.io/swsh35/logo.png' } },
    { id: 'swsh3', name: 'Darkness Ablaze', series: 'Sword & Shield', releaseDate: '2020-08-14', total: 201, images: { logo: 'https://images.pokemontcg.io/swsh3/logo.png' } },
    { id: 'swsh2', name: 'Rebel Clash', series: 'Sword & Shield', releaseDate: '2020-05-01', total: 209, images: { logo: 'https://images.pokemontcg.io/swsh2/logo.png' } },
    { id: 'swsh1', name: 'Sword & Shield', series: 'Sword & Shield', releaseDate: '2020-02-07', total: 216, images: { logo: 'https://images.pokemontcg.io/swsh1/logo.png' } },
    { id: 'sm12', name: 'Cosmic Eclipse', series: 'Sun & Moon', releaseDate: '2019-11-01', total: 272, images: { logo: 'https://images.pokemontcg.io/sm12/logo.png' } },
    { id: 'sm115', name: 'Hidden Fates', series: 'Sun & Moon', releaseDate: '2019-08-23', total: 163, images: { logo: 'https://images.pokemontcg.io/sm115/logo.png' } },
    { id: 'sm11', name: 'Unified Minds', series: 'Sun & Moon', releaseDate: '2019-08-02', total: 258, images: { logo: 'https://images.pokemontcg.io/sm11/logo.png' } },
    { id: 'sm10', name: 'Unbroken Bonds', series: 'Sun & Moon', releaseDate: '2019-05-03', total: 234, images: { logo: 'https://images.pokemontcg.io/sm10/logo.png' } },
    { id: 'sm9', name: 'Team Up', series: 'Sun & Moon', releaseDate: '2019-02-01', total: 196, images: { logo: 'https://images.pokemontcg.io/sm9/logo.png' } },
    { id: 'base1', name: 'Base Set', series: 'Base', releaseDate: '1999-01-09', total: 102, images: { logo: 'https://images.pokemontcg.io/base1/logo.png' } },
    { id: 'base2', name: 'Jungle', series: 'Base', releaseDate: '1999-06-16', total: 64, images: { logo: 'https://images.pokemontcg.io/base2/logo.png' } },
    { id: 'base3', name: 'Fossil', series: 'Base', releaseDate: '1999-10-10', total: 62, images: { logo: 'https://images.pokemontcg.io/base3/logo.png' } },
    { id: 'base4', name: 'Base Set 2', series: 'Base', releaseDate: '2000-02-24', total: 130, images: { logo: 'https://images.pokemontcg.io/base4/logo.png' } },
    { id: 'base5', name: 'Team Rocket', series: 'Base', releaseDate: '2000-04-24', total: 83, images: { logo: 'https://images.pokemontcg.io/base5/logo.png' } },
    { id: 'gym1', name: "Gym Heroes", series: 'Gym', releaseDate: '2000-08-14', total: 132, images: { logo: 'https://images.pokemontcg.io/gym1/logo.png' } },
    { id: 'gym2', name: "Gym Challenge", series: 'Gym', releaseDate: '2000-10-16', total: 132, images: { logo: 'https://images.pokemontcg.io/gym2/logo.png' } },
    { id: 'neo1', name: 'Neo Genesis', series: 'Neo', releaseDate: '2000-12-16', total: 111, images: { logo: 'https://images.pokemontcg.io/neo1/logo.png' } },
    { id: 'neo2', name: 'Neo Discovery', series: 'Neo', releaseDate: '2001-06-01', total: 75, images: { logo: 'https://images.pokemontcg.io/neo2/logo.png' } },
    { id: 'neo3', name: 'Neo Revelation', series: 'Neo', releaseDate: '2001-09-21', total: 66, images: { logo: 'https://images.pokemontcg.io/neo3/logo.png' } },
    { id: 'neo4', name: 'Neo Destiny', series: 'Neo', releaseDate: '2002-02-28', total: 113, images: { logo: 'https://images.pokemontcg.io/neo4/logo.png' } },
];

// ---- Load all sets from Pokemon TCG API -------------------------------------

async function loadAllSets() {
    console.log('loadAllSets called - fetching from API');
    const setSelector = document.getElementById('setSelector');

    if (!setSelector) {
        console.error('setSelector element not found!');
        return;
    }

    // Sets are already in HTML, just try to update from API
    try {
        const setsUrl = shouldUseProxy()
            ? `${getApiBaseUrl()}/api/tcg/sets?orderBy=-releaseDate`
            : 'https://api.pokemontcg.io/v2/sets?orderBy=-releaseDate';

        const response = await fetch(setsUrl);
        const data = await response.json();

        if (data.data && data.data.length > 0) {
            allSetsData = data.data;
            console.log('Loaded', allSetsData.length, 'sets from API');
        }
    } catch (err) {
        console.log('API fetch failed, using HTML fallback sets:', err.message);
    }
}

// ---- Populate set selector dropdown -----------------------------------------

function populateSetSelector(sets) {
    const setSelector = document.getElementById('setSelector');
    if (!setSelector) {
        console.error('populateSetSelector: setSelector not found');
        return;
    }
    console.log('Populating selector with', sets.length, 'sets');
    setSelector.innerHTML = '<option value="">Select a set...</option>';

    // Group by series
    const grouped = {};
    sets.forEach(set => {
        const series = set.series || 'Other';
        if (!grouped[series]) grouped[series] = [];
        grouped[series].push(set);
    });

    // Create optgroups
    Object.keys(grouped).forEach(series => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = series;

        grouped[series].forEach(set => {
            const option = document.createElement('option');
            option.value = set.id;
            option.textContent = `${set.name} (${set.releaseDate || 'N/A'})`;
            option.dataset.series = set.series;
            optgroup.appendChild(option);
        });

        setSelector.appendChild(optgroup);
    });
}

// ---- Filter sets by series in the dropdown ----------------------------------

function filterSetsBySeries(series) {
    const setSelector = document.getElementById('setSelector');
    if (!setSelector) return;

    // Show/hide optgroups based on series filter
    const optgroups = setSelector.querySelectorAll('optgroup');
    optgroups.forEach(optgroup => {
        const groupSeries = optgroup.dataset.series || '';
        if (series === 'all' || groupSeries === series || groupSeries.includes(series) || series.includes(groupSeries)) {
            optgroup.style.display = '';
        } else {
            optgroup.style.display = 'none';
        }
    });

    // Reset selection
    setSelector.value = '';
}

// ---- Debounced set loader ---------------------------------------------------

let loadSetTimeout = null;

function debouncedLoadSet(setId) {
    if (loadSetTimeout) clearTimeout(loadSetTimeout);
    loadSetTimeout = setTimeout(() => {
        loadSetChaseCards(setId);
    }, 150);
}

// ---- Request coalescing - prevent duplicate API calls -----------------------
// (uses pendingRequests Map from state.js)

async function coalesceRequest(key, requestFn) {
    if (pendingRequests.has(key)) {
        return pendingRequests.get(key);
    }

    const promise = requestFn().finally(() => {
        pendingRequests.delete(key);
    });

    pendingRequests.set(key, promise);
    return promise;
}

// ---- Demo data for when TCG API is down/slow --------------------------------

const DEMO_SET_DATA = {
    'sv8pt5': {
        set: { id: 'sv8pt5', name: 'Prismatic Evolutions', series: 'Scarlet & Violet', releaseDate: '2025/01/17', printedTotal: 182, total: 225, images: { logo: 'https://images.pokemontcg.io/sv8pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv8pt5/symbol.png' } },
        cards: [
            { id: 'sv8pt5-161', name: 'Umbreon ex', number: '161', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/161.png', large: 'https://images.pokemontcg.io/sv8pt5/161_hires.png' }, tcgplayer: { prices: { holofoil: { market: 299.99 } } } },
            { id: 'sv8pt5-189', name: 'Eevee', number: '189', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/189.png', large: 'https://images.pokemontcg.io/sv8pt5/189_hires.png' }, tcgplayer: { prices: { holofoil: { market: 149.99 } } } },
            { id: 'sv8pt5-186', name: 'Sylveon ex', number: '186', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/186.png', large: 'https://images.pokemontcg.io/sv8pt5/186_hires.png' }, tcgplayer: { prices: { holofoil: { market: 89.99 } } } },
            { id: 'sv8pt5-162', name: 'Vaporeon ex', number: '162', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/162.png', large: 'https://images.pokemontcg.io/sv8pt5/162_hires.png' }, tcgplayer: { prices: { holofoil: { market: 79.99 } } } },
            { id: 'sv8pt5-163', name: 'Jolteon ex', number: '163', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/163.png', large: 'https://images.pokemontcg.io/sv8pt5/163_hires.png' }, tcgplayer: { prices: { holofoil: { market: 74.99 } } } },
            { id: 'sv8pt5-164', name: 'Flareon ex', number: '164', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/164.png', large: 'https://images.pokemontcg.io/sv8pt5/164_hires.png' }, tcgplayer: { prices: { holofoil: { market: 69.99 } } } },
            { id: 'sv8pt5-165', name: 'Espeon ex', number: '165', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/165.png', large: 'https://images.pokemontcg.io/sv8pt5/165_hires.png' }, tcgplayer: { prices: { holofoil: { market: 84.99 } } } },
            { id: 'sv8pt5-166', name: 'Glaceon ex', number: '166', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/166.png', large: 'https://images.pokemontcg.io/sv8pt5/166_hires.png' }, tcgplayer: { prices: { holofoil: { market: 79.99 } } } },
            { id: 'sv8pt5-167', name: 'Leafeon ex', number: '167', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8pt5/167.png', large: 'https://images.pokemontcg.io/sv8pt5/167_hires.png' }, tcgplayer: { prices: { holofoil: { market: 74.99 } } } },
        ]
    },
    'sv8': {
        set: { id: 'sv8', name: 'Surging Sparks', series: 'Scarlet & Violet', releaseDate: '2024/11/08', printedTotal: 191, total: 252, images: { logo: 'https://images.pokemontcg.io/sv8/logo.png', symbol: 'https://images.pokemontcg.io/sv8/symbol.png' } },
        cards: [
            { id: 'sv8-230', name: 'Pikachu ex', number: '230', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8/230.png', large: 'https://images.pokemontcg.io/sv8/230_hires.png' }, tcgplayer: { prices: { holofoil: { market: 189.99 } } } },
            { id: 'sv8-225', name: 'Charizard ex', number: '225', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8/225.png', large: 'https://images.pokemontcg.io/sv8/225_hires.png' }, tcgplayer: { prices: { holofoil: { market: 124.99 } } } },
            { id: 'sv8-226', name: 'Raichu ex', number: '226', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv8/226.png', large: 'https://images.pokemontcg.io/sv8/226_hires.png' }, tcgplayer: { prices: { holofoil: { market: 54.99 } } } },
        ]
    },
    'swsh7': {
        set: { id: 'swsh7', name: 'Evolving Skies', series: 'Sword & Shield', releaseDate: '2021/08/27', printedTotal: 203, total: 237, images: { logo: 'https://images.pokemontcg.io/swsh7/logo.png', symbol: 'https://images.pokemontcg.io/swsh7/symbol.png' } },
        cards: [
            { id: 'swsh7-215', name: 'Umbreon VMAX', number: '215', rarity: 'Secret Rare', images: { small: 'https://images.pokemontcg.io/swsh7/215.png', large: 'https://images.pokemontcg.io/swsh7/215_hires.png' }, tcgplayer: { prices: { holofoil: { market: 399.99 } } } },
            { id: 'swsh7-212', name: 'Rayquaza VMAX', number: '212', rarity: 'Secret Rare', images: { small: 'https://images.pokemontcg.io/swsh7/212.png', large: 'https://images.pokemontcg.io/swsh7/212_hires.png' }, tcgplayer: { prices: { holofoil: { market: 249.99 } } } },
            { id: 'swsh7-203', name: 'Dragonite V', number: '203', rarity: 'Secret Rare', images: { small: 'https://images.pokemontcg.io/swsh7/203.png', large: 'https://images.pokemontcg.io/swsh7/203_hires.png' }, tcgplayer: { prices: { holofoil: { market: 89.99 } } } },
        ]
    },
    'sv3pt5': {
        set: { id: 'sv3pt5', name: '151', series: 'Scarlet & Violet', releaseDate: '2023/09/22', printedTotal: 165, total: 207, images: { logo: 'https://images.pokemontcg.io/sv3pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv3pt5/symbol.png' } },
        cards: [
            { id: 'sv3pt5-205', name: 'Mew ex', number: '205', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv3pt5/205.png', large: 'https://images.pokemontcg.io/sv3pt5/205_hires.png' }, tcgplayer: { prices: { holofoil: { market: 124.99 } } } },
            { id: 'sv3pt5-199', name: 'Charizard ex', number: '199', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv3pt5/199.png', large: 'https://images.pokemontcg.io/sv3pt5/199_hires.png' }, tcgplayer: { prices: { holofoil: { market: 179.99 } } } },
            { id: 'sv3pt5-198', name: 'Alakazam ex', number: '198', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv3pt5/198.png', large: 'https://images.pokemontcg.io/sv3pt5/198_hires.png' }, tcgplayer: { prices: { holofoil: { market: 49.99 } } } },
        ]
    },
    'sv4pt5': {
        set: { id: 'sv4pt5', name: 'Paldean Fates', series: 'Scarlet & Violet', releaseDate: '2024/01/26', printedTotal: 91, total: 245, images: { logo: 'https://images.pokemontcg.io/sv4pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv4pt5/symbol.png' } },
        cards: [
            { id: 'sv4pt5-220', name: 'Charizard ex', number: '220', rarity: 'Shiny Rare', images: { small: 'https://images.pokemontcg.io/sv4pt5/220.png', large: 'https://images.pokemontcg.io/sv4pt5/220_hires.png' }, tcgplayer: { prices: { holofoil: { market: 89.99 } } } },
            { id: 'sv4pt5-234', name: 'Maushold ex', number: '234', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv4pt5/234.png', large: 'https://images.pokemontcg.io/sv4pt5/234_hires.png' }, tcgplayer: { prices: { holofoil: { market: 34.99 } } } },
        ]
    },
    'sv6pt5': {
        set: { id: 'sv6pt5', name: 'Shrouded Fable', series: 'Scarlet & Violet', releaseDate: '2024/08/02', printedTotal: 99, total: 99, images: { logo: 'https://images.pokemontcg.io/sv6pt5/logo.png', symbol: 'https://images.pokemontcg.io/sv6pt5/symbol.png' } },
        cards: [
            { id: 'sv6pt5-81', name: 'Greninja ex', number: '81', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv6pt5/81.png', large: 'https://images.pokemontcg.io/sv6pt5/81_hires.png' }, tcgplayer: { prices: { holofoil: { market: 64.99 } } } },
            { id: 'sv6pt5-99', name: 'Pecharunt ex', number: '99', rarity: 'Special Illustration Rare', images: { small: 'https://images.pokemontcg.io/sv6pt5/99.png', large: 'https://images.pokemontcg.io/sv6pt5/99_hires.png' }, tcgplayer: { prices: { holofoil: { market: 44.99 } } } },
        ]
    }
};

function getDemoData(setId) {
    const demo = DEMO_SET_DATA[setId];
    if (!demo) return null;
    return {
        data: demo.cards.map(c => ({ ...c, set: demo.set })),
        _isDemo: true
    };
}

// ---- Main set loader (chase cards) ------------------------------------------

async function loadSetChaseCards(setId) {
    if (!setId) {
        console.warn('loadSetChaseCards called with empty setId');
        return;
    }

    console.log('[Set Load] Starting load for set:', setId);

    return coalesceRequest(`set_${setId}`, async () => {
        console.log('[Set Load] Processing set:', setId);
        currentSetId = setId;
        const chaseGrid = document.getElementById('chaseCardsGrid');
        if (!chaseGrid) {
            console.error('chaseCardsGrid not found');
            return;
        }

        // Check for ANY cached data immediately (before showing loading)
        const cacheKey = `set_cards_${setId}`;
        console.log('[Set Load] Checking cache for key:', cacheKey);
        const staleCache = sessionStorage.getItem(cacheKey);
        let hasCachedData = false;

        if (staleCache) {
            try {
                const cachedData = JSON.parse(staleCache);
                const cardCount = cachedData.data?.length || 0;
                console.log('[Set Load] Found cached data:', cardCount, 'cards');

                if (cachedData.data && cachedData.data.length > 0) {
                    console.log('[Set Load] Loading cached data immediately for', setId);
                    currentSetCards = cachedData.data;
                    const setInfo = cachedData.data[0]?.set || { id: setId, name: setId };
                    console.log('[Set Load] Set info from immediate cache:', setInfo);
                    displaySetInfo(setInfo);
                    displayChaseCards(currentSetCards, setInfo);
                    displaySetStats(currentSetCards, setInfo);
                    hasCachedData = true;
                    console.log('[Set Load] Cached data displayed, fetching fresh data in background');
                } else {
                    console.log('[Set Load] Cached data exists but has no cards');
                }
            } catch (e) {
                console.error('[Set Load] Failed to parse cached data:', e);
            }
        } else {
            console.log('[Set Load] No cached data found for', setId);
        }

        // Only show loading skeleton if we don't have cached data
        if (!hasCachedData) {
            chaseGrid.innerHTML = Array(12).fill(0).map(() => `
                <div style="background: var(--bg-card); border-radius: 12px; overflow: hidden; border: 1px solid var(--border);">
                    <div style="width: 100%; aspect-ratio: 245/342; background: linear-gradient(90deg, var(--bg) 25%, var(--surface) 50%, var(--bg) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite;"></div>
                    <div style="padding: 0.75rem;">
                        <div style="height: 14px; background: var(--bg); border-radius: 4px; margin-bottom: 0.5rem;"></div>
                        <div style="height: 10px; background: var(--bg); border-radius: 4px; width: 60%;"></div>
                    </div>
                </div>
            `).join('');
        }

        // Show info cards immediately
        const setInfoCard = document.getElementById('setInfoCard');
        const pullRatesCard = document.getElementById('pullRatesCard');
        const setStatsCard = document.getElementById('setStatsCard');
        if (setInfoCard) {
            setInfoCard.style.display = 'block';
            console.log('[Set Load] Showing setInfoCard');
        }
        if (pullRatesCard) {
            pullRatesCard.style.display = 'block';
            console.log('[Set Load] Showing pullRatesCard');
        }
        if (setStatsCard) {
            setStatsCard.style.display = 'block';
            console.log('[Set Load] Showing setStatsCard');
        }

        try {
            // Check cache first - validate card count AND set ID matches
            const cached = sessionStorage.getItem(cacheKey);
            if (cached) {
                const data = JSON.parse(cached);
                const cardCount = data.data?.length || 0;
                const cachedSetId = data.data?.[0]?.set?.id;

                // Verify cache matches requested set AND has enough cards
                if (cachedSetId === setId && cardCount >= 30) {
                    console.log('[Set Load] Using valid cache for', setId, '- count:', cardCount);
                    currentSetCards = data.data;
                    const setInfo = data.data[0]?.set || { id: setId, name: setId };
                    console.log('[Set Load] Set info from cache:', setInfo);
                    requestAnimationFrame(() => {
                        console.log('[Set Load] Rendering cached data...');
                        displaySetInfo(setInfo);
                        displayChaseCards(currentSetCards, setInfo);
                        displaySetStats(currentSetCards, setInfo);
                    });
                } else {
                    console.log('[Set Load] Cache invalid - expected:', setId, 'got:', cachedSetId, 'count:', cardCount);
                }
            }

            // Fetch cards with retry logic
            console.log('[Set Load] Fetching cards from API for set:', setId, '(hasCachedData:', hasCachedData, ')');
            let data = null;
            let lastError = null;

            for (let attempt = 1; attempt <= 3; attempt++) {
                try {
                    console.log(`[Set Load] Attempt ${attempt}/3 for set ${setId}`);
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => {
                        controller.abort(new Error('Request timeout - API is slow'));
                    }, 45000);

                    // First, try to verify set exists (only on first attempt)
                    if (attempt === 1) {
                        try {
                            const setCheckController = new AbortController();
                            const setCheckTimeout = setTimeout(() => setCheckController.abort(), 10000);

                            const setCheckUrl = shouldUseProxy()
                                ? `${getApiBaseUrl()}/api/tcg/sets/${setId}`
                                : `https://api.pokemontcg.io/v2/sets/${setId}`;

                            const setCheckResponse = await fetch(setCheckUrl, {
                                method: 'GET',
                                headers: { 'Accept': 'application/json' },
                                signal: setCheckController.signal
                            });
                            clearTimeout(setCheckTimeout);

                            if (setCheckResponse.ok) {
                                const setData = await setCheckResponse.json();
                                const setInfo = setData.data || setData;
                                console.log('[Set Load] Set exists in API:', setInfo?.name || setId);
                                if (setInfo) {
                                    window._cachedSetInfo = window._cachedSetInfo || {};
                                    window._cachedSetInfo[setId] = setInfo;
                                }
                            } else if (setCheckResponse.status === 404) {
                                throw new Error(`Set "${setId}" not found in Pokemon TCG API. This set may not be available yet.`);
                            } else {
                                console.warn('[Set Load] Set check returned status:', setCheckResponse.status);
                            }
                        } catch (setCheckError) {
                            if (setCheckError.name === 'AbortError') {
                                console.warn('[Set Load] Set check timed out, continuing with card fetch');
                            } else if (setCheckError.message?.includes('not found')) {
                                throw setCheckError;
                            } else {
                                console.warn('[Set Load] Set check failed:', setCheckError.message, '- continuing with card fetch');
                            }
                        }
                    }

                    // ALWAYS use the backend API for set cards
                    const apiUrl = `${API}/api/sets/${setId}/cards`;
                    console.log(`[Set Load] Fetching from backend: ${apiUrl}`);

                    const response = await fetch(apiUrl, {
                        method: 'GET',
                        headers: { 'Accept': 'application/json' },
                        signal: controller.signal
                    });
                    clearTimeout(timeoutId);

                    if (!response.ok) {
                        if (response.status === 404) {
                            throw new Error(`Set "${setId}" not found in Pokemon TCG API. This set may not be available yet.`);
                        }
                        throw new Error(`API returned ${response.status}: ${response.statusText}`);
                    }

                    data = await response.json();
                    console.log('[Set Load] API response:', data.data?.length, 'cards (attempt', attempt, ')');

                    if (!data.data || data.data.length === 0) {
                        throw new Error(`No cards found for set "${setId}". This set may be empty or not yet in the API.`);
                    }

                    console.log(`[Set Load] Received ${data.total_cards || data.data.length} cards from backend`);
                    break;

                } catch (e) {
                    if (e.name === 'AbortError') {
                        lastError = new Error('Request timed out - Pokemon TCG API is slow. Please try again.');
                    } else if (e.message?.includes('not found') || e.message?.includes('No cards found')) {
                        lastError = e;
                        console.error(`[Set Load] Set ${setId} not available:`, e.message);
                        break;
                    } else {
                        lastError = e;
                    }
                    console.warn(`[Set Load] Attempt ${attempt} failed:`, lastError.message);
                    if (attempt < 3 && !lastError.message?.includes('not found') && !lastError.message?.includes('No cards found')) {
                        console.log('[Set Load] Retrying in 2 seconds...');
                        await new Promise(r => setTimeout(r, 2000));
                    } else {
                        break;
                    }
                }
            }

            if (!data) {
                // Before throwing error, try to use stale cache as fallback
                console.warn('[Set Load] All API attempts failed, checking for stale cache...');
                const staleCacheFallback = sessionStorage.getItem(cacheKey);
                if (staleCacheFallback) {
                    try {
                        const cachedData = JSON.parse(staleCacheFallback);
                        if (cachedData.data && cachedData.data.length > 0) {
                            console.log('[Set Load] Using stale cache as fallback due to API timeout');
                            currentSetCards = cachedData.data;
                            const setInfo = cachedData.data[0]?.set || { id: setId, name: setId };
                            console.log('[Set Load] Set info from stale cache:', setInfo);

                            displaySetInfo(setInfo);
                            displayChaseCards(currentSetCards, setInfo);
                            displaySetStats(currentSetCards, setInfo);

                            const warningDiv = document.createElement('div');
                            warningDiv.style.cssText = 'grid-column: 1 / -1; text-align: center; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; margin-bottom: 1rem;';
                            warningDiv.innerHTML = '<div style="font-size: 0.875rem; color: var(--text-muted);">Showing cached data (API timeout). Data may be outdated.</div>';
                            chaseGrid.insertBefore(warningDiv, chaseGrid.firstChild);
                            return;
                        }
                    } catch (e) {
                        console.error('[Set Load] Failed to parse stale cache:', e);
                    }
                } else {
                    console.error('[Set Load] No stale cache available for fallback');
                }
                throw lastError || new Error('Failed to fetch cards after 3 attempts');
            }

            // Cache the results
            try {
                sessionStorage.setItem(cacheKey, JSON.stringify(data));
                console.log('[Set Load] Cached', data.data?.length || 0, 'cards for set', setId);
            } catch (e) {
                console.error('[Set Load] Cache storage failed:', e.message);
                if (e.name === 'QuotaExceededError') {
                    console.log('[Set Load] Clearing old cache entries...');
                    const keys = Object.keys(sessionStorage).filter(k => k.startsWith('set_cards_') && k !== cacheKey);
                    keys.slice(0, 5).forEach(k => sessionStorage.removeItem(k));
                    try {
                        sessionStorage.setItem(cacheKey, JSON.stringify(data));
                        console.log('[Set Load] Successfully cached after clearing old entries');
                    } catch (e2) {
                        console.error('[Set Load] Still failed to cache after cleanup:', e2);
                    }
                }
            }

            if (data.data && data.data.length > 0) {
                console.log('[Set Load] Successfully loaded', data.data.length, 'cards for set', setId);
                currentSetCards = data.data;

                let setInfo = data.data[0]?.set || { id: setId, name: setId };
                if (window._cachedSetInfo && window._cachedSetInfo[setId]) {
                    setInfo = { ...setInfo, ...window._cachedSetInfo[setId] };
                    console.log('[Set Load] Using cached set info for complete data');
                }
                console.log('[Set Load] Set info from API:', setInfo);

                displaySetInfo(setInfo);
                displayChaseCards(currentSetCards, setInfo);
                displaySetStats(currentSetCards, setInfo);
            } else {
                const isNewSet = ['sv8pt5', 'sv9', 'sv10'].includes(setId);
                chaseGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">
                    <div class="empty-icon inbox" style="margin-bottom: 0.75rem;"></div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text-secondary);">No cards found for this set</div>
                    <div style="font-size: 0.875rem; margin-bottom: 1rem;">This set may be too new and not yet in the Pokemon TCG API database, or the set ID might be incorrect.</div>
                    ${isNewSet
                        ? '<div style="font-size: 0.75rem; margin-top: 0.5rem; color: var(--text-muted);">Tip: Try an older set like "151" (sv3pt5) or "Obsidian Flames" (sv3).</div>'
                        : '<div style="font-size: 0.75rem; margin-top: 0.5rem; color: var(--text-muted);">Tip: Try selecting a different set from the dropdown.</div>'}
                    <div style="display: flex; gap: 0.5rem; justify-content: center; margin-top: 1rem; flex-wrap: wrap;">
                        <button class="btn" onclick="document.getElementById('setSelector').value='sv3pt5'; debouncedLoadSet('sv3pt5');">Try: 151</button>
                        <button class="btn" onclick="document.getElementById('setSelector').value='sv3'; debouncedLoadSet('sv3');">Try: Obsidian Flames</button>
                    </div>
                </div>`;
            }
        } catch (error) {
            console.error('[Set Load] Error loading set cards:', error);
            const isTimeout = error.message?.includes('timeout') || error.message?.includes('aborted') || error.message?.includes('abort');
            console.error('[Set Load] Error details:', {
                message: error.message,
                name: error.name,
                isTimeout: isTimeout,
                setId: setId
            });

            // Try to use stale cache as last resort
            const staleCacheError = sessionStorage.getItem(cacheKey);
            if (staleCacheError) {
                try {
                    const cachedData = JSON.parse(staleCacheError);
                    if (cachedData.data && cachedData.data.length > 0) {
                        console.log('Using stale cache as fallback due to API timeout');
                        currentSetCards = cachedData.data;
                        const setInfo = cachedData.data[0]?.set || { id: setId, name: setId };
                        requestAnimationFrame(() => {
                            displaySetInfo(setInfo);
                            displayChaseCards(currentSetCards, setInfo);
                            displaySetStats(currentSetCards, setInfo);
                        });

                        displaySetInfo(setInfo);
                        displayChaseCards(currentSetCards, setInfo);
                        displaySetStats(currentSetCards, setInfo);

                        const warningDiv = document.createElement('div');
                        warningDiv.style.cssText = 'grid-column: 1 / -1; text-align: center; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; margin-bottom: 1rem;';
                        warningDiv.innerHTML = '<div style="font-size: 0.875rem; color: var(--text-muted);">Showing cached data (API timeout). Data may be outdated.</div>';
                        chaseGrid.insertBefore(warningDiv, chaseGrid.firstChild);
                        return;
                    }
                } catch (e) {
                    console.log('Failed to parse stale cache:', e);
                }
            }

            // No cache available - show error
            chaseGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
                <div class="empty-icon ${isTimeout ? 'timeout' : 'error'}" style="margin-bottom: 0.75rem;"></div>
                <div style="color: var(--red); font-weight: 600; margin-bottom: 0.5rem;">${isTimeout ? 'API Unavailable' : 'Error Loading Cards'}</div>
                <div style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 1rem;">${isTimeout ? 'The Pokemon TCG API is currently slow. Please try again.' : error.message}</div>
                <button class="btn" onclick="loadSetChaseCards('${setId}')" style="margin-top: 0.5rem;">Try Again</button>
            </div>`;
        }
    }); // End of coalesceRequest
}

// ---- Display set info (logo, name, series, release date, pull rates) --------

function displaySetInfo(setInfo) {
    if (!setInfo) {
        console.warn('[Display] displaySetInfo called with no setInfo');
        return;
    }
    console.log('[Display] displaySetInfo called with:', setInfo);
    const logo = document.getElementById('setLogo');
    const name = document.getElementById('setName');
    const series = document.getElementById('setSeries');
    const releaseDate = document.getElementById('setReleaseDate');
    const totalCards = document.getElementById('setTotalCards');

    if (!logo || !name) {
        console.error('[Display] Missing DOM elements for setInfo');
        return;
    }

    // Set logo - try multiple sources
    let logoUrl = setInfo.images?.logo || setInfo.images?.symbol || '';

    // Add .png extension if URL doesn't have one
    if (logoUrl && !logoUrl.match(/\.(png|jpg|jpeg|webp|gif|svg)$/i)) {
        logoUrl = logoUrl + '.png';
    }

    if (logoUrl) {
        logo.src = logoUrl;
        logo.style.display = 'block';
        logo.onerror = function() {
            if (setInfo.id) {
                this.src = `https://images.pokemontcg.io/${setInfo.id}/logo.png`;
            }
        };
    } else {
        if (setInfo.id) {
            logo.src = `https://images.pokemontcg.io/${setInfo.id}/logo.png`;
            logo.style.display = 'block';
        }
    }
    logo.alt = setInfo.name || 'Set Logo';

    name.textContent = setInfo.name || setInfo.id || 'Unknown Set';
    if (series) series.textContent = `Series: ${setInfo.series || setInfo.name?.split(' ')[0] || 'Unknown'}`;
    if (releaseDate) releaseDate.textContent = `Released: ${setInfo.releaseDate || setInfo.releasedAt || 'N/A'}`;
    if (totalCards) {
        const cardCount = setInfo.total || setInfo.printedTotal || setInfo.cardCount || currentSetCards?.length || '?';
        totalCards.textContent = `Cards: ${cardCount}`;
    }

    // Display pull rates for this era
    const pullRatesGrid = document.getElementById('pullRatesGrid');
    if (pullRatesGrid) {
        const era = getSetEra(setInfo.series || setInfo.name);
        const pullRates = PULL_RATES[era] || PULL_RATES['default'];

        pullRatesGrid.innerHTML = Object.entries(pullRates).map(([rarity, data]) => `
            <div style="padding: 0.5rem; background: var(--bg); border-radius: 6px; text-align: center;">
                <div style="font-size: 0.625rem; color: var(--text-muted);">${rarity}</div>
                <div style="font-size: 1rem; font-weight: 700; font-family: 'Space Mono', monospace; color: var(--purple);">${data.odds}</div>
                <div style="font-size: 0.5rem; color: var(--text-muted);">${data.pct}%</div>
            </div>
        `).join('');
    }
}

// ---- Price helpers ----------------------------------------------------------

const priceCache = new Map();

function getBestCardPrice(card) {
    const cardId = card.id;
    if (cardId && priceCache.has(cardId)) {
        return priceCache.get(cardId);
    }

    // Check for direct price field first (from our backend API)
    if (card.price && card.price > 0) {
        if (cardId) priceCache.set(cardId, card.price);
        return card.price;
    }

    const prices = card.tcgplayer?.prices || {};
    const MAX_VALID_PRICE = 5000;

    const allPrices = [];

    // Loop through all price variants (holofoil, reverseHolofoil, normal, etc.)
    Object.keys(prices).forEach(variant => {
        const variantPrices = prices[variant];
        if (variantPrices && typeof variantPrices === 'object') {
            const price = variantPrices.market || variantPrices.mid || variantPrices.high;
            if (price && price > 0 && price < MAX_VALID_PRICE) {
                allPrices.push(price);
            }
        }
    });

    const bestPrice = allPrices.length > 0 ? Math.max(...allPrices) : 0;

    if (cardId) {
        priceCache.set(cardId, bestPrice);
    }

    return bestPrice;
}

// ---- Display chase cards sorted by value ------------------------------------

function displayChaseCards(cards, setInfo) {
    console.log('[Display] displayChaseCards called with', cards?.length || 0, 'cards');
    const chaseGrid = document.getElementById('chaseCardsGrid');
    if (!chaseGrid) {
        console.error('[Display] chaseCardsGrid not found');
        return;
    }

    if (!cards || cards.length === 0) {
        console.warn('[Display] No cards provided to displayChaseCards');
        chaseGrid.innerHTML = '<div class="empty" style="grid-column: 1 / -1;"><div class="empty-icon inbox"></div><div>No cards found for this set</div></div>';
        return;
    }

    try {
        // Known high-value chase cards by set (boost these even if prices missing)
        const knownChaseCards = {
            'swsh7': [
                { pattern: /umbreon.*vmax/i, minPrice: 500, name: 'Umbreon VMAX Alt Art' },
                { pattern: /rayquaza.*vmax/i, minPrice: 300, name: 'Rayquaza VMAX Alt Art' },
                { pattern: /espeon.*vmax/i, minPrice: 200, name: 'Espeon VMAX Alt Art' },
                { pattern: /sylveon.*vmax/i, minPrice: 200, name: 'Sylveon VMAX Alt Art' },
                { pattern: /glaceon.*vmax/i, minPrice: 200, name: 'Glaceon VMAX Alt Art' },
                { pattern: /leafeon.*vmax/i, minPrice: 200, name: 'Leafeon VMAX Alt Art' },
                { pattern: /flareon.*vmax/i, minPrice: 150, name: 'Flareon VMAX Alt Art' },
                { pattern: /jolteon.*vmax/i, minPrice: 150, name: 'Jolteon VMAX Alt Art' },
                { pattern: /vaporeon.*vmax/i, minPrice: 150, name: 'Vaporeon VMAX Alt Art' },
                { pattern: /dragonite.*v.*alt/i, minPrice: 200, name: 'Dragonite V Alt Art' },
                { pattern: /noivern.*v.*alt/i, minPrice: 100, name: 'Noivern V Alt Art' }
            ]
        };

        const setId = setInfo?.id || '';
        const chasePatterns = knownChaseCards[setId] || [];

        // Pre-calculate prices once, then sort
        const cardsWithPrices = cards.map(card => {
            let price = getBestCardPrice(card);
            const cardName = (card.name || '').toLowerCase();
            const rarity = (card.rarity || '').toLowerCase();
            const cardNumber = parseInt(card.number) || 0;

            // Check if this is a known chase card
            for (const chase of chasePatterns) {
                if (chase.pattern.test(cardName)) {
                    const isAltArt = rarity.includes('alternate') ||
                                   rarity.includes('secret') ||
                                   rarity.includes('special illustration') ||
                                   rarity.includes('ultra rare') ||
                                   (cardNumber > 200 && setId === 'swsh7');

                    if (isAltArt && price < chase.minPrice) {
                        price = Math.max(price, chase.minPrice);
                        console.log(`Boosted ${card.name} (#${card.number}, ${card.rarity}) to $${price} (known chase card)`);
                    } else if (isAltArt) {
                        console.log(`${card.name} (#${card.number}, ${card.rarity}) - Price: $${price}`);
                    }
                    break;
                }
            }

            // Also boost any card with high number (200+) and valuable rarity in Evolving Skies
            if (setId === 'swsh7' && cardNumber > 200 && price < 100) {
                if (rarity.includes('alternate') || rarity.includes('secret') || rarity.includes('ultra rare')) {
                    price = Math.max(price, 150);
                    console.log(`Boosted high-number card ${card.name} (#${card.number}) to $${price}`);
                }
            }

            return { card, price };
        });

        // Sort by price (highest first), but also prioritize known chase cards
        cardsWithPrices.sort((a, b) => {
            const aCard = a.card;
            const bCard = b.card;
            const aNum = parseInt(aCard.number) || 0;
            const bNum = parseInt(bCard.number) || 0;
            const aRarity = (aCard.rarity || '').toLowerCase();
            const bRarity = (bCard.rarity || '').toLowerCase();

            // Prioritize high-numbered alt arts in Evolving Skies (200+)
            if (setId === 'swsh7') {
                const aIsHighAlt = aNum > 200 && (aRarity.includes('alternate') || aRarity.includes('secret') || aRarity.includes('ultra rare'));
                const bIsHighAlt = bNum > 200 && (bRarity.includes('alternate') || bRarity.includes('secret') || bRarity.includes('ultra rare'));
                if (aIsHighAlt && !bIsHighAlt) return -1;
                if (!aIsHighAlt && bIsHighAlt) return 1;
            }

            if (Math.abs(a.price - b.price) < 10) {
                const aIsChase = chasePatterns.some(c => c.pattern.test((aCard.name || '').toLowerCase()));
                const bIsChase = chasePatterns.some(c => c.pattern.test((bCard.name || '').toLowerCase()));
                if (aIsChase && !bIsChase) return -1;
                if (!aIsChase && bIsChase) return 1;
            }
            return b.price - a.price;
        });

        // Take top 50 cards by price for display
        let chaseCards = cardsWithPrices.slice(0, 50).map(item => item.card);

        // For Evolving Skies, also include any high-numbered alt arts that might have been missed
        if (setId === 'swsh7') {
            const umbreonCards = cards.filter(c => c.name?.toLowerCase().includes('umbreon'));
            const rayquazaCards = cards.filter(c => c.name?.toLowerCase().includes('rayquaza'));

            console.log(`Evolving Skies - Found ${umbreonCards.length} Umbreon cards:`, umbreonCards.map(c => `${c.name} #${c.number} (${c.rarity}) - $${getBestCardPrice(c)}`));
            console.log(`Evolving Skies - Found ${rayquazaCards.length} Rayquaza cards:`, rayquazaCards.map(c => `${c.name} #${c.number} (${c.rarity}) - $${getBestCardPrice(c)}`));

            const highNumberAlts = cards
                .filter(c => {
                    const num = parseInt(c.number) || 0;
                    const rar = (c.rarity || '').toLowerCase();
                    return num > 200 && (rar.includes('alternate') || rar.includes('secret') || rar.includes('ultra rare'));
                })
                .filter(c => !chaseCards.some(cc => cc.id === c.id));

            console.log(`Evolving Skies - Found ${highNumberAlts.length} high-numbered alt arts:`, highNumberAlts.map(c => `${c.name} #${c.number} (${c.rarity})`));

            if (highNumberAlts.length > 0) {
                console.log(`Adding ${highNumberAlts.length} high-numbered alt arts that were missed`);
                chaseCards = [...chaseCards.slice(0, 50 - highNumberAlts.length), ...highNumberAlts];
            }

            // Ensure Umbreon VMAX and Rayquaza VMAX are in the list
            const mustHaveCards = cards.filter(c => {
                const n = (c.name || '').toLowerCase();
                return (n.includes('umbreon') && n.includes('vmax')) ||
                       (n.includes('rayquaza') && n.includes('vmax'));
            });

            mustHaveCards.forEach(mustHave => {
                if (!chaseCards.some(cc => cc.id === mustHave.id)) {
                    console.log(`Force-adding missing chase card: ${mustHave.name} #${mustHave.number}`);
                    chaseCards.unshift(mustHave);
                }
            });

            chaseCards = chaseCards.slice(0, 50);
        }

        if (chaseCards.length === 0) {
            const allCards = cards.slice(0, 30);
            if (allCards.length === 0) {
                chaseGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted);">No cards found for this set</div>';
                return;
            }
            renderCardGrid(allCards, setInfo, chaseGrid);
            return;
        }

        // Calculate set value index using ALL cards with prices > $1
        const allValuableCards = cardsWithPrices.filter(item => item.price >= 1);
        const totalChaseValue = allValuableCards.reduce((sum, item) => sum + item.price, 0);
        const valueEl = document.getElementById('setValueIndex');
        if (valueEl) valueEl.textContent = '$' + totalChaseValue.toFixed(0);

        renderCardGrid(chaseCards, setInfo, chaseGrid);

    } catch (error) {
        console.error('Error in displayChaseCards:', error);
        chaseGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--red);">Error displaying cards: ${error.message}</div>`;
    }
}

// ---- Fetch population data for a card (PSA, CGC, BGS) -----------------------

async function fetchCardPopulation(cardName, cardNumber, setId) {
    try {
        const response = await fetch(`${API}/prices/card/${encodeURIComponent(cardName)}`, {
            headers: { 'Accept': 'application/json' },
            timeout: 5000
        }).catch(() => null);

        if (response?.ok) {
            const data = await response.json();
            if (data.population) {
                return data.population;
            }
        }
    } catch (e) {
        // API not available, use estimates
    }

    return null;
}

// ---- Estimate population based on card characteristics ----------------------

function estimatePopulation(card, price) {
    const rarity = (card.rarity || '').toLowerCase();
    const cardNumber = parseInt(card.number) || 0;

    let psa10 = 0, psa9 = 0, cgc10 = 0, cgc95 = 0, bgs10 = 0, bgs95 = 0;

    if (price > 500) {
        psa10 = Math.max(20, Math.floor(price / 25));
        psa9 = Math.floor(psa10 * 4);
        cgc10 = Math.max(5, Math.floor(psa10 * 0.4));
        cgc95 = Math.floor(cgc10 * 3);
        bgs10 = Math.max(3, Math.floor(psa10 * 0.25));
        bgs95 = Math.floor(bgs10 * 2);
    } else if (price > 200) {
        psa10 = Math.max(10, Math.floor(price / 20));
        psa9 = Math.floor(psa10 * 5);
        cgc10 = Math.max(3, Math.floor(psa10 * 0.5));
        cgc95 = Math.floor(cgc10 * 3.5);
        bgs10 = Math.max(2, Math.floor(psa10 * 0.3));
        bgs95 = Math.floor(bgs10 * 2.5);
    } else if (price > 50) {
        psa10 = Math.max(5, Math.floor(price / 12));
        psa9 = Math.floor(psa10 * 6);
        cgc10 = Math.max(2, Math.floor(psa10 * 0.6));
        cgc95 = Math.floor(cgc10 * 4);
        bgs10 = Math.max(1, Math.floor(psa10 * 0.4));
        bgs95 = Math.floor(bgs10 * 3);
    } else if (price > 10) {
        psa10 = Math.max(1, Math.floor(price / 8));
        psa9 = Math.floor(psa10 * 7);
        cgc10 = Math.max(0, Math.floor(psa10 * 0.7));
        cgc95 = Math.floor(cgc10 * 5);
    }

    // Boost for alt arts and secret rares
    if (rarity.includes('alternate') || rarity.includes('secret') ||
        rarity.includes('special illustration') || cardNumber > 200) {
        psa10 = Math.floor(psa10 * 1.8);
        psa9 = Math.floor(psa9 * 1.5);
        cgc10 = Math.floor(cgc10 * 1.6);
        cgc95 = Math.floor(cgc95 * 1.4);
        bgs10 = Math.floor(bgs10 * 1.5);
        bgs95 = Math.floor(bgs95 * 1.3);
    }

    return {
        PSA: { 10: psa10, 9: psa9, 8: Math.floor(psa9 * 1.8) },
        CGC: { 10: cgc10, '9.5': cgc95, 9: Math.floor(cgc95 * 1.6) },
        BGS: { 10: bgs10, '9.5': bgs95, 9: Math.floor(bgs95 * 1.7) }
    };
}

// ---- Render card grid into a container --------------------------------------

function renderCardGrid(cards, setInfo, container) {
    // Store the displayed cards for click handler access
    currentSetCards = cards;

    const fragment = document.createDocumentFragment();
    const tempDiv = document.createElement('div');

    tempDiv.innerHTML = cards.map((card, index) => {
        const price = getBestCardPrice(card);
        const cardId = card.id || '';
        const cardName = (card.name || 'Unknown').replace(/'/g, "\\'");
        const cardImage = getAssetImageOverride(card) || card.images?.small || card.images?.large || '';
        const setName = card.set?.name || setInfo?.name || '';

        return `
            <div class="card-grid-item chase-card" data-card-id="${cardId}" data-card-index="${index}"
                 onclick="showChaseCardDetail(${index})"
                 title="Click for detailed pricing">
                <img src="${cardImage}"
                     alt="${cardName}"
                     loading="lazy"
                     decoding="async"
                    onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22167%22><rect fill=%22%23171717%22 width=%22120%22 height=%22167%22/><text x=%2260%22 y=%2285%22 fill=%22%23525252%22 text-anchor=%22middle%22 font-size=%2232%22>CARD</text></svg>'">
                <div class="card-title">${cardName}</div>
                <div class="card-set">${setName}</div>
                <div class="card-price">${price > 0 ? '$' + price.toFixed(2) : 'See Price'}</div>
            </div>
        `;
    }).join('');

    while (tempDiv.firstChild) {
        fragment.appendChild(tempDiv.firstChild);
    }

    container.innerHTML = '';
    container.appendChild(fragment);
}

// ---- Display set statistics -------------------------------------------------

function displaySetStats(cards, setInfo) {
    try {
        const chaseCards = cards.filter(card => getBestCardPrice(card) >= 1);
        const prices = chaseCards.map(card => getBestCardPrice(card));
        const totalValue = prices.reduce((sum, p) => sum + p, 0);
        const avgValue = prices.length > 0 ? totalValue / prices.length : 0;
        const topValue = prices.length > 0 ? Math.max(...prices) : 0;

        // Estimate EV per pack (simplified)
        const era = getSetEra(setInfo?.series);
        const pullRates = PULL_RATES[era] || PULL_RATES['default'];
        const chaseOdds = pullRates['Ultra Rare']?.pct || pullRates['Holo Rare']?.pct || 5;
        const evPerPack = (avgValue * (chaseOdds / 100)).toFixed(2);
        const packsToHit = Math.round(100 / chaseOdds);

        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl('statTotalCards', setInfo?.total || cards.length);
        setEl('statChaseCards', chaseCards.length);
        setEl('statAvgValue', '$' + avgValue.toFixed(2));
        setEl('statTopValue', '$' + topValue.toFixed(2));
        setEl('statEvPack', '$' + evPerPack);
        setEl('statPacksToHit', '~' + packsToHit);
    } catch (error) {
        console.error('Error in displaySetStats:', error);
    }
}

// ---- Pull odds for a rarity -------------------------------------------------

function getPullOddsForRarity(rarity, pullRates) {
    const rarityLower = rarity.toLowerCase();

    if (rarityLower.includes('illustration') || rarityLower.includes('special art')) {
        return pullRates['Illustration Rare']?.odds || pullRates['Special Art Rare']?.odds || '1:45';
    }
    if (rarityLower.includes('hyper') || rarityLower.includes('secret') || rarityLower.includes('rainbow')) {
        return pullRates['Hyper Rare']?.odds || pullRates['Secret Rare']?.odds || '1:72';
    }
    if (rarityLower.includes('full art') || rarityLower.includes('alternate')) {
        return pullRates['Full Art']?.odds || pullRates['Alternate Art']?.odds || '1:36';
    }
    if (rarityLower.includes('ultra') || rarityLower.includes('double')) {
        return pullRates['Ultra Rare']?.odds || pullRates['Double Rare']?.odds || '1:18';
    }
    if (rarityLower.includes('holo') && !rarityLower.includes('reverse')) {
        return pullRates['Holo Rare']?.odds || '1:3';
    }
    if (rarityLower.includes('rare')) {
        return pullRates['Rare']?.odds || '1:3';
    }
    return '1:1';
}

// ---- Rarity category bucketing ----------------------------------------------

function getRarityCategory(rarity) {
    const rarityLower = (rarity || '').toLowerCase();

    // Illustration Rare category (SV era)
    if (rarityLower === 'illustration rare' ||
        rarityLower.includes('illustration rare')) return 'illustration';

    // Special Art category (SIR, Full Art, Secret, Hyper, Rainbow, Gold)
    if (rarityLower === 'special illustration rare' ||
        rarityLower.includes('special illustration') ||
        rarityLower.includes('secret') ||
        rarityLower.includes('hyper') ||
        rarityLower.includes('rainbow') ||
        rarityLower.includes('gold') ||
        rarityLower === 'rare ultra' ||
        rarityLower === 'rare secret' ||
        rarityLower === 'rare rainbow') return 'special';

    // Holo/Ultra category (Double Rare, Ultra Rare, V, VMAX, VSTAR, ex, GX)
    if (rarityLower === 'double rare' ||
        rarityLower === 'ultra rare' ||
        rarityLower.includes('rare holo v') ||
        rarityLower.includes('vmax') ||
        rarityLower.includes('vstar') ||
        rarityLower.includes('holo') ||
        rarityLower === 'rare' ||
        rarityLower.includes(' ex') ||
        rarityLower.includes(' gx')) return 'holo';

    return 'other';
}

// ---- Filter chase cards by rarity -------------------------------------------

function filterChaseCards(filter) {
    console.log('Filtering by:', filter);

    // Update active button
    document.querySelectorAll('.chase-filter').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.rarity === filter);
    });

    // Filter cards
    const cards = document.querySelectorAll('.chase-card');
    let shown = 0, hidden = 0;
    const categories = {};

    cards.forEach(card => {
        const cardRarity = card.dataset.rarity || 'other';
        categories[cardRarity] = (categories[cardRarity] || 0) + 1;

        if (filter === 'all') {
            card.style.display = '';
            shown++;
        } else if (cardRarity === filter) {
            card.style.display = '';
            shown++;
        } else {
            card.style.display = 'none';
            hidden++;
        }
    });

    console.log('Card categories found:', categories);
    console.log(`Filter "${filter}": ${shown} shown, ${hidden} hidden`);

    // Show message if no cards match filter
    if (shown === 0 && filter !== 'all') {
        const grid = document.getElementById('chaseCardsGrid');
        if (grid && !grid.querySelector('.no-match-msg')) {
            const msg = document.createElement('div');
            msg.className = 'no-match-msg';
            msg.style.cssText = 'grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--text-muted);';
            msg.textContent = `No "${filter}" cards found in this set. Try "All" to see all cards.`;
            grid.prepend(msg);
        }
    } else {
        document.querySelectorAll('.no-match-msg').forEach(m => m.remove());
    }
}

// ---- Show chase card detail (switches to Cards tab) -------------------------

async function showChaseCardDetail(index) {
    console.log('showChaseCardDetail called with index:', index);
    console.log('currentSetCards length:', currentSetCards?.length);

    if (!currentSetCards || !currentSetCards[index]) {
        console.error('Card not found at index:', index, 'currentSetCards:', currentSetCards?.length);
        return;
    }

    let card = currentSetCards[index];
    console.log('Opening card detail for:', card.name);

    // Switch to the Cards tab
    switchSection('card');

    // Set up the card data
    allCardResults = [card];
    selectedCard = card;

    // Show loading in detail view
    const detail = document.getElementById('cardDetail');
    const grid = document.getElementById('cardGrid');
    const results = document.getElementById('cardResults');

    if (results) results.style.display = 'none';
    if (grid) grid.style.display = 'none';
    if (detail) detail.style.display = 'block';

    // Show loading state
    const detailName = document.getElementById('detailName');
    const detailImage = document.getElementById('detailImage');
    const detailPrices = document.getElementById('detailPrices');
    if (detailName) detailName.textContent = card.name || 'Loading...';
    if (detailImage) detailImage.src = getAssetImageOverride(card) || card.images?.large || card.images?.small || '';
    if (detailPrices) detailPrices.innerHTML = '<div class="loading"><div class="spinner"></div>Loading prices...</div>';

    // Fetch all variations of this card (same name, different sets)
    let cardVariations = [card];
    try {
        console.log('Fetching all variations of:', card.name);
        const res = await fetch(`https://api.pokemontcg.io/v2/cards?q=name:"${encodeURIComponent(card.name)}"&pageSize=30&orderBy=-set.releaseDate`);
        const data = await res.json();
        if (data.data?.length) {
            cardVariations = data.data;
            // Prefer moonbreon (215/203) if it exists in variations
            const moonbreon = cardVariations.find(c =>
                c.name?.toLowerCase().includes('umbreon') &&
                c.name?.toLowerCase().includes('vmax') &&
                (c.set?.name?.toLowerCase().includes('evolving') || c.set?.id === 'swsh6' || c.set?.id === 'swsh7') &&
                (c.number === '215' || c.number === '215/203')
            );
            if (moonbreon && card.name?.toLowerCase().includes('umbreon') && card.name?.toLowerCase().includes('vmax')) {
                card = moonbreon;
                selectedCard = moonbreon;
                allCardResults = [moonbreon];
                console.log('Preferring moonbreon (215/203) variation');
            }
            console.log('Found', cardVariations.length, 'variations');
        }
    } catch (e) {
        console.log('Variation fetch failed:', e);
    }

    // Ensure card has basic price data from TCGPlayer
    if (!card.priceData && card.tcgplayer?.prices) {
        const prices = card.tcgplayer.prices;
        card.priceData = {
            raw: {
                price: prices.holofoil?.market || prices.normal?.market || prices.reverseHolofoil?.market || 0,
                low: prices.holofoil?.low || prices.normal?.low || 0,
                high: prices.holofoil?.high || prices.normal?.high || 0
            }
        };
    }

    // Override card.images directly for moonbreon
    const moonbreonOverride = getAssetImageOverride(card);
    if (moonbreonOverride && card) {
        if (!card.images) card.images = {};
        card.images.large = moonbreonOverride;
        card.images.small = moonbreonOverride;
        if (DEBUG_MODE) console.log('[Asset Override] Directly set card.images to moonbreon URL');
    }

    // Display the card detail
    try {
        displayCardDetail(card, cardVariations);
    } catch (e) {
        console.error('Error in displayCardDetail:', e);
        if (detailPrices) {
            detailPrices.innerHTML = `<div style="grid-column: 1/-1; padding: 1rem; color: #ef4444;">Error loading prices: ${e.message}</div>`;
        }
    }

    // Fetch real graded prices asynchronously (PriceCharting can take >5s)
    const requestId = ++cardDetailRequestSeq;
    const cardRef = card;
    const variationsRef = cardVariations;
    (async () => {
        try {
            console.log('Fetching graded prices (async)...');
            const setParam = cardRef.set?.name ? `?set=${encodeURIComponent(cardRef.set.name)}` : '';
            const priceData = await api(`/prices/card/${encodeURIComponent(cardRef.name)}${setParam}`, { timeout: 25000 });
            if (requestId !== cardDetailRequestSeq || selectedCard !== cardRef) return;
            if (priceData && !priceData.error) {
                cardRef.priceData = priceData;
                displayCardDetail(cardRef, variationsRef);
            }
        } catch (e) {
            console.log('Async graded price fetch failed:', e?.message || e);
        }
    })();
}

// ---- Fetch all cards from Pokemon TCG API (for card search) -----------------

const tcgSearchCache = new Map();

async function fetchAllCardsFromTCG(name) {
    const cacheKey = name.toLowerCase();
    if (tcgSearchCache.has(cacheKey)) {
        console.log('Using cached results for:', name);
        return tcgSearchCache.get(cacheKey);
    }

    const searchName = name.replace(/[^\w\s]/g, '').trim();
    console.log('Searching Pokemon TCG API for:', searchName);

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000);

        console.log('Fetching from API...');
        const searchUrl = shouldUseProxy()
            ? `${getApiBaseUrl()}/api/tcg/cards?q=name:"${searchName}*"&pageSize=50&orderBy=-set.releaseDate`
            : `https://api.pokemontcg.io/v2/cards?q=name:"${searchName}*"&pageSize=50&orderBy=-set.releaseDate`;

        let tcgRes = await fetch(searchUrl, {
            headers: { 'Accept': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        console.log('API response status:', tcgRes.status);
        let tcgData = await tcgRes.json();
        console.log('API returned', tcgData.data?.length || 0, 'cards');

        // If no results with quotes, try without
        if (!tcgData.data?.length) {
            console.log('No results, trying without quotes...');
            const controller2 = new AbortController();
            const timeoutId2 = setTimeout(() => controller2.abort(), 30000);

            const partialUrl = shouldUseProxy()
                ? `${getApiBaseUrl()}/api/tcg/cards?q=name:${searchName}*&pageSize=50&orderBy=-set.releaseDate`
                : `https://api.pokemontcg.io/v2/cards?q=name:${searchName}*&pageSize=50&orderBy=-set.releaseDate`;

            const partialRes = await fetch(partialUrl, {
                headers: { 'Accept': 'application/json' },
                signal: controller2.signal
            });
            clearTimeout(timeoutId2);
            tcgData = await partialRes.json();
            console.log('Second attempt returned', tcgData.data?.length || 0, 'cards');
        }

        if (tcgData.data?.length > 0) {
            const rarityOrder = {
                'Special Illustration Rare': 0, 'Illustration Rare': 1, 'Secret Rare': 2,
                'Hyper Rare': 3, 'Ultra Rare': 4, 'Double Rare': 5, 'Rare Holo VMAX': 6,
                'Rare Holo V': 7, 'Rare Holo': 8, 'Rare': 9, 'Uncommon': 10, 'Common': 11
            };

            const sortedCards = tcgData.data.sort((a, b) => {
                const priceA = a.tcgplayer?.prices?.holofoil?.market || a.tcgplayer?.prices?.normal?.market || 0;
                const priceB = b.tcgplayer?.prices?.holofoil?.market || b.tcgplayer?.prices?.normal?.market || 0;
                if (priceB !== priceA) return priceB - priceA;

                const rarityA = rarityOrder[a.rarity] ?? 5;
                const rarityB = rarityOrder[b.rarity] ?? 5;
                return rarityA - rarityB;
            });

            tcgSearchCache.set(cacheKey, sortedCards);
            return sortedCards;
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            console.error('Card search timed out - API is slow');
        } else {
            console.error('Card search error:', e.message);
        }
    }

    console.log('Returning empty results');
    return [];
}

// ---- Initialize database when section is shown ------------------------------

function initDatabase() {
    console.log('initDatabase called, allSetsData.length =', allSetsData.length);
    loadAllSets();
}
