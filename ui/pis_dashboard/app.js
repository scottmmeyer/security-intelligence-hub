const SLOW_THRESHOLD_MS = 5000;
const REQUEST_TIMEOUT_MS = 12000;
const MIN_BANNER_VISIBLE_MS = 1200;

const STATUS_LOADING = "LOADING";
const STATUS_LOADED = "LOADED";
const STATUS_SLOW = "SLOW";
const STATUS_FAILED = "FAILED";

const SECTION_DEFINITIONS = {
  inventory: {
    label: "Snapshot Inventory",
    targetIds: ["snapshotInventory"],
    loadingMessage: "Loading snapshot history...",
    slowMessage: "Snapshot history is taking longer than expected...",
  },
  timeline: {
    label: "Value Timeline",
    targetIds: ["valueTimeline"],
    loadingMessage: "Loading portfolio timeline...",
    slowMessage: "Portfolio timeline is taking longer than expected...",
  },
  latest: {
    label: "Latest Snapshot Summary",
    targetIds: ["latestSummary", "topHoldings"],
    loadingMessage: "Loading latest snapshot summary...",
    slowMessage: "Latest snapshot summary is taking longer than expected...",
  },
  health: {
    label: "Snapshot Health",
    targetIds: ["historyHealth"],
    loadingMessage: "Loading snapshot health...",
    slowMessage: "Snapshot health is taking longer than expected...",
  },
  lineageOverview: {
    label: "SIH Lineage Summary",
    targetIds: ["lineageSummary"],
    loadingMessage: "Loading lineage...",
    slowMessage: "Lineage data is taking longer than expected...",
  },
  governance: {
    label: "Snapshot Governance",
    targetIds: ["governanceSummary", "governanceTable"],
    loadingMessage: "Loading governance results...",
    slowMessage: "Governance results are taking longer than expected...",
  },
  canonical: {
    label: "Canonical Daily Portfolio State",
    targetIds: ["canonicalSummary", "canonicalTable"],
    loadingMessage: "Loading canonical portfolio state...",
    slowMessage: "Canonical portfolio state is taking longer than expected...",
  },
  latestChanges: {
    label: "Latest Changes",
    targetIds: ["latestChanges"],
    loadingMessage: "Loading latest changes...",
    slowMessage: "Latest changes are taking longer than expected...",
  },
  newPositions: {
    label: "New Positions",
    targetIds: ["newPositions"],
    loadingMessage: "Loading new positions...",
    slowMessage: "New positions are taking longer than expected...",
  },
  exitedPositions: {
    label: "Exited Positions",
    targetIds: ["exitedPositions"],
    loadingMessage: "Loading exited positions...",
    slowMessage: "Exited positions are taking longer than expected...",
  },
  increasedPositions: {
    label: "Increased Positions",
    targetIds: ["increasedPositions"],
    loadingMessage: "Loading increased positions...",
    slowMessage: "Increased positions are taking longer than expected...",
  },
  reducedPositions: {
    label: "Reduced Positions",
    targetIds: ["reducedPositions"],
    loadingMessage: "Loading reduced positions...",
    slowMessage: "Reduced positions are taking longer than expected...",
  },
  changeSummary: {
    label: "Change Summary",
    targetIds: ["changeSummaryText", "changeSummaryTable"],
    loadingMessage: "Loading change summary...",
    slowMessage: "Change summary is taking longer than expected...",
  },
  lineageMatches: {
    label: "Latest Recommendation Matches",
    targetIds: ["lineageLatestMatches"],
    loadingMessage: "Loading lineage...",
    slowMessage: "Lineage data is taking longer than expected...",
  },
  lineageUnmatched: {
    label: "Unmatched Changes",
    targetIds: ["lineageUnmatched"],
    loadingMessage: "Loading lineage...",
    slowMessage: "Lineage data is taking longer than expected...",
  },
  lineageDetail: {
    label: "Lineage Summary",
    targetIds: ["lineageKpis", "lineageSummaryTable"],
    loadingMessage: "Loading lineage...",
    slowMessage: "Lineage data is taking longer than expected...",
  },
  lineageSourceBreakdown: {
    label: "Recommendation Source Breakdown",
    targetIds: ["lineageSourceBreakdown"],
    loadingMessage: "Loading lineage...",
    slowMessage: "Lineage data is taking longer than expected...",
  },
  attributionSummary: {
    label: "Recommendation Outcome Summary",
    targetIds: ["attributionSummary"],
    loadingMessage: "Loading attribution...",
    slowMessage: "Attribution data is taking longer than expected...",
  },
  attributionWinners: {
    label: "Top Winning Recommendations",
    targetIds: ["topWinningRecommendations"],
    loadingMessage: "Loading attribution...",
    slowMessage: "Attribution data is taking longer than expected...",
  },
  attributionLosers: {
    label: "Top Losing Recommendations",
    targetIds: ["topLosingRecommendations"],
    loadingMessage: "Loading attribution...",
    slowMessage: "Attribution data is taking longer than expected...",
  },
  attributionSourcePerformance: {
    label: "Recommendation Source Performance",
    targetIds: ["recommendationSourcePerformance"],
    loadingMessage: "Loading attribution...",
    slowMessage: "Attribution data is taking longer than expected...",
  },
  benchmarkSummary: {
    label: "Benchmark Performance Summary",
    targetIds: ["benchmarkSummary"],
    loadingMessage: "Loading benchmark data...",
    slowMessage: "Benchmark data is taking longer than expected...",
  },
  benchmarkTrend: {
    label: "Portfolio vs Benchmark Trend",
    targetIds: ["benchmarkTrend"],
    loadingMessage: "Loading benchmark trend...",
    slowMessage: "Benchmark trend is taking longer than expected...",
  },
  benchmarkTopAlpha: {
    label: "Top Alpha Recommendations",
    targetIds: ["benchmarkTopAlpha"],
    loadingMessage: "Loading benchmark data...",
    slowMessage: "Benchmark data is taking longer than expected...",
  },
  benchmarkLowestAlpha: {
    label: "Lowest Alpha Recommendations",
    targetIds: ["benchmarkLowestAlpha"],
    loadingMessage: "Loading benchmark data...",
    slowMessage: "Benchmark data is taking longer than expected...",
  },
  benchmarkSourceAlpha: {
    label: "Source Alpha Rankings",
    targetIds: ["benchmarkSourceAlpha"],
    loadingMessage: "Loading benchmark data...",
    slowMessage: "Benchmark data is taking longer than expected...",
  },
  benchmarkQuality: {
    label: "Benchmark Quality Summary",
    targetIds: ["benchmarkQuality"],
    loadingMessage: "Loading benchmark quality...",
    slowMessage: "Benchmark quality is taking longer than expected...",
  },
};

const SUBSYSTEM_DEFINITIONS = {
  snapshotInventory: {
    label: "Snapshot Inventory",
    sectionKeys: ["inventory", "timeline", "latest", "health"],
  },
  governance: {
    label: "Governance",
    sectionKeys: ["governance"],
  },
  canonical: {
    label: "Canonical Daily State",
    sectionKeys: ["canonical"],
  },
  changeDetection: {
    label: "Change Detection",
    sectionKeys: ["latestChanges", "newPositions", "exitedPositions", "increasedPositions", "reducedPositions", "changeSummary"],
  },
  lineage: {
    label: "Lineage",
    sectionKeys: ["lineageOverview", "lineageMatches", "lineageUnmatched", "lineageDetail", "lineageSourceBreakdown"],
  },
  attribution: {
    label: "Performance Attribution",
    sectionKeys: ["attributionSummary", "attributionWinners", "attributionLosers", "attributionSourcePerformance"],
  },
  benchmarkAttribution: {
    label: "Benchmark Attribution",
    sectionKeys: ["benchmarkSummary", "benchmarkTrend", "benchmarkTopAlpha", "benchmarkLowestAlpha", "benchmarkSourceAlpha", "benchmarkQuality"],
  },
};

