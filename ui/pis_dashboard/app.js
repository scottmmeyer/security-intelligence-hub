const SLOW_THRESHOLD_MS = 5000;
const REQUEST_TIMEOUT_MS = 12000;
const MIN_BANNER_VISIBLE_MS = 1200;
const PIS_BUILD_JS = "2026-06-23-runtime-01";
console.log("[PIS_BOOT] app.js loaded", { build: PIS_BUILD_JS });
window.__PIS_BUILD_JS__ = PIS_BUILD_JS;

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
  driftSummary: {
    label: "Allocation Drift Summary",
    targetIds: ["driftSummaryCards", "driftObservations"],
    loadingMessage: "Loading allocation drift summary...",
    slowMessage: "Drift summary is taking longer than expected...",
  },
  driftTrendTable: {
    label: "Drift Trend Table",
    targetIds: ["driftTrendTable"],
    loadingMessage: "Loading drift trend table...",
    slowMessage: "Drift trend table is taking longer than expected...",
  },
  driftWorsening: {
    label: "Top Worsening Nodes",
    targetIds: ["driftWorseningTable"],
    loadingMessage: "Loading worsening nodes...",
    slowMessage: "Worsening nodes taking longer than expected...",
  },
  driftImproving: {
    label: "Top Improving Nodes",
    targetIds: ["driftImprovingTable"],
    loadingMessage: "Loading improving nodes...",
    slowMessage: "Improving nodes taking longer than expected...",
  },
  actionAttributionSummary: {
    label: "Action Attribution Summary",
    targetIds: ["actionAttributionSummaryCards", "actionAttributionObservations"],
    loadingMessage: "Loading action attribution summary...",
    slowMessage: "Action attribution is taking longer than expected...",
  },
  actionAttributionTable: {
    label: "Recommendation Action Status",
    targetIds: ["actionAttributionTable"],
    loadingMessage: "Loading recommendation action status...",
    slowMessage: "Recommendation actions taking longer than expected...",
  },
  actionAttributionSources: {
    label: "Source Effectiveness",
    targetIds: ["actionAttributionSourcesTable"],
    loadingMessage: "Loading source effectiveness...",
    slowMessage: "Source effectiveness taking longer than expected...",
  },
  actionAttributionMissed: {
    label: "Missed Opportunities",
    targetIds: ["actionAttributionMissedTable"],
    loadingMessage: "Loading missed opportunities...",
    slowMessage: "Missed opportunities taking longer than expected...",
  },
  dorSummary: {
    label: "DIL Outcome Summary",
    targetIds: ["dorSummaryCards", "dorObservations"],
    loadingMessage: "Loading DIL outcome summary...",
    slowMessage: "DIL outcome review taking longer than expected...",
  },
  dorCohorts: {
    label: "DIL Cohort Performance",
    targetIds: ["dorCohortTable"],
    loadingMessage: "Loading DIL cohort performance...",
    slowMessage: "DIL cohort data taking longer than expected...",
  },
  dorMissedWinners: {
    label: "Top Missed Winners",
    targetIds: ["dorMissedWinnersTable"],
    loadingMessage: "Loading missed winners...",
    slowMessage: "Missed winners taking longer than expected...",
  },
  dorFollowedWinners: {
    label: "Top Followed Winners",
    targetIds: ["dorFollowedWinnersTable"],
    loadingMessage: "Loading followed winners...",
    slowMessage: "Followed winners taking longer than expected...",
  },
  policyCurrent: {
    label: "Current Policy Summary",
    targetIds: ["policyCurrentCards", "policyCurrentNodes"],
    loadingMessage: "Loading policy summary...",
    slowMessage: "Policy data taking longer than expected...",
  },
  policyHistory: {
    label: "Policy Version Timeline",
    targetIds: ["policyHistoryTable"],
    loadingMessage: "Loading policy history...",
    slowMessage: "Policy history taking longer than expected...",
  },
  policyDiff: {
    label: "Policy Diff Viewer",
    targetIds: ["policyDiffTable"],
    loadingMessage: "Loading policy diff...",
    slowMessage: "Policy diff taking longer than expected...",
  },
  policyGovObs: {
    label: "Policy Governance Observations",
    targetIds: ["policyGovObs"],
    loadingMessage: "Loading governance observations...",
    slowMessage: "Governance observations taking longer than expected...",
  },
  policyChangeSummary: {
    label: "AI-004B: Policy Change Summary",
    targetIds: ["policyChangeSummaryEl"],
    loadingMessage: "Loading policy change summary...",
    slowMessage: "Policy change summary loading...",
  },
  policyImpact: {
    label: "AI-004B: Recommendation Impact",
    targetIds: ["policyImpactEl"],
    loadingMessage: "Loading policy impact...",
    slowMessage: "Policy impact loading...",
  },
  policyTimeline: {
    label: "AI-004B: Policy Timeline",
    targetIds: ["policyTimelineEl"],
    loadingMessage: "Loading policy timeline...",
    slowMessage: "Policy timeline loading...",
  },
  complianceSummary: {
    label: "Compliance Summary",
    targetIds: ["complianceSummaryCards", "complianceTopViolations"],
    loadingMessage: "Loading compliance summary...",
    slowMessage: "Compliance summary taking longer than expected...",
  },
  complianceLeaderboard: {
    label: "Compliance Leaderboard",
    targetIds: ["complianceLeaderboardTable"],
    loadingMessage: "Loading compliance leaderboard...",
    slowMessage: "Compliance leaderboard taking longer than expected...",
  },
  complianceViolations: {
    label: "Persistent Violations",
    targetIds: ["complianceViolationsTable"],
    loadingMessage: "Loading violations...",
    slowMessage: "Violations taking longer than expected...",
  },
  complianceBest: {
    label: "Most Compliant Nodes",
    targetIds: ["complianceBestTable"],
    loadingMessage: "Loading most compliant nodes...",
    slowMessage: "Most compliant nodes taking longer than expected...",
  },
  // MEI: Market Event Intelligence
  meiCalendarSummary: {
    label: "MEI: Event Calendar",
    targetIds: ["meiCalendarCards", "meiCalendarObservations"],
    loadingMessage: "Loading market event calendar...",
    slowMessage: "Event calendar is taking longer than expected...",
  },
  meiCalendarTable: {
    label: "MEI: Upcoming Events",
    targetIds: ["meiCalendarTable"],
    loadingMessage: "Loading upcoming events...",
    slowMessage: "Upcoming events taking longer than expected...",
  },
  meiExposuresSummary: {
    label: "MEI: Portfolio Exposure Summary",
    targetIds: ["meiExposuresSummaryCards"],
    loadingMessage: "Loading exposure summary...",
    slowMessage: "Exposure summary taking longer than expected...",
  },
  meiExposuresTable: {
    label: "MEI: Event Exposure Detail",
    targetIds: ["meiExposuresTable"],
    loadingMessage: "Loading event exposure detail...",
    slowMessage: "Exposure detail taking longer than expected...",
  },
  meiContextSummary: {
    label: "MEI: Recommendation Event Context",
    targetIds: ["meiContextSummaryCards", "meiContextObservations"],
    loadingMessage: "Loading recommendation context...",
    slowMessage: "Recommendation context taking longer than expected...",
  },
  meiContextTable: {
    label: "MEI: Recommendation Context Detail",
    targetIds: ["meiContextTable"],
    loadingMessage: "Loading recommendation context detail...",
    slowMessage: "Recommendation context detail taking longer than expected...",
  },
  meiHistory: {
    label: "MEI: Event Impact History",
    targetIds: ["meiHistoryCards", "meiHistoryTable"],
    loadingMessage: "Loading event impact history...",
    slowMessage: "Event history taking longer than expected...",
  },
  meiOutcomeSummary: {
    label: "MEI-002: Event Outcome Summary",
    targetIds: ["meiOutcomeCards"],
    loadingMessage: "Loading event outcome summary...",
    slowMessage: "Outcome data loading...",
  },
  meiOutcomeTable: {
    label: "MEI-002: Historical Event Outcomes",
    targetIds: ["meiOutcomeTable"],
    loadingMessage: "Loading historical outcomes...",
    slowMessage: "Outcome table loading...",
  },
  meiEventImpact: {
    label: "MEI-002: Event Type Effectiveness",
    targetIds: ["meiEventImpactTable"],
    loadingMessage: "Loading event effectiveness...",
    slowMessage: "Effectiveness data loading...",
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
  allocationDrift: {
    label: "Allocation Drift Trends",
    sectionKeys: ["driftSummary", "driftTrendTable", "driftWorsening", "driftImproving"],
  },
  actionAttribution: {
    label: "Recommendation Action Attribution",
    sectionKeys: ["actionAttributionSummary", "actionAttributionTable", "actionAttributionSources", "actionAttributionMissed"],
  },
  dislocationOutcomeReview: {
    label: "Dislocation Outcome Review",
    sectionKeys: ["dorSummary", "dorCohorts", "dorMissedWinners", "dorFollowedWinners"],
  },
  allocationPolicyGovernance: {
    label: "Allocation Policy Governance",
    sectionKeys: ["policyCurrent", "policyHistory", "policyDiff", "policyGovObs", "policyChangeSummary", "policyImpact", "policyTimeline"],
  },
  allocationCompliance: {
    label: "Allocation Compliance Intelligence",
    sectionKeys: ["complianceSummary", "complianceLeaderboard", "complianceViolations", "complianceBest"],
  },
  marketEventIntelligence: {
    label: "Market Event Intelligence",
    sectionKeys: ["meiCalendarSummary", "meiCalendarTable", "meiExposuresSummary", "meiExposuresTable", "meiContextSummary", "meiContextTable", "meiHistory", "meiOutcomeSummary", "meiOutcomeTable", "meiEventImpact"],
  },
};

const requestCache = new Map();
const sectionStates = {};
const sectionErrors = {};
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

function asSignedPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "-";
  return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
}

function escHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function elapsedSeconds() {
  return ((Date.now() - dashboardStartedAt) / 1000).toFixed(1);
}

function getHtmlBuildMarker() {
  const markerNode = document.getElementById("pisBuildMarkerHtml");
  return markerNode ? String(markerNode.textContent || "").trim() : "UNKNOWN";
}

