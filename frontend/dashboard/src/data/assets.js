/**
 * Asset database and state management
 * All asset data is loaded from the backend API
 */

import { BACKEND_URL } from '../config.js';

const INDEXA_ICON = 'https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://indexacapital.com&size=64';

// Icono de la deuda del Estado español. Vive en public/icons del propio bundle, así
// que BASE_URL lo resuelve solo en los dos despliegues: '/' en el de Finanzas y
// '/static/finanzas/' en el del Planificador.
const TESORO_ES_ICON = `${import.meta.env.BASE_URL}icons/bono-tesoro-es.svg`;

/**
 * Deuda del Estado español: Bonos y Obligaciones (ES0000012...) y Letras del Tesoro
 * (ES0L...). Se reconoce por el ISIN, que es el dato que identifica al emisor.
 */
function isSpanishTreasuryBond(isin) {
    if (!isin) return false;
    const code = String(isin).trim().toUpperCase();
    return code.startsWith('ES00000') || code.startsWith('ES0L');
}

/**
 * Icono de un activo. El de la deuda española no se guarda en la BD a propósito: al
 * resolverse aquí vale igual para las líneas que ya existían y para las que se creen,
 * y la ruta se ajusta sola a cada despliegue en vez de quedar congelada en un campo.
 */
function resolveAssetIcon(asset) {
    if (asset.image_url) return asset.image_url;
    // Las cuentas Indexa no guardan image_url en la BD: el icono correcto solo se
    // asigna cuando updateIndexa() consigue refrescar en vivo desde la API de Indexa.
    // Si esa llamada falla (token caducado, etc.), sin este fallback se quedan con el
    // icono genérico gris aunque sepamos que son cuentas Indexa (indexa_api=true).
    if (asset.indexa_api) return INDEXA_ICON;
    if (isSpanishTreasuryBond(asset.isin)) return TESORO_ES_ICON;
    return 'https://via.placeholder.com/64';
}


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
            isin: a.isin || null,
            api_id: a.coingecko_id || null,
            coincap_id: a.coincap_id || null,
            indexa_api: a.indexa_api || false,
            manual: a.manual || false,
            coupon_rate: a.coupon_rate || null,
            bond_start_date: a.bond_start_date || null,
            bond_maturity_date: a.bond_maturity_date || null,
            coupon_frequency: a.coupon_frequency || 1,
            img: resolveAssetIcon(a),
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
 * Update an asset's properties and persist to backend
 */
export async function updateAssetAPI(id, updates) {
    updateAsset(id, updates);
    try {
        const payload = {};
        if (updates.qty !== undefined) payload.quantity = updates.qty;
        if (updates.price !== undefined) payload.price_eur = updates.price;
        if (updates.name !== undefined) payload.name = updates.name;
        if (updates.ticker !== undefined) payload.ticker = updates.ticker;
        if (updates.cat !== undefined) payload.category = updates.cat;
        if (updates.plat !== undefined) payload.platform = updates.plat;
        if (updates.yahoo !== undefined) payload.yahoo_symbol = updates.yahoo;
        if (updates.coupon_rate !== undefined) payload.coupon_rate = updates.coupon_rate;
        if (updates.manual !== undefined) payload.manual = updates.manual;

        const res = await fetch(`${BACKEND_URL}/api/assets/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        return res.ok;
    } catch (e) {
        console.error(`Error updating asset ${id} on backend:`, e);
        return false;
    }
}

/**
 * Create a new asset and persist to backend
 */
export async function createAssetAPI(assetData) {
    try {
        const payload = {
            id: assetData.id || assetData.name.toLowerCase().replace(/[^a-z0-9]/g, '_').substring(0, 16) + '_' + Date.now().toString().slice(-4),
            name: assetData.name,
            ticker: assetData.ticker || '',
            category: assetData.cat || assetData.category,
            platform: assetData.plat || assetData.platform || '',
            quantity: parseFloat(assetData.qty || assetData.quantity || 0),
            price_eur: parseFloat(assetData.price || assetData.price_eur || 1.0),
            currency: assetData.currency || 'EUR',
            yahoo_symbol: assetData.yahoo || assetData.yahoo_symbol || null,
            isin: assetData.isin ? String(assetData.isin).trim().toUpperCase() : null,
            coingecko_id: assetData.api_id || assetData.coingecko_id || null,
            coincap_id: assetData.coincap_id || null,
            indexa_api: false,
            // Un activo con ISIN sí tiene precio automático (Börse Frankfurt), así que
            // no debe marcarse como manual aunque no tenga símbolo de Yahoo.
            manual: assetData.manual !== undefined ? assetData.manual : (assetData.cat === 'Cash' || (!assetData.yahoo && !assetData.isin)),
            coupon_rate: assetData.coupon_rate ? parseFloat(assetData.coupon_rate) : null,
            bond_start_date: assetData.bond_start_date || null,
            bond_maturity_date: assetData.bond_maturity_date || null,
            coupon_frequency: assetData.coupon_frequency ? parseInt(assetData.coupon_frequency, 10) : 1,
            image_url: assetData.img || assetData.image_url || null
        };

        const res = await fetch(`${BACKEND_URL}/api/assets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const created = await res.json();
            addAsset({
                id: created.id,
                name: created.name,
                ticker: created.ticker || '',
                cat: created.category,
                plat: created.platform || '',
                qty: created.quantity,
                price: created.price_eur,
                currency: created.currency || 'EUR',
                yahoo: created.yahoo_symbol || null,
                isin: created.isin || null,
                api_id: created.coingecko_id || null,
                coincap_id: created.coincap_id || null,
                indexa_api: created.indexa_api || false,
                manual: created.manual || false,
                coupon_rate: created.coupon_rate || null,
                bond_start_date: created.bond_start_date || null,
                bond_maturity_date: created.bond_maturity_date || null,
                coupon_frequency: created.coupon_frequency || 1,
                img: resolveAssetIcon(created),
                change24h: 0.0
            });
            return created;
        }
        return null;
    } catch (e) {
        console.error('Error creating asset on backend:', e);
        return null;
    }
}

/**
 * Delete an asset from backend and state
 */
export async function deleteAssetAPI(id) {
    removeAsset(id);
    try {
        const res = await fetch(`${BACKEND_URL}/api/assets/${id}`, {
            method: 'DELETE'
        });
        return res.ok;
    } catch (e) {
        console.error(`Error deleting asset ${id} on backend:`, e);
        return false;
    }
}

/**
 * Get assets with crypto API IDs
 */
export function getCryptoAssets() {
    return state.assets.filter(a => a.api_id && !a.manual);
}

/**
 * Get assets with Yahoo Finance tickers (stocks and bonds)
 */
export function getStockAssets() {
    return state.assets.filter(a => a.yahoo && !a.manual);
}

/**
 * Get bond/fixed income assets
 */
export function getBondAssets() {
    return state.assets.filter(a => a.cat === 'Renta Fija' || a.coupon_rate);
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