const requestCache = new Map();
const sectionStates = {};
const subsystemStates = {};
let dashboardStartedAt = 0;
let bannerHideTimerId = null;
const executiveState = {
  snapshots: [],
  timeline: [],
  latest: {},
  governanceLatest: { snapshots: [], status_counts: {} },
  governanceSummary: { total_snapshots: 0, status_counts: {} },
  canonicalLatest: { latest: {} },
  canonicalSummary: { selected_dates: 0, unselected_dates: 0, selected_status_counts: {} },
  latestChanges: { summary: null, new_positions: [], exited_positions: [], increased_positions: [], reduced_positions: [] },
  lineageLatest: { summary: null, matches: [], unmatched: [], source_breakdown: [] },
  attributionLatest: { summary: null, records: [], top_winning_recommendations: [], top_losing_recommendations: [], source_performance: [] },
  benchmarkLatest: { benchmark_symbol: "SPY", alignment_policy: "NEAREST_PRIOR_TRADING_DAY", latest_portfolio_excess_return: null, top_positive_alpha_recommendations: [], worst_negative_alpha_recommendations: [], source_alpha_ranking: [], quality: {} },
  benchmarkSeries: { benchmark_symbol: "SPY", series: [] },
};

function asCurrency(value) {
  const num = Number(value || 0);
  return Number.isFinite(num)
    ? num.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 })
    : "$0.00";
}

function asSignedCurrency(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  const abs = Math.abs(num).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  return num >= 0 ? `+${abs}` : `-${abs.replace("$", "$")}`;
}

function asInt(value) {
  const num = Number(value || 0);
  return Number.isFinite(num) ? Math.round(num).toLocaleString("en-US") : "0";
}

function asPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${num.toFixed(2)}%`;
}

function elapsedSeconds() {
  return ((Date.now() - dashboardStartedAt) / 1000).toFixed(1);
}

function formatErrorReason(error) {
  if (!error) return "Unknown error.";
  const message = error.message || String(error);
  if (message.includes("Request timeout")) {
    return "Request timed out while waiting for the server.";
  }
  return message;
}

function renderEmpty(targetId, message) {
  const node = document.getElementById(targetId);
  if (!node) return;
  node.innerHTML = `<p class="empty">${message}</p>`;
}

function renderStatusMessage(targetId, tone, headline, detail = "") {
  const node = document.getElementById(targetId);
  if (!node) return;
  const detailHtml = detail ? `<div class="status-note">${detail}</div>` : "";
  node.innerHTML = `
    <div class="status-message status-message-${tone}">
      <strong>${headline}</strong>
      ${detailHtml}
    </div>
  `;
}

function renderLoading(targetId, message) {
  renderStatusMessage(targetId, "loading", message);
}

function renderSlow(targetId, message) {
  renderStatusMessage(targetId, "slow", message, `${elapsedSeconds()}s elapsed`);
}

function renderFailure(targetId, error) {
  renderStatusMessage(targetId, "failed", "Data unavailable", formatErrorReason(error));
}

function renderTable(targetId, headers, rows) {
  const node = document.getElementById(targetId);
  if (!node) return;
  if (!rows.length) {
    node.innerHTML = '<p class="empty">No rows available.</p>';
    return;
  }
  const thead = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody>`;
  node.innerHTML = `<table>${thead}${tbody}</table>`;
}

async function loadJson(path, timeoutMs = REQUEST_TIMEOUT_MS) {
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error(`Request timeout after ${timeoutMs}ms for ${path}`)), timeoutMs);
  });
  const response = await Promise.race([
    fetch(path, { cache: "no-store" }),
    timeoutPromise,
  ]);
  if (!response.ok) {
    throw new Error(`Failed to load ${path} (HTTP ${response.status})`);
  }
  return response.json();
}

function requestJson(path) {
  if (!requestCache.has(path)) {
    requestCache.set(path, loadJson(path));
  }
  return requestCache.get(path);
}

function statusClass(status) {
  return `section-badge-${String(status || "").toLowerCase()}`;
}

function statusSymbol(status) {
  if (status === STATUS_LOADED) return "✓";
  if (status === STATUS_FAILED) return "!";
  return "⟳";
}

function aggregateStatuses(statuses) {
  if (!statuses.length) return STATUS_LOADING;
  if (statuses.every((status) => status === STATUS_LOADED)) return STATUS_LOADED;
  if (statuses.some((status) => status === STATUS_FAILED)) return STATUS_FAILED;
  if (statuses.some((status) => status === STATUS_SLOW)) return STATUS_SLOW;
  return STATUS_LOADING;
}

function ensureSectionBadges() {
  Object.keys(SECTION_DEFINITIONS).forEach((sectionKey) => {
    const panel = document.querySelector(`[data-section-key="${sectionKey}"]`);
    if (!panel) return;
    const heading = panel.querySelector("h2");
    if (!heading) return;
    heading.classList.add("section-heading");
    let badge = panel.querySelector(".section-badge");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "section-badge section-badge-loading";
      badge.dataset.sectionBadge = sectionKey;
      badge.textContent = STATUS_LOADING;
      heading.appendChild(badge);
    }
  });
}

function renderDashboardStatusPanel() {
  const node = document.getElementById("dashboardStatusPanel");
  if (!node) return;

  const statuses = Object.values(subsystemStates);
  const anyFailed = statuses.some((status) => status === STATUS_FAILED);
  const anySlow = statuses.some((status) => status === STATUS_SLOW);
  const allLoaded = statuses.length > 0 && statuses.every((status) => status === STATUS_LOADED);
  const overallLabel = anyFailed || anySlow ? "⚠ Degraded" : allLoaded ? "✓ Healthy" : "⟳ Loading";
  const overallClass = anyFailed || anySlow ? "section-badge-slow" : allLoaded ? "section-badge-loaded" : "section-badge-loading";

  const rows = Object.entries(SUBSYSTEM_DEFINITIONS).map(([key, config]) => {
    const status = subsystemStates[key] || STATUS_LOADING;
    return `
      <li class="dashboard-status-item">
        <span class="dashboard-status-label">${statusSymbol(status)} ${config.label}</span>
        <span class="section-badge ${statusClass(status)}">${status}</span>
      </li>
    `;
  }).join("");

  node.innerHTML = `
    <div class="dashboard-status-header">
      <div>
        <h2>System Status</h2>
        <p class="subtitle">Current subsystem visibility across dashboard sections.</p>
        <div class="health-overall"><span class="section-badge ${overallClass}">${overallLabel}</span></div>
      </div>
    </div>
    <ul class="dashboard-status-list">${rows}</ul>
  `;
}

function extractReasonTokens(raw) {
  const text = String(raw || "").toUpperCase();
  const tokens = text.match(/[A-Z_]{3,}/g) || [];
  return tokens.filter((token) => token !== "TRUE" && token !== "FALSE" && token !== "NONE");
}

