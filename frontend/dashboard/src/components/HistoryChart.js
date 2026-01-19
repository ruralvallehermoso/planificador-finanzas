/**
 * History Chart component - Line chart for portfolio evolution
 */

import { Chart, LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Legend, Tooltip } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { formatEUR, formatCurrency } from '../utils/formatters.js';
import { getDisplayCurrency, convertValue } from '../data/assets.js';

// Register Chart.js components
Chart.register(LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Legend, Tooltip);

let historyChartInstance = null;

/**
 * Create history chart container HTML
 */
export function createHistoryChartContainer() {
    return `
    <div class="history-chart-section">
        <div class="history-chart-card">
            <div class="history-chart-header">
                <h3 class="history-chart-title">Evolución del Portafolio</h3>
                <div class="history-period-buttons" id="period-buttons">
                    <button class="period-btn active" data-period="24h">24h</button>
                    <button class="period-btn" data-period="7d">7D</button>
                    <button class="period-btn" data-period="1m">1M</button>
                    <button class="period-btn" data-period="3m">3M</button>
                    <button class="period-btn" data-period="6m">6M</button>
                    <button class="period-btn" data-period="1y">1Y</button>
                    <button class="period-btn" data-period="3y">3Y</button>
                </div>
            </div>
            
            <div class="history-performance-row" id="performance-display">
                <div class="performance-main">
                    <span class="performance-value" id="perf-value">--</span>
                    <span class="performance-change" id="perf-change">--%</span>
                </div>
                <div class="performance-24h" id="perf-24h">
                    <span class="perf-24h-label">24h:</span>
                    <span class="perf-24h-value" id="perf-24h-change">--%</span>
                </div>
            </div>
            
            <div class="history-filter-row" id="history-filters">
                <select class="history-select" id="history-view-select">
                    <option value="global">Cartera Global</option>
                    <option value="Acciones">Acciones</option>
                    <option value="Cripto">Cripto</option>
                    <option value="Fondos">Fondos</option>
                    <option value="Cash">Cash</option>
                </select>
                <select class="history-select" id="history-asset-select">
                    <option value="">Todos los activos</option>
                </select>
            </div>
            
            <div class="history-chart-container">
                <canvas id="historyChart"></canvas>
            </div>
        </div>
    </div>
    `;
}

/**
 * Render the history line chart
 * @param {Array<{date: string, value: number}>} data - Historical data points
 * @param {boolean} isPositive - Whether the change is positive (for color)
 */
export function renderHistoryChart(data, isPositive = true) {
    const canvas = document.getElementById('historyChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.classList.contains('dark');

    // Destroy existing chart
    if (historyChartInstance) {
        historyChartInstance.destroy();
    }

    if (!data || data.length === 0) {
        // Show empty state
        ctx.font = '14px Inter';
        ctx.fillStyle = isDark ? '#64748b' : '#94a3b8';
        ctx.textAlign = 'center';
        ctx.fillText('No hay datos históricos disponibles', canvas.width / 2, canvas.height / 2);
        return;
    }

    const labels = data.map(d => new Date(d.date));
    const values = data.map(d => d.value);

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    if (isPositive) {
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
    } else {
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
    }

    const lineColor = isPositive ? '#10b981' : '#ef4444';

    historyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                data: values,
                borderColor: lineColor,
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: lineColor,
                pointHoverBorderColor: isDark ? '#1e293b' : '#ffffff',
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: isDark ? '#1e293b' : '#ffffff',
                    titleColor: isDark ? '#e2e8f0' : '#1e293b',
                    bodyColor: isDark ? '#cbd5e1' : '#64748b',
                    borderColor: isDark ? '#334155' : '#e2e8f0',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        title: (ctx) => {
                            const date = new Date(ctx[0].parsed.x);
                            return date.toLocaleDateString('es-ES', {
                                day: 'numeric',
                                month: 'short',
                                year: 'numeric'
                            });
                        },
                        label: (ctx) => formatCurrency(convertValue(ctx.parsed.y), getDisplayCurrency())
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'dd MMM'
                        }
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: isDark ? '#64748b' : '#94a3b8',
                        font: { size: 10 },
                        maxTicksLimit: 6
                    }
                },
                y: {
                    position: 'right',
                    grid: {
                        color: isDark ? 'rgba(51, 65, 85, 0.5)' : 'rgba(226, 232, 240, 0.5)'
                    },
                    ticks: {
                        color: isDark ? '#64748b' : '#94a3b8',
                        font: { size: 10 },
                        callback: (value) => formatCurrency(convertValue(value), getDisplayCurrency())
                    }
                }
            },
            animation: {
                duration: 500
            }
        }
    });
}

/**
 * Update performance display
 * @param {object} perf - Performance data
 * @param {object} perf24h - 24h performance data
 */
export function updatePerformanceDisplay(perf, perf24h) {
    const valueEl = document.getElementById('perf-value');
    const changeEl = document.getElementById('perf-change');
    const change24hEl = document.getElementById('perf-24h-change');

    if (perf && valueEl && changeEl) {
        const currency = getDisplayCurrency();
        valueEl.textContent = formatCurrency(convertValue(perf.current_value), currency);

        const sign = perf.change_percent >= 0 ? '+' : '';
        changeEl.textContent = `${sign}${perf.change_percent.toFixed(2)}% (${sign}${formatCurrency(convertValue(perf.change_absolute), currency)})`;
        changeEl.className = `performance-change ${perf.change_percent >= 0 ? 'positive' : 'negative'}`;
    }

    if (perf24h && change24hEl) {
        const sign = perf24h.change_percent >= 0 ? '+' : '';
        change24hEl.textContent = `${sign}${perf24h.change_percent.toFixed(2)}%`;
        change24hEl.className = `perf-24h-value ${perf24h.change_percent >= 0 ? 'positive' : 'negative'}`;
    }
}

/**
 * Populate asset selector dropdown
 * @param {Array} assets - List of assets
 * @param {string} category - Current selected category to filter
 */
export function populateAssetSelector(assets, category = null) {
    const select = document.getElementById('history-asset-select');
    if (!select) return;

    // Filter assets by category if provided
    const filteredAssets = category && category !== 'global'
        ? assets.filter(a => a.cat === category || a.category === category)
        : assets;

    // Keep first option
    select.innerHTML = '<option value="">Todos los activos</option>';

    filteredAssets.forEach(asset => {
        const option = document.createElement('option');
        option.value = asset.id;
        option.textContent = asset.name;
        select.appendChild(option);
    });
}

