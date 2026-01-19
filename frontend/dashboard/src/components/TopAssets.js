/**
 * Top Movers sidebar component - Shows assets with largest 24h changes
 */

import { formatEUR, formatCurrency } from '../utils/formatters.js';
import { getAssets, getDisplayCurrency, convertValue } from '../data/assets.js';

import { BACKEND_URL } from '../config.js';

/**
 * Create top assets container HTML
 */
export function createTopAssets() {
    return `
    <div class="top-assets-section">
        <h3 class="section-title">Top Movers (24h)</h3>
        <div id="top-assets-list" class="top-assets-list"></div>
    </div>
    `;
}

/**
 * Fetch 24h changes from backend
 */
async function fetch24hChanges() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/assets/changes`);
        if (!res.ok) throw new Error('Failed to fetch changes');
        return await res.json();
    } catch (e) {
        console.error('Error fetching 24h changes:', e);
        return [];
    }
}

/**
 * Render top movers list with 24h changes
 */
export async function renderTopAssets(filter) {
    const list = document.getElementById('top-assets-list');
    if (!list) return;

    // Show loading state
    list.innerHTML = '<div class="loading">Cargando...</div>';

    // Fetch 24h changes from API (for percentage changes)
    const changes = await fetch24hChanges();

    // Get live asset data from frontend
    const liveAssets = getAssets('All');

    // Create a map of live assets by ID for quick lookup
    const liveAssetMap = {};
    liveAssets.forEach(asset => {
        liveAssetMap[asset.id] = asset;
    });

    // Merge backend 24h changes with frontend live values
    const mergedData = changes.map(item => {
        const liveAsset = liveAssetMap[item.id];
        if (liveAsset) {
            // Use frontend's live price for current value
            return {
                ...item,
                current_value: liveAsset.price * liveAsset.qty
            };
        }
        return item;
    });

    // Filter by min value (1000€) and take top 20 by absolute change
    const top20 = mergedData
        .filter(item => item.current_value >= 1000)
        .slice(0, 20);

    if (top20.length === 0) {
        list.innerHTML = '<div class="no-data">Sin datos de 24h</div>';
        return;
    }

    const currency = getDisplayCurrency();

    list.innerHTML = top20.map(item => {
        const isPositive = item.change_24h_pct >= 0;
        const sign = isPositive ? '+' : '';
        const colorClass = isPositive ? 'positive' : 'negative';

        return `
        <div class="top-asset-item">
            <span class="top-asset-name">${item.name}</span>
            <div class="top-asset-values">
                <span class="top-asset-value">${formatCurrency(convertValue(item.current_value), currency)}</span>
                <span class="top-asset-pct ${colorClass}">${sign}${item.change_24h_pct.toFixed(1)}%</span>
            </div>
        </div>
        `;
    }).join('');
}