function topReasonForStatus(status) {
  const counts = {};
  (executiveState.governanceLatest.snapshots || []).forEach((row) => {
    if (String(row.governance_status || "").toUpperCase() !== status) return;
    extractReasonTokens(row.reasons).forEach((token) => {
      counts[token] = (counts[token] || 0) + 1;
    });
  });
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return sorted.length ? sorted[0][0] : "-";
}

function renderExecutiveKpiHeader() {
  const node = document.getElementById("executiveKpiHeader");
  if (!node) return;

  const statusCounts = executiveState.governanceSummary.status_counts || {};
  const latestChange = Number(executiveState.latestChanges.summary && executiveState.latestChanges.summary.portfolio_value_change);
  const latestValue = Number(executiveState.latest.total_value);
  const lineageMatches = Array.isArray(executiveState.lineageLatest.matches) ? executiveState.lineageLatest.matches.length : 0;
  const attributionWinners = Number(executiveState.attributionLatest.summary && executiveState.attributionLatest.summary.winner_count);

  const items = [
    ["Snapshots", asInt(executiveState.snapshots.length)],
    ["Canonical Days", asInt(executiveState.canonicalSummary.selected_dates)],
    ["PASS", asInt(statusCounts.PASS)],
    ["WARNING", asInt(statusCounts.WARNING)],
    ["REJECT", asInt(statusCounts.REJECT)],
    ["Latest Portfolio Value", Number.isFinite(latestValue) ? asCurrency(latestValue) : "-"],
    ["Latest Change", Number.isFinite(latestChange) ? asSignedCurrency(latestChange) : "-"],
    ["Lineage Matches", asInt(lineageMatches)],
    ["Attribution Winners", Number.isFinite(attributionWinners) ? asInt(attributionWinners) : "0"],
  ];

  node.innerHTML = items
    .map(([label, value]) => `
      <div class="executive-kpi">
        <div class="executive-kpi-label">${label}</div>
        <div class="executive-kpi-value">${value}</div>
      </div>
    `)
    .join("");
}

function renderGovernanceSummaryCard() {
  const node = document.getElementById("governanceSummaryCard");
  if (!node) return;
  const statusCounts = executiveState.governanceSummary.status_counts || {};
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>PASS</span><strong>${asInt(statusCounts.PASS)}</strong></li>
      <li class="metric-item"><span>WARNING</span><strong>${asInt(statusCounts.WARNING)}</strong></li>
      <li class="metric-item"><span>REJECT</span><strong>${asInt(statusCounts.REJECT)}</strong></li>
      <li class="metric-item"><span>Top rejection reason</span><strong>${topReasonForStatus("REJECT")}</strong></li>
      <li class="metric-item"><span>Top warning reason</span><strong>${topReasonForStatus("WARNING")}</strong></li>
    </ul>
  `;
}

function renderCanonicalSelectionCard() {
  const node = document.getElementById("canonicalSelectionCard");
  if (!node) return;
  const statusCounts = executiveState.governanceSummary.status_counts || {};
  const latest = (executiveState.canonicalLatest && executiveState.canonicalLatest.latest) || {};
  const policy = String(latest.selection_reason || "Latest-ingested PASS candidate").replace("Selected ", "").replace(".", "");
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>Selected Dates</span><strong>${asInt(executiveState.canonicalSummary.selected_dates)}</strong></li>
      <li class="metric-item"><span>Selection Policy</span><strong>${policy || "Latest-ingested PASS candidate"}</strong></li>
      <li class="metric-item"><span>Rejected Snapshots Excluded</span><strong>${asInt(statusCounts.REJECT)}</strong></li>
      <li class="metric-item"><span>Warning Snapshots Ignored</span><strong>${asInt(statusCounts.WARNING)}</strong></li>
    </ul>
  `;
}

function renderPortfolioTrendCard() {
  const node = document.getElementById("portfolioTrendCard");
  if (!node) return;
  const timeline = executiveState.timeline || [];
  const latest = Number(timeline[0] && timeline[0].portfolio_value);
  const prior = Number(timeline[1] && timeline[1].portfolio_value);
  const change = Number.isFinite(latest) && Number.isFinite(prior) ? latest - prior : Number.NaN;
  const changePct = Number.isFinite(change) && prior !== 0 ? (change / prior) * 100 : Number.NaN;
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>Latest Value</span><strong>${Number.isFinite(latest) ? asCurrency(latest) : "-"}</strong></li>
      <li class="metric-item"><span>Prior Value</span><strong>${Number.isFinite(prior) ? asCurrency(prior) : "-"}</strong></li>
      <li class="metric-item"><span>Change</span><strong>${Number.isFinite(change) ? asSignedCurrency(change) : "-"}</strong></li>
      <li class="metric-item"><span>Change %</span><strong>${Number.isFinite(changePct) ? asPercent(changePct) : "-"}</strong></li>
    </ul>
  `;
}

function renderChangeDetectionSummaryCard() {
  const node = document.getElementById("changeDetectionSummaryCard");
  if (!node) return;
  const summary = executiveState.latestChanges.summary || {};
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>New Positions</span><strong>${asInt(summary.new_holdings_count)}</strong></li>
      <li class="metric-item"><span>Exited Positions</span><strong>${asInt(summary.exited_holdings_count)}</strong></li>
      <li class="metric-item"><span>Increased Positions</span><strong>${asInt(summary.increased_holdings_count)}</strong></li>
      <li class="metric-item"><span>Reduced Positions</span><strong>${asInt(summary.reduced_holdings_count)}</strong></li>
    </ul>
  `;
}

function renderLineageSummaryCard() {
  const node = document.getElementById("lineageSummaryCard");
  if (!node) return;
  const summary = executiveState.lineageLatest.summary || {};
  const total = Number(summary.total_changes || 0);
  const unmatched = Number(summary.unmatched || 0);
  const matched = Number.isFinite(total) ? Math.max(total - unmatched, 0) : 0;
  const rate = total > 0 ? (matched / total) * 100 : Number.NaN;
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>Matched High</span><strong>${asInt(summary.matched_high)}</strong></li>
      <li class="metric-item"><span>Matched Medium</span><strong>${asInt(summary.matched_medium)}</strong></li>
      <li class="metric-item"><span>Matched Low</span><strong>${asInt(summary.matched_low)}</strong></li>
      <li class="metric-item"><span>Unmatched</span><strong>${asInt(summary.unmatched)}</strong></li>
      <li class="metric-item"><span>Match Rate %</span><strong>${Number.isFinite(rate) ? asPercent(rate) : "-"}</strong></li>
    </ul>
  `;
}

function benchmarkQualityBadge(included, excluded) {
  const total = included + excluded;
  if (total === 0) return '<span class="section-badge section-badge-loading">NO DATA</span>';
  const pct = total > 0 ? (included / total) * 100 : 0;
  if (pct >= 80) return '<span class="section-badge section-badge-loaded">HEALTHY</span>';
  return '<span class="section-badge section-badge-slow">DEGRADED</span>';
}

function renderBenchmarkSummaryCard() {
  const node = document.getElementById("benchmarkSummaryCard");
  if (!node) return;
  const latest = executiveState.benchmarkLatest.latest_portfolio_excess_return || {};
  const sym = executiveState.benchmarkLatest.benchmark_symbol || "SPY";
  const quality = executiveState.benchmarkLatest.quality || {};
  const included = Number(quality.included_rows || 0);
  const excluded = Number(quality.excluded_rows || 0);
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>Benchmark</span><strong>${sym}</strong></li>
      <li class="metric-item"><span>Latest Portfolio Return</span><strong>${asPercent(latest.portfolio_return_pct)}</strong></li>
      <li class="metric-item"><span>Latest Benchmark Return</span><strong>${asPercent(latest.benchmark_return_pct)}</strong></li>
      <li class="metric-item"><span>Latest Excess Return</span><strong>${asPercent(latest.excess_return_pct)}</strong></li>
      <li class="metric-item"><span>Data Quality</span><strong>${benchmarkQualityBadge(included, excluded)}</strong></li>
    </ul>
  `;
}