function formatErrorReason(error) {
  if (!error) return "Unknown error.";
  const message = error.message || String(error);
  const requestPath = error.requestPath ? `Endpoint: ${error.requestPath}. ` : "";
  if (message.includes("Request timeout")) {
    return `${requestPath}Request timed out while waiting for the server.`;
  }
  return `${requestPath}${message}`;
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
    setTimeout(() => {
      const timeoutError = new Error(`Request timeout after ${timeoutMs}ms for ${path}`);
      timeoutError.requestPath = path;
      reject(timeoutError);
    }, timeoutMs);
  });
  let response;
  try {
    response = await Promise.race([
      fetch(path, { cache: "no-store" }),
      timeoutPromise,
    ]);
  } catch (error) {
    if (error && !error.requestPath) {
      error.requestPath = path;
    }
    throw error;
  }
  if (!response.ok) {
    const httpError = new Error(`Failed to load ${path} (HTTP ${response.status})`);
    httpError.requestPath = path;
    throw httpError;
  }
  try {
    return await response.json();
  } catch (_error) {
    const parseError = new Error(`Invalid JSON response from ${path}`);
    parseError.requestPath = path;
    throw parseError;
  }
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
  const totalSections = Object.keys(SECTION_DEFINITIONS).length;
  const completedSections = Object.values(sectionStates).filter((status) => status === STATUS_LOADED || status === STATUS_FAILED).length;
  const failedSections = Object.values(sectionStates).filter((status) => status === STATUS_FAILED).length;
  const fullyCompleted = totalSections > 0 && completedSections >= totalSections;
  const loadOutcome = !fullyCompleted
    ? "Loading"
    : anyFailed
      ? "Loaded with unavailable sections"
      : anySlow
        ? "Loaded with warnings"
        : "Loaded";
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

  const failedDiagnostics = Object.entries(sectionErrors)
    .filter(([, error]) => Boolean(error))
    .map(([sectionKey, error]) => {
      const label = (SECTION_DEFINITIONS[sectionKey] && SECTION_DEFINITIONS[sectionKey].label) || sectionKey;
      return `<li class="metric-item"><span>${label}</span><strong>${formatErrorReason(error)}</strong></li>`;
    })
    .join("");

  const firstFailedEntry = Object.entries(sectionErrors).find(([, error]) => Boolean(error));
  const firstFailedSection = firstFailedEntry ? firstFailedEntry[0] : "-";
  const firstFailedEndpoint = firstFailedEntry && firstFailedEntry[1] && firstFailedEntry[1].requestPath
    ? String(firstFailedEntry[1].requestPath)
    : "-";
  const firstFailedMessage = firstFailedEntry ? formatErrorReason(firstFailedEntry[1]) : "-";
  const cacheBusted = window.location.search.includes("v=") ? "YES" : "NO";

  const diagnosticsHtml = failedDiagnostics
    ? `
      <details class="detail-toggle" style="margin-top:12px;">
        <summary>Section diagnostics</summary>
        <ul class="metric-list" style="margin-top:8px;">${failedDiagnostics}</ul>
      </details>
    `
    : `<p class="status-note" style="margin-top:10px;">No section-level diagnostics to report.</p>`;

  const bootInfoHtml = `
    <ul class="metric-list" style="margin-top:10px;">
      <li class="metric-item"><span>JS build marker</span><strong>${PIS_BUILD_JS}</strong></li>
      <li class="metric-item"><span>HTML build marker</span><strong>${getHtmlBuildMarker() || "UNKNOWN"}</strong></li>
      <li class="metric-item"><span>Sections planned</span><strong>${totalSections}</strong></li>
      <li class="metric-item"><span>Sections completed</span><strong>${completedSections}</strong></li>
      <li class="metric-item"><span>Sections failed</span><strong>${failedSections}</strong></li>
      <li class="metric-item"><span>First failed section</span><strong>${firstFailedSection}</strong></li>
      <li class="metric-item"><span>Failed endpoint</span><strong>${firstFailedEndpoint}</strong></li>
      <li class="metric-item"><span>First failure message</span><strong>${firstFailedMessage}</strong></li>
      <li class="metric-item"><span>Cache-busted URL detected</span><strong>${cacheBusted}</strong></li>
    </ul>
  `;

  node.innerHTML = `
    <div class="dashboard-status-header">
      <div>
        <h2>System Status</h2>
        <p class="subtitle">Current subsystem visibility across dashboard sections.</p>
        <div class="health-overall"><span class="section-badge ${overallClass}">${overallLabel}</span></div>
        <p class="status-note">Dashboard load outcome: <strong>${loadOutcome}</strong></p>
      </div>
    </div>
    <ul class="dashboard-status-list">${rows}</ul>
    ${bootInfoHtml}
    ${diagnosticsHtml}
  `;
}

function renderStartupFailure(error) {
  const banner = document.getElementById("dashboardLoadingBanner");
  const statusPanel = document.getElementById("dashboardStatusPanel");
  const stack = String((error && error.stack) || "").split("\n").slice(0, 5).join("\n");
  const message = formatErrorReason(error);

  if (banner) {
    banner.classList.remove("hidden");
    banner.innerHTML = `
      <div>
        <div class="dashboard-banner-title">Dashboard failed during startup</div>
        <div class="dashboard-banner-text">${message}</div>
        <div class="dashboard-banner-meta">JS build: ${PIS_BUILD_JS} | HTML build: ${getHtmlBuildMarker() || "UNKNOWN"}</div>
      </div>
    `;
  }

  if (statusPanel) {
    statusPanel.innerHTML = `
      <div class="dashboard-status-header">
        <div>
          <h2>Startup Failure Diagnostics</h2>
          <p class="subtitle">Dashboard failed during startup.</p>
          <div class="health-overall"><span class="section-badge section-badge-failed">FAILED</span></div>
        </div>
      </div>
      <ul class="metric-list" style="margin-top:10px;">
        <li class="metric-item"><span>Message</span><strong>${message}</strong></li>
        <li class="metric-item"><span>JS build marker</span><strong>${PIS_BUILD_JS}</strong></li>
        <li class="metric-item"><span>HTML build marker</span><strong>${getHtmlBuildMarker() || "UNKNOWN"}</strong></li>
        <li class="metric-item"><span>Sections planned</span><strong>${Object.keys(SECTION_DEFINITIONS).length}</strong></li>
        <li class="metric-item"><span>Sections completed</span><strong>0</strong></li>
      </ul>
      <details class="detail-toggle" open>
        <summary>Startup stack trace (first 5 lines)</summary>
        <pre style="white-space:pre-wrap;font-size:0.8rem;">${stack || "No stack trace available."}</pre>
      </details>
    `;
  }

  console.error("[PIS_BOOT] startup failed", {
    build: PIS_BUILD_JS,
    htmlBuild: getHtmlBuildMarker(),
    message,
    stack,
  });
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

function _timelineReturn(points, days) {
  if (!Array.isArray(points) || points.length < 2) return null;
  const latest = points[0];
  const targetMs = latest.date.getTime() - (days * 24 * 60 * 60 * 1000);
  const baseline = points.find((point) => point.date.getTime() <= targetMs);
  if (!baseline || baseline.value === 0) return null;
  return ((latest.value - baseline.value) / baseline.value) * 100;
}

function renderPerformanceReturnsCard() {
  const node = document.getElementById("performanceReturnsCard");
  if (!node) return;

  const points = (executiveState.timeline || [])
    .map((row) => {
      const value = Number(row.portfolio_value);
      const snapshotDate = String(row.snapshot_date || "");
      const dateObj = new Date(snapshotDate);
      if (!Number.isFinite(value) || Number.isNaN(dateObj.getTime())) return null;
      return { value, date: dateObj, snapshotDate };
    })
    .filter(Boolean)
    .sort((a, b) => b.date.getTime() - a.date.getTime());

  if (points.length < 2) {
    node.innerHTML = `
      <ul class="metric-list">
        <li class="metric-item"><span>Performance Status</span><strong>Unavailable / validation pending</strong></li>
        <li class="metric-item"><span>Reason</span><strong>Insufficient snapshot history</strong></li>
        <li class="metric-item"><span>Performance Confidence</span><strong>Unavailable</strong></li>
      </ul>
      <p class="status-note">Performance return is shown as a snapshot-based estimate because external cash flows have not yet been fully reconciled. Do not treat as final performance attribution.</p>
    `;
    return;
  }

  const latest = points[0];
  const start = points[points.length - 1];
  const absoluteChange = latest.value - start.value;
  const totalReturn = start.value !== 0 ? ((absoluteChange / start.value) * 100) : null;
  const return1d = _timelineReturn(points, 1);
  const return5d = _timelineReturn(points, 5);
  const return1m = _timelineReturn(points, 30);

  const benchmarkLatest = (executiveState.benchmarkLatest || {}).latest_portfolio_excess_return || {};
  const benchmarkExcess = Number(benchmarkLatest.excess_return_pct);

  node.innerHTML = `
    <ul class="metric-list">
      <li class="metric-item"><span>Latest Portfolio Value</span><strong>${asCurrency(latest.value)}</strong></li>
      <li class="metric-item"><span>Start Value (first snapshot)</span><strong>${asCurrency(start.value)}</strong></li>
      <li class="metric-item"><span>Absolute Gain/Loss</span><strong>${asSignedCurrency(absoluteChange)}</strong></li>
      <li class="metric-item"><span>Total Return</span><strong>${Number.isFinite(totalReturn) ? asSignedPercent(totalReturn) : "Unavailable / validation pending"}</strong></li>
      <li class="metric-item"><span>1D Return</span><strong>${Number.isFinite(return1d) ? asSignedPercent(return1d) : "Unavailable / validation pending"}</strong></li>
      <li class="metric-item"><span>5D Return</span><strong>${Number.isFinite(return5d) ? asSignedPercent(return5d) : "Unavailable / validation pending"}</strong></li>
      <li class="metric-item"><span>1M Return</span><strong>${Number.isFinite(return1m) ? asSignedPercent(return1m) : "Unavailable / validation pending"}</strong></li>
      <li class="metric-item"><span>Since Inception Return</span><strong>${Number.isFinite(totalReturn) ? asSignedPercent(totalReturn) : "Unavailable / validation pending"}</strong></li>
      <li class="metric-item"><span>Benchmark Comparison (excess)</span><strong>${Number.isFinite(benchmarkExcess) ? asSignedPercent(benchmarkExcess) : "Unavailable / validation pending"}</strong></li>
      <li class="metric-item"><span>Performance Confidence</span><strong>Snapshot-based estimate (cash-flow-unadjusted)</strong></li>
    </ul>
    <p class="status-note">Performance return is shown as a snapshot-based estimate because external cash flows have not yet been fully reconciled. Do not treat as final performance attribution.</p>
    <p class="status-note">Window anchor: ${latest.snapshotDate} vs ${start.snapshotDate}.</p>
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
  renderPerformanceReturnsCard();
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
  sectionErrors[sectionKey] = null;
  setSectionState(sectionKey, STATUS_LOADING);
}

function markSectionSlow(sectionKey) {
  if (sectionStates[sectionKey] === STATUS_LOADING) {
    setSectionState(sectionKey, STATUS_SLOW);
  }
}

function completeSection(sectionKey) {
  sectionErrors[sectionKey] = null;
  sectionStates[sectionKey] = STATUS_LOADED;
  updateSectionBadge(sectionKey, STATUS_LOADED);
  updateSubsystemStatuses();
  updateDashboardBanner();
}

function failSection(sectionKey, error) {
  sectionErrors[sectionKey] = error || new Error("Unknown section failure.");
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
      console.error(`[PIS Dashboard] Section ${sectionKey} failed`, {
        sectionKey,
        endpoint: error && error.requestPath ? error.requestPath : null,
        message: error && error.message ? error.message : String(error),
      });
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

// ─── PIS-007: Allocation Drift Trend render functions ─────────────────────────

function _driftBadge(direction) {
  if (direction === "WORSENING") return '<span class="section-badge" style="background:#c62828;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.78em;">WORSENING</span>';
  if (direction === "IMPROVING") return '<span class="section-badge" style="background:#2e7d32;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.78em;">IMPROVING</span>';
  return '<span class="section-badge" style="background:#666;color:#fff;padding:2px 8px;border-radius:4px;font-size:0.78em;">STABLE</span>';
}

function _severityBadge(severity) {
  const colors = { SIGNIFICANT: "#b71c1c", MODERATE: "#e65100", MINOR: "#f9a825", NONE: "#aaa" };
  const color = colors[severity] || "#aaa";
  return `<span style="color:${color};font-weight:600;font-size:0.8em;">${severity}</span>`;
}

function _driftPpDisplay(val) {
  if (val == null) return "-";
  const n = parseFloat(val);
  if (isNaN(n)) return "-";
  const color = n > 0.05 ? "#e65100" : n < -0.05 ? "#1565c0" : "#2e7d32";
  return `<span style="color:${color};font-weight:600;">${n >= 0 ? "+" : ""}${n.toFixed(2)}pp</span>`;
}

function renderDriftSummary(payload) {
  const cards = [
    { label: "Dates Available", value: String(payload.dates_available || 0) },
    { label: "Improving Nodes", value: String(payload.improving_count || 0), color: "#2e7d32" },
    { label: "Worsening Nodes", value: String(payload.worsening_count || 0), color: "#c62828" },
    { label: "Stable Nodes",    value: String(payload.stable_count || 0) },
  ];
  const dateRange = payload.current_date
    ? `<p style="color:#666;font-size:0.85em;margin:0 0 12px;">Analysis range through <strong>${payload.current_date}</strong>${payload.prior_date ? ` — prior date: ${payload.prior_date}` : ""}</p>`
    : "";

  let mostImprovedHtml = "";
  if (payload.most_improved_node) {
    const n = payload.most_improved_node;
    mostImprovedHtml = `<div style="padding:10px 14px;background:#e8f5e9;border-left:4px solid #2e7d32;margin-bottom:8px;">
      <strong style="color:#2e7d32;">Most Improved:</strong> ${escHtml(n.node_label || n.node_key)}
      — drift ${_driftPpDisplay(n.prior_drift_pct)} → ${_driftPpDisplay(n.current_drift_pct)}
    </div>`;
  }
  let mostDetHtml = "";
  if (payload.most_deteriorated_node) {
    const n = payload.most_deteriorated_node;
    mostDetHtml = `<div style="padding:10px 14px;background:#ffebee;border-left:4px solid #c62828;margin-bottom:8px;">
      <strong style="color:#c62828;">Most Deteriorated:</strong> ${escHtml(n.node_label || n.node_key)}
      — drift ${_driftPpDisplay(n.prior_drift_pct)} → ${_driftPpDisplay(n.current_drift_pct)}
    </div>`;
  }

  const cardHtml = cards.map(c =>
    `<div style="background:#f5f5f5;border-radius:6px;padding:14px 20px;min-width:110px;text-align:center;display:inline-block;margin:4px 6px 4px 0;">
      <div style="font-size:1.6em;font-weight:700;${c.color ? `color:${c.color};` : ""}">${escHtml(c.value)}</div>
      <div style="font-size:0.78em;color:#666;margin-top:2px;">${escHtml(c.label)}</div>
    </div>`
  ).join("");

  const el = document.getElementById("driftSummaryCards");
  if (el) el.innerHTML = dateRange + `<div style="margin-bottom:12px;">${cardHtml}</div>` + mostImprovedHtml + mostDetHtml;

  // Observations
  const obsEl = document.getElementById("driftObservations");
  if (obsEl) {
    const obs = payload.observations || [];
    if (obs.length === 0) {
      obsEl.innerHTML = "<p style='color:#888;font-size:0.9em;'>No notable drift observations for this period.</p>";
    } else {
      const items = obs.map(o => `<li style="margin-bottom:6px;">${escHtml(o)}</li>`).join("");
      obsEl.innerHTML = `<p style="font-weight:600;margin-bottom:8px;">Key Observations</p><ul style="padding-left:18px;margin:0;">${items}</ul>`;
    }
  }
}

function renderDriftTrendTable(payload) {
  const nodes = payload.nodes || [];
  const rows = nodes.map((n) => [
    escHtml(n.node_key || "-"),
    escHtml(n.node_label || "-"),
    _driftPpDisplay(n.current_drift_pct),
    n.prior_drift_pct != null ? _driftPpDisplay(n.prior_drift_pct) : "-",
    n.drift_delta_pp != null ? _driftPpDisplay(n.drift_delta_pp) : "-",
    _driftBadge(n.trend_direction),
    _severityBadge(n.trend_severity),
    n.drift_velocity_pp_per_day != null
      ? `${parseFloat(n.drift_velocity_pp_per_day) >= 0 ? "+" : ""}${parseFloat(n.drift_velocity_pp_per_day).toFixed(3)}pp/d`
      : "-",
    String(n.dates_available || 0),
  ]);
  renderTable(
    "driftTrendTable",
    ["Node Key", "Label", "Current Drift", "Prior Drift", "Drift Delta", "Trend", "Severity", "Velocity", "Dates"],
    rows,
    { rawHtml: true },
  );
}

function renderDriftTopNodes(targetId, nodes, direction) {
  const top5 = nodes
    .sort((a, b) => Math.abs(b.magnitude_delta_pp || 0) - Math.abs(a.magnitude_delta_pp || 0))
    .slice(0, 5);
  if (top5.length === 0) {
    const el = document.getElementById(targetId);
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No ${direction.toLowerCase()} nodes detected.</p>`;
    return;
  }
  const rows = top5.map((n) => [
    escHtml(n.node_key || "-"),
    escHtml(n.node_label || "-"),
    _driftPpDisplay(n.current_drift_pct),
    n.prior_drift_pct != null ? _driftPpDisplay(n.prior_drift_pct) : "-",
    n.magnitude_delta_pp != null ? _driftPpDisplay(n.magnitude_delta_pp) : "-",
    _severityBadge(n.trend_severity),
  ]);
  renderTable(
    targetId,
    ["Node Key", "Label", "Current Drift", "Prior Drift", "Magnitude Δ", "Severity"],
    rows,
    { rawHtml: true },
  );
}

