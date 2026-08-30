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

    const promises = assets.map(async (asset) => {
        if (!asset.yahoo) {
            if (asset.coupon_rate && asset.coupon_rate > 0) {
                const dailyRate = (asset.coupon_rate / 100) / 365;
                results[asset.id] = (asset.price || 1.0) * (1 + dailyRate);
            }
            return;
        }

        const price = await fetchStockPrice(asset.yahoo);
        const isBond = asset.cat === 'Renta Fija' || (asset.coupon_rate && asset.coupon_rate > 0);

        if (price !== null) {
            if (isBond) {
                // Los bonos manuales usan una unidad sintética (~1.0/unidad), no el precio
                // absoluto que devuelve Yahoo para el ticker. Solo se reinterpreta como
                // TIR/Yield cuando hay cupón para poder ajustarla según la duración;
                // si no hay cupón, no hay forma segura de interpretar ese número y se
                // mantiene el precio actual (nunca se multiplica la cantidad por un valor
                // ajeno a la escala de este activo, que fue lo que infló el total al añadir
                // un bono con símbolo Yahoo pero sin cupón).
                if (price > 0 && price <= 15.0 && asset.coupon_rate) {
                    const duration = 8.5;
                    const yieldDiff = (asset.coupon_rate - price) / 100;
                    const adjustedFactor = Math.max(0.8, 1.0 + duration * yieldDiff);
                    const base = (asset.price <= 10.0) ? 1.0 : 100.0;
                    results[asset.id] = Number((base * adjustedFactor).toFixed(4));
                } else if (asset.coupon_rate && asset.coupon_rate > 0) {
                    const dailyRate = (asset.coupon_rate / 100) / 365;
                    results[asset.id] = (asset.price || 1.0) * (1 + dailyRate);
                }
                // Sin cupón y sin una TIR interpretable: no se toca el precio.
            } else if (price > 5.0) {
                results[asset.id] = asset.currency === 'USD' ? price * usdToEur : price;
            } else {
                results[asset.id] = asset.currency === 'USD' ? price * usdToEur : price;
            }
        } else if (asset.coupon_rate && asset.coupon_rate > 0) {
            const dailyRate = (asset.coupon_rate / 100) / 365;
            results[asset.id] = (asset.price || 1.0) * (1 + dailyRate);
        }
    });

    await Promise.all(promises);
    return results;
}