function renderAttributionSummaryCard() {
  const node = document.getElementById("attributionSummaryCard");
  if (!node) return;
  const summary = executiveState.attributionLatest.summary || {};
  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>Matched Recommendations</span><strong>${asInt(summary.matched_recommendations)}</strong></li>
      <li class="metric-item"><span>Winners</span><strong>${asInt(summary.winner_count)}</strong></li>
      <li class="metric-item"><span>Neutral</span><strong>${asInt(summary.neutral_count)}</strong></li>
      <li class="metric-item"><span>Losers</span><strong>${asInt(summary.loser_count)}</strong></li>
      <li class="metric-item"><span>Total Directional Attribution</span><strong>${asSignedCurrency(summary.total_directional_attribution)}</strong></li>
    </ul>
  `;
}

function renderExecutiveCards() {
  renderExecutiveKpiHeader();
  renderGovernanceSummaryCard();
  renderCanonicalSelectionCard();
  renderPortfolioTrendCard();
  renderChangeDetectionSummaryCard();
  renderLineageSummaryCard();
  renderAttributionSummaryCard();
  renderBenchmarkSummaryCard();
}

function renderBenchmarkSummary(latestPayload) {
  const node = document.getElementById("benchmarkSummary");
  if (!node) return;
  const latest = latestPayload.latest_portfolio_excess_return || {};
  const sym = latestPayload.benchmark_symbol || "SPY";
  const quality = latestPayload.quality || {};
  const included = Number(quality.included_rows || 0);
  const excluded = Number(quality.excluded_rows || 0);
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Benchmark</div><div class="kpi-value">${sym}</div></div>
      <div class="kpi"><div class="kpi-label">Portfolio Return %</div><div class="kpi-value">${asPercent(latest.portfolio_return_pct)}</div></div>
      <div class="kpi"><div class="kpi-label">Benchmark Return %</div><div class="kpi-value">${asPercent(latest.benchmark_return_pct)}</div></div>
      <div class="kpi"><div class="kpi-label">Excess Return %</div><div class="kpi-value">${asPercent(latest.excess_return_pct)}</div></div>
    </div>
    <p style="margin-top:10px;">Alignment policy: <span class="status-chip">${latestPayload.alignment_policy || "-"}</span>&nbsp;
      Data quality: ${benchmarkQualityBadge(included, excluded)}
      (${included} included, ${excluded} excluded)
    </p>
  `;
}

function renderBenchmarkTrend(seriesPayload) {
  const series = Array.isArray(seriesPayload.series) ? seriesPayload.series : [];
  const ok = series.filter((r) => r.data_quality_status === "OK");
  const cumPortfolio = ok.reduce((acc, r) => acc + Number(r.portfolio_return_pct || 0), 0);
  const cumBenchmark = ok.reduce((acc, r) => acc + Number(r.benchmark_return_pct || 0), 0);
  const cumExcess = ok.reduce((acc, r) => acc + Number(r.excess_return_pct || 0), 0);
  const node = document.getElementById("benchmarkTrend");
  if (!node) return;
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Intervals</div><div class="kpi-value">${series.length}</div></div>
      <div class="kpi"><div class="kpi-label">Cumulative Portfolio Return</div><div class="kpi-value">${asPercent(cumPortfolio)}</div></div>
      <div class="kpi"><div class="kpi-label">Cumulative Benchmark Return</div><div class="kpi-value">${asPercent(cumBenchmark)}</div></div>
      <div class="kpi"><div class="kpi-label">Cumulative Excess Return</div><div class="kpi-value">${asPercent(cumExcess)}</div></div>
    </div>
  `;
}

function renderBenchmarkTopAlpha(latestPayload) {
  const rows = (latestPayload.top_positive_alpha_recommendations || []).map((r) => [
    r.recommendation_id || "-",
    r.symbol || "-",
    r.recommendation_source || "-",
    asPercent(r.benchmark_return_pct),
    asPercent(r.directional_return_pct),
    asPercent(r.recommendation_excess_return_pct),
  ]);
  renderTable(
    "benchmarkTopAlpha",
    ["Recommendation", "Symbol", "Source", "Benchmark Return %", "Rec Return %", "Excess Return %"],
    rows,
  );
}

function renderBenchmarkLowestAlpha(latestPayload) {
  const rows = (latestPayload.worst_negative_alpha_recommendations || []).map((r) => [
    r.recommendation_id || "-",
    r.symbol || "-",
    r.recommendation_source || "-",
    asPercent(r.benchmark_return_pct),
    asPercent(r.directional_return_pct),
    asPercent(r.recommendation_excess_return_pct),
  ]);
  renderTable(
    "benchmarkLowestAlpha",
    ["Recommendation", "Symbol", "Source", "Benchmark Return %", "Rec Return %", "Excess Return %"],
    rows,
  );
}

function renderBenchmarkSourceAlpha(sourcesPayload) {
  const rows = (sourcesPayload.source_summary || []).map((r) => [
    r.recommendation_source || "-",
    asInt(r.matched_recommendations),
    asPercent(r.alpha_win_rate),
    asPercent(r.avg_excess_return_pct),
    asSignedCurrency(r.total_directional_attribution),
  ]);
  renderTable(
    "benchmarkSourceAlpha",
    ["Source", "Recommendations", "Alpha Win Rate", "Avg Excess Return %", "Total Attribution"],
    rows,
  );
}

function renderBenchmarkQuality(latestPayload) {
  const node = document.getElementById("benchmarkQuality");
  if (!node) return;
  const quality = latestPayload.quality || {};
  const included = Number(quality.included_rows || 0);
  const excluded = Number(quality.excluded_rows || 0);
  const reasonCounts = quality.excluded_reason_counts || {};
  const reasonList = Object.entries(reasonCounts)
    .map(([reason, count]) => `<li class="metric-item"><span>${reason}</span><strong>${count}</strong></li>`)
    .join("") || '<li class="metric-item"><span>No exclusions</span><strong>—</strong></li>';
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Included Rows</div><div class="kpi-value">${included}</div></div>
      <div class="kpi"><div class="kpi-label">Excluded Rows</div><div class="kpi-value">${excluded}</div></div>
      <div class="kpi"><div class="kpi-label">Quality</div><div class="kpi-value">${benchmarkQualityBadge(included, excluded)}</div></div>
    </div>
    <details class="detail-toggle" style="margin-top:10px;">
      <summary>Exclusion reason counts</summary>
      <ul class="metric-list" style="margin-top:8px;">${reasonList}</ul>
    </details>
  `;
}

function updateSubsystemStatuses() {
  Object.entries(SUBSYSTEM_DEFINITIONS).forEach(([key, config]) => {
    const states = config.sectionKeys.map((sectionKey) => sectionStates[sectionKey] || STATUS_LOADING);
    subsystemStates[key] = aggregateStatuses(states);
  });
  renderDashboardStatusPanel();
}

