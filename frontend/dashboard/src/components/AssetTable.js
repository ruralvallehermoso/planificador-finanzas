/**
 * Asset Table component
 */

import { formatEUR, formatPrice, formatCurrency, formatPriceCurrency } from '../utils/formatters.js';
import { getAssets, getIndexaConnected, getTotalValue, getDisplayCurrency, convertValue } from '../data/assets.js';

/**
 * Create asset table HTML
 */
export function createAssetTable() {
    return `
    <div class="asset-table-container">
        <div class="table-header-row">
            <h2 class="table-title" id="list-title">Cartera de Activos</h2>
            <div class="table-meta">
                <span id="asset-count">0</span> items<br>
                <span id="usd-rate" class="usd-rate">USD: ...</span>
            </div>
        </div>

        <div class="table-card">
            <div class="table-card-scroll">
                <table class="asset-table">
                    <thead>
                        <tr>
                            <th>Activo</th>
                            <th class="text-center">Tipo</th>
                            <th class="text-right">Peso (%)</th>
                            <th class="text-right">Precio</th>
                            <th class="text-right">24h %</th>
                            <th class="text-right">Total</th>
                        </tr>
                    </thead>
                    <tbody id="asset-table-body"></tbody>
                </table>
            </div>
        </div>
    </div>
    `;
}

/**
 * Render asset rows
 */
export function renderAssetTable(filter, onEdit) {
    const tbody = document.getElementById('asset-table-body');
    const countEl = document.getElementById('asset-count');

    if (!tbody) return;

    const assets = getAssets(filter);
    const total = getTotalValue(filter);
    const indexaConnected = getIndexaConnected();
    const currency = getDisplayCurrency();

    // Update count
    if (countEl) countEl.textContent = assets.length;

    // Sort by value descending
    const sorted = [...assets].sort((a, b) => (b.price * b.qty) - (a.price * a.qty));

    tbody.innerHTML = sorted.map(item => {
        const totalVal = item.price * item.qty;
        const percent = total > 0 ? ((totalVal / total) * 100).toFixed(1) : 0;
        const change24h = item.change24h || 0;

        // Animation class for price changes
        let animClass = '';
        if (item.lastRenderedPrice && item.price !== item.lastRenderedPrice) {
            animClass = item.price > item.lastRenderedPrice ? 'animate-up' : 'animate-down';
        }
        item.lastRenderedPrice = item.price;

        // Badge HTML
        const badge = getBadgeHtml(item, indexaConnected);

        // Icon HTML
        const iconHtml = getIconHtml(item);

        // Color classes
        const colorClass = change24h > 0 ? 'text-green' : (change24h < 0 ? 'text-red' : '');
        const formatChange = change24h > 0 ? `+${change24h.toFixed(2)}%` : `${change24h.toFixed(2)}%`;

        return `
        <tr class="asset-row" data-id="${item.id}">
            <td class="cell-asset">
                <div class="asset-info">
                    ${iconHtml}
                    <div class="asset-name">${item.name}</div>
                </div>
            </td>
            <td class="cell-type">
                <div class="type-label">${item.cat}</div>
                ${badge}
            </td>
            <td class="cell-weight">
                <div class="weight-value">${percent}%</div>
                <div class="weight-bar">
                    <div class="weight-fill" style="width: ${Math.min(parseFloat(percent) * 3, 100)}%"></div>
                </div>
            </td>
            <td class="cell-price ${animClass}">
                <div class="price-value">${formatPriceCurrency(convertValue(item.price), currency)}</div>
                <div class="qty-value">${item.qty < 10 ? item.qty.toFixed(4) : item.qty.toFixed(0)} un.</div>
            </td>
            <td class="cell-change ${colorClass} text-right">
                <div class="change-value">${formatChange}</div>
            </td>
            <td class="cell-total">
                <div class="total-value ${colorClass}">${formatCurrency(convertValue(totalVal), currency)}</div>
            </td>
        </tr>
        `;
    }).join('');

    // Add click handlers for editable items
    if (onEdit) {
        tbody.querySelectorAll('.badge-editable').forEach(badge => {
            badge.addEventListener('click', (e) => {
                e.stopPropagation();
                onEdit(badge.dataset.id);
            });
        });
    }
}

/**
 * Get badge HTML for an asset
 */
function getBadgeHtml(item, indexaConnected) {
    if (item.indexa_api) {
        return `<span class="badge badge-live">${indexaConnected ? 'LIVE' : 'OFFLINE'}</span>`;
    }
    if (item.manual) {
        return `<span class="badge badge-manual badge-editable" data-id="${item.id}">EDIT</span>`;
    }
    if (item.api_id) {
        return `<span class="badge badge-live badge-editable" data-id="${item.id}">CRYPTO</span>`;
    }
    if (item.yahoo) {
        return `<span class="badge badge-stock badge-editable" data-id="${item.id}">STOCK</span>`;
    }
    return `<span class="badge badge-manual badge-editable" data-id="${item.id}">MANUAL</span>`;
}

/**
 * Get icon HTML for an asset
 */
function getIconHtml(item) {
    const tickerLabel = (item.ticker || '???').substring(0, 3);

    if (item.img) {
        return `
            <img src="${item.img}" class="asset-icon" 
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
            <div class="asset-icon-fallback" style="display:none">${tickerLabel}</div>
        `;
    }
    return `<div class="asset-icon-fallback">${tickerLabel}</div>`;
}

/**
 * Update USD rate display
 */
export function updateUsdRate(rate) {
    const el = document.getElementById('usd-rate');
    if (el) {
        el.textContent = `USD: ${rate.toFixed(4)}`;
    }
}
