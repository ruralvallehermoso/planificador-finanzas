/**
 * Main application entry point
 */

// Data layer
import {
    getActiveFilter,
    setUsdToEur,
    getUsdToEur,
    updateAsset,
    addAsset,
    removeAsset,
    getStockAssets,
    getCryptoAssets,
    setIndexaConnected,
    getAssets,
    getTotalValue,
    loadAssetsFromAPI
} from './data/assets.js';

// API services
import { fetchUsdEurRate, fetchStockPrices } from './services/yahoo.js';
import { fetchCryptoPrices } from './services/coingecko.js';
import { fetchIndexaAccounts } from './services/indexa.js';
import { fetchPortfolioHistory, fetchPortfolioPerformance } from './services/history.js';

// Components
import { createHeader, setupHeaderListeners, updateHeaderTotals, setLoading, renderPortfolioSparkline } from './components/Header.js';
import { createAssetTable, renderAssetTable, updateUsdRate } from './components/AssetTable.js';
import { createChartContainer, renderChart } from './components/Chart.js';
import { createTopAssets, renderTopAssets } from './components/TopAssets.js';
import { createIndexaCard, renderIndexaCard } from './components/IndexaCard.js';
import { createModal, setupModalListeners, openModal } from './components/Modal.js';
import { createPortfolioEvolution, setupEvolutionListeners, renderPortfolioEvolution } from './components/PortfolioEvolution.js';
import {
    createHistoryChartContainer,
    renderHistoryChart,
    updatePerformanceDisplay,
    populateAssetSelector
} from './components/HistoryChart.js';
import { createSimulatorView, setupSimulatorListeners, updateSimulator } from './components/Simulador.js';

// Utils
import { initTheme } from './utils/theme.js';
import { BACKEND_URL } from './config.js';

// Application state
let currentView = 'portfolio'; // 'portfolio' or 'history'
let currentPeriod = '24h';  // Must match the default active button in HistoryChart.js
let currentCategory = null;
let currentAssetId = null;

/**
 * Initialize the application
 */
async function init() {
    // Initialize theme
    initTheme();

    // Load assets from API before rendering
    await loadAssetsFromAPI();

    // Check for view parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const viewParam = urlParams.get('view');
    if (viewParam === 'simulator') {
        currentView = 'simulator';
    } else if (viewParam === 'history') {
        currentView = 'history';
    }

    // Render initial layout
    const app = document.getElementById('app');
    if (!app) return;

    app.innerHTML = `
        ${createHeader()}
        <div class="main-content">
            <div class="view-toggle" id="view-toggle">
                <button class="view-toggle-btn ${currentView === 'portfolio' ? 'active' : ''}" data-view="portfolio">Cartera</button>
                <button class="view-toggle-btn ${currentView === 'history' ? 'active' : ''}" data-view="history">Histórico</button>
                <button class="view-toggle-btn ${currentView === 'simulator' ? 'active' : ''}" data-view="simulator">Simulador</button>
            </div>
            
            <div id="portfolio-view" class="${currentView === 'portfolio' ? '' : 'hidden'}">
                <div class="main-grid">
                    <div class="left-panel">
                        ${createPortfolioEvolution()}
                        ${createAssetTable()}
                    </div>
                    <div class="right-panel">
                        ${createChartContainer()}
                        ${createTopAssets()}
                        ${createIndexaCard()}
                    </div>
                </div>
            </div>
            
            <div id="history-view" class="${currentView === 'history' ? '' : 'hidden'}">
                ${createHistoryChartContainer()}
            </div>
            
            <div id="simulator-view" class="${currentView === 'simulator' ? '' : 'hidden'}">
                ${createSimulatorView()}
            </div>
        </div>
        ${createModal()}
    `;

    // Setup event listeners
    setupHeaderListeners(updateMarkets, handleFilterChange);
    setupModalListeners(handleModalSave);
    setupViewToggle();
    setupHistoryListeners();
    setupEvolutionListeners();
    setupSimulatorListeners();

    if (currentView === 'history') {
        updateHistoryData();
    } else if (currentView === 'simulator') {
        updateSimulator();
    }

    // Show loading state immediately - don't render stale data until markets are updated
    setLoading(true);

    // Fetch market data immediately (this will call render() and renderPortfolioEvolution when done)
    updateMarkets();
}

/**
 * Setup view toggle listeners
 */