function updateDashboardBanner() {
  const banner = document.getElementById("dashboardLoadingBanner");
  if (!banner) return;
  const statuses = Object.keys(SECTION_DEFINITIONS).map((sectionKey) => sectionStates[sectionKey] || STATUS_LOADING);
  const total = statuses.length;
  const completed = statuses.filter((status) => status === STATUS_LOADED || status === STATUS_FAILED).length;
  const slowCount = statuses.filter((status) => status === STATUS_SLOW).length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const elapsedMs = Date.now() - dashboardStartedAt;
  const canHide = elapsedMs >= MIN_BANNER_VISIBLE_MS;

  if (bannerHideTimerId !== null) {
    clearTimeout(bannerHideTimerId);
    bannerHideTimerId = null;
  }

  if (completed === total && canHide) {
    banner.classList.add("hidden");
    banner.innerHTML = "";
    return;
  }

  if (completed === total && !canHide) {
    bannerHideTimerId = setTimeout(() => {
      bannerHideTimerId = null;
      updateDashboardBanner();
    }, Math.max(0, MIN_BANNER_VISIBLE_MS - elapsedMs));
  }

  banner.classList.remove("hidden");
  const meta = completed === total
    ? `Finalizing dashboard view - ${elapsedSeconds()}s elapsed`
    : slowCount
      ? `${completed} of ${total} sections loaded (${percent}%) - ${slowCount} slow ${slowCount === 1 ? "section" : "sections"} - ${elapsedSeconds()}s elapsed`
      : `${completed} of ${total} sections loaded (${percent}%) - ${elapsedSeconds()}s elapsed`;
  banner.innerHTML = `
    <div class="dashboard-banner-spinner" aria-hidden="true"></div>
    <div>
      <div class="dashboard-banner-title">Portfolio Intelligence Dashboard</div>
      <div class="dashboard-banner-text">Loading data...</div>
      <div class="dashboard-banner-meta">${meta}</div>
      <div class="dashboard-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" aria-label="Dashboard loading progress">
        <div class="dashboard-progress-fill" style="width: ${percent}%;"></div>
      </div>
    </div>
  `;
}

function updateSectionBadge(sectionKey, status) {
  const badge = document.querySelector(`[data-section-badge="${sectionKey}"]`);
  if (!badge) return;
  badge.className = `section-badge ${statusClass(status)}`;
  badge.textContent = status;
}

function renderSectionLoadingState(sectionKey, status) {
  const definition = SECTION_DEFINITIONS[sectionKey];
  if (!definition) return;
  const message = status === STATUS_SLOW ? definition.slowMessage : definition.loadingMessage;
  const renderer = status === STATUS_SLOW ? renderSlow : renderLoading;
  definition.targetIds.forEach((targetId) => renderer(targetId, message));
}

function renderSectionFailureState(sectionKey, error) {
  const definition = SECTION_DEFINITIONS[sectionKey];
  if (!definition) return;
  definition.targetIds.forEach((targetId) => renderFailure(targetId, error));
}

function setSectionState(sectionKey, status, error = null) {
  sectionStates[sectionKey] = status;
  updateSectionBadge(sectionKey, status);
  if (status === STATUS_LOADING || status === STATUS_SLOW) {
    renderSectionLoadingState(sectionKey, status);
  }
  if (status === STATUS_FAILED) {
    renderSectionFailureState(sectionKey, error);
  }
  updateSubsystemStatuses();
  updateDashboardBanner();
}

function beginSection(sectionKey) {
  setSectionState(sectionKey, STATUS_LOADING);
}

function markSectionSlow(sectionKey) {
  if (sectionStates[sectionKey] === STATUS_LOADING) {
    setSectionState(sectionKey, STATUS_SLOW);
  }
}

function completeSection(sectionKey) {
  sectionStates[sectionKey] = STATUS_LOADED;
  updateSectionBadge(sectionKey, STATUS_LOADED);
  updateSubsystemStatuses();
  updateDashboardBanner();
}

function failSection(sectionKey, error) {
  setSectionState(sectionKey, STATUS_FAILED, error);
}

function runSectionTask(sectionKey, requestFactory, onSuccess) {
  beginSection(sectionKey);
  const slowTimer = setTimeout(() => markSectionSlow(sectionKey), SLOW_THRESHOLD_MS);
  requestFactory()
    .then((payload) => {
      clearTimeout(slowTimer);
      onSuccess(payload);
      completeSection(sectionKey);
    })
    .catch((error) => {
      clearTimeout(slowTimer);
      failSection(sectionKey, error);
    });
}

function renderInventory(snapshots) {
  const rows = snapshots.map((s) => [
    s.snapshot_date || "-",
    s.account_number || "-",
    s.account_name || "-",
    asInt(s.positions),
    asCurrency(s.market_value),
    asCurrency(s.cash_value),
    s.source_file || "-",
    s.ingestion_timestamp || "-",
    s.snapshot_id || "-",
  ]);
  renderTable(
    "snapshotInventory",
    ["Date", "Account #", "Account Name", "Positions", "Market Value", "Cash", "Source File", "Ingested", "Snapshot ID"],
    rows,
  );
}

function renderTimeline(timeline) {
  const rows = timeline.map((t) => [
    t.snapshot_date || "-",
    asCurrency(t.portfolio_value),
    asCurrency(t.cash_value),
    asInt(t.positions),
    t.change_vs_prior_snapshot === null ? "-" : asSignedCurrency(t.change_vs_prior_snapshot),
  ]);
  renderTable(
    "valueTimeline",
    ["Date", "Portfolio Value", "Cash", "Positions", "Change vs Prior Snapshot"],
    rows,
  );
}

function renderLatest(latest) {
  const node = document.getElementById("latestSummary");
  if (!node) return;
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Snapshot Date</div><div class="kpi-value">${latest.snapshot_date || "-"}</div></div>
      <div class="kpi"><div class="kpi-label">Total Value</div><div class="kpi-value">${asCurrency(latest.total_value)}</div></div>
      <div class="kpi"><div class="kpi-label">Cash</div><div class="kpi-value">${asCurrency(latest.cash)}</div></div>
      <div class="kpi"><div class="kpi-label">Positions</div><div class="kpi-value">${asInt(latest.position_count)}</div></div>
    </div>
  `;

  const holdings = Array.isArray(latest.largest_holdings) ? latest.largest_holdings : [];
  const rows = holdings.map((h, idx) => [String(idx + 1), h.symbol || "-", asCurrency(h.market_value)]);
  renderTable("topHoldings", ["Rank", "Symbol", "Market Value"], rows);
}

function renderHealth(health) {
  const node = document.getElementById("historyHealth");
  if (!node) return;
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">First Snapshot</div><div class="kpi-value">${health.first_snapshot_date || "-"}</div></div>
      <div class="kpi"><div class="kpi-label">Latest Snapshot</div><div class="kpi-value">${health.latest_snapshot_date || "-"}</div></div>
      <div class="kpi"><div class="kpi-label">Snapshot Count</div><div class="kpi-value">${asInt(health.snapshot_count)}</div></div>
      <div class="kpi"><div class="kpi-label">Missing Days</div><div class="kpi-value">${asInt(health.missing_days)}</div></div>
    </div>
    <p style="margin-top:10px;"><span class="status-chip">Duplicate uploads prevented: ${asInt(health.duplicate_uploads_prevented)}</span></p>
  `;
}

