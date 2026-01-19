/**
 * History service for portfolio historical data
 */

import { BACKEND_URL } from '../config.js';

/**
 * Fetch portfolio history data
 * @param {string} period - Period: 24h, 7d, 1m, 3m, 6m, 1y, 3y
 * @param {string|null} category - Category filter (Acciones, Cripto, Fondos, Cash)
 * @param {string|null} assetId - Individual asset ID
 * @returns {Promise<Array<{date: string, value: number}>>}
 */
export async function fetchPortfolioHistory(period = '1m', category = null, assetId = null) {
    try {
        const params = new URLSearchParams({ period });
        if (category) params.append('category', category);
        if (assetId) params.append('asset_id', assetId);

        const res = await fetch(`${BACKEND_URL}/api/portfolio/history?${params}`);
        if (!res.ok) throw new Error('Failed to fetch history');

        return await res.json();
    } catch (e) {
        console.error('Error fetching portfolio history:', e);
        return [];
    }
}

/**
 * Fetch portfolio performance metrics
 * @param {string} period - Period: 24h, 7d, 1m, 3m, 6m, 1y, 3y
 * @param {string|null} category - Category filter
 * @param {string|null} assetId - Individual asset ID
 * @returns {Promise<{current_value: number, previous_value: number, change_percent: number, change_absolute: number, period: string}|null>}
 */
export async function fetchPortfolioPerformance(period = '24h', category = null, assetId = null) {
    try {
        const params = new URLSearchParams({ period });
        if (category) params.append('category', category);
        if (assetId) params.append('asset_id', assetId);

        const res = await fetch(`${BACKEND_URL}/api/portfolio/performance?${params}`);
        if (!res.ok) throw new Error('Failed to fetch performance');

        return await res.json();
    } catch (e) {
        console.error('Error fetching portfolio performance:', e);
        return null;
    }
}

/**
 * Trigger snapshot creation (for testing)
 * @returns {Promise<{success: boolean, snapshots_created: number, date: string}|null>}
 */
export async function createSnapshot() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/portfolio/snapshot`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error('Failed to create snapshot');

        return await res.json();
    } catch (e) {
        console.error('Error creating snapshot:', e);
        return null;
    }
}
