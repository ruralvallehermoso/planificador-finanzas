/**
 * Yahoo Finance API service
 */

const CORS_PROXY = 'https://corsproxy.io/?';

/**
 * Fetch USD to EUR exchange rate
 */
export async function fetchUsdEurRate() {
    try {
        const timestamp = `&_=${Date.now()}`;
        const url = CORS_PROXY + encodeURIComponent('https://query1.finance.yahoo.com/v8/finance/chart/EUR=X?interval=1d&range=1d') + timestamp;
        const res = await fetch(url);

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        const rate = data.chart?.result?.[0]?.meta?.regularMarketPrice;

        if (rate) {
            return rate;
        }
        throw new Error('Invalid response structure');
    } catch (e) {
        console.error('Error fetching USD/EUR rate:', e);
        return null;
    }
}

/**
 * Fetch stock price for a single ticker
 */
export async function fetchStockPrice(ticker) {
    try {
        const timestamp = `&_=${Date.now()}`;
        const url = CORS_PROXY + encodeURIComponent(`https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=1d&range=1d`) + timestamp;
        const res = await fetch(url);

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        const price = data.chart?.result?.[0]?.meta?.regularMarketPrice;

        if (price > 0) {
            return price;
        }
        return null;
    } catch (e) {
        console.error(`Error fetching stock ${ticker}:`, e);
        return null;
    }
}

/**
 * Fetch prices for multiple stocks
 * @param {Array} assets - Array of asset objects with yahoo property
 * @param {number} usdToEur - USD to EUR conversion rate
 * @returns {Promise<Object>} - Map of asset id to price in EUR
 */
export async function fetchStockPrices(assets, usdToEur) {
    const results = {};

    // Los bonos de Renta Fija no se recalculan aquí: el backend (market_client.py,
    // llamado vía /api/update_markets en cada carga) ya calcula su precio de forma
    // consistente — precio de mercado real si el ticker resuelve a una cotización, o
    // valor a la par + interés simple devengado desde el alta si no. Tener esa misma
    // lógica duplicada en el cliente hacía que ambos cálculos pudieran divergir entre
    // sí, y el valor mostrado dependiera de cuál terminara último.
    const promises = assets.map(async (asset) => {
        const isBond = asset.cat === 'Renta Fija' || (asset.coupon_rate && asset.coupon_rate > 0);
        if (isBond || !asset.yahoo) return;

        const price = await fetchStockPrice(asset.yahoo);
        if (price !== null) {
            results[asset.id] = asset.currency === 'USD' ? price * usdToEur : price;
        }
    });

    await Promise.all(promises);
    return results;
}