function renderLineage(lineage) {
  const node = document.getElementById("lineageSummary");
  if (!node) return;
  node.innerHTML = `
    <ul class="lineage-list">
      <li><strong>Total SIH Analyses Captured:</strong> ${asInt(lineage.total_sih_analyses_captured)}</li>
      <li><strong>Latest PAR:</strong> ${lineage.latest_par || "-"}</li>
      <li><strong>Latest Mandate:</strong> ${lineage.latest_mandate || "-"}</li>
      <li><strong>Latest Upload Date:</strong> ${lineage.latest_upload_date || "-"}</li>
    </ul>
  `;
}

function renderGovernanceSummary(summaryPayload, latestPayload) {
  const node = document.getElementById("governanceSummary");
  if (!node) return;
  const statusCounts = (summaryPayload && summaryPayload.status_counts) || (latestPayload && latestPayload.status_counts) || {};
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">PASS</div><div class="kpi-value">${asInt(statusCounts.PASS)}</div></div>
      <div class="kpi"><div class="kpi-label">WARNING</div><div class="kpi-value">${asInt(statusCounts.WARNING)}</div></div>
      <div class="kpi"><div class="kpi-label">REJECT</div><div class="kpi-value">${asInt(statusCounts.REJECT)}</div></div>
      <div class="kpi"><div class="kpi-label">Snapshots Evaluated</div><div class="kpi-value">${asInt(summaryPayload.total_snapshots)}</div></div>
    </div>
  `;
}

function governanceChip(status) {
  const value = String(status || "").toUpperCase();
  if (value === "PASS") return '<span class="status-chip gov-pass">PASS</span>';
  if (value === "WARNING") return '<span class="status-chip gov-warning">WARNING</span>';
  if (value === "REJECT") return '<span class="status-chip gov-reject">REJECT</span>';
  return '<span class="status-chip">UNKNOWN</span>';
}

function renderGovernanceTable(latestPayload) {
  const rows = (latestPayload.snapshots || []).map((row) => [
    row.snapshot_date || "-",
    row.snapshot_id || "-",
    governanceChip(row.governance_status),
    row.reasons || "-",
    row.scope_valid || "-",
    row.value_valid || "-",
    row.source_valid || "-",
  ]);
  renderTable(
    "governanceTable",
    ["Snapshot Date", "Snapshot ID", "Status", "Reasons", "Scope Valid", "Value Valid", "Source Valid"],
    rows,
  );
}

function renderCanonicalSummary(summaryPayload, latestPayload) {
  const node = document.getElementById("canonicalSummary");
  if (!node) return;
  const counts = (summaryPayload && summaryPayload.selected_status_counts) || {};
  const latest = (latestPayload && latestPayload.latest) || {};
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Selected Dates</div><div class="kpi-value">${asInt(summaryPayload.selected_dates)}</div></div>
      <div class="kpi"><div class="kpi-label">Unselected Dates</div><div class="kpi-value">${asInt(summaryPayload.unselected_dates)}</div></div>
      <div class="kpi"><div class="kpi-label">Selected PASS</div><div class="kpi-value">${asInt(counts.PASS)}</div></div>
      <div class="kpi"><div class="kpi-label">Latest Canonical Date</div><div class="kpi-value">${latest.snapshot_date || "-"}</div></div>
    </div>
  `;
}

function renderCanonicalTable(historyPayload) {
  const rows = (historyPayload.history || []).map((row) => [
    row.snapshot_date || "-",
    row.canonical_snapshot_id || "-",
    governanceChip(row.governance_status),
    asCurrency(row.portfolio_value),
    row.selection_reason || "-",
  ]);
  renderTable(
    "canonicalTable",
    ["Date", "Selected Snapshot", "Governance Status", "Portfolio Value", "Selection Reason"],
    rows,
  );
}

function renderLatestChanges(summary) {
  const node = document.getElementById("latestChanges");
  if (!node) return;
  if (!summary) {
    node.innerHTML = '<p class="empty">No prior snapshot available for comparison yet.</p>';
    return;
  }
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Compared Snapshot</div><div class="kpi-value">${summary.snapshot_date || "-"}</div></div>
      <div class="kpi"><div class="kpi-label">Portfolio Value Change</div><div class="kpi-value">${asSignedCurrency(summary.portfolio_value_change)}</div></div>
      <div class="kpi"><div class="kpi-label">Cash Change</div><div class="kpi-value">${asSignedCurrency(summary.cash_change)}</div></div>
      <div class="kpi"><div class="kpi-label">Position Count Change</div><div class="kpi-value">${asInt(summary.position_count_change)}</div></div>
    </div>
  `;
}

function renderChangeTables(changePayload) {
  const newRows = (changePayload.new_positions || []).map((r) => [r.symbol || "-", asCurrency(r.new_market_value)]);
  renderTable("newPositions", ["Symbol", "Market Value"], newRows);

  const exitedRows = (changePayload.exited_positions || []).map((r) => [r.symbol || "-", asCurrency(r.old_market_value)]);
  renderTable("exitedPositions", ["Symbol", "Prior Market Value"], exitedRows);

  const increasedRows = (changePayload.increased_positions || []).map((r) => [
    r.symbol || "-",
    Number(r.delta_quantity || 0).toFixed(4),
    asSignedCurrency(r.delta_market_value),
  ]);
  renderTable("increasedPositions", ["Symbol", "Quantity Delta", "Market Value Delta"], increasedRows);

  const reducedRows = (changePayload.reduced_positions || []).map((r) => [
    r.symbol || "-",
    Number(r.delta_quantity || 0).toFixed(4),
    asSignedCurrency(r.delta_market_value),
  ]);
  renderTable("reducedPositions", ["Symbol", "Quantity Delta", "Market Value Delta"], reducedRows);
}

function renderChangeSummaryHistory(summaryPayload) {
  const summary = Array.isArray(summaryPayload.summary) ? summaryPayload.summary : [];
  const summaryNode = document.getElementById("changeSummaryText");
  if (summaryNode) {
    const latest = summary[0] || null;
    if (!latest) {
      summaryNode.innerHTML = '<p class="empty">Change summary unavailable until at least two snapshot dates exist.</p>';
    } else {
      summaryNode.innerHTML = `
        <p>
          Compared to prior snapshot (${latest.prior_snapshot_date || "-"} -> ${latest.snapshot_date || "-"}):
          New Positions: ${asInt(latest.new_holdings_count)},
          Exited Positions: ${asInt(latest.exited_holdings_count)},
          Increased Positions: ${asInt(latest.increased_holdings_count)},
          Reduced Positions: ${asInt(latest.reduced_holdings_count)}.
        </p>
      `;
    }
  }

  const rows = summary.map((r) => [
    r.snapshot_date || "-",
    r.prior_snapshot_date || "-",
    asSignedCurrency(r.portfolio_value_change),
    asSignedCurrency(r.cash_change),
    asInt(r.new_holdings_count),
    asInt(r.exited_holdings_count),
    asInt(r.increased_holdings_count),
    asInt(r.reduced_holdings_count),
  ]);
  renderTable(
    "changeSummaryTable",
    ["Snapshot Date", "Prior Date", "Portfolio Value Change", "Cash Change", "New", "Exited", "Increased", "Reduced"],
    rows,
  );
}

function renderLineageMatches(payload) {
  const rows = (payload.matches || []).map((r) => [
    r.symbol || "-",
    r.change_type || "-",
    r.matched_recommendation || r.matched_recommendation_id || "-",
    r.recommendation_source || "-",
    r.confidence || "-",
  ]);
  renderTable("lineageLatestMatches", ["Symbol", "Observed Change", "Matched Recommendation", "Source", "Confidence"], rows);
}

function renderLineageUnmatched(payload) {
  const rows = (payload.unmatched || []).map((r) => [
    r.symbol || "-",
    r.change_type || "-",
    r.confidence || "NONE",
  ]);
  renderTable("lineageUnmatched", ["Symbol", "Observed Change", "Confidence"], rows);
}

function renderLineageSummary(latestPayload, summaryPayload) {
  const summary = latestPayload.summary || null;
  const kpiNode = document.getElementById("lineageKpis");
  if (kpiNode) {
    if (!summary) {
      kpiNode.innerHTML = '<p class="empty">No lineage summary available yet.</p>';
    } else {
      kpiNode.innerHTML = `
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-label">Total Changes</div><div class="kpi-value">${asInt(summary.total_changes)}</div></div>
          <div class="kpi"><div class="kpi-label">Matched High</div><div class="kpi-value">${asInt(summary.matched_high)}</div></div>
          <div class="kpi"><div class="kpi-label">Matched Medium</div><div class="kpi-value">${asInt(summary.matched_medium)}</div></div>
          <div class="kpi"><div class="kpi-label">Matched Low</div><div class="kpi-value">${asInt(summary.matched_low)}</div></div>
          <div class="kpi"><div class="kpi-label">Unmatched</div><div class="kpi-value">${asInt(summary.unmatched)}</div></div>
        </div>
      `;
    }
  }

  const rows = (summaryPayload.summary || []).map((r) => [
    r.snapshot_date || "-",
    asInt(r.total_changes),
    asInt(r.matched_high),
    asInt(r.matched_medium),
    asInt(r.matched_low),
    asInt(r.unmatched),
  ]);
  renderTable("lineageSummaryTable", ["Snapshot Date", "Total Changes", "High", "Medium", "Low", "Unmatched"], rows);
}

function renderLineageSourceBreakdown(payload) {
  const rows = (payload.source_breakdown || []).map((r) => [r.source || "-", asInt(r.count)]);
  renderTable("lineageSourceBreakdown", ["Source", "Matched Count"], rows);
}

function renderAttributionSummary(latestPayload, historyPayload, summaryPayload) {
  const node = document.getElementById("attributionSummary");
  if (!node) return;
  const latestSummary = (latestPayload && latestPayload.summary) || {};
  const historyRows = Array.isArray(historyPayload.summary) ? historyPayload.summary : [];
  const aggregate = (summaryPayload && summaryPayload.summary) || {};
  node.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Latest Snapshot</div><div class="kpi-value">${latestSummary.snapshot_date || "-"}</div></div>
      <div class="kpi"><div class="kpi-label">History Rows</div><div class="kpi-value">${asInt(historyRows.length)}</div></div>
      <div class="kpi"><div class="kpi-label">Total Directional Attribution</div><div class="kpi-value">${asSignedCurrency(aggregate.total_directional_attribution)}</div></div>
      <div class="kpi"><div class="kpi-label">Average Return %</div><div class="kpi-value">${asPercent(aggregate.average_directional_return_pct)}</div></div>
    </div>
  `;
}