function setupViewToggle() {
    const toggleContainer = document.getElementById('view-toggle');
    if (!toggleContainer) return;

    toggleContainer.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

/**
 * Switch between portfolio and history views
 */
function switchView(view) {
    currentView = view;

    // Update toggle buttons
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Show/hide views
    const portfolioView = document.getElementById('portfolio-view');
    const historyView = document.getElementById('history-view');
    const simulatorView = document.getElementById('simulator-view');

    portfolioView.classList.add('hidden');
    historyView.classList.add('hidden');
    simulatorView.classList.add('hidden');

    if (view === 'portfolio') {
        portfolioView.classList.remove('hidden');
    } else if (view === 'history') {
        historyView.classList.remove('hidden');
        updateHistoryData();
    } else if (view === 'simulator') {
        simulatorView.classList.remove('hidden');
        updateSimulator();
    }
}

/**
 * Setup history panel listeners
 */
function setupHistoryListeners() {
    // Period buttons
    const periodButtons = document.getElementById('period-buttons');
    if (periodButtons) {
        periodButtons.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentPeriod = btn.dataset.period;

                // Update active state
                periodButtons.querySelectorAll('.period-btn').forEach(b => {
                    b.classList.toggle('active', b === btn);
                });

                updateHistoryData();
            });
        });
    }

    // View selector (category)
    const viewSelect = document.getElementById('history-view-select');
    if (viewSelect) {
        viewSelect.addEventListener('change', () => {
            const value = viewSelect.value;
            currentCategory = value === 'global' ? null : value;
            currentAssetId = null;

            // Update asset selector based on category
            populateAssetSelector(getAssets(), currentCategory);

            updateHistoryData();
        });
    }


    // Asset selector
    const assetSelect = document.getElementById('history-asset-select');
    if (assetSelect) {
        assetSelect.addEventListener('change', () => {
            currentAssetId = assetSelect.value || null;
            updateHistoryData();
        });
    }

    // Populate asset selector with current assets
    populateAssetSelector(getAssets());
}

/**
 * Update history chart and performance data
 */
async function updateHistoryData() {
    try {
        // Fetch history and performance data in parallel
        const [history, performance, perf24h] = await Promise.all([
            fetchPortfolioHistory(currentPeriod, currentCategory, currentAssetId),
            fetchPortfolioPerformance(currentPeriod, currentCategory, currentAssetId),
            fetchPortfolioPerformance('24h', currentCategory, currentAssetId)
        ]);

        // Use frontend's live current value (backend may have stale prices)
        let adjustedPerformance = performance;
        let adjustedPerf24h = perf24h;

        // Calculate current value from frontend data
        let currentValue = 0;

        if (currentAssetId) {
            // Individual asset - find it in frontend data
            const assets = getAssets('All');
            const asset = assets.find(a => a.id === currentAssetId);
            if (asset) {
                currentValue = asset.price * asset.qty;
            }
        } else if (currentCategory) {
            // Category view - sum assets in that category
            const assets = getAssets(currentCategory);
            currentValue = assets.reduce((sum, a) => sum + (a.price * a.qty), 0);
        } else {
            // Global portfolio
            currentValue = getTotalValue('All');
        }

        // Override backend's stale current_value with frontend's live value
        if (currentValue > 0) {
            // For 24h period, use the dedicated perf24h calculation for both displays
            // This ensures consistency since daily historical data doesn't have hourly granularity
            const perfForPeriod = currentPeriod === '24h' ? perf24h : performance;

            if (perfForPeriod && perfForPeriod.previous_value > 0) {
                const changeAbsolute = currentValue - perfForPeriod.previous_value;
                const changePercent = (changeAbsolute / perfForPeriod.previous_value) * 100;
                adjustedPerformance = {
                    ...perfForPeriod,
                    current_value: currentValue,
                    change_absolute: changeAbsolute,
                    change_percent: changePercent
                };
            }

            if (perf24h && perf24h.previous_value > 0) {
                const changeAbsolute24h = currentValue - perf24h.previous_value;
                const changePercent24h = (changeAbsolute24h / perf24h.previous_value) * 100;
                adjustedPerf24h = {
                    ...perf24h,
                    current_value: currentValue,
                    change_absolute: changeAbsolute24h,
                    change_percent: changePercent24h
                };
            }
        }

        // Determine if change is positive
        const isPositive = adjustedPerformance ? adjustedPerformance.change_percent >= 0 : true;

        // Inject current live value as the last point in history so chart reflects actual state
        let adjustedHistory = history || [];
        if (adjustedHistory.length > 0 && currentValue > 0) {
            // Add current value as the final data point (now)
            const now = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
            adjustedHistory = [...adjustedHistory, { date: now, value: currentValue }];
        }

        // Render chart with adjusted history
        renderHistoryChart(adjustedHistory, isPositive);

        // Update performance display
        updatePerformanceDisplay(adjustedPerformance, adjustedPerf24h);

    } catch (e) {
        console.error('Error updating history data:', e);
    }
}


