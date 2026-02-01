
let currentSimData = null;

/**
 * Create simulator view container HTML
 */
export function createSimulatorView() {
    return `
    <style>
      .metric-card.interactive {
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          position: relative;
          border: 1px solid transparent;
      }
      .metric-card.interactive:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
          border-color: var(--primary);
      }
      .metric-card.interactive::after {
          content: '👆 Ver detalle';
          position: absolute;
          bottom: 4px;
          right: 8px;
          font-size: 0.65rem;
          color: var(--primary);
          opacity: 0;
          transition: opacity 0.2s;
          font-weight: bold;
      }
      .metric-card.interactive:hover::after {
          opacity: 1;
      }
      
      /* Detail Modal Styles */
      .detail-section {
          margin-bottom: 20px;
          padding: 15px;
          background: var(--bg-main);
          border-radius: 8px;
      }
      .detail-row {
          display: flex;
          justify-content: space-between;
          padding: 8px 0;
          border-bottom: 1px solid var(--border-color);
      }
      .detail-row.total {
          font-weight: bold;
          border-top: 2px solid var(--border-color);
          border-bottom: double var(--border-color);
          margin-top: 10px;
          font-size: 1.1em;
      }
      .detail-explanation {
          font-size: 0.85em;
          color: var(--text-muted);
          margin-bottom: 15px;
          font-style: italic;
          line-height: 1.5;
      }
      .detail-table {
          width: 100%;
          font-size: 0.8rem;
          border-collapse: collapse;
      }
      .detail-table th {
          text-align: left;
          background: var(--bg-card);
          padding: 8px;
          position: sticky;
          top: 0;
      }
      .detail-table td {
          padding: 6px 8px;
          border-bottom: 1px solid var(--border-color);
      }
      .badge-math {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.7em;
          font-weight: bold;
          margin-right: 8px;
          width: 24px;
          text-align: center;
      }
      .bg-plus { background: #dcfce7; color: #166534; }
      .bg-minus { background: #fee2e2; color: #991b1b; }
      .bg-equals { background: #e0e7ff; color: #3730a3; }
    </style>

    <div class="simulator-container">
        <div class="simulator-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <h2 class="simulator-title">Simulador: Inversión vs Deuda <span style="font-size: 0.6em; color: #94a3b8; font-weight: normal;">(v1.9-INTERACTIVE)</span></h2>
                <p class="simulator-subtitle">Compara si es más rentable mantener tu inversión o amortizar la hipoteca.</p>
            </div>
            <button id="open-config-btn" class="btn-secondary">
                <span>⚙️</span> Configuración
            </button>
        </div>

        <div class="simulator-grid">
            <!-- Main Content: Metrics & Chart -->
            <div class="simulator-main">
                <div class="simulator-metrics">
                    <div class="metric-card">
                        <span class="metric-label">Valor Inicial Cartera</span>
                        <span class="metric-value" id="sim-portfolio-basis">--</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Valor Actual Cartera</span>
                        <span class="metric-value" id="sim-portfolio-value">--</span>
                    </div>
                    <div class="metric-card interactive" id="sim-mortgage-card">
                        <span class="metric-label">Coste Hipoteca (Intereses)</span>
                        <span class="metric-value" id="sim-mortgage-cost">--</span>
                        <div style="font-size:0.6rem; color:#64748b; margin-top:4px;">Haz clic para ver desglose</div>
                    </div>
                    <div class="metric-card interactive" id="sim-net-card">
                        <span class="metric-label">Ganancia Neta Operación</span>
                        <span class="metric-value" id="sim-net-balance">--</span>
                        <span class="metric-delta" id="sim-roi">--%</span>
                        <div style="font-size:0.6rem; color:#64748b; margin-top:4px;">Ult. Pago: <span id="sim-debug-date">--</span></div>
                    </div>
                </div>

                <div class="simulator-card chart-card">
                    <h3 class="card-title">Evolución Comparativa</h3>
                    <div class="simulator-chart-container">
                        <canvas id="simulatorChart"></canvas>
                    </div>
                </div>
                
                <div class="simulator-card table-card">
                    <h3 class="card-title">Desglose de Activos</h3>
                    <div class="simulator-table-container">
                        <table class="simulator-table" id="asset-breakdown-table">
                            <thead>
                                <tr>
                                    <th>Activo</th>
                                    <th>Tipo</th>
                                    <th>V. Inicial</th>
                                    <th>V. Actual</th>
                                    <th>Variación</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Table rows will be inserted here -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="simulator-card table-card">
                    <h3 class="card-title">Cuadro de Amortización</h3>
                    
                    <!-- New Summary Header matching PDF style -->
                    <div class="amortization-summary" style="display: flex; justify-content: space-around; margin-bottom: 20px; text-align: center; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <div style="font-size: 0.9em; color: #64748b;">💰 Total Intereses</div>
                            <div style="font-size: 1.5em; font-weight: bold;" id="amort-total-int">--</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: #64748b;">🏠 Capital</div>
                            <div style="font-size: 1.5em; font-weight: bold;" id="amort-capital">--</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: #64748b;">📅 Fin Hipoteca</div>
                            <div style="font-size: 1.5em; font-weight: bold;" id="amort-end-date">--</div>
                        </div>
                    </div>

                    <div class="simulator-table-container">
                        <table class="simulator-table" id="amortization-table">
                            <thead>
                                <tr>
                                    <th>📅 Fecha</th>
                                    <th>💳 Cuota</th>
                                    <th>📉 Int.</th>
                                    <th>📈 Amort.</th>
                                    <th>✅ Int. Pag.</th>
                                    <th>⏳ Int. Pend.</th>
                                    <th>✅ Cap. Pag.</th>
                                    <th>🏠 Deuda</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Table rows will be inserted here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Configuration Modal -->
    <div id="simulator-config-modal" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Configuración de Hipoteca</h3>
                <button id="close-modal-btn" class="close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <div class="simulator-form">
                    <div class="form-group">
                        <label for="mortgage-principal">Capital Pendiente (€)</label>
                        <input type="number" id="mortgage-principal" value="127000" step="1000">
                    </div>
                    <div class="form-group">
                        <label for="mortgage-rate">Interés Anual (%)</label>
                        <input type="number" id="mortgage-rate" value="2.5" step="0.1">
                    </div>
                    <div class="form-group">
                        <label for="mortgage-years">Plazo Restante (Años)</label>
                        <input type="number" id="mortgage-years" value="15" step="1">
                    </div>
                    <hr class="separator">
                    <div class="form-group">
                        <label for="portfolio-basis">Base de Inversión (Coste) (€)</label>
                        <input type="number" id="portfolio-basis" placeholder="Auto (Histórico)" step="1000">
                        <small>Si se deja vacío, se estima del histórico.</small>
                    </div>
                    <div class="form-group">
                        <label for="tax-rate">Impuestos Plusvalía (%)</label>
                        <input type="number" id="tax-rate" value="19" step="1">
                    </div>
                    <button id="calculate-simulator" class="btn-primary">Recalcular y Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Detail Information Modal -->
    <div id="simulator-detail-modal" class="modal-overlay">
        <div class="modal-content" style="max-width: 600px; max-height: 85vh; display: flex; flex-direction: column;">
            <div class="modal-header">
                <h3 class="modal-title" id="detail-modal-title">Detalle</h3>
                <button id="close-detail-modal-btn" class="close-btn">&times;</button>
            </div>
            <div class="modal-body" id="detail-modal-body" style="overflow-y: auto;">
                <!-- Dynamic Content -->
            </div>
        </div>
    </div>
    `;
}