// ─── PIS-008: Action Attribution render functions ─────────────────────────────

function _statusBadge(status) {
  const cfg = {
    FOLLOWED:           { bg: "#2e7d32", label: "FOLLOWED" },
    PARTIALLY_FOLLOWED: { bg: "#558b2f", label: "PARTIAL" },
    IGNORED:            { bg: "#757575", label: "IGNORED" },
    OPPOSED:            { bg: "#c62828", label: "OPPOSED" },
    EXPIRED:            { bg: "#e65100", label: "EXPIRED" },
  };
  const c = cfg[status] || { bg: "#999", label: status || "UNKNOWN" };
  return `<span style="background:${c.bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.78em;font-weight:600;">${c.label}</span>`;
}

function _confBadge(conf) {
  const colors = { HIGH: "#1b5e20", MEDIUM: "#1565c0", LOW: "#e65100", NONE: "#999" };
  const color = colors[conf] || "#999";
  return `<span style="color:${color};font-size:0.8em;font-weight:600;">${conf || "—"}</span>`;
}

function renderActionAttributionSummary(payload) {
  const cards = [
    { label: "Total Records",      value: String(payload.total_attribution_records || 0) },
    { label: "Followed",           value: String(payload.followed_count || 0),           color: "#2e7d32" },
    { label: "Partially Followed", value: String(payload.partially_followed_count || 0), color: "#558b2f" },
    { label: "Ignored",            value: String(payload.ignored_count || 0),            color: "#757575" },
    { label: "Opposed",            value: String(payload.opposed_count || 0),            color: "#c62828" },
    { label: "Expired",            value: String(payload.expired_count || 0),            color: "#e65100" },
  ];
  const rates = [
    { label: "Follow Rate",  value: (payload.follow_rate_pct  || 0).toFixed(1) + "%" },
    { label: "Ignore Rate",  value: (payload.ignore_rate_pct  || 0).toFixed(1) + "%" },
    { label: "Oppose Rate",  value: (payload.oppose_rate_pct  || 0).toFixed(1) + "%" },
    { label: "Avg Response", value: payload.avg_response_days != null ? payload.avg_response_days + "d" : "—" },
    { label: "Sources",      value: (payload.sources_covered || []).join(", ") || "—" },
  ];
  const cardHtml = cards.map(c =>
    `<div style="background:#f5f5f5;border-radius:6px;padding:12px 18px;min-width:90px;text-align:center;display:inline-block;margin:4px 6px 4px 0;">
      <div style="font-size:1.5em;font-weight:700;${c.color ? `color:${c.color};` : ""}">${escHtml(c.value)}</div>
      <div style="font-size:0.75em;color:#666;margin-top:2px;">${escHtml(c.label)}</div>
    </div>`
  ).join("");
  const rateHtml = rates.map(r =>
    `<span style="margin-right:16px;font-size:0.9em;"><strong>${escHtml(r.label)}:</strong> ${escHtml(r.value)}</span>`
  ).join("");

  const el = document.getElementById("actionAttributionSummaryCards");
  if (el) el.innerHTML = `<div style="margin-bottom:10px;">${cardHtml}</div><div style="color:#555;margin-top:6px;">${rateHtml}</div>`;

  const obsEl = document.getElementById("actionAttributionObservations");
  if (obsEl) {
    const obs = payload.observations || [];
    if (obs.length === 0) {
      obsEl.innerHTML = "<p style='color:#888;font-size:0.9em;'>No action attribution observations available.</p>";
    } else {
      obsEl.innerHTML = `<ul style="padding-left:18px;margin:8px 0;">${obs.map(o => `<li style="margin-bottom:5px;">${escHtml(o)}</li>`).join("")}</ul>`;
    }
  }
}

function renderActionAttributionTable(payload) {
  const records = (payload.records || []).slice(0, 100);  // cap display at 100
  const rows = records.map(r => [
    escHtml(r.recommendation_id || "—"),
    escHtml(r.recommendation_source || "—"),
    escHtml(r.symbol || "—"),
    escHtml(r.recommended_direction || "—"),
    _statusBadge(r.action_status),
    _confBadge(r.action_confidence),
    r.response_days != null ? String(r.response_days) + "d" : "—",
    escHtml(r.outcome || "—"),
    escHtml(r.recommendation_date || "—"),
  ]);
  renderTable(
    "actionAttributionTable",
    ["Rec ID", "Source", "Symbol", "Direction", "Status", "Confidence", "Delay", "Outcome", "Rec Date"],
    rows,
    { rawHtml: true },
  );
}

function renderActionAttributionSources(payload) {
  const scorecards = payload.scorecards || [];
  const rows = scorecards.map(s => [
    escHtml(s.source || "—"),
    String(s.total_recommendations || 0),
    `<span style="color:#2e7d32;font-weight:600;">${(s.follow_rate_pct || 0).toFixed(1)}%</span>`,
    `<span style="color:#757575;">${(s.ignore_rate_pct || 0).toFixed(1)}%</span>`,
    `<span style="color:#c62828;">${(s.oppose_rate_pct || 0).toFixed(1)}%</span>`,
    s.avg_response_days != null ? s.avg_response_days + "d" : "—",
    s.winner_count != null ? `${s.winner_count}W / ${s.loser_count}L` : "—",
    s.win_rate_pct != null ? `${s.win_rate_pct.toFixed(1)}%` : "—",
  ]);
  renderTable(
    "actionAttributionSourcesTable",
    ["Source", "Total", "Follow Rate", "Ignore Rate", "Oppose Rate", "Avg Delay", "W/L", "Win Rate"],
    rows,
    { rawHtml: true },
  );
}

