/**
 * CoinGecko API service
 */

const API_BASE = 'https://api.coingecko.com/api/v3';

/**
 * Fetch crypto prices for multiple assets
 * @param {Array} assets - Array of asset objects with api_id property
 * @returns {Promise<Object>} - Map of api_id to price in EUR
 */
export async function fetchCryptoPrices(assets) {
    try {
        const ids = assets.map(a => a.api_id).filter(Boolean).join(',');

        if (!ids) {
            return {};
        }

        const timestamp = `&_=${Date.now()}`;
        const res = await fetch(`${API_BASE}/simple/price?ids=${ids}&vs_currencies=eur${timestamp}`);

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();

        // Convert to asset id -> price map
        const results = {};
        assets.forEach(asset => {
            if (asset.api_id && data[asset.api_id]?.eur) {
                results[asset.id] = data[asset.api_id].eur;
            }
        });

        return results;
    } catch (e) {
        console.error('Error fetching crypto prices:', e);
        return {};
    }
}
