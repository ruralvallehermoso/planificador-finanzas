/**
 * Chart component using Chart.js
 */

import { Chart, DoughnutController, ArcElement, Legend, Tooltip } from 'chart.js';
import { getAssets } from '../data/assets.js';

// Register Chart.js components
Chart.register(DoughnutController, ArcElement, Legend, Tooltip);

let chartInstance = null;

// Vibrant color palette
const VIBRANT_PALETTE = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
    '#FF9F40', '#42f59e', '#f542e6', '#ecf542', '#42e9f5',
    '#f54242', '#a1f542', '#4242f5', '#f5a142', '#42f542'
];

const CATEGORY_COLORS = {
    'Acciones': '#6366f1',
    'Cripto': '#10b981',
    'Fondos': '#f59e0b',
    'Cash': '#ec4899'
};

/**
 * Create chart container HTML
 */
export function createChartContainer() {
    return `
    <div class="chart-section">
        <div class="chart-card">
            <div class="chart-header">
                <h3 class="chart-title" id="chart-title">Distribución</h3>
            </div>
            <div class="chart-container">
                <canvas id="mainChart"></canvas>
            </div>
        </div>
    </div>
    `;
}

/**
 * Render the doughnut chart
 */
export function renderChart(filter) {
    const canvas = document.getElementById('mainChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.classList.contains('dark');

    let labels = [];
    let data = [];
    let colors = [];

    if (filter === 'All') {
        // Show category breakdown
        const groups = { 'Acciones': 0, 'Cripto': 0, 'Fondos': 0, 'Cash': 0 };
        getAssets('All').forEach(item => {
            if (groups[item.cat] !== undefined) {
                groups[item.cat] += item.price * item.qty;
            }
        });
        labels = Object.keys(groups);
        data = Object.values(groups);
        colors = labels.map(l => CATEGORY_COLORS[l] || '#888');
    } else {
        // Show top 10 assets in category
        const assets = getAssets(filter);
        const sorted = [...assets].sort((a, b) => (b.price * b.qty) - (a.price * a.qty));
        const top = sorted.slice(0, 10);
        const otherVal = sorted.slice(10).reduce((acc, i) => acc + (i.price * i.qty), 0);

        labels = top.map(i => i.name);
        data = top.map(i => i.price * i.qty);

        if (otherVal > 0) {
            labels.push('Otros');
            data.push(otherVal);
        }

        colors = labels.map((_, i) => VIBRANT_PALETTE[i % VIBRANT_PALETTE.length]);
    }

    // Calculate percentages for labels
    const total = data.reduce((acc, val) => acc + val, 0);
    const labelsWithPercent = labels.map((label, i) => {
        const percent = ((data[i] / total) * 100).toFixed(1);
        return `${label} (${percent}%)`;
    });

    // Destroy existing chart
    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labelsWithPercent,
            datasets: [{
                data,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 8,
                        color: isDark ? '#94a3b8' : '#64748b',
                        font: { size: 9 }
                    }
                }
            },
            cutout: '70%',
            animation: { duration: 500 }
        }
    });
}