function renderActionAttributionMissed(payload) {
  const missed = payload.missed_opportunities || [];
  if (missed.length === 0) {
    const el = document.getElementById("actionAttributionMissedTable");
    if (el) el.innerHTML = "<p style='color:#888;font-size:0.9em;'>No missed opportunities detected.</p>";
    return;
  }
  const rows = missed.map(m => [
    escHtml(m.recommendation_id || "—"),
    escHtml(m.symbol || "—"),
    escHtml(m.recommendation_source || "—"),
    escHtml(m.recommended_direction || "—"),
    `<span style="color:#c62828;font-weight:600;">${escHtml(m.outcome || "—")}</span>`,
    escHtml(m.recommendation_date || "—"),
  ]);
  renderTable(
    "actionAttributionMissedTable",
    ["Rec ID", "Symbol", "Source", "Direction", "Outcome", "Rec Date"],
    rows,
    { rawHtml: true },
  );
}

// ─── ISSUE-12D: Dislocation Outcome Review render functions ───────────────────

const _UCF_LABEL_COLORS = {
  CORE_CONVICTION_LEADER: "#1b5e20",
  HIGH_CONVICTION_ANCHOR: "#2e7d32",
  DEPLOYMENT_CANDIDATE:   "#388e3c",
  TRIM_WATCH:             "#c62828",
};

function _ucfBadge(label) {
  const color = _UCF_LABEL_COLORS[label] || "#555";
  const short = (label || "").replace("_", " ");
  return `<span style="color:${color};font-weight:600;font-size:0.82em;">${short}</span>`;
}

function _govFlagBadges(flags) {
  if (!flags || !flags.length) return "<span style='color:#aaa;font-size:0.8em;'>—</span>";
  const colors = { MISSED_WINNER: "#c62828", FOLLOWED_LOSER: "#e65100", SIGNAL_CONFLICT: "#f57c00" };
  return flags.map(f => {
    const c = colors[f] || "#555";
    return `<span style="color:${c};font-weight:600;font-size:0.78em;margin-right:4px;">${f.replace(/_/g,' ')}</span>`;
  }).join("");
}

function renderDORSummary(payload) {
  const cards = [
    { label: "Total DIL Records", value: String(payload.total_dil_records || 0) },
    { label: "Followed", value: String(payload.followed_count || 0), color: "#2e7d32" },
    { label: "Ignored",  value: String(payload.ignored_count  || 0), color: "#757575" },
    { label: "Winners",  value: String(payload.winner_count   || 0), color: "#1b5e20" },
    { label: "Losers",   value: String(payload.loser_count    || 0), color: "#c62828" },
    { label: "Dates",    value: String(payload.dates_covered  || 0) },
  ];
  const rates = [
    { label: "Follow Rate", value: (payload.follow_rate_pct || 0).toFixed(1) + "%" },
    { label: "Win Rate",    value: (payload.win_rate_pct    || 0).toFixed(1) + "%" },
    { label: "Avg Alpha",   value: (payload.avg_alpha_pct   || 0) > 0
        ? "+" + payload.avg_alpha_pct.toFixed(1) + "pp"
        : (payload.avg_alpha_pct || 0).toFixed(1) + "pp" },
    { label: "Missed Winners", value: String(payload.missed_winner_count || 0) },
  ];
  const cardHtml = cards.map(c =>
    `<div style="background:#f5f5f5;border-radius:6px;padding:12px 18px;min-width:90px;text-align:center;display:inline-block;margin:4px 6px 4px 0;">
      <div style="font-size:1.5em;font-weight:700;${c.color ? `color:${c.color};` : ""}">${escHtml(c.value)}</div>
      <div style="font-size:0.75em;color:#666;margin-top:2px;">${escHtml(c.label)}</div>
    </div>`
  ).join("");
  const rateHtml = rates.map(r =>
    `<span style="margin-right:16px;font-size:0.9em;"><strong>${escHtml(r.label)}:</strong> ${escHtml(r.value)}</span>`
  ).join("");

  const el = document.getElementById("dorSummaryCards");
  if (el) el.innerHTML = `<div style="margin-bottom:10px;">${cardHtml}</div><div style="color:#555;margin-top:6px;">${rateHtml}</div>`;

  const govFlags = payload.governance_flags || [];
  const obsEl = document.getElementById("dorObservations");
  if (obsEl) {
    let html = "";
    if (govFlags.length) {
      html += `<div style="margin-bottom:8px;">${govFlags.map(f => _govFlagBadges([f])).join(" ")}</div>`;
    }
    const obs = payload.observations || [];
    if (obs.length) {
      html += `<p style="font-weight:600;margin-bottom:6px;">Governance Observations</p>`;
      html += `<ul style="padding-left:18px;margin:0;">${obs.map(o => `<li style="margin-bottom:5px;">${escHtml(o)}</li>`).join("")}</ul>`;
    }
    if (!html) html = `<p style="color:#888;font-size:0.9em;">No governance observations available.</p>`;
    obsEl.innerHTML = html;
  }
}

function renderDORCohorts(payload) {
  const cohorts = payload.cohorts || [];
  const rows = cohorts.map(c => [
    _ucfBadge(c.ucf_label),
    escHtml(c.direction || "—"),
    String(c.total_count || 0),
    String(c.followed_count || 0),
    String(c.ignored_count || 0),
    `<span style="color:#2e7d32;font-weight:600;">${(c.follow_rate_pct || 0).toFixed(1)}%</span>`,
    String(c.winner_count || 0),
    String(c.loser_count || 0),
    `<span style="font-weight:600;">${(c.win_rate_pct || 0).toFixed(1)}%</span>`,
    (c.avg_alpha_pct || 0) !== 0 ? `${(c.avg_alpha_pct >= 0 ? "+" : "")}${c.avg_alpha_pct.toFixed(1)}pp` : "—",
    String(c.missed_winner_count || 0),
  ]);
  renderTable("dorCohortTable",
    ["UCF Label", "Dir", "Total", "Followed", "Ignored", "Follow%", "Winners", "Losers", "Win%", "Avg Alpha", "Missed W"],
    rows, { rawHtml: true });
}