function renderAttributionWinners(payload) {
  const rows = (payload.top_winning_recommendations || []).map((r) => [
    r.matched_recommendation || r.matched_recommendation_id || "-",
    r.recommendation_source || "-",
    asInt(r.count),
    asSignedCurrency(r.total_directional_attribution),
  ]);
  renderTable("topWinningRecommendations", ["Recommendation", "Source", "Matches", "Directional Attribution"], rows);
}

function renderAttributionLosers(payload) {
  const rows = (payload.top_losing_recommendations || []).map((r) => [
    r.matched_recommendation || r.matched_recommendation_id || "-",
    r.recommendation_source || "-",
    asInt(r.count),
    asSignedCurrency(r.total_directional_attribution),
  ]);
  renderTable("topLosingRecommendations", ["Recommendation", "Source", "Matches", "Directional Attribution"], rows);
}

function renderAttributionSourcePerformance(payload) {
  const rows = (payload.source_performance || []).map((r) => [
    r.source || "-",
    asInt(r.matched_count),
    asInt(r.winner_count),
    asInt(r.neutral_count),
    asInt(r.loser_count),
    asPercent(r.win_rate_pct),
    asSignedCurrency(r.total_directional_attribution),
  ]);
  renderTable(
    "recommendationSourcePerformance",
    ["Source", "Matches", "Winners", "Neutral", "Losers", "Win Rate", "Directional Attribution"],
    rows,
  );
}

function initializeDashboardShell() {
  dashboardStartedAt = Date.now();
  requestCache.clear();
  Object.keys(SECTION_DEFINITIONS).forEach((sectionKey) => {
    sectionStates[sectionKey] = STATUS_LOADING;
  });
  ensureSectionBadges();
  Object.keys(SECTION_DEFINITIONS).forEach((sectionKey) => {
    renderSectionLoadingState(sectionKey, STATUS_LOADING);
    updateSectionBadge(sectionKey, STATUS_LOADING);
  });
  updateSubsystemStatuses();
  updateDashboardBanner();
  ["executiveKpiHeader", "governanceSummaryCard", "canonicalSelectionCard", "portfolioTrendCard", "changeDetectionSummaryCard", "lineageSummaryCard", "attributionSummaryCard", "benchmarkSummaryCard"].forEach((id) => {
    renderLoading(id, "Loading executive summary...");
  });
}

