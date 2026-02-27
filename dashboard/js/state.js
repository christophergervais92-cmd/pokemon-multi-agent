// PokeAgent - Shared Global State

// Card lookup state
let allCardResults = [];
let selectedCard = null;
let allVariations = [];
let cardDetailRequestSeq = 0;

// Chart state
let currentChartRange = '1M';
let currentChartGrade = 'raw';
let priceHistoryData = {};
let allGradePrices = {};
let chartContext = { data: [], xScale: null, yScale: null, padding: null, width: 0, height: 0, isUp: true };

// Database state
let allSetsData = [];
let currentSetCards = [];
let currentSetId = null;
const productImageCache = {};

// API
let API = getDefaultAPI();
let settings = optimizedLocalStorageGet('settings', {});

// Load saved API setting
if (settings.api) {
    API = settings.api;
} else {
    const savedApi = localStorage.getItem('api');
    if (savedApi) {
        API = savedApi;
        settings.api = savedApi;
        optimizedLocalStorageSet('settings', settings);
    }
}

// Live connection
let liveConnection = null;

// Request dedup
let pendingRequests = new Map();
