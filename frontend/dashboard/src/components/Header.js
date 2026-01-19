/**
 * Header component
 */

import { formatEUR, formatCurrency } from '../utils/formatters.js';
import { getActiveFilter, setActiveFilter, getTotalValue, getUsdToEur, getDisplayCurrency, setDisplayCurrency, convertValue } from '../data/assets.js';
import { toggleTheme, updateThemeIcons } from '../utils/theme.js';
import { renderSparkline } from './SparklineChart.js';
import { fetchPortfolioHistory, fetchPortfolioPerformance } from '../services/history.js';

const FILTERS = ['All', 'Cripto', 'Acciones', 'Fondos'];
const FILTER_LABELS = { 'All': 'TODO', 'Cripto': 'CRIPTO', 'Acciones': 'ACCIONES', 'Fondos': 'FONDOS' };

/**
 * Create header HTML
 */
export function createHeader() {
    return `
    <div class="header-container">
        <div class="header-content">
            <div class="header-left">
                <div class="logo">
                    <svg class="logo-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                </div>
                <div class="logo-text">
                    <h1>Master Portfolio</h1>
                    <div class="status-area" id="status-area">
                        <span class="status-dot" id="status-dot"></span>
                        <span class="status-text" id="status-text">LISTO</span>
                    </div>
                </div>
            </div>

            <div class="filter-buttons" id="filter-buttons">
                ${FILTERS.map(f => `
                    <button class="filter-btn ${f === 'All' ? 'active' : ''}" data-filter="${f}">
                        ${FILTER_LABELS[f]}
                    </button>
                `).join('')}
            </div>

            <div class="header-right">
                <button class="icon-btn" id="theme-toggle" title="Cambiar Tema">
                    <svg id="theme-toggle-dark-icon" class="hidden" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
                    </svg>
                    <svg id="theme-toggle-light-icon" class="hidden" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
                            fill-rule="evenodd" clip-rule="evenodd"></path>
                    </svg>
                </button>

                <button class="icon-btn" id="refresh-btn" title="Forzar Actualización">
                    <svg id="refresh-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </button>

                <button class="icon-btn currency-toggle" id="currency-toggle" title="Cambiar Divisa">
                    <span class="currency-symbol" id="currency-symbol">€</span>
                </button>

                <div class="total-display-wrapper">
                    <canvas id="portfolio-sparkline" width="100" height="40" class="portfolio-sparkline"></canvas>
                    <div class="total-display">
                        <p class="total-label" id="total-label">PATRIMONIO GLOBAL</p>
                        <p class="total-value" id="global-total">---</p>
                        <p class="total-change" id="global-change"></p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `;
}

/**
 * Setup header event listeners
 */
export function setupHeaderListeners(onRefresh, onFilterChange) {
    // Theme toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            toggleTheme();
            // Trigger re-render for chart colors
            if (onFilterChange) onFilterChange(getActiveFilter());
        });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', onRefresh);
    }

    // Status area click
    const statusArea = document.getElementById('status-area');
    if (statusArea) {
        statusArea.addEventListener('click', onRefresh);
    }

    // Filter buttons
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.dataset.filter;
            setActiveFilter(filter);
            updateFilterButtons(filter);
            if (onFilterChange) onFilterChange(filter);
        });
    });

    // Currency toggle
    const currencyBtn = document.getElementById('currency-toggle');
    if (currencyBtn) {
        currencyBtn.addEventListener('click', () => {
            const current = getDisplayCurrency();
            const newCurrency = current === 'EUR' ? 'USD' : 'EUR';
            setDisplayCurrency(newCurrency);
            updateCurrencyIcon(newCurrency);
            // Trigger re-render to update all values
            if (onFilterChange) onFilterChange(getActiveFilter());
        });
    }

    // Initialize theme icons
    updateThemeIcons();
    // Initialize currency icon
    updateCurrencyIcon(getDisplayCurrency());
}

/**
 * Update filter button styles
 */
function updateFilterButtons(activeFilter) {
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(btn => {
        const filter = btn.dataset.filter;
        btn.classList.remove('active', 'filter-cripto', 'filter-acciones', 'filter-fondos');

        if (filter === activeFilter) {
            btn.classList.add('active');
            if (filter === 'Cripto') btn.classList.add('filter-cripto');
            if (filter === 'Acciones') btn.classList.add('filter-acciones');
            if (filter === 'Fondos') btn.classList.add('filter-fondos');
        }
    });
}

/**
 * Update header totals
 */
export function updateHeaderTotals(filter) {
    const totalLabel = document.getElementById('total-label');
    const totalValue = document.getElementById('global-total');
    const usdRate = document.getElementById('usd-rate');

    const total = getTotalValue(filter);
    const currency = getDisplayCurrency();
    const displayValue = convertValue(total);

    if (totalLabel) {
        totalLabel.textContent = filter === 'All' ? 'PATRIMONIO GLOBAL' : `VALOR ${filter.toUpperCase()}`;
    }

    if (totalValue) {
        totalValue.textContent = formatCurrency(displayValue, currency);
    }
}

/**
 * Update currency icon in header
 */
function updateCurrencyIcon(currency) {
    const symbol = document.getElementById('currency-symbol');
    if (symbol) {
        symbol.textContent = currency === 'EUR' ? '€' : '$';
    }
}

/**
 * Set loading state
 */
export function setLoading(loading) {
    const icon = document.getElementById('refresh-icon');
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');

    if (loading) {
        if (icon) icon.classList.add('spin');
        if (dot) dot.className = 'status-dot loading';
        if (text) {
            text.textContent = 'ACTUALIZANDO...';
            text.className = 'status-text loading';
        }
    } else {
        if (icon) icon.classList.remove('spin');
        if (dot) dot.className = 'status-dot online';
        if (text) {
            text.textContent = 'ACTUALIZADO';
            text.className = 'status-text online';
            setTimeout(() => {
                if (text) text.className = 'status-text';
            }, 3000);
        }
    }
}

/**
 * Render portfolio sparkline chart
 * @param {string} filter - Current filter (All, Cripto, Acciones, Fondos)
 */
export async function renderPortfolioSparkline(filter) {
    const changeEl = document.getElementById('global-change');

    try {
        // Fetch data based on filter
        const category = filter === 'All' ? null : filter;
        const [history, perf24h] = await Promise.all([
            fetchPortfolioHistory('7d', category, null),
            fetchPortfolioPerformance('24h', category, null)
        ]);

        // Get frontend's live current value
        const currentValue = getTotalValue(filter);

        // Render sparkline - add current value as last point for accuracy
        if (history && history.length > 0) {
            const values = history.map(h => h.value);
            values.push(currentValue); // Add live value as last point
            const isPositive = currentValue >= values[0];
            renderSparkline('portfolio-sparkline', values, isPositive, 100, 40);
        }

        // Update 24h change display using frontend's live value
        if (changeEl && perf24h && perf24h.previous_value > 0) {
            // Calculate change using frontend's current value vs backend's previous value
            const changeAbsolute = currentValue - perf24h.previous_value;
            const changePercent = (changeAbsolute / perf24h.previous_value) * 100;

            const sign = changePercent >= 0 ? '+' : '';
            changeEl.textContent = `24h: ${sign}${changePercent.toFixed(2)}%`;
            changeEl.className = `total-change ${changePercent >= 0 ? 'positive' : 'negative'}`;
        }
    } catch (e) {
        console.error('Error rendering portfolio sparkline:', e);
    }
}
