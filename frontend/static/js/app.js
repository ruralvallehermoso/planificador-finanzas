(() => {
  const state = {
    assets: [],
    filter: "All",
    chart: null,
    usdToEur: null,
    editTargetId: null,
  };

  const formatEUR = (n) =>
    new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(n);

  const formatPrice = (n) =>
    new Intl.NumberFormat("es-ES", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(n);

  function setThemeIcons() {
    const darkIcon = document.getElementById("theme-toggle-dark-icon");
    const lightIcon = document.getElementById("theme-toggle-light-icon");
    if (document.documentElement.classList.contains("dark")) {
      darkIcon.classList.add("hidden");
      lightIcon.classList.remove("hidden");
    } else {
      darkIcon.classList.remove("hidden");
      lightIcon.classList.add("hidden");
    }
  }

  function toggleTheme() {
    if (document.documentElement.classList.contains("dark")) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("color-theme", "light");
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("color-theme", "dark");
    }
    setThemeIcons();
    render();
  }

  function setLoading(loading) {
    const icon = document.getElementById("refresh-icon");
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    if (loading) {
      icon.classList.add("animate-spin");
      dot.className = "w-2 h-2 rounded-full bg-yellow-500 animate-pulse";
      text.innerText = "ACTUALIZANDO...";
      text.classList.add("text-yellow-500");
    } else {
      icon.classList.remove("animate-spin");
      dot.className = "w-2 h-2 rounded-full bg-emerald-500";
      text.innerText = "ACTUALIZADO";
      text.classList.remove("text-yellow-500");
      text.classList.add("text-emerald-500");
      setTimeout(() => {
        text.classList.remove("text-emerald-500");
        text.classList.add("text-slate-500");
      }, 3000);
    }
  }

  async function loadAssets() {
    const url =
      state.filter && state.filter !== "All"
        ? `/api/assets?category=${encodeURIComponent(state.filter)}`
        : "/api/assets";
    const res = await fetch(url);
    const data = await res.json();
    state.assets = data;
    render();
  }

  async function updateMarkets() {
    try {
      setLoading(true);
      const res = await fetch("/api/markets/update", { method: "POST" });
      const data = await res.json();
      if (data.usd_to_eur) {
        state.usdToEur = data.usd_to_eur;
        document.getElementById("usd-rate").innerText =
          "USD: " + state.usdToEur.toFixed(4);
      }
    } catch (e) {
      console.error("Error actualizando mercados", e);
    } finally {
      await loadAssets();
      setLoading(false);
    }
  }

  function openEditModal(id) {
    state.editTargetId = id;
    const asset = state.assets.find((a) => a.id === id);
    if (!asset) return;
    document.getElementById("manual-price").value = asset.price_eur;
    document.getElementById("manual-qty").value = asset.quantity;
    const modal = document.getElementById("editModal");
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }

  function closeEditModal() {
    const modal = document.getElementById("editModal");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    state.editTargetId = null;
  }

  async function saveManualEdit() {
    if (!state.editTargetId) return;
    const qty = parseFloat(document.getElementById("manual-qty").value);
    const price = parseFloat(document.getElementById("manual-price").value);
    await fetch(`/api/assets/${encodeURIComponent(state.editTargetId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quantity: qty,
        price_eur: price,
        manual: true,
      }),
    });
    closeEditModal();
    await loadAssets();
  }

  function render() {
    const tbody = document.getElementById("asset-table");
    tbody.innerHTML = "";
    const data = [...state.assets];

    const currentTotal = data.reduce(
      (acc, a) => acc + (a.price_eur || 0) * (a.quantity || 0),
      0
    );

    document.getElementById("total-label").innerText =
      state.filter === "All"
        ? "PATRIMONIO GLOBAL"
        : `VALOR ${state.filter.toUpperCase()}`;
    document.getElementById("global-total").innerText =
      formatEUR(currentTotal);
    document.getElementById("asset-count").innerText = data.length;

    data.sort(
      (a, b) =>
        (b.price_eur || 0) * (b.quantity || 0) -
        (a.price_eur || 0) * (a.quantity || 0)
    );

    data.forEach((item) => {
      const totalVal = (item.price_eur || 0) * (item.quantity || 0);
      const percent =
        currentTotal > 0 ? ((totalVal / currentTotal) * 100).toFixed(1) : 0;

      let badge = `<span class="text-[10px] px-2 py-0.5 rounded bg-amber-100 text-amber-700 border border-amber-200 cursor-pointer" data-edit="${item.id}">MANUAL</span>`;
      if (item.indexa_api) {
        badge =
          '<span class="text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-200">INDEXA</span>';
      } else if (item.coingecko_id) {
        badge = `<span class="text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-200 cursor-pointer" data-edit="${item.id}">CRYPTO</span>`;
      } else if (item.yahoo_symbol) {
        badge = `<span class="text-[10px] px-2 py-0.5 rounded bg-blue-100 text-blue-700 border border-blue-200 cursor-pointer" data-edit="${item.id}">STOCK</span>`;
      }

      let iconHtml = "";
      const tickerLabel = (item.ticker || "???").substring(0, 3);
      if (item.image_url) {
        iconHtml = `
          <img src="${item.image_url}" class="w-8 h-8 rounded-full bg-white p-1 object-contain" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
          <div class="w-8 h-8 rounded-lg bg-slate-700/50 hidden items-center justify-center text-[9px] font-bold text-slate-300 shrink-0 font-mono border border-slate-600/30">${tickerLabel}</div>
        `;
      } else {
        iconHtml = `
          <div class="w-8 h-8 rounded-lg bg-slate-700/50 flex items-center justify-center text-[9px] font-bold text-slate-300 shrink-0 font-mono border border-slate-600/30">${tickerLabel}</div>
        `;
      }

      const tr = document.createElement("tr");
      tr.className =
        "hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors group border-b border-slate-200 dark:border-slate-700/30 last:border-0";
      tr.innerHTML = `
        <td class="px-5 py-3.5">
          <a href="/assets/${encodeURIComponent(
            item.id
          )}" class="flex items-center gap-3">
            ${iconHtml}
            <div class="text-slate-900 dark:text-white font-semibold text-sm leading-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">${item.name}</div>
          </a>
        </td>
        <td class="px-5 py-3.5 text-center">
          <div class="text-[10px] text-slate-500 uppercase tracking-wide font-bold mb-1">${item.category}</div>
          ${badge}
        </td>
        <td class="px-5 py-3.5 text-right">
          <div class="font-mono text-xs text-indigo-600 dark:text-indigo-300 font-bold">${percent}%</div>
          <div class="h-1 w-24 ml-auto bg-slate-200 dark:bg-slate-800 rounded-full mt-1 overflow-hidden">
            <div class="h-full bg-indigo-500 opacity-50" style="width: ${Math.min(
              parseFloat(percent) * 3,
              100
            )}%"></div>
          </div>
        </td>
        <td class="px-5 py-3.5 text-right">
          <div class="mono text-sm text-slate-900 dark:text-white">${formatPrice(
            item.price_eur || 0
          )}</div>
          <div class="text-[10px] text-slate-500 dark:text-slate-600 font-mono">${
            (item.quantity || 0) < 10
              ? (item.quantity || 0).toFixed(4)
              : (item.quantity || 0).toFixed(0)
          } un.</div>
        </td>
        <td class="px-5 py-3.5 text-right">
          <div class="text-emerald-600 dark:text-emerald-400 font-bold text-sm mono tracking-tight">${formatEUR(
            totalVal
          )}</div>
        </td>
      `;
      tbody.appendChild(tr);
    });

    renderChart(data, currentTotal);
    renderTopList(data, currentTotal);

    // Delegación para abrir modal de edición
    tbody.querySelectorAll("[data-edit]").forEach((el) => {
      el.addEventListener("click", () => openEditModal(el.dataset.edit));
    });
  }

  function renderChart(data, total) {
    if (typeof Chart === "undefined") return;
    const canvas = document.getElementById("mainChart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let labels = [];
    let points = [];
    let colors = [];

    const vibrantPalette = [
      "#FF6384",
      "#36A2EB",
      "#FFCE56",
      "#4BC0C0",
      "#9966FF",
      "#FF9F40",
      "#42f59e",
      "#f542e6",
      "#ecf542",
      "#42e9f5",
      "#f54242",
      "#a1f542",
      "#4242f5",
      "#f5a142",
      "#42f542",
    ];

    if (state.filter === "All") {
      const groups = { Acciones: 0, Cripto: 0, Fondos: 0, Cash: 0 };
      data.forEach((i) => {
        if (groups[i.category] !== undefined) {
          groups[i.category] += (i.price_eur || 0) * (i.quantity || 0);
        }
      });
      labels = Object.keys(groups);
      points = Object.values(groups);
      colors = ["#6366f1", "#10b981", "#f59e0b", "#ec4899"];
    } else {
      const sorted = [...data].sort(
        (a, b) =>
          (b.price_eur || 0) * (b.quantity || 0) -
          (a.price_eur || 0) * (a.quantity || 0)
      );
      const top = sorted.slice(0, 10);
      const otherVal = sorted
        .slice(10)
        .reduce(
          (acc, i) => acc + (i.price_eur || 0) * (i.quantity || 0),
          0
        );
      labels = top.map((i) => i.name);
      points = top.map((i) => (i.price_eur || 0) * (i.quantity || 0));
      if (otherVal > 0) {
        labels.push("Otros");
        points.push(otherVal);
      }
      colors = labels.map(
        (_, i) => vibrantPalette[i % vibrantPalette.length]
      );
    }

    const isDark = document.documentElement.classList.contains("dark");
    if (state.chart) state.chart.destroy();
    state.chart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data: points, backgroundColor: colors, borderWidth: 0 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              boxWidth: 8,
              color: isDark ? "#94a3b8" : "#64748b",
              font: { size: 9 },
            },
          },
        },
        cutout: "70%",
        animation: { duration: 500 },
      },
    });
  }

  function renderTopList(data, total) {
    const list = document.getElementById("top-assets-list");
    list.innerHTML = "";
    const top = [...data].sort(
      (a, b) =>
        (b.price_eur || 0) * (b.quantity || 0) -
        (a.price_eur || 0) * (a.quantity || 0)
    );
    top.slice(0, 5).forEach((i) => {
      const val = (i.price_eur || 0) * (i.quantity || 0);
      const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
      const div = document.createElement("div");
      div.className =
        "flex justify-between items-center text-xs p-2 rounded bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors";
      div.innerHTML = `
        <span class="text-slate-600 dark:text-slate-300 font-medium truncate max-w-[100px]">${i.name}</span>
        <div class="text-right">
          <span class="text-slate-900 dark:text-white font-mono font-bold block">${formatEUR(
            val
          )}</span>
          <span class="text-[10px] text-indigo-500 dark:text-indigo-400 font-bold">${pct}%</span>
        </div>
      `;
      list.appendChild(div);
    });
  }

  function setupFilterButtons() {
    document.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const f = btn.dataset.filter;
        state.filter = f || "All";
        document.querySelectorAll(".filter-btn").forEach((b) => {
          b.className =
            "filter-btn px-6 py-1.5 rounded-full text-xs font-bold text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors";
        });
        let color = "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm";
        if (f === "Cripto")
          color = "bg-purple-600 text-white shadow-lg shadow-purple-500/30";
        if (f === "Acciones")
          color = "bg-blue-600 text-white shadow-lg shadow-blue-500/30";
        if (f === "Fondos")
          color = "bg-emerald-600 text-white shadow-lg shadow-emerald-500/30";
        btn.className = `filter-btn px-6 py-1.5 rounded-full text-xs font-bold transform scale-105 ${color}`;
        loadAssets();
      });
    });
  }

  function init() {
    document
      .getElementById("theme-toggle")
      .addEventListener("click", toggleTheme);
    document
      .getElementById("refresh-button")
      .addEventListener("click", updateMarkets);
    document
      .getElementById("cancel-edit")
      .addEventListener("click", closeEditModal);
    document
      .getElementById("save-edit")
      .addEventListener("click", saveManualEdit);

    setThemeIcons();
    setupFilterButtons();
    loadAssets().then(() => {
      // Pequeño delay para primera actualización de mercados (similar al HTML original)
      setTimeout(updateMarkets, 1000);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();