function renderDORMissedWinners(payload) {
  const missed = payload.missed_winners || [];
  if (!missed.length) {
    const el = document.getElementById("dorMissedWinnersTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No missed winners identified in current observation window.</p>`;
    return;
  }
  const rows = missed.map(m => [
    escHtml(m.symbol || "—"),
    _ucfBadge(m.ucf_label),
    escHtml(m.snapshot_date || "—"),
    escHtml(m.recommended_direction || "—"),
    escHtml(m.signal_direction || "—"),
    `<span style="color:#2e7d32;font-weight:600;">${escHtml(m.outcome || "—")}</span>`,
    m.excess_return_pct ? `+${parseFloat(m.excess_return_pct).toFixed(1)}pp` : "—",
  ]);
  renderTable("dorMissedWinnersTable",
    ["Symbol", "UCF Label", "Date", "Direction", "Signal", "Outcome", "Alpha"],
    rows, { rawHtml: true });
}

function renderDORFollowedWinners(payload) {
  const records = (payload.records || []).filter(r => r.action_status === "FOLLOWED" && r.outcome === "WINNER").slice(0, 10);
  if (!records.length) {
    const el = document.getElementById("dorFollowedWinnersTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No followed winners in current observation window.</p>`;
    return;
  }
  const rows = records.map(r => [
    escHtml(r.symbol || "—"),
    _ucfBadge(r.ucf_label),
    escHtml(r.snapshot_date || "—"),
    escHtml(r.recommended_direction || "—"),
    `<span style="color:#2e7d32;font-weight:700;">${escHtml(r.outcome)}</span>`,
    r.excess_return_pct ? `+${parseFloat(r.excess_return_pct).toFixed(1)}pp` : "—",
    _govFlagBadges(r.governance_flags),
  ]);
  renderTable("dorFollowedWinnersTable",
    ["Symbol", "UCF Label", "Date", "Direction", "Outcome", "Alpha", "Flags"],
    rows, { rawHtml: true });
}

// ─── AI-004: Allocation Policy Governance render functions ────────────────────

function _directionBadge(dir) {
  const cfg = {
    INCREASED: { bg: "#2e7d32", label: "+" },
    DECREASED: { bg: "#c62828", label: "−" },
    ADDED:     { bg: "#1565c0", label: "NEW" },
    REMOVED:   { bg: "#757575", label: "DEL" },
  };
  const c = cfg[dir] || { bg: "#999", label: dir };
  return `<span style="background:${c.bg};color:#fff;padding:1px 7px;border-radius:3px;font-size:0.8em;font-weight:700;">${c.label}</span>`;
}

function renderPolicyCurrent(payload) {
  const cards = [
    { label: "Policy ID",       value: payload.policy_id || "—" },
    { label: "Methodology",     value: payload.methodology_id || "—" },
    { label: "Effective Date",  value: payload.effective_date || "—" },
    { label: "Config Hash",     value: (payload.config_hash || "—").substring(0, 10) },
    { label: "Node Count",      value: String(payload.node_count || 0) },
    { label: "Run Count",       value: String(payload.run_count || 0) },
  ];
  const cardHtml = cards.map(c =>
    `<div style="background:#f5f5f5;border-radius:6px;padding:12px 18px;min-width:110px;text-align:center;display:inline-block;margin:4px 6px 4px 0;">
      <div style="font-size:1.1em;font-weight:700;">${escHtml(c.value)}</div>
      <div style="font-size:0.75em;color:#666;margin-top:2px;">${escHtml(c.label)}</div>
    </div>`
  ).join("");

  const sp = payload.structural_policy || {};
  const constraintHtml = Object.keys(sp).length > 0
    ? `<div style="margin-top:10px;font-size:0.88em;color:#444;">
        ${Object.entries(sp).map(([k,v]) => `<span style="margin-right:12px;"><strong>${escHtml(k)}:</strong> ${escHtml(String(v))}</span>`).join("")}
       </div>`
    : "";

  const cardsEl = document.getElementById("policyCurrentCards");
  if (cardsEl) cardsEl.innerHTML = `<div>${cardHtml}</div>${constraintHtml}`;

  // Node targets summary table (top 10)
  const targets = payload.node_targets || {};
  const topNodes = Object.entries(targets)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);
  const nodeRows = topNodes.map(([k, v]) => [escHtml(k), `${parseFloat(v).toFixed(1)}%`]);
  const nodesEl = document.getElementById("policyCurrentNodes");
  if (nodesEl && nodeRows.length > 0) {
    const tbody = nodeRows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("");
    nodesEl.innerHTML = `<p style="font-weight:600;font-size:0.9em;margin:8px 0 4px;">Node Targets (top 12)</p><table><thead><tr><th>Node</th><th>Target %</th></tr></thead><tbody>${tbody}</tbody></table>`;
  }
}

function renderPolicyHistory(payload) {
  const versions = payload.versions || [];
  if (!versions.length) {
    const el = document.getElementById("policyHistoryTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No policy version history available.</p>`;
    return;
  }
  const rows = versions.map(v => [
    escHtml(v.fingerprint_id ? v.fingerprint_id.substring(0, 28) : "—"),
    escHtml(v.recalculation_id ? v.recalculation_id.substring(0, 24) : "—"),
    escHtml(v.first_seen_date || "—"),
    escHtml(v.last_seen_date || "—"),
    String(v.run_count || 0),
    String(v.node_count || 0),
  ]);
  renderTable("policyHistoryTable",
    ["Fingerprint", "Recalculation ID", "First Seen", "Last Seen", "Runs", "Nodes"],
    rows);
}

function renderPolicyDiff(payload) {
  const diffs = payload.diffs || [];
  if (!diffs.length || !payload.has_changes) {
    const el = document.getElementById("policyDiffTable");
    if (el) el.innerHTML = `<div style="background:#e8f5e9;padding:12px 16px;border-left:4px solid #2e7d32;border-radius:4px;">
      <strong style="color:#2e7d32;">No policy changes detected.</strong>
      A single allocation policy version has been active across all observed analysis runs.
      This panel will display target changes when a new policy recalculation occurs.
    </div>`;
    return;
  }
  const allRows = [];
  for (const diff of diffs) {
    for (const c of diff.changed_targets || []) {
      allRows.push([
        _directionBadge(c.change_direction),
        escHtml(c.node_key || "—"),
        `${parseFloat(c.from_pct || 0).toFixed(1)}%`,
        `${parseFloat(c.to_pct || 0).toFixed(1)}%`,
        `<span style="font-weight:600;color:${c.delta_pp > 0 ? '#2e7d32' : '#c62828'};">${c.delta_pp >= 0 ? "+" : ""}${parseFloat(c.delta_pp || 0).toFixed(2)}pp</span>`,
        escHtml(diff.from_date || "—"),
        escHtml(diff.to_date || "—"),
      ]);
    }
  }
  if (allRows.length) {
    renderTable("policyDiffTable",
      ["Change", "Node", "From", "To", "Delta", "From Date", "To Date"],
      allRows, { rawHtml: true });
  }
}

function renderPolicyGovObs(payload) {
  const obs = payload.observations || [];
  const el = document.getElementById("policyGovObs");
  if (!el) return;
  if (!obs.length) {
    el.innerHTML = `<p style="color:#888;font-size:0.9em;">No governance observations available.</p>`;
    return;
  }
  el.innerHTML = `<ul style="padding-left:18px;margin:0;">${obs.map(o => `<li style="margin-bottom:7px;">${escHtml(o)}</li>`).join("")}</ul>`;
}

// ─── AI-004B: Policy Change Intelligence render functions ─────────────────────

const _SEVERITY_COLORS = {
  STRUCTURAL: { bg: "#fdecea", border: "#c0392b", text: "#c0392b", badge: "STRUCTURAL" },
  MAJOR:      { bg: "#fff3cd", border: "#856404", text: "#856404", badge: "MAJOR" },
  MODERATE:   { bg: "#fff8e1", border: "#b8860b", text: "#b8860b", badge: "MODERATE" },
  MINOR:      { bg: "#f0f4f8", border: "#1a5c8a", text: "#1a5c8a", badge: "MINOR" },
  INITIAL:    { bg: "#e8f5e9", border: "#2e7d32", text: "#2e7d32", badge: "INITIAL" },
  STABLE:     { bg: "#e8f5e9", border: "#2e7d32", text: "#2e7d32", badge: "STABLE" },
  INFO:       { bg: "#e8f0fa", border: "#1a5c8a", text: "#1a5c8a", badge: "INFO" },
  OK:         { bg: "#e8f5e9", border: "#2e7d32", text: "#2e7d32", badge: "OK" },
  WARN:       { bg: "#fff3cd", border: "#856404", text: "#856404", badge: "WARN" },
};

function _severityBadge(sev) {
  const cfg = _SEVERITY_COLORS[sev] || _SEVERITY_COLORS.INFO;
  return `<span style="display:inline-block;border-radius:4px;padding:1px 8px;font-size:0.70rem;font-weight:700;background:${cfg.bg};color:${cfg.text};border:1px solid ${cfg.border}">${cfg.badge}</span>`;
}

function renderPolicyChangeSummary(payload) {
  const el = document.getElementById("policyChangeSummaryEl");
  if (!el) return;

  const hasChanges  = payload.has_changes;
  const severity    = payload.current_severity || "STABLE";
  const changeCount = payload.change_count || 0;
  const notifications = payload.notifications || [];
  const summaries   = payload.change_summaries || [];
  const govNote     = payload.governance_note || "";

  // Overview strip
  const cfg = _SEVERITY_COLORS[severity] || _SEVERITY_COLORS.STABLE;
  const overviewHtml = `<div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:14px;align-items:flex-start">
    <div class="kpi"><div class="kpi-label">Policy Versions</div><div class="kpi-value">${payload.change_count != null ? changeCount + 1 : "—"}</div></div>
    <div class="kpi"><div class="kpi-label">Changes Detected</div><div class="kpi-value">${changeCount}</div></div>
    <div class="kpi"><div class="kpi-label">Current Severity</div>
      <div class="kpi-value" style="font-size:1.0rem">${_severityBadge(severity)}</div></div>
    <div style="flex:1 1 220px;font-size:0.76rem;color:#666;padding:8px 12px;background:#f5f0e8;border-left:3px solid #c5d8ef;border-radius:0 4px 4px 0">${govNote}</div>
  </div>`;

  // Notification cards
  const notifHtml = notifications.map(n => {
    const nc = _SEVERITY_COLORS[n.severity] || _SEVERITY_COLORS.INFO;
    return `<div style="border-left:4px solid ${nc.border};background:${nc.bg};padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
        <span style="font-weight:700;font-size:0.84rem">${escHtml(n.title)}</span>
        ${_severityBadge(n.severity)}
        ${n.date ? `<span style="font-size:0.72rem;color:#888">${escHtml(n.date)}</span>` : ""}
      </div>
      <div style="font-size:0.78rem;color:#333">${escHtml(n.body)}</div>
    </div>`;
  }).join("");

  // Change summaries (if any)
  let changesHtml = "";
  if (summaries.length) {
    changesHtml = `<div style="font-weight:700;font-size:0.82rem;margin:12px 0 6px">Policy Version Transitions</div>`;
    changesHtml += summaries.map(s => {
      const changed = s.changed_targets || [];
      const topChanges = changed.slice(0, 5).map(c => {
        const dir = c.delta_pp >= 0
          ? `<span style="color:#2e7d32">↑ ${c.node_key}: ${c.from_pct.toFixed(1)}% → ${c.to_pct.toFixed(1)}% (+${c.delta_pp.toFixed(1)}pp)</span>`
          : `<span style="color:#c0392b">↓ ${c.node_key}: ${c.from_pct.toFixed(1)}% → ${c.to_pct.toFixed(1)}% (${c.delta_pp.toFixed(1)}pp)</span>`;
        return `<div style="font-size:0.76rem;margin:2px 0">${dir}</div>`;
      }).join("");
      return `<div style="border:1px solid #e0d8c8;border-radius:6px;padding:10px 14px;margin-bottom:8px;background:#fafaf8">
        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:6px">
          <span style="font-family:monospace;font-size:0.76rem">${escHtml((s.from_version_id||"?").slice(0,20))}</span>
          <span style="color:#888">→</span>
          <span style="font-family:monospace;font-size:0.76rem">${escHtml((s.to_version_id||"?").slice(0,20))}</span>
          ${_severityBadge(s.severity)}
          <span style="font-size:0.72rem;color:#888">${escHtml(s.from_date||"")} → ${escHtml(s.to_date||"")}</span>
          <span style="font-size:0.72rem;color:#888">${s.nodes_changed} node(s) changed</span>
        </div>
        ${topChanges}
        ${s.operator_note ? `<div style="margin-top:6px;font-size:0.76rem;color:#555;background:#f0f0e8;padding:4px 8px;border-radius:4px">${escHtml(s.operator_note)}</div>` : ""}
      </div>`;
    }).join("");
  } else {
    changesHtml = `<div style="background:#e8f5e9;padding:12px 16px;border-left:4px solid #2e7d32;border-radius:4px;font-size:0.82rem">
      <strong style="color:#2e7d32">Policy Stable</strong> — No allocation target changes detected across observed analysis runs.
    </div>`;
  }

  el.innerHTML = overviewHtml + notifHtml + changesHtml;
}

function renderPolicyImpact(payload) {
  const el = document.getElementById("policyImpactEl");
  if (!el) return;

  const recImpact  = payload.rec_impact || {};
  const beforeAfter = payload.before_after || [];

  // Recommendation impact section
  const impacted = recImpact.policy_impacted || [];
  let recHtml = `<div style="font-weight:700;font-size:0.82rem;margin:0 0 8px">Recommendation Impact</div>`;
  if (recImpact.impact_summary) {
    recHtml += `<div style="font-size:0.78rem;color:#333;background:#f5f0e8;padding:8px 12px;border-radius:4px;margin-bottom:8px">${escHtml(recImpact.impact_summary)}</div>`;
  }
  if (impacted.length) {
    const rows = impacted.map(r => `<tr>
      <td style="font-size:0.76rem;font-weight:600">${escHtml(r.recommendation_type||"").replace(/_/g," ")}</td>
      <td style="font-family:monospace;font-size:0.74rem">${escHtml(r.node_key||"—")}</td>
      <td style="font-size:0.74rem">${escHtml((r.affected_symbols||[]).join(", ")||"—")}</td>
      <td><span style="font-size:0.70rem;font-weight:600;background:#e8f0fa;color:#1a5c8a;border-radius:3px;padding:1px 6px">${escHtml((r.impact_type||"").replace(/_/g," "))}</span></td>
      <td style="font-size:0.72rem;color:#555">${escHtml(r.impact_note||"")}</td>
    </tr>`).join("");
    recHtml += `<table class="pis-table" style="font-size:0.79rem">
      <thead><tr><th>Type</th><th>Node</th><th>Symbols</th><th>Impact</th><th>Note</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  // Before/After table
  let baHtml = "";
  if (beforeAfter.length) {
    baHtml = `<div style="font-weight:700;font-size:0.82rem;margin:16px 0 8px">Allocation Before/After</div>
    <table class="pis-table" style="font-size:0.79rem">
      <thead><tr><th>Node</th><th>Previous</th><th>Current</th><th>Δ</th><th>Direction</th></tr></thead>
      <tbody>${beforeAfter.map(r => `<tr ${r.is_high_importance ? 'style="background:#fffde7"' : ''}>
        <td style="font-family:monospace;font-size:0.74rem;font-weight:${r.is_high_importance?'700':'400'}">${escHtml(r.node_key)}</td>
        <td style="text-align:right">${parseFloat(r.previous_pct||0).toFixed(1)}%</td>
        <td style="text-align:right">${parseFloat(r.current_pct||0).toFixed(1)}%</td>
        <td style="text-align:right;font-weight:700;color:${r.delta_pp>=0?'#2e7d32':'#c62828'}">
          ${r.delta_pp>=0?"+":""}${parseFloat(r.delta_pp||0).toFixed(2)}pp
        </td>
        <td><span style="font-size:0.70rem">${_directionBadge(r.change_direction)}</span></td>
      </tr>`).join("")}</tbody>
    </table>`;
  } else if (!payload.has_changes) {
    baHtml = `<div style="font-size:0.80rem;color:#888;margin-top:12px">No allocation target changes detected — before/after view is not applicable when policy is stable.</div>`;
  }

  el.innerHTML = recHtml + baHtml;
}

function renderPolicyTimeline(payload) {
  const el = document.getElementById("policyTimelineEl");
  if (!el) return;
  const timeline = payload.timeline || [];
  if (!timeline.length) {
    el.innerHTML = `<p style="color:#888;font-size:0.9em">No policy timeline data available.</p>`;
    return;
  }
  const rows = timeline.map(t => [
    escHtml((t.fingerprint_id||"—").slice(0,28)),
    escHtml(t.first_seen_date||"—"),
    escHtml(t.last_seen_date||"—"),
    String(t.run_count||0),
    String(t.node_count||0),
    String(t.nodes_changed||0),
    _severityBadge(t.severity||"INITIAL"),
    escHtml(t.operator_note||"—"),
  ]);
  renderTable("policyTimelineEl",
    ["Fingerprint", "First Seen", "Last Seen", "Runs", "Nodes", "Changed", "Severity", "Note"],
    rows, { rawHtml: true });
}

// ─── PA-006: Allocation Compliance render functions ───────────────────────────

const _COMPLIANCE_COLORS = {
  COMPLIANT:     "#2e7d32",
  WARNING:       "#e65100",
  NON_COMPLIANT: "#c62828",
};

const _COMP_SEVERITY_COLORS = {
  HIGHLY_COMPLIANT:           "#2e7d32",
  MOSTLY_COMPLIANT:           "#558b2f",
  MIXED:                      "#f57c00",
  PERSISTENTLY_NON_COMPLIANT: "#c62828",
};

function _compBadge(status) {
  const color = _COMPLIANCE_COLORS[status] || "#999";
  return `<span style="background:${color};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.78em;font-weight:600;">${status || "—"}</span>`;
}

function _severityBadge2(severity) {
  const color = _COMP_SEVERITY_COLORS[severity] || "#999";
  const short = (severity || "—").replace(/_/g, " ");
  return `<span style="color:${color};font-weight:600;font-size:0.8em;">${short}</span>`;
}

function _driftColor(drift) {
  const n = parseFloat(drift || 0);
  const color = n > 0.1 ? "#e65100" : n < -0.1 ? "#1565c0" : "#2e7d32";
  return `<span style="color:${color};">${n >= 0 ? "+" : ""}${n.toFixed(2)}pp</span>`;
}

function renderComplianceSummary(payload) {
  const cards = [
    { label: "Total Nodes",     value: String(payload.total_nodes || 0) },
    { label: "Compliant",       value: String(payload.currently_compliant || 0), color: "#2e7d32" },
    { label: "Warning",         value: String(payload.currently_warning || 0), color: "#e65100" },
    { label: "Non-Compliant",   value: String(payload.currently_non_compliant || 0), color: "#c62828" },
    { label: "Highly Compliant",value: String(payload.highly_compliant_count || 0), color: "#1b5e20" },
    { label: "Persistent Violations", value: String(payload.persistently_non_compliant_count || 0), color: "#b71c1c" },
    { label: "Dates Covered",   value: String(payload.dates_covered || 0) },
  ];
  const cardHtml = cards.map(c =>
    `<div style="background:#f5f5f5;border-radius:6px;padding:12px 18px;min-width:90px;text-align:center;display:inline-block;margin:4px 6px 4px 0;">
      <div style="font-size:1.4em;font-weight:700;${c.color ? `color:${c.color};` : ""}">${escHtml(c.value)}</div>
      <div style="font-size:0.73em;color:#666;margin-top:2px;">${escHtml(c.label)}</div>
    </div>`
  ).join("");

  const el = document.getElementById("complianceSummaryCards");
  if (el) el.innerHTML = cardHtml;

  // Top violations highlight
  const violations = payload.top_violations || [];
  const violEl = document.getElementById("complianceTopViolations");
  if (violEl) {
    if (!violations.length) {
      violEl.innerHTML = `<p style="color:#2e7d32;font-size:0.9em;margin-top:8px;">No persistent violations detected.</p>`;
    } else {
      const items = violations.map(v =>
        `<div style="padding:8px 12px;background:#fff8e1;border-left:4px solid #c62828;margin:4px 0;border-radius:2px;font-size:0.88em;">
          <strong style="color:#c62828;">${escHtml(v.node_key)}</strong>
          — compliance rate: ${v.compliance_rate_pct.toFixed(0)}%,
          current drift: ${v.current_drift_pct >= 0 ? "+" : ""}${v.current_drift_pct.toFixed(2)}pp,
          streak: ${v.current_streak}d
         </div>`
      ).join("");
      const obs = (payload.observations || []).map(o => `<li style="margin-bottom:5px;">${escHtml(o)}</li>`).join("");
      violEl.innerHTML = `<p style="font-weight:600;margin:10px 0 6px;">Persistent Violations</p>${items}` +
        (obs ? `<p style="font-weight:600;margin:12px 0 6px;">Governance Observations</p><ul style="padding-left:18px;margin:0;">${obs}</ul>` : "");
    }
  }
}

function renderComplianceLeaderboard(payload) {
  const nodes = payload.nodes || [];
  const rows = nodes.map(n => [
    escHtml(n.node_key || "—"),
    _compBadge(n.current_status),
    _severityBadge2(n.compliance_severity),
    `<span style="font-weight:600;">${(n.compliance_rate_pct || 0).toFixed(1)}%</span>`,
    _driftColor(n.current_drift_pct),
    String(n.current_streak || 0),
    String(n.longest_compliant_streak || 0),
    String(n.longest_non_compliant_streak || 0),
    String(n.dates_available || 0),
  ]);
  renderTable("complianceLeaderboardTable",
    ["Node", "Status", "Severity", "Compliance%", "Current Drift", "Streak", "Longest C", "Longest NC", "Dates"],
    rows, { rawHtml: true });
}

function renderComplianceViolations(payload) {
  const nodes = (payload.nodes || [])
    .filter(n => n.compliance_severity === "PERSISTENTLY_NON_COMPLIANT" ||
                 n.non_compliance_rate_pct > 30)
    .sort((a, b) => a.compliance_rate_pct - b.compliance_rate_pct)
    .slice(0, 10);
  if (!nodes.length) {
    const el = document.getElementById("complianceViolationsTable");
    if (el) el.innerHTML = `<p style="color:#2e7d32;font-size:0.9em;">No persistent violations in current observation window.</p>`;
    return;
  }
  const rows = nodes.map(n => [
    escHtml(n.node_key || "—"),
    _compBadge(n.current_status),
    `<span style="color:#c62828;font-weight:600;">${(n.compliance_rate_pct || 0).toFixed(1)}%</span>`,
    `<span style="color:#c62828;">${(n.non_compliance_rate_pct || 0).toFixed(1)}%</span>`,
    String(n.longest_non_compliant_streak || 0),
    _driftColor(n.current_drift_pct),
  ]);
  renderTable("complianceViolationsTable",
    ["Node", "Status", "Compliance%", "NC Rate%", "Longest NC Streak", "Current Drift"],
    rows, { rawHtml: true });
}

function renderComplianceBest(payload) {
  const nodes = (payload.nodes || [])
    .filter(n => n.compliance_severity === "HIGHLY_COMPLIANT")
    .sort((a, b) => b.compliance_rate_pct - a.compliance_rate_pct)
    .slice(0, 10);
  if (!nodes.length) {
    const el = document.getElementById("complianceBestTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No highly compliant nodes yet.</p>`;
    return;
  }
  const rows = nodes.map(n => [
    escHtml(n.node_key || "—"),
    `<span style="color:#2e7d32;font-weight:700;">${(n.compliance_rate_pct || 0).toFixed(1)}%</span>`,
    _compBadge(n.current_status),
    String(n.longest_compliant_streak || 0),
    _driftColor(n.current_drift_pct),
  ]);
  renderTable("complianceBestTable",
    ["Node", "Compliance%", "Current Status", "Longest Compliant Streak", "Current Drift"],
    rows, { rawHtml: true });
}

// ── MEI Render Functions ────────────────────────────────────────────────────

function _meiImpactBadge(level) {
  const cfg = {
    HIGH:   { bg: "#fdecea", color: "#c62828", border: "#f5c6c2" },
    MEDIUM: { bg: "#fff8e1", color: "#e65100", border: "#ffe082" },
    LOW:    { bg: "#f1f8e9", color: "#33691e", border: "#c5e1a5" },
  }[level] || { bg: "#f5f5f5", color: "#555", border: "#ccc" };
  return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:${cfg.bg};color:${cfg.color};border:1px solid ${cfg.border};font-size:0.74rem;font-weight:700;">${escHtml(level||"—")}</span>`;
}

function _meiSensBadge(level) {
  const cfg = {
    HIGH:     { bg: "#fdecea", color: "#c62828" },
    MODERATE: { bg: "#fff8e1", color: "#e65100" },
    LOW:      { bg: "#f1f8e9", color: "#33691e" },
    NONE:     { bg: "#f5f5f5", color: "#888" },
  }[level] || { bg: "#f5f5f5", color: "#888" };
  return `<span style="display:inline-block;padding:2px 7px;border-radius:999px;background:${cfg.bg};color:${cfg.color};font-size:0.73rem;font-weight:600;">${escHtml(level||"—")}</span>`;
}

function _meiExposureBadge(label) {
  if (label === "EVENT_EXPOSED") {
    return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:#fff3e0;color:#e65100;border:1px solid #ffe082;font-size:0.73rem;font-weight:700;">⚡ EVENT EXPOSED</span>`;
  }
  return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:#f1f8e9;color:#2e7d32;border:1px solid #c5e1a5;font-size:0.73rem;font-weight:600;">✔ CLEAN</span>`;
}

function _meiObsBlock(observations) {
  if (!observations || !observations.length) return "";
  const items = observations.map(o => `<li style="padding:4px 0;border-bottom:1px solid #ece8e0;">${escHtml(o)}</li>`).join("");
  return `<ul style="margin:0;padding:0 0 0 16px;font-size:0.87rem;color:#374151;">${items}</ul>`;
}

function renderMeiCalendarSummary(payload) {
  const cards = document.getElementById("meiCalendarCards");
  const obsEl = document.getElementById("meiCalendarObservations");

  if (cards) {
    const nh = payload.next_high_impact_event;
    const nhText = nh
      ? `${escHtml(nh.event_name)} in ${nh.days_away === 0 ? "today" : nh.days_away === 1 ? "tomorrow" : nh.days_away + " days"}`
      : "None in next 14 days";
    cards.innerHTML = `<div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Events (Next 14 Days)</div><div class="kpi-value">${payload.events_next_14_days || 0}</div></div>
      <div class="kpi"><div class="kpi-label">HIGH Impact (14d)</div><div class="kpi-value" style="color:#c62828;">${payload.high_impact_next_14_days || 0}</div></div>
      <div class="kpi"><div class="kpi-label">MEDIUM Impact (14d)</div><div class="kpi-value" style="color:#e65100;">${payload.medium_impact_next_14_days || 0}</div></div>
      <div class="kpi"><div class="kpi-label">Events (Next 30 Days)</div><div class="kpi-value">${payload.events_next_30_days || 0}</div></div>
    </div>
    <div style="margin-top:10px;padding:10px 12px;background:#fdf8f0;border:1px solid #e9d8c0;border-radius:8px;font-size:0.88rem;">
      <strong>Next HIGH Impact Event:</strong> ${nhText}
    </div>`;
  }

  if (obsEl) obsEl.innerHTML = _meiObsBlock(payload.observations);
}

function renderMeiCalendarTable(payload) {
  const events = payload.events || [];
  if (!events.length) {
    const el = document.getElementById("meiCalendarTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No events in the next 14 days.</p>`;
    return;
  }
  const rows = events.map(e => [
    escHtml(e.event_date || "—"),
    String(e.days_away != null ? (e.days_away === 0 ? "Today" : e.days_away === 1 ? "Tomorrow" : e.days_away + "d") : "—"),
    _meiImpactBadge(e.impact_level),
    escHtml(e.event_name || "—"),
    escHtml(e.event_type || "—"),
    `<span style="color:#555;font-size:0.83rem;">${escHtml((e.sensitivity_tags || []).join(", ") || "—")}</span>`,
    `<span style="color:#666;font-size:0.82rem;white-space:normal;">${escHtml(e.consensus_expectation || "—")}</span>`,
  ]);
  renderTable("meiCalendarTable",
    ["Date", "Days Away", "Impact", "Event", "Type", "Sensitivity Tags", "Consensus"],
    rows, { rawHtml: true });
}

function renderMeiExposuresSummary(payload) {
  const el = document.getElementById("meiExposuresSummaryCards");
  if (!el) return;
  const maxEv = payload.max_high_exposure_event;
  const maxEvText = maxEv
    ? `${escHtml(maxEv.event_name)} (${maxEv.high_count} holdings)`
    : "—";
  const topSyms = (payload.most_exposed_symbols || []).slice(0, 8).map(s => escHtml(s)).join(", ") || "—";
  el.innerHTML = `<div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Events Analyzed</div><div class="kpi-value">${payload.total_events_analyzed || 0}</div></div>
    <div class="kpi"><div class="kpi-label">HIGH×HIGH Events</div><div class="kpi-value" style="color:#c62828;">${payload.high_impact_high_exposure || 0}</div></div>
    <div class="kpi"><div class="kpi-label">Broadest Exposure</div><div class="kpi-value" style="font-size:0.8rem;">${maxEvText}</div></div>
    <div class="kpi"><div class="kpi-label">Most Exposed Symbols</div><div class="kpi-value" style="font-size:0.78rem;font-weight:600;">${topSyms}</div></div>
  </div>`;
}

function renderMeiExposuresTable(payload) {
  const exposures = payload.event_exposures || [];
  if (!exposures.length) {
    const el = document.getElementById("meiExposuresTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No event exposure data available.</p>`;
    return;
  }
  const rows = exposures.map(e => {
    const highSyms = (e.high_exposure || []).slice(0, 6).map(h => escHtml(h.symbol)).join(", ") || "—";
    const modSyms = (e.moderate_exposure || []).slice(0, 4).map(h => escHtml(h.symbol)).join(", ") || "—";
    return [
      escHtml(e.event_date || "—"),
      _meiImpactBadge(e.impact_level),
      escHtml(e.event_name || "—"),
      `<span style="color:#c62828;font-weight:700;">${e.high_count || 0}</span>`,
      `<span style="color:#e65100;font-weight:600;">${e.moderate_count || 0}</span>`,
      `<span style="font-size:0.82rem;color:#444;">${highSyms}</span>`,
      `<span style="font-size:0.82rem;color:#666;">${modSyms}</span>`,
    ];
  });
  renderTable("meiExposuresTable",
    ["Date", "Impact", "Event", "HIGH Exposed", "MOD Exposed", "HIGH Holdings", "MODERATE Holdings"],
    rows, { rawHtml: true });
}

function renderMeiContextSummary(payload) {
  const cards = document.getElementById("meiContextSummaryCards");
  const obsEl = document.getElementById("meiContextObservations");

  if (cards) {
    cards.innerHTML = `<div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Total Recommendations</div><div class="kpi-value">${payload.total_recommendations || 0}</div></div>
      <div class="kpi"><div class="kpi-label">Event Exposed</div><div class="kpi-value" style="color:#e65100;">${payload.event_exposed_count || 0}</div></div>
      <div class="kpi"><div class="kpi-label">Clean (No Exposure)</div><div class="kpi-value" style="color:#2e7d32;">${payload.clean_count || 0}</div></div>
      <div class="kpi"><div class="kpi-label">HIGH Sensitivity Exposed</div><div class="kpi-value" style="color:#c62828;">${payload.high_sensitivity_exposed || 0}</div></div>
    </div>
    <div style="margin-top:10px;padding:8px 12px;background:#fdf8f0;border:1px solid #e9d8c0;border-radius:8px;font-size:0.82rem;color:#555;">
      MEI is informational only — no recommendation scores, rankings, or deployment gates are modified.
    </div>`;
  }

  if (obsEl) obsEl.innerHTML = _meiObsBlock(payload.observations);
}

function renderMeiContextTable(payload) {
  const items = payload.items || [];
  if (!items.length) {
    const el = document.getElementById("meiContextTable");
    if (el) el.innerHTML = `<p style="color:#888;font-size:0.9em;">No active recommendations to display context for.</p>`;
    return;
  }
  const rows = items.map(item => {
    const evNames = (item.upcoming_events || []).slice(0, 2)
      .map(e => `${escHtml(e.event_name)} (${e.days_away}d)`)
      .join("; ") || "None";
    return [
      `<strong>${escHtml(item.symbol || "—")}</strong>`,
      `<span style="font-size:0.82rem;color:#555;">${escHtml((item.recommendation_type||"").replace(/_/g," "))}</span>`,
      _meiExposureBadge(item.event_exposure_label),
      _meiSensBadge(item.max_sensitivity),
      `<span style="font-size:0.82rem;color:#444;">${evNames}</span>`,
      `<span style="font-size:0.82rem;color:#374151;white-space:normal;">${escHtml(item.operator_note || "—")}</span>`,
    ];
  });
  renderTable("meiContextTable",
    ["Symbol", "Recommendation", "Event Exposure", "Max Sensitivity", "Upcoming Events", "Operator Note"],
    rows, { rawHtml: true });
}

function renderMeiHistory(payload) {
  const cardsEl = document.getElementById("meiHistoryCards");
  const tableEl = document.getElementById("meiHistoryTable");

  if (cardsEl) {
    const avgRet = payload.avg_portfolio_return_pct;
    const avgText = avgRet != null
      ? `${avgRet >= 0 ? "+" : ""}${Number(avgRet).toFixed(2)}%`
      : "—";
    cardsEl.innerHTML = `<div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Events Tracked</div><div class="kpi-value">${payload.total_events_tracked || 0}</div></div>
      <div class="kpi"><div class="kpi-label">Avg Portfolio Return</div><div class="kpi-value">${avgText}</div></div>
      <div class="kpi"><div class="kpi-label">Positive Outcomes</div><div class="kpi-value" style="color:#2e7d32;">${payload.positive_event_count || 0}</div></div>
      <div class="kpi"><div class="kpi-label">Negative Outcomes</div><div class="kpi-value" style="color:#c62828;">${payload.negative_event_count || 0}</div></div>
    </div>
    <div style="margin-top:10px;">
      ${_meiObsBlock(payload.observations)}
    </div>`;
  }

  if (tableEl) {
    // Table is populated from full history; summary endpoint doesn't include event list
    tableEl.innerHTML = `<p style="color:#888;font-size:0.85em;font-style:italic;">Event history table loads from /api/mei/event-history. Phase 1 initializes the repository — outcomes will be recorded as events occur.</p>`;
  }
}

// ── end MEI Render Functions ─────────────────────────────────────────────────

function initializeDashboardShell() {
  dashboardStartedAt = Date.now();
  requestCache.clear();
  Object.keys(SECTION_DEFINITIONS).forEach((sectionKey) => {
    sectionStates[sectionKey] = STATUS_LOADING;
    sectionErrors[sectionKey] = null;
  });
  ensureSectionBadges();
  Object.keys(SECTION_DEFINITIONS).forEach((sectionKey) => {
    renderSectionLoadingState(sectionKey, STATUS_LOADING);
    updateSectionBadge(sectionKey, STATUS_LOADING);
  });
  updateSubsystemStatuses();
  updateDashboardBanner();
  ["executiveKpiHeader", "governanceSummaryCard", "canonicalSelectionCard", "portfolioTrendCard", "performanceReturnsCard", "changeDetectionSummaryCard", "lineageSummaryCard", "attributionSummaryCard", "benchmarkSummaryCard"].forEach((id) => {
    renderLoading(id, "Loading executive summary...");
  });
}

function initialize() {
  console.log("[PIS_BOOT] initializeDashboard start", {
    build: PIS_BUILD_JS,
    sectionsPlanned: Object.keys(SECTION_DEFINITIONS).length,
    htmlBuild: getHtmlBuildMarker(),
  });
  initializeDashboardShell();

  runSectionTask("inventory", () => requestJson("/api/pis/snapshots"), (snapshotsPayload) => {
    const snapshots = Array.isArray(snapshotsPayload)
      ? snapshotsPayload
      : (Array.isArray(snapshotsPayload.snapshots) ? snapshotsPayload.snapshots : []);
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

  runSectionTask("driftSummary", () => requestJson("/api/pis/allocation-drift/summary"), (driftSummary) => {
    renderDriftSummary(driftSummary || {});
  });

  runSectionTask("driftTrendTable", () => requestJson("/api/pis/allocation-drift/latest"), (driftLatest) => {
    renderDriftTrendTable(driftLatest || {});
  });

  runSectionTask("driftWorsening", () => requestJson("/api/pis/allocation-drift/latest"), (driftLatest) => {
    renderDriftTopNodes("driftWorseningTable", (driftLatest.nodes || []).filter(n => n.trend_direction === "WORSENING"), "WORSENING");
  });

  runSectionTask("driftImproving", () => requestJson("/api/pis/allocation-drift/latest"), (driftLatest) => {
    renderDriftTopNodes("driftImprovingTable", (driftLatest.nodes || []).filter(n => n.trend_direction === "IMPROVING"), "IMPROVING");
  });

  runSectionTask("actionAttributionSummary", () => requestJson("/api/pis/action-attribution/summary"), (payload) => {
    renderActionAttributionSummary(payload || {});
  });

  runSectionTask("actionAttributionTable", () => requestJson("/api/pis/action-attribution/recommendations"), (payload) => {
    renderActionAttributionTable(payload || {});
  });

  runSectionTask("actionAttributionSources", () => requestJson("/api/pis/action-attribution/sources"), (payload) => {
    renderActionAttributionSources(payload || {});
  });

  runSectionTask("actionAttributionMissed", () => requestJson("/api/pis/action-attribution/sources"), (payload) => {
    renderActionAttributionMissed(payload || {});
  });

  runSectionTask("dorSummary", () => requestJson("/api/pis/dor/summary"), (payload) => {
    renderDORSummary(payload || {});
  });

  runSectionTask("dorCohorts", () => requestJson("/api/pis/dor/cohorts"), (payload) => {
    renderDORCohorts(payload || {});
  });

  runSectionTask("dorMissedWinners", () => requestJson("/api/pis/dor/cohorts"), (payload) => {
    renderDORMissedWinners(payload || {});
  });

  runSectionTask("dorFollowedWinners", () => requestJson("/api/pis/dor/recommendations"), (payload) => {
    renderDORFollowedWinners(payload || {});
  });

  runSectionTask("policyCurrent", () => requestJson("/api/pis/policy/current"), (payload) => {
    renderPolicyCurrent(payload || {});
  });

  runSectionTask("policyHistory", () => requestJson("/api/pis/policy/history"), (payload) => {
    renderPolicyHistory(payload || {});
  });

  runSectionTask("policyDiff", () => requestJson("/api/pis/policy/diff"), (payload) => {
    renderPolicyDiff(payload || {});
  });

  runSectionTask("policyGovObs", () => requestJson("/api/pis/policy/diff"), (payload) => {
    renderPolicyGovObs(payload || {});
  });

  // ── AI-004B: Policy Change Intelligence ──────────────────────────────────
  runSectionTask("policyChangeSummary", () => requestJson("/api/pis/policy/summary"), (payload) => {
    renderPolicyChangeSummary(payload || {});
  });
  runSectionTask("policyImpact", () => requestJson("/api/pis/policy/impact"), (payload) => {
    renderPolicyImpact(payload || {});
  });
  runSectionTask("policyTimeline", () => requestJson("/api/pis/policy/timeline"), (payload) => {
    renderPolicyTimeline(payload || {});
  });

  runSectionTask("complianceSummary", () => requestJson("/api/pis/compliance/summary"), (payload) => {
    renderComplianceSummary(payload || {});
  });

  runSectionTask("complianceLeaderboard", () => requestJson("/api/pis/compliance/latest"), (payload) => {
    renderComplianceLeaderboard(payload || {});
  });

  runSectionTask("complianceViolations", () => requestJson("/api/pis/compliance/latest"), (payload) => {
    renderComplianceViolations(payload || {});
  });

  runSectionTask("complianceBest", () => requestJson("/api/pis/compliance/latest"), (payload) => {
    renderComplianceBest(payload || {});
  });

  // ── MEI: Market Event Intelligence ────────────────────────────────────────
  runSectionTask("meiCalendarSummary", () => requestJson("/api/mei/events/summary"), (payload) => {
    renderMeiCalendarSummary(payload || {});
  });

  runSectionTask("meiCalendarTable", () => requestJson("/api/mei/events"), (payload) => {
    renderMeiCalendarTable(payload || {});
  });

  runSectionTask("meiExposuresSummary", () => requestJson("/api/mei/exposures/summary"), (payload) => {
    renderMeiExposuresSummary(payload || {});
  });

  runSectionTask("meiExposuresTable", () => requestJson("/api/mei/exposures"), (payload) => {
    renderMeiExposuresTable(payload || {});
  });

  runSectionTask("meiContextSummary", () => requestJson("/api/mei/recommendation-context/summary"), (payload) => {
    renderMeiContextSummary(payload || {});
  });

  runSectionTask("meiContextTable", () => requestJson("/api/mei/recommendation-context"), (payload) => {
    renderMeiContextTable(payload || {});
  });

  runSectionTask("meiHistory", () => requestJson("/api/mei/event-history/summary"), (payload) => {
    renderMeiHistory(payload || {});
  });

  // ── MEI-002: Event Outcome Attribution ──────────────────────────────────
  runSectionTask("meiOutcomeSummary", () => requestJson("/api/mei/outcome-summary"), (payload) => {
    renderMeiOutcomeSummary(payload || {});
  });
  runSectionTask("meiOutcomeTable", () => requestJson("/api/mei/outcomes"), (payload) => {
    renderMeiOutcomeTable(payload || {});
  });
  runSectionTask("meiEventImpact", () => requestJson("/api/mei/event-impact"), (payload) => {
    renderMeiEventImpact(payload || {});
  });
}

// ── MEI-002 render functions ──────────────────────────────────────────────────

function _fmtPct(v) {
  if (v == null) return "—";
  const n = parseFloat(v);
  const cls = n >= 0 ? "color:#2e7d32" : "color:#c0392b";
  return `<span style="${cls};font-weight:700">${n >= 0 ? "+" : ""}${n.toFixed(2)}%</span>`;
}

function renderMeiOutcomeSummary(payload) {
  const el = document.getElementById("meiOutcomeCards");
  if (!el) return;
  const govNote = payload.governance_note || "Informational only — no scoring changes.";
  const topTypes = (payload.top_event_types || []).slice(0, 3);
  const impactful = (payload.most_impactful || []).slice(0, 5);

  el.innerHTML = `
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Events Analyzed</div><div class="kpi-value">${payload.event_count || 0}</div></div>
      <div class="kpi"><div class="kpi-label">With Attribution</div><div class="kpi-value">${payload.attributed_count || 0}</div></div>
      <div class="kpi"><div class="kpi-label">Avg Portfolio Return (5d)</div>
        <div class="kpi-value">${_fmtPct(payload.avg_portfolio_return_5d)}</div></div>
    </div>
    <div style="font-size:0.78rem;color:#666;margin:8px 0 12px;padding:6px 10px;background:#f5f0e8;border-left:3px solid #c5d8ef;border-radius:0 4px 4px 0">${govNote}</div>
    ${impactful.length ? `
    <div style="font-weight:700;font-size:0.82rem;margin:12px 0 6px">Most Impactful Events</div>
    <table class="pis-table" style="font-size:0.80rem">
      <thead><tr><th>Event</th><th>Date</th><th>Type</th><th>1d Return</th><th>5d Return</th><th>Top Winners</th></tr></thead>
      <tbody>
        ${impactful.map(o => `<tr>
          <td style="font-weight:600">${o.event_name || o.event_id}</td>
          <td>${o.event_date || "—"}</td>
          <td><span class="badge">${(o.event_type || "").replace(/_/g," ")}</span></td>
          <td>${_fmtPct(o.portfolio_return_1d)}</td>
          <td>${_fmtPct(o.portfolio_return_5d)}</td>
          <td style="font-size:0.74rem">${(o.top_winners || []).slice(0,3).map(w => `<span class="badge">${w.symbol} ${_fmtPct(w.return_pct)}</span>`).join(" ")}</td>
        </tr>`).join("")}
      </tbody>
    </table>` : ""}
    ${topTypes.length ? `
    <div style="font-weight:700;font-size:0.82rem;margin:16px 0 6px">Top Event Types by Impact</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      ${topTypes.map(t => `<div class="kpi" style="min-width:160px">
        <div class="kpi-label">${t.event_type_label || t.event_type}</div>
        <div class="kpi-value">${_fmtPct(t.avg_return_5d_pct)}</div>
        <div style="font-size:0.70rem;color:#888">${t.event_count} events</div>
      </div>`).join("")}
    </div>` : ""}`;
}

function renderMeiOutcomeTable(payload) {
  const el = document.getElementById("meiOutcomeTable");
  if (!el) return;
  const outcomes = (payload.outcomes || []).filter(o => o.portfolio_return_5d != null);
  if (!outcomes.length) {
    el.innerHTML = `<div style="color:#888;padding:12px">No attributed event outcomes yet. Run refresh to compute from historical events.</div>`;
    return;
  }
  const sorted = [...outcomes].sort((a, b) => str(a.event_date) < str(b.event_date) ? 1 : -1);
  function str(v) { return String(v || ""); }
  el.innerHTML = `<table class="pis-table" style="font-size:0.79rem">
    <thead><tr>
      <th>Event</th><th>Date</th><th>Type</th><th>Impact</th>
      <th>1d Port.</th><th>5d Port.</th><th>10d Port.</th>
      <th>Top Winner</th><th>Top Loser</th><th>Coverage</th>
    </tr></thead>
    <tbody>${sorted.map(o => {
      const winner = (o.top_winners || [])[0];
      const loser  = (o.top_losers  || [])[0];
      return `<tr>
        <td style="font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${o.event_name || o.event_id}</td>
        <td style="white-space:nowrap">${o.event_date || "—"}</td>
        <td><span class="badge" style="font-size:0.68rem">${(o.event_type||"").replace(/_/g," ")}</span></td>
        <td><span class="badge badge-${(o.impact_level||"LOW").toLowerCase()}">${o.impact_level||"—"}</span></td>
        <td>${_fmtPct(o.portfolio_return_1d)}</td>
        <td>${_fmtPct(o.portfolio_return_5d)}</td>
        <td>${_fmtPct(o.portfolio_return_10d)}</td>
        <td style="font-size:0.74rem">${winner ? `${winner.symbol} ${_fmtPct(winner.return_pct)}` : "—"}</td>
        <td style="font-size:0.74rem">${loser  ? `${loser.symbol} ${_fmtPct(loser.return_pct)}` : "—"}</td>
        <td style="font-size:0.72rem;color:#888">${o.coverage_pct != null ? o.coverage_pct + "%" : "—"}</td>
      </tr>`;
    }).join("")}</tbody>
  </table>
  <div style="font-size:0.70rem;color:#888;margin-top:6px">
    Portfolio return = weighted average of held securities' price change over the window.
    Approximation only — does not reflect actual account performance.
  </div>`;
}

function renderMeiEventImpact(payload) {
  const el = document.getElementById("meiEventImpactTable");
  if (!el) return;
  const rows = payload.effectiveness || [];
  if (!rows.length) {
    el.innerHTML = `<div style="color:#888;padding:12px">No effectiveness data yet.</div>`;
    return;
  }
  el.innerHTML = `<table class="pis-table" style="font-size:0.79rem">
    <thead><tr>
      <th>Event Type</th><th>Events</th>
      <th>Avg 1d Return</th><th>Avg 5d Return</th>
      <th>Volatility (5d)</th><th>Consistency</th>
      <th>Importance</th>
    </tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td style="font-weight:600">${r.event_type_label || r.event_type}</td>
      <td style="text-align:right">${r.event_count}</td>
      <td style="text-align:right">${_fmtPct(r.avg_return_1d_pct)}</td>
      <td style="text-align:right">${_fmtPct(r.avg_return_5d_pct)}</td>
      <td style="text-align:right;color:#856404">${r.volatility_5d_pct != null ? "±" + parseFloat(r.volatility_5d_pct).toFixed(2) + "%" : "—"}</td>
      <td style="text-align:right">${r.consistency_pct != null ? r.consistency_pct + "%" : "—"}</td>
      <td style="text-align:right;font-weight:700">${r.importance_score != null ? parseFloat(r.importance_score).toFixed(1) : "—"}</td>
    </tr>`).join("")}</tbody>
  </table>
  <div style="font-size:0.70rem;color:#888;margin-top:6px">
    Importance = avg(|5d return|) × event count. Consistency = fraction of events where 1d and 5d returns moved in same direction.
    Research only — informational, no scoring changes.
  </div>`;
}

function bootstrapDashboard() {
  try {
    console.log("[PIS_BOOT] bootstrapDashboard invoked", { build: PIS_BUILD_JS });
    initialize();
  } catch (error) {
    renderStartupFailure(error);
  }
}

if (document.readyState === "loading") {
  console.log("[PIS_BOOT] DOMContentLoaded registered", { build: PIS_BUILD_JS });
  document.addEventListener("DOMContentLoaded", bootstrapDashboard, { once: true });
} else {
  console.log("[PIS_BOOT] DOM already ready, booting immediately", { build: PIS_BUILD_JS });
  bootstrapDashboard();
}