/**
 * Setup listeners for simulator
 */
export function setupSimulatorListeners() {
    const btn = document.getElementById('calculate-simulator');
    if (btn) {
        btn.addEventListener('click', () => {
            updateSimulator();
            const modal = document.getElementById('simulator-config-modal');
            if (modal) modal.classList.remove('open');
        });
    }

    // Config Modal Listeners
    const openBtn = document.getElementById('open-config-btn');
    const closeBtn = document.getElementById('close-modal-btn');
    const modal = document.getElementById('simulator-config-modal');

    if (openBtn) openBtn.addEventListener('click', () => modal && modal.classList.add('open'));
    if (closeBtn) closeBtn.addEventListener('click', () => modal && modal.classList.remove('open'));
    if (modal) modal.addEventListener('click', (e) => e.target === modal && modal.classList.remove('open'));

    // Detail Modal Listeners
    const closeDetailBtn = document.getElementById('close-detail-modal-btn');
    const detailModal = document.getElementById('simulator-detail-modal');

    if (closeDetailBtn) closeDetailBtn.addEventListener('click', () => detailModal && detailModal.classList.remove('open'));
    if (detailModal) detailModal.addEventListener('click', (e) => e.target === detailModal && detailModal.classList.remove('open'));

    // Card Interaction Listeners
    const mortgageCard = document.getElementById('sim-mortgage-card');
    const netCard = document.getElementById('sim-net-card');

    if (mortgageCard) {
        mortgageCard.addEventListener('click', () => showDetailModal('mortgage'));
    }
    if (netCard) {
        netCard.addEventListener('click', () => showDetailModal('net'));
    }
}