/**
 * Render the UI based on current state
 */
function render() {
    const filter = getActiveFilter();

    updateHeaderTotals(filter);
    renderAssetTable(filter, openModal);
    renderChart(filter);
    renderTopAssets(filter);

    // Render portfolio sparkline and Indexa card asynchronously
    renderPortfolioSparkline(filter);
    renderIndexaCard();
}

/**
 * Handle filter change
 */
function handleFilterChange(filter) {
    render();
}

/**
 * Handle modal save
 */
function handleModalSave() {
    render();
}

/**
 * Update market data from all APIs
 */
async function updateMarkets() {
    setLoading(true);

    try {
        // 1. Fetch USD/EUR rate
        const rate = await fetchUsdEurRate();
        if (rate) {
            setUsdToEur(rate);
            updateUsdRate(rate);
        }

        // 2. Fetch stock prices
        const stockAssets = getStockAssets();
        const stockPrices = await fetchStockPrices(stockAssets, getUsdToEur());
        Object.entries(stockPrices).forEach(([id, price]) => {
            updateAsset(id, { price });
        });

        // 3. Fetch crypto prices
        const cryptoAssets = getCryptoAssets();
        const cryptoPrices = await fetchCryptoPrices(cryptoAssets);
        Object.entries(cryptoPrices).forEach(([id, price]) => {
            updateAsset(id, { price });
        });

        // 4. Fetch Indexa data
        await updateIndexa();

        // 5. Sync with backend so other apps (like Planificador) see the updated data
        try {
            fetch(`${BACKEND_URL}/api/markets/update`, { method: 'POST' }).catch(err => console.error('Error syncing with backend:', err));
        } catch (e) {
            console.error('Backend sync failed:', e);
        }

    } catch (e) {
        console.error('Error updating markets:', e);
    } finally {
        render();

        // Refresh the portfolio evolution chart with current period
        const activeBtn = document.querySelector('.portfolio-evolution .period-btn.active');
        const period = activeBtn ? activeBtn.dataset.period : '24h';
        renderPortfolioEvolution(period);

        // Refresh history view if currently visible
        const historyView = document.getElementById('history-view');
        if (historyView && !historyView.classList.contains('hidden')) {
            updateHistoryData();
        }

        // Refresh simulator view if currently visible
        const simulatorView = document.getElementById('simulator-view');
        if (simulatorView && !simulatorView.classList.contains('hidden')) {
            updateSimulator();
        }

        // Save portfolio status to shared file for Planificador to read
        try {
            const currentValue = getTotalValue('All');
            const perf24h = await fetchPortfolioPerformance('24h', null, null);
            const history = await fetchPortfolioHistory('7d', null, null);

            let changePercent = 0;
            if (perf24h && perf24h.previous_value > 0) {
                changePercent = ((currentValue - perf24h.previous_value) / perf24h.previous_value) * 100;
            }

            const historyValues = history ? history.map(h => h.value) : [];
            historyValues.push(currentValue); // Add current value as last point

            await fetch(`${BACKEND_URL}/api/portfolio/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_value: currentValue,
                    change_percent: changePercent,
                    history: historyValues,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (e) {
            console.error('Error saving portfolio status:', e);
        }

        setLoading(false);
    }
}

/**
 * Update Indexa Capital data
 */
async function updateIndexa() {
    const result = await fetchIndexaAccounts();

    if (result.success && result.accounts.length > 0) {
        setIndexaConnected(true);

        // Remove placeholder
        removeAsset('idx_1');

        // Add each account as a separate asset
        result.accounts.forEach(account => {
            addAsset({
                id: `idx_${account.account_number}`,
                name: account.name,
                ticker: 'IDX',
                cat: 'Fondos',
                plat: 'Indexa',
                qty: 1,
                price: account.market_value,
                indexa_api: true,
                risk_profile: account.risk_profile,
                variation_pct: account.variation_pct,
                img: 'https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://indexacapital.com&size=64'
            });
        });
        console.log(`✅ Indexa: ${result.accounts.length} accounts loaded (Total: ${result.totalValue.toFixed(2)}€)`);

        // Refresh history asset selector if we are in historical view
        const historyView = document.getElementById('history-view');
        if (historyView && !historyView.classList.contains('hidden')) {
            const viewSelect = document.getElementById('history-view-select');
            const category = viewSelect ? (viewSelect.value === 'global' ? null : viewSelect.value) : null;
            populateAssetSelector(getAssets(), category);
        }
    } else {

        setIndexaConnected(false);

        // Update placeholder with error
        updateAsset('idx_1', {
            name: `Indexa (${result.error})`,
            price: 0
        });
    }
}

// Start the application
document.addEventListener('DOMContentLoaded', init);
