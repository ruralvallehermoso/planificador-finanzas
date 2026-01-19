/**
 * Asset database and state management
 * All asset data is loaded from the backend API
 */

import { BACKEND_URL } from '../config.js';

// Application state - assets loaded from API
let state = {
    assets: [],
    activeFilter: 'All',
    usdToEur: 0.95,
    indexaConnected: false,
    isLoaded: false,
    displayCurrency: 'EUR' // 'EUR' or 'USD'
};

/**
 * Load all assets from the backend API
 */
export async function loadAssetsFromAPI() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/assets`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        // Map backend fields to frontend format
        state.assets = data.map(a => ({
            id: a.id,
            name: a.name,
            ticker: a.ticker || '',
            cat: a.category,
            plat: a.platform || '',
            qty: a.quantity,
            price: a.price_eur,
            currency: a.currency || 'EUR',
            yahoo: a.yahoo_symbol || null,
            api_id: a.coingecko_id || null,
            indexa_api: a.indexa_api || false,
            manual: a.manual || false,
            img: a.image_url || 'https://via.placeholder.com/64',
            change24h: a.change_24h_pct || 0.0
        }));

        state.isLoaded = true;
        console.log(`✅ Loaded ${state.assets.length} assets from API`);
        return state.assets;
    } catch (error) {
        console.error('❌ Error loading assets from API:', error);
        state.isLoaded = false;
        return [];
    }
}

/**
 * Check if assets are loaded
 */
export function isAssetsLoaded() {
    return state.isLoaded;
}

/**
 * Get all assets, optionally filtered by category
 */
export function getAssets(filter = 'All') {
    if (filter === 'All') {
        return state.assets;
    }
    return state.assets.filter(a => a.cat === filter);
}

/**
 * Get a single asset by ID
 */
export function getAssetById(id) {
    return state.assets.find(a => a.id === id);
}

/**
 * Update an asset's properties (local state only)
 */
export function updateAsset(id, updates) {
    const index = state.assets.findIndex(a => a.id === id);
    if (index !== -1) {
        state.assets[index] = { ...state.assets[index], ...updates };
    }
}

/**
 * Add a new asset (local state only)
 */
export function addAsset(asset) {
    const existingIndex = state.assets.findIndex(a => a.id === asset.id);
    if (existingIndex !== -1) {
        state.assets[existingIndex] = asset;
    } else {
        state.assets.push(asset);
    }
}

/**
 * Remove an asset by ID (local state only)
 */
export function removeAsset(id) {
    const index = state.assets.findIndex(a => a.id === id);
    if (index !== -1) {
        state.assets.splice(index, 1);
    }
}

/**
 * Get/set active filter
 */
export function getActiveFilter() {
    return state.activeFilter;
}

export function setActiveFilter(filter) {
    state.activeFilter = filter;
}

/**
 * Get/set USD to EUR rate
 */
export function getUsdToEur() {
    return state.usdToEur;
}

export function setUsdToEur(rate) {
    state.usdToEur = rate;
}

/**
 * Get/set Indexa connection status
 */
export function getIndexaConnected() {
    return state.indexaConnected;
}

export function setIndexaConnected(connected) {
    state.indexaConnected = connected;
}

/**
 * Calculate total value of assets
 */
export function getTotalValue(filter = 'All') {
    return getAssets(filter).reduce((acc, a) => acc + (a.price * a.qty), 0);
}

/**
 * Get assets with crypto API IDs
 */
export function getCryptoAssets() {
    return state.assets.filter(a => a.api_id && !a.manual);
}

/**
 * Get assets with Yahoo Finance tickers
 */
export function getStockAssets() {
    return state.assets.filter(a => a.yahoo && !a.manual);
}

/**
 * Get/set display currency (EUR or USD)
 */
export function getDisplayCurrency() {
    return state.displayCurrency;
}

export function setDisplayCurrency(currency) {
    state.displayCurrency = currency;
}

/**
 * Convert value from EUR to the current display currency
 * @param {number} valueInEur - Value in EUR
 * @returns {number} - Value in selected display currency
 */
export function convertValue(valueInEur) {
    if (state.displayCurrency === 'USD') {
        // Convert EUR to USD: divide by USD-to-EUR rate (since rate is USD→EUR)
        return valueInEur / state.usdToEur;
    }
    return valueInEur;
}