/**
 * Show Detail Modal with specific content
 */
function showDetailModal(type) {
    if (!currentSimData) return;

    const modal = document.getElementById('simulator-detail-modal');
    const title = document.getElementById('detail-modal-title');
    const body = document.getElementById('detail-modal-body');

    if (!modal || !title || !body) return;

    if (type === 'mortgage') {
        title.textContent = "📜 Desglose Coste Hipoteca";

        // Find paid installments
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        // Use globalSchedule or currentSimData.amortization_schedule
        const paidItems = (currentSimData.amortization_schedule || [])
            .filter(item => {
                // Parse date
                let d = item.date;
                if (typeof d === "string") {
                    if (d.includes("/")) {
                        const parts = d.split("/");
                        d = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
                    } else {
                        d = new Date(d);
                    }
                }
                return d <= today;
            })
            .sort((a, b) => new Date(b.date) - new Date(a.date)); // Newest first

        const totalInterest = currentSimData.total_interest_paid;

        body.innerHTML = `
            <div class="detail-explanation">
                Este valor representa el dinero que has pagado en concepto de <b>Intereses</b> hasta la fecha. 
                <br><br>
                ⚠️ <b>Nota importante:</b> La parte del pago correspondiente a la <i>Amortización de Capital</i> NO se considera coste, ya que reduce tu deuda (es dinero que pasa de tu banco al valor de tu casa).
            </div>

            <div class="detail-section">
                <table class="detail-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th style="text-align:right">Cuota Total</th>
                            <th style="text-align:right">Interés (Coste)</th>
                            <th style="text-align:right">Amortización</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${paidItems.map(item => `
                            <tr>
                                <td>${item.date}</td>
                                <td style="text-align:right; color:#94a3b8">${formatEUR(item.payment)}</td>
                                <td style="text-align:right; font-weight:bold; color:#ef4444">${formatEUR(item.interest)}</td>
                                <td style="text-align:right; color:#10b981">${formatEUR(item.principal)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                    <tfoot>
                        <tr style="font-weight:bold; background:#f8fafc">
                            <td>TOTAL</td>
                            <td></td>
                            <td style="text-align:right; color:#ef4444">${formatEUR(totalInterest)}</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;
    }
    else if (type === 'net') {
        title.textContent = "💰 Cálculo Ganancia Neta";

        const gross = currentSimData.portfolio_value - currentSimData.portfolio_basis;
        const taxes = Math.max(0, gross * 0.19); // Approx, actually backend sends it within net_benefit logic but we can estimate or use if passed
        // Actually, backend sends: net_benefit = gross - taxes.
        // And balance = net_benefit - interest.

        // Let's reconstruct or use data if available.
        // We can infer taxes: Gross - NetBenefit = Taxes.
        const netBenefitPortfolio = currentSimData.net_benefit; // After taxes, before mortgage
        const inferredTaxes = gross - currentSimData.net_benefit;
        const interest = currentSimData.total_interest_paid;
        const finalBalance = currentSimData.balance;

        body.innerHTML = `
            <div class="detail-explanation">
                Explicación paso a paso de cómo se calcula la rentabilidad real de la operación ("Ganancia Neta").
                Se restan los impuestos y el coste de oportunidad (intereses hipoteca pagados).
            </div>

            <div class="detail-section">
                <div class="detail-row">
                    <span>Valor Actual Cartera</span>
                    <span>${formatEUR(currentSimData.portfolio_value)}</span>
                </div>
                <div class="detail-row">
                    <span>Coste Inicial (Inversión)</span>
                    <span style="color:#94a3b8">-${formatEUR(currentSimData.portfolio_basis)}</span>
                </div>
                <div class="detail-row" style="border-top:1px dashed #e2e8f0; margin-top:5px; padding-top:5px">
                    <span class="badge-math bg-plus">+</span>
                    <span>Ganancia Bruta</span>
                    <span style="font-weight:bold">${formatEUR(gross)}</span>
                </div>
                
                <div class="detail-row">
                    <span class="badge-math bg-minus">-</span>
                    <span>Impuestos (aprox 19%)</span>
                    <span style="color:#ef4444">${formatEUR(inferredTaxes)}</span>
                </div>
                <div class="detail-row">
                    <span class="badge-math bg-minus">-</span>
                    <span>Coste Hipoteca (Intereses pagados)</span>
                    <span style="color:#ef4444">${formatEUR(interest)}</span>
                </div>
                
                <div class="detail-row total">
                    <span class="badge-math bg-equals">=</span>
                    <span>GANANCIA NETA FINAL</span>
                    <span style="color:${finalBalance >= 0 ? '#10b981' : '#ef4444'}">${formatEUR(finalBalance)}</span>
                </div>
            </div>
        `;
    }

    modal.classList.add('open');
}

/**
 * Fetch data and render simulator content
 */
export async function updateSimulator() {
    const principal = parseFloat(document.getElementById('mortgage-principal').value);
    const rate = parseFloat(document.getElementById('mortgage-rate').value);
    const years = parseInt(document.getElementById('mortgage-years').value);
    const basisInput = document.getElementById('portfolio-basis').value;
    const taxRate = parseFloat(document.getElementById('tax-rate').value);

    const payload = {
        mortgage: {
            principal,
            annual_rate: rate,
            years
        },
        tax_rate: taxRate,
        start_date: "2025-11-24" // Matching user preference from Streamlit
    };

    if (basisInput) {
        payload.portfolio_basis = parseFloat(basisInput);
    }

    try {
        const response = await fetch(`${BACKEND_URL}/api/simulator/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        renderSimulatorResults(data);
    } catch (error) {
        console.error("Error updating simulator:", error);
    }
}

/**
 * Render results in the UI
 */
function renderSimulatorResults(data) {
    currentSimData = data; // Store globally

    // 1. Update Metrics
    document.getElementById('sim-portfolio-basis').textContent = formatEUR(data.portfolio_basis);
    document.getElementById('sim-portfolio-value').textContent = formatEUR(data.portfolio_value);
    document.getElementById('sim-mortgage-cost').textContent = formatEUR(data.total_interest_paid);

    const balanceEl = document.getElementById('sim-net-balance');
    const roiEl = document.getElementById('sim-roi');
    const cardEl = document.getElementById('sim-net-card');

    balanceEl.textContent = formatEUR(data.balance);
    roiEl.textContent = `${data.roi_pct > 0 ? '+' : ''}${data.roi_pct.toFixed(2)}%`;

    // Enhanced Debug Display
    const debugEl = document.getElementById('sim-debug-date');
    if (data.last_paid_date) {
        debugEl.textContent = data.last_paid_date;
        debugEl.style.color = "#10b981"; // Green
    } else {
        debugEl.innerHTML = `<span style="color:red">NULL</span> <br>Today: ${data.server_today}`;
        console.log("SIM DEBUG LOG:", data.debug_log);
    }

    // UI color styling
    if (data.is_profitable) {
        cardEl.classList.add('profitable');
        cardEl.classList.remove('not-profitable');
    } else {
        cardEl.classList.add('not-profitable');
        cardEl.classList.remove('profitable');
    }

    // 2. Render Chart (Historical)
    renderSimulatorChart(data.daily_history);

    // 3. Render Tables
    renderAssetBreakdown(data.asset_breakdown);
    renderAmortizationTable(data.amortization_schedule);
}

/**
 * Render asset breakdown table
 */
function renderAssetBreakdown(breakdown) {
    const tbody = document.querySelector('#asset-breakdown-table tbody');
    if (!tbody) return;

    // Sort by value descending
    const sorted = [...breakdown].sort((a, b) => b.current_value - a.current_value);

    tbody.innerHTML = sorted.map(a => `
        <tr>
            <td>${a.name}</td>
            <td><small>${a.category}</small></td>
            <td>${formatEUR(a.initial_value)}</td>
            <td>${formatEUR(a.current_value)}</td>
            <td class="${a.change_pct >= 0 ? 'text-success' : 'text-danger'}">
                ${a.change_pct > 0 ? '+' : ''}${a.change_pct.toFixed(2)}%
            </td>
        </tr>
    `).join('');
}

/**
 * Render comparison chart
 */
function renderSimulatorChart(history) {
    const canvas = document.getElementById('simulatorChart');
    if (!canvas) return;

    if (simulatorChartInstance) {
        simulatorChartInstance.destroy();
    }

    const isDark = document.documentElement.classList.contains('dark');

    // Format dates for labels
    const labels = history.map(h => {
        const d = new Date(h.date);
        return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
    });

    const benefitData = history.map(h => h.net_benefit);
    const interestData = history.map(h => h.interest_paid);

    const ctx = canvas.getContext('2d');

    simulatorChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Beneficio Neto Cartera',
                    data: benefitData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Coste Acumulado Hipoteca',
                    data: interestData,
                    borderColor: '#ef4444',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: isDark ? '#e2e8f0' : '#1e293b' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: isDark ? '#334155' : '#e2e8f0' },
                    ticks: {
                        color: isDark ? '#94a3b8' : '#64748b',
                        callback: (v) => formatEUR(v)
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: isDark ? '#94a3b8' : '#64748b' }
                }
            }
        }
    });
}


let globalSchedule = [];
let currentYear = new Date().getFullYear();

function renderAmortizationTable(schedule) {
    // Update global reference
    if (schedule && schedule.length > 0) {
        globalSchedule = schedule;
    } else if (globalSchedule.length > 0) {
        schedule = globalSchedule;
    } else {
        return; // No data
    }

    // Find container
    const tableContainer = document.querySelector('.simulator-table-container');
    const tbody = document.querySelector('#amortization-table tbody');
    if (!tbody || !tableContainer) return;

    // --- Update Summary Header (Only once or always? Always is fine) ---
    const totalInterest = schedule.reduce((sum, s) => sum + s.interest, 0);
    const capital = schedule[0]?.remaining_balance + schedule[0]?.principal || 127000;
    const lastRow = schedule[schedule.length - 1];
    let endDateStr = "--";

    if (lastRow && lastRow.date) {
        const dStr = String(lastRow.date);
        if (dStr.includes('/')) {
            const parts = dStr.split('/');
            if (parts.length === 3) endDateStr = `${parts[1]}/${parts[2]}`;
        } else if (dStr.includes('-')) {
            const d = new Date(dStr);
            endDateStr = `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear()}`;
        }
    }

    const elTotal = document.getElementById('amort-total-int');
    if (elTotal) elTotal.textContent = formatEUR(totalInterest);
    const elCap = document.getElementById('amort-capital');
    if (elCap) elCap.textContent = formatEUR(capital);
    const elEnd = document.getElementById('amort-end-date');
    if (elEnd) elEnd.textContent = endDateStr;


    // --- Year Selector ---
    // Extract Years
    const years = [...new Set(schedule.map(s => new Date(s.date).getFullYear()))].sort();

    // Default currentYear if not in list (e.g. mortgage starts later)
    if (!years.includes(currentYear)) {
        if (years.length > 0) currentYear = years[0];
    }

    // Check if Selector Exists
    let selector = document.getElementById('amort-year-selector');
    if (!selector) {
        selector = document.createElement('div');
        selector.id = 'amort-year-selector';
        selector.style.cssText = "display: flex; gap: 8px; overflow-x: auto; padding-bottom: 10px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0;";
        // Insert before table
        const table = document.getElementById('amortization-table');
        table.parentNode.insertBefore(selector, table);
    }

    // Render Years
    selector.innerHTML = years.map(y => {
        const isActive = (y === currentYear);
        const bg = isActive ? '#3b82f6' : '#f1f5f9';
        const color = isActive ? 'white' : '#64748b';
        return `<button onclick="window.setAmortYear(${y})" class="year-btn" style="padding: 6px 12px; border-radius: 20px; border: none; background: ${bg}; color: ${color}; cursor: pointer; font-size: 0.9em; white-space: nowrap;">${y}</button>`;
    }).join('');

    // Expose global setter
    window.setAmortYear = (y) => {
        currentYear = y;
        renderAmortizationTable(globalSchedule);
    };


    // --- Render Table for Current Year ---
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let foundNext = false;
    let nextIndex = -1;

    // Calculate global 'next' index for highlighting
    schedule.forEach((s, i) => {
        const d = new Date(s.date);
        d.setHours(0, 0, 0, 0);
        if (!foundNext && d >= today) {
            foundNext = true;
            nextIndex = i;
        }
    });

    // Filter by Year
    const filteredrows = schedule.map((s, i) => ({ ...s, globalIndex: i })).filter(s => {
        return new Date(s.date).getFullYear() === currentYear;
    });

    tbody.innerHTML = filteredrows.map(s => {
        const i = s.globalIndex;
        let rowClass = "";
        let statusIcon = "";
        const rowDate = new Date(s.date);
        rowDate.setHours(0, 0, 0, 0);

        const isPaid = (rowDate <= today);
        const isNext = (i === nextIndex);

        if (isPaid) {
            rowClass = "paid-row";
            statusIcon = "✅";
        } else if (isNext) {
            rowClass = "next-row";
            statusIcon = "👉";
        }

        let pendingInt = s.pending_interest !== undefined ? s.pending_interest : 0;

        // Inline Styles
        let style = "";
        if (rowClass === "paid-row") {
            style = "background-color: #f1f5f9; color: #94a3b8; text-decoration: line-through;";
        } else if (rowClass === "next-row") {
            style = "background-color: #ecfdf5; border-left: 4px solid #10b981; font-weight: bold; color: #0f172a;";
        }

        return `
        <tr style="${style}">
            <td>${statusIcon} ${s.date}</td>
            <td>${formatEUR(s.payment)}</td>
            <td>${formatEUR(s.interest)}</td>
            <td>${formatEUR(s.principal)}</td>
            <td class="${rowClass === 'paid-row' ? '' : 'text-success'}">${formatEUR(s.cumulative_interest)}</td>
            <td style="${rowClass === 'paid-row' ? 'text-decoration: none;' : 'color: #64748b;'}">${formatEUR(pendingInt)}</td>
            <td class="${rowClass === 'paid-row' ? '' : 'text-success'}">${formatEUR(s.cumulative_principal)}</td>
            <td style="font-weight: bold;">${formatEUR(s.remaining_balance)}</td>
        </tr>
    `}).join('');
}
