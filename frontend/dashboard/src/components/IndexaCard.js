/**
 * Indexa Card component - Shows Indexa Capital accounts with sparkline charts
 */

import { formatEUR } from '../utils/formatters.js';
import { getAssets, getIndexaConnected } from '../data/assets.js';
import { renderSparkline } from './SparklineChart.js';
import { fetchPortfolioHistory } from '../services/history.js';

import { BACKEND_URL } from '../config.js';

/**
 * Create Indexa card container HTML
 */
export function createIndexaCard() {
    return `
    <div class="indexa-card" id="indexa-card">
        <div class="indexa-header">
            <div class="indexa-title-row">
                <h3 class="indexa-title">Indexa Capital</h3>
                <span class="indexa-status" id="indexa-status">--</span>
            </div>
            <div class="indexa-total" id="indexa-total">--</div>
            <div class="indexa-variation" id="indexa-variation">--%</div>
        </div>
        <div class="indexa-chart-container">
            <canvas id="indexa-sparkline" width="280" height="60"></canvas>
        </div>
        <div class="indexa-accounts" id="indexa-accounts"></div>
    </div>
    `;
}

/**
 * Fetch 24h changes for Indexa accounts from backend
 */
async function fetchIndexa24hChanges() {
    try {
        const res = await fetch(`${BACKEND_URL}/api/assets/changes?min_value=0`);
        if (!res.ok) throw new Error('Failed to fetch changes');
        const data = await res.json();
        // Filter only Indexa accounts
        return data.filter(a => a.id.startsWith('idx_'));
    } catch (e) {
        console.error('Error fetching Indexa 24h changes:', e);
        return [];
    }
}

/**
 * Render Indexa card with data
 */
export async function renderIndexaCard() {
    const statusEl = document.getElementById('indexa-status');
    const totalEl = document.getElementById('indexa-total');
    const variationEl = document.getElementById('indexa-variation');
    const accountsEl = document.getElementById('indexa-accounts');

    const connected = getIndexaConnected();
    const indexaAssets = getAssets('Fondos').filter(a => a.id && a.id.startsWith('idx_'));

    // Fetch 24h changes from backend
    const changes24h = await fetchIndexa24hChanges();
    const changesMap = {};
    changes24h.forEach(c => { changesMap[c.id] = c.change_24h_pct; });

    // Update status
    if (statusEl) {
        statusEl.textContent = connected ? 'LIVE' : 'OFFLINE';
        statusEl.className = `indexa-status ${connected ? 'live' : 'offline'}`;
    }

    // Calculate total
    const total = indexaAssets.reduce((sum, a) => sum + (a.price * a.qty), 0);
    if (totalEl) {
        totalEl.textContent = formatEUR(total);
    }

    // Calculate weighted 24h variation from API data
    let weightedVariation = 0;
    if (total > 0) {
        indexaAssets.forEach(a => {
            const value = a.price * a.qty;
            const weight = value / total;
            const change = changesMap[a.id] || 0;
            weightedVariation += change * weight;
        });
    }

    if (variationEl) {
        const sign = weightedVariation >= 0 ? '+' : '';
        variationEl.textContent = `24h: ${sign}${weightedVariation.toFixed(2)}%`;
        variationEl.className = `indexa-variation ${weightedVariation >= 0 ? 'positive' : 'negative'}`;
    }

    // Render individual accounts with 24h changes
    if (accountsEl) {
        accountsEl.innerHTML = indexaAssets.map(account => {
            const value = account.price * account.qty;
            const change24h = changesMap[account.id] || 0;
            const sign = change24h >= 0 ? '+' : '';
            const varClass = change24h >= 0 ? 'positive' : 'negative';

            return `
            <div class="indexa-account-item">
                <div class="indexa-account-info">
                    <div class="indexa-account-name">${account.name}</div>
                </div>
                <div class="indexa-account-values">
                    <div class="indexa-account-value">${formatEUR(value)}</div>
                    <div class="indexa-account-var ${varClass}">${sign}${change24h.toFixed(2)}%</div>
                </div>
            </div>
            `;
        }).join('');
    }

    // Fetch and render sparkline
    try {
        const history = await fetchPortfolioHistory('1m', 'Fondos', null);
        if (history && history.length > 0) {
            const values = history.map(h => h.value);
            const isPositive = values[values.length - 1] >= values[0];
            renderSparkline('indexa-sparkline', values, isPositive, 280, 60);
        }
    } catch (e) {
        console.error('Error rendering Indexa sparkline:', e);
    }
}
