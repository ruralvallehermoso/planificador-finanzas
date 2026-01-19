/**
 * Portfolio Evolution Chart - Modern hero chart for portfolio overview
 */

import { Chart, LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Legend, Tooltip } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { formatEUR, formatCurrency } from '../utils/formatters.js';
import { fetchPortfolioHistory, fetchPortfolioPerformance } from '../services/history.js';
import { getTotalValue, getDisplayCurrency, convertValue } from '../data/assets.js';

// Register Chart.js components
Chart.register(LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Legend, Tooltip);

let portfolioChart = null;

/**
 * Create portfolio evolution container HTML
 */
export function createPortfolioEvolution() {
    return `
    <div class="portfolio-evolution">
        <div class="evolution-header">
            <div class="evolution-info">
                <div class="evolution-value" id="evolution-value">--</div>
                <div class="evolution-change" id="evolution-change">--%</div>
            </div>
            <div class="evolution-periods">
                <button class="period-btn active" data-period="24h">24H</button>
                <button class="period-btn" data-period="7d">7D</button>
                <button class="period-btn" data-period="1m">1M</button>
                <button class="period-btn" data-period="3m">3M</button>
                <button class="period-btn" data-period="1y">1Y</button>
                <button class="period-btn" data-period="3y">MAX</button>
            </div>
        </div>
        <div class="evolution-chart-wrapper">
            <canvas id="portfolio-evolution-chart"></canvas>
        </div>
    </div>
    `;
}

/**
 * Setup event listeners for period buttons
 */
export function setupEvolutionListeners() {
    const buttons = document.querySelectorAll('.portfolio-evolution .period-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            buttons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const period = e.target.dataset.period;
            await renderPortfolioEvolution(period);
        });
    });
}

/**
 * Render the portfolio evolution chart
 */
export async function renderPortfolioEvolution(period = '1m') {
    console.log('📊 Rendering portfolio evolution chart for period:', period);

    const valueEl = document.getElementById('evolution-value');
    const changeEl = document.getElementById('evolution-change');
    const canvas = document.getElementById('portfolio-evolution-chart');

    if (!canvas) {
        console.warn('📊 Canvas element not found');
        return;
    }

    // Fetch data
    const [history, performance] = await Promise.all([
        fetchPortfolioHistory(period),
        fetchPortfolioPerformance(period)
    ]);

    console.log('📊 History data points:', history?.length, 'Performance:', performance);

    // Update value and change using FRONTEND current value (backend may have stale prices)
    const currentValue = getTotalValue('All');

    if (valueEl && changeEl) {
        const currency = getDisplayCurrency();
        const displayValue = convertValue(currentValue);
        valueEl.textContent = formatCurrency(displayValue, currency);

        // Calculate change using frontend's live current value vs backend's historical previous value
        if (performance && performance.previous_value > 0) {
            const changeAbsolute = currentValue - performance.previous_value;
            const changePercent = (changeAbsolute / performance.previous_value) * 100;
            const displayAbsolute = convertValue(changeAbsolute);

            const sign = changePercent >= 0 ? '+' : '';
            changeEl.textContent = `${sign}${changePercent.toFixed(2)}% (${sign}${formatCurrency(displayAbsolute, currency)})`;
            changeEl.className = `evolution-change ${changePercent >= 0 ? 'positive' : 'negative'}`;
        }
    }

    // Render chart
    if (!history || history.length === 0) {
        console.warn('No history data for portfolio evolution chart');
        return;
    }

    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.classList.contains('dark');

    // Destroy existing chart
    if (portfolioChart) {
        portfolioChart.destroy();
        portfolioChart = null;
    }

    // Build chart data from history, injecting current live value as the last point
    const labels = history.map(h => new Date(h.date));
    const values = history.map(h => h.value);

    // Add current live value as the final point (now) so chart reflects actual current state
    const now = new Date();
    labels.push(now);
    values.push(currentValue);

    // Determine color based on actual change: current value vs first historical value
    const isPositive = currentValue >= values[0];

    // Get parent height for gradient (canvas.height may be 0 initially)
    const parent = canvas.parentElement;
    const gradientHeight = parent ? parent.clientHeight : 200;

    // Create gradient using the parent's actual height
    const gradient = ctx.createLinearGradient(0, 0, 0, gradientHeight);
    if (isPositive) {
        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
        gradient.addColorStop(0.5, 'rgba(16, 185, 129, 0.1)');
        gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');
    } else {
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.4)');
        gradient.addColorStop(0.5, 'rgba(239, 68, 68, 0.1)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
    }

    const lineColor = isPositive ? '#10b981' : '#ef4444';

    console.log('📊 Creating chart - Canvas dims:', canvas.width, 'x', canvas.height, 'Parent height:', gradientHeight, 'IsPositive:', isPositive);

    try {
        portfolioChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    borderColor: lineColor,
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0, // Straight lines - no interpolation
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: lineColor,
                    pointHoverBorderColor: isDark ? '#1e293b' : '#ffffff',
                    pointHoverBorderWidth: 3
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
                        padding: 14,
                        cornerRadius: 12,
                        displayColors: false,
                        titleFont: { size: 12, weight: '500' },
                        bodyFont: { size: 16, weight: '600' },
                        callbacks: {
                            title: (items) => new Date(items[0].parsed.x).toLocaleDateString('es-ES', {
                                weekday: 'short',
                                day: 'numeric',
                                month: 'short',
                                year: 'numeric'
                            }),
                            label: (item) => formatCurrency(convertValue(item.parsed.y), getDisplayCurrency())
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            // Backend provides daily data, so always use 'day' as base unit
                            unit: period === '24h' || period === '7d' ? 'day' : 'week',
                            displayFormats: {
                                day: 'dd MMM',
                                week: 'dd MMM'
                            }
                        },
                        grid: { display: false },
                        border: { display: false },
                        ticks: {
                            color: isDark ? '#64748b' : '#94a3b8',
                            font: { size: 11 },
                            maxTicksLimit: 6
                        }
                    },
                    y: {
                        position: 'right',
                        grid: {
                            color: isDark ? 'rgba(51, 65, 85, 0.3)' : 'rgba(226, 232, 240, 0.5)',
                            drawBorder: false
                        },
                        border: { display: false },
                        ticks: {
                            color: isDark ? '#64748b' : '#94a3b8',
                            font: { size: 11 },
                            callback: (val) => formatCurrency(convertValue(val), getDisplayCurrency())
                        }
                    }
                },
                animation: {
                    duration: 600,
                    easing: 'easeOutQuart'
                }
            }
        });
        console.log('📊 Chart created successfully');
    } catch (error) {
        console.error('📊 Error creating chart:', error);
    }
}