function initialize() {
  initializeDashboardShell();

  runSectionTask("inventory", () => requestJson("/api/pis/snapshots"), (snapshotsPayload) => {
    const snapshots = Array.isArray(snapshotsPayload.snapshots) ? snapshotsPayload.snapshots : [];
    executiveState.snapshots = snapshots;
    renderExecutiveCards();
    if (!snapshots.length) {
      renderEmpty("snapshotInventory", "No snapshot inventory found yet.");
      return;
    }
    renderInventory(snapshots);
  });

  runSectionTask("timeline", () => requestJson("/api/pis/summary"), (summary) => {
    const timeline = Array.isArray(summary.timeline) ? summary.timeline : [];
    executiveState.timeline = timeline;
    renderExecutiveCards();
    if (!timeline.length) {
      renderEmpty("valueTimeline", "No timeline available yet.");
      return;
    }
    renderTimeline(timeline);
  });

  runSectionTask("latest", () => requestJson("/api/pis/latest"), (latest) => {
    executiveState.latest = latest || {};
    renderExecutiveCards();
    renderLatest(latest || {});
  });

  runSectionTask("health", () => requestJson("/api/pis/health"), (health) => {
    renderHealth(health || {});
  });

  runSectionTask("lineageOverview", () => requestJson("/api/pis/summary"), (summary) => {
    renderLineage(summary.lineage || {});
  });

  runSectionTask("governance", () => Promise.all([
    requestJson("/api/pis/governance-summary"),
    requestJson("/api/pis/governance/latest"),
  ]), ([governanceSummary, governanceLatest]) => {
    executiveState.governanceSummary = governanceSummary || { total_snapshots: 0, status_counts: {} };
    executiveState.governanceLatest = governanceLatest || { snapshots: [], status_counts: {} };
    renderExecutiveCards();
    renderGovernanceSummary(governanceSummary || {}, governanceLatest || {});
    renderGovernanceTable(governanceLatest || {});
  });

  runSectionTask("canonical", () => Promise.all([
    requestJson("/api/pis/canonical-summary"),
    requestJson("/api/pis/canonical/latest"),
    requestJson("/api/pis/canonical/history"),
  ]), ([canonicalSummary, canonicalLatest, canonicalHistory]) => {
    executiveState.canonicalSummary = canonicalSummary || { selected_dates: 0, unselected_dates: 0, selected_status_counts: {} };
    executiveState.canonicalLatest = canonicalLatest || { latest: {} };
    renderExecutiveCards();
    renderCanonicalSummary(canonicalSummary || {}, canonicalLatest || {});
    renderCanonicalTable(canonicalHistory || {});
  });

  runSectionTask("latestChanges", () => requestJson("/api/pis/changes/latest"), (latestChanges) => {
    executiveState.latestChanges = latestChanges || { summary: null, new_positions: [], exited_positions: [], increased_positions: [], reduced_positions: [] };
    renderExecutiveCards();
    renderLatestChanges((latestChanges && latestChanges.summary) || null);
  });

  ["newPositions", "exitedPositions", "increasedPositions", "reducedPositions"].forEach((sectionKey) => {
    runSectionTask(sectionKey, () => requestJson("/api/pis/changes/latest"), (latestChanges) => {
      renderChangeTables(latestChanges || {});
    });
  });

  runSectionTask("changeSummary", () => requestJson("/api/pis/change-summary"), (changeSummary) => {
    renderChangeSummaryHistory(changeSummary || {});
  });

  runSectionTask("lineageMatches", () => requestJson("/api/pis/lineage/latest"), (lineageLatest) => {
    executiveState.lineageLatest = lineageLatest || { summary: null, matches: [], unmatched: [], source_breakdown: [] };
    renderExecutiveCards();
    renderLineageMatches(lineageLatest || {});
  });

  runSectionTask("lineageUnmatched", () => requestJson("/api/pis/lineage/latest"), (lineageLatest) => {
    executiveState.lineageLatest = lineageLatest || { summary: null, matches: [], unmatched: [], source_breakdown: [] };
    renderExecutiveCards();
    renderLineageUnmatched(lineageLatest || {});
  });

  runSectionTask("lineageDetail", () => Promise.all([
    requestJson("/api/pis/lineage/latest"),
    requestJson("/api/pis/lineage-summary"),
  ]), ([lineageLatest, lineageSummary]) => {
    executiveState.lineageLatest = lineageLatest || { summary: null, matches: [], unmatched: [], source_breakdown: [] };
    renderExecutiveCards();
    renderLineageSummary(lineageLatest || {}, lineageSummary || {});
  });

  runSectionTask("lineageSourceBreakdown", () => requestJson("/api/pis/lineage/latest"), (lineageLatest) => {
    executiveState.lineageLatest = lineageLatest || { summary: null, matches: [], unmatched: [], source_breakdown: [] };
    renderExecutiveCards();
    renderLineageSourceBreakdown(lineageLatest || {});
  });

  runSectionTask("attributionSummary", () => Promise.all([
    requestJson("/api/pis/attribution/latest"),
    requestJson("/api/pis/attribution/history"),
    requestJson("/api/pis/attribution-summary"),
  ]), ([attributionLatest, attributionHistory, attributionSummary]) => {
    executiveState.attributionLatest = attributionLatest || { summary: null, records: [], top_winning_recommendations: [], top_losing_recommendations: [], source_performance: [] };
    renderExecutiveCards();
    renderAttributionSummary(attributionLatest || {}, attributionHistory || {}, attributionSummary || {});
  });

  runSectionTask("attributionWinners", () => requestJson("/api/pis/attribution/latest"), (attributionLatest) => {
    executiveState.attributionLatest = attributionLatest || { summary: null, records: [], top_winning_recommendations: [], top_losing_recommendations: [], source_performance: [] };
    renderExecutiveCards();
    renderAttributionWinners(attributionLatest || {});
  });

  runSectionTask("attributionLosers", () => requestJson("/api/pis/attribution/latest"), (attributionLatest) => {
    executiveState.attributionLatest = attributionLatest || { summary: null, records: [], top_winning_recommendations: [], top_losing_recommendations: [], source_performance: [] };
    renderExecutiveCards();
    renderAttributionLosers(attributionLatest || {});
  });

  runSectionTask("attributionSourcePerformance", () => requestJson("/api/pis/attribution/latest"), (attributionLatest) => {
    executiveState.attributionLatest = attributionLatest || { summary: null, records: [], top_winning_recommendations: [], top_losing_recommendations: [], source_performance: [] };
    renderExecutiveCards();
    renderAttributionSourcePerformance(attributionLatest || {});
  });

  runSectionTask("benchmarkSummary", () => requestJson("/api/pis/benchmark-attribution/latest"), (benchmarkLatest) => {
    executiveState.benchmarkLatest = benchmarkLatest || { benchmark_symbol: "SPY", alignment_policy: "NEAREST_PRIOR_TRADING_DAY", latest_portfolio_excess_return: null, top_positive_alpha_recommendations: [], worst_negative_alpha_recommendations: [], source_alpha_ranking: [], quality: {} };
    renderExecutiveCards();
    renderBenchmarkSummary(benchmarkLatest || {});
  });

  runSectionTask("benchmarkTrend", () => requestJson("/api/pis/benchmark-attribution/returns"), (benchmarkReturns) => {
    executiveState.benchmarkSeries = benchmarkReturns || { benchmark_symbol: "SPY", series: [] };
    renderBenchmarkTrend(benchmarkReturns || {});
  });

  runSectionTask("benchmarkTopAlpha", () => requestJson("/api/pis/benchmark-attribution/latest"), (benchmarkLatest) => {
    executiveState.benchmarkLatest = benchmarkLatest || { benchmark_symbol: "SPY", alignment_policy: "NEAREST_PRIOR_TRADING_DAY", latest_portfolio_excess_return: null, top_positive_alpha_recommendations: [], worst_negative_alpha_recommendations: [], source_alpha_ranking: [], quality: {} };
    renderBenchmarkTopAlpha(benchmarkLatest || {});
  });

  runSectionTask("benchmarkLowestAlpha", () => requestJson("/api/pis/benchmark-attribution/latest"), (benchmarkLatest) => {
    executiveState.benchmarkLatest = benchmarkLatest || { benchmark_symbol: "SPY", alignment_policy: "NEAREST_PRIOR_TRADING_DAY", latest_portfolio_excess_return: null, top_positive_alpha_recommendations: [], worst_negative_alpha_recommendations: [], source_alpha_ranking: [], quality: {} };
    renderBenchmarkLowestAlpha(benchmarkLatest || {});
  });

  runSectionTask("benchmarkSourceAlpha", () => requestJson("/api/pis/benchmark-attribution/sources"), (benchmarkSources) => {
    renderBenchmarkSourceAlpha(benchmarkSources || {});
  });

  runSectionTask("benchmarkQuality", () => requestJson("/api/pis/benchmark-attribution/latest"), (benchmarkLatest) => {
    renderBenchmarkQuality(benchmarkLatest || {});
  });
}

initialize();
