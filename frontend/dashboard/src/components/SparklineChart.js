/**
 * Sparkline Chart component - Mini inline chart for quick visualization
 */

import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler } from 'chart.js';

// Register Chart.js components
Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler);

let sparklineInstances = {};

/**
 * Create a sparkline chart in a canvas element
 * @param {string} canvasId - Canvas element ID
 * @param {Array<number>} data - Array of values
 * @param {boolean} isPositive - Whether the trend is positive (green) or negative (red)
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 */
export function renderSparkline(canvasId, data, isPositive = true, width = 100, height = 40) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (sparklineInstances[canvasId]) {
        sparklineInstances[canvasId].destroy();
    }

    if (!data || data.length === 0) {
        return;
    }

    // Set canvas dimensions
    canvas.width = width;
    canvas.height = height;

    const lineColor = isPositive ? '#10b981' : '#ef4444';
    const fillColor = isPositive ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';

    sparklineInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                data: data,
                borderColor: lineColor,
                backgroundColor: fillColor,
                borderWidth: 1.5,
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            },
            animation: {
                duration: 300
            }
        }
    });
}

/**
 * Create sparkline HTML element
 * @param {string} id - Unique ID for the canvas
 * @param {number} width - Width in pixels
 * @param {number} height - Height in pixels
 */
export function createSparklineHtml(id, width = 100, height = 40) {
    return `<canvas id="${id}" width="${width}" height="${height}" class="sparkline-canvas"></canvas>`;
}

/**
 * Destroy a sparkline chart
 * @param {string} canvasId - Canvas element ID
 */
export function destroySparkline(canvasId) {
    if (sparklineInstances[canvasId]) {
        sparklineInstances[canvasId].destroy();
        delete sparklineInstances[canvasId];
    }
}
