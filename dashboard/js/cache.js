// PokeAgent - Cache Layer (Memory + IndexedDB)
// =============================================================================
// Provides image, price, card data, and API response caching via IndexedDB.
// Depends on globals: DB_NAME, DB_VERSION (from config.js)
// =============================================================================

let cache = new Map();
let db = null;

// ---------------------------------------------------------------------------
// IndexedDB initialization
// ---------------------------------------------------------------------------
async function initIndexedDB() {
    if (!('indexedDB' in window)) {
        console.warn('IndexedDB not supported, using localStorage fallback');
        return null;
    }

    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };

        request.onupgradeneeded = (event) => {
            const database = event.target.result;

            // Object stores
            if (!database.objectStoreNames.contains('images')) {
                database.createObjectStore('images', { keyPath: 'id' });
            }
            if (!database.objectStoreNames.contains('prices')) {
                const priceStore = database.createObjectStore('prices', { keyPath: 'id' });
                priceStore.createIndex('cardName', 'cardName', { unique: false });
                priceStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
            if (!database.objectStoreNames.contains('cardData')) {
                const cardStore = database.createObjectStore('cardData', { keyPath: 'id' });
                cardStore.createIndex('name', 'name', { unique: false });
            }
            if (!database.objectStoreNames.contains('apiCache')) {
                database.createObjectStore('apiCache', { keyPath: 'key' });
            }
        };
    });
}

// ---------------------------------------------------------------------------
// Image store/get
// ---------------------------------------------------------------------------
async function storeImage(id, imageUrl) {
    if (!db) return;
    try {
        const tx = db.transaction(['images'], 'readwrite');
        await tx.objectStore('images').put({ id, imageUrl, timestamp: Date.now() });
    } catch (e) {
        console.warn('Failed to store image in IndexedDB:', e);
    }
}

async function getImage(id) {
    if (!db) return null;
    try {
        const tx = db.transaction(['images'], 'readonly');
        const result = await tx.objectStore('images').get(id);
        return result ? result.imageUrl : null;
    } catch (e) {
        console.warn('Failed to get image from IndexedDB:', e);
        return null;
    }
}

// ---------------------------------------------------------------------------
// Price store/get
// ---------------------------------------------------------------------------
async function storePrice(cardId, cardName, grade, price, source) {
    if (!db) return;
    try {
        const tx = db.transaction(['prices'], 'readwrite');
        await tx.objectStore('prices').put({
            id: `${cardId}_${grade}`,
            cardId,
            cardName,
            grade,
            price,
            source,
            timestamp: Date.now()
        });
    } catch (e) {
        console.warn('Failed to store price in IndexedDB:', e);
    }
}

async function getPrice(cardId, grade) {
    if (!db) return null;
    try {
        const tx = db.transaction(['prices'], 'readonly');
        const result = await tx.objectStore('prices').get(`${cardId}_${grade}`);
        return result ? result.price : null;
    } catch (e) {
        return null;
    }
}

// ---------------------------------------------------------------------------
// Card data store/get
// ---------------------------------------------------------------------------
async function storeCardData(cardId, cardData) {
    if (!db) return;
    try {
        const tx = db.transaction(['cardData'], 'readwrite');
        await tx.objectStore('cardData').put({
            id: cardId,
            name: cardData.name,
            data: cardData,
            timestamp: Date.now()
        });
    } catch (e) {
        console.warn('Failed to store card data in IndexedDB:', e);
    }
}

async function getCardData(cardId) {
    if (!db) return null;
    try {
        const tx = db.transaction(['cardData'], 'readonly');
        const result = await tx.objectStore('cardData').get(cardId);
        return result ? result.data : null;
    } catch (e) {
        return null;
    }
}

// ---------------------------------------------------------------------------
// API response cache store/get
// ---------------------------------------------------------------------------
async function storeAPICache(key, data, ttl = 300000) {
    if (!db) return;
    try {
        const tx = db.transaction(['apiCache'], 'readwrite');
        await tx.objectStore('apiCache').put({
            key,
            data,
            timestamp: Date.now(),
            ttl
        });
    } catch (e) {
        console.warn('Failed to store API cache in IndexedDB:', e);
    }
}

async function getAPICache(key) {
    if (!db) return null;
    try {
        const tx = db.transaction(['apiCache'], 'readonly');
        const result = await tx.objectStore('apiCache').get(key);
        if (!result) return null;

        // Check if expired
        if (Date.now() - result.timestamp > result.ttl) {
            const deleteTx = db.transaction(['apiCache'], 'readwrite');
            deleteTx.objectStore('apiCache').delete(key);
            return null;
        }

        return result.data;
    } catch (e) {
        return null;
    }
}

// ---------------------------------------------------------------------------
// Clean old entries (run periodically)
// ---------------------------------------------------------------------------
async function cleanIndexedDB() {
    if (!db) return;
    try {
        const cutoff = Date.now() - (7 * 24 * 60 * 60 * 1000); // 7 days

        // Clean prices older than 7 days
        const priceTx = db.transaction(['prices'], 'readwrite');
        const priceIndex = priceTx.objectStore('prices').index('timestamp');
        const priceRange = IDBKeyRange.upperBound(cutoff);
        const priceCursor = await priceIndex.openCursor(priceRange);
        if (priceCursor) {
            await priceCursor.delete();
            while (priceCursor.continue()) {
                await priceCursor.delete();
            }
        }

        // Clean API cache
        const cacheTx = db.transaction(['apiCache'], 'readwrite');
        const cacheStore = cacheTx.objectStore('apiCache');
        const cacheCursor = await cacheStore.openCursor();
        if (cacheCursor) {
            do {
                if (Date.now() - cacheCursor.value.timestamp > cacheCursor.value.ttl) {
                    cacheCursor.delete();
                }
            } while (cacheCursor.continue());
        }

        console.log('IndexedDB cleanup complete');
    } catch (e) {
        console.warn('IndexedDB clean failed:', e);
    }
}
