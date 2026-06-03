/* Portfolio Alignment Analysis — app.js
 *
 * Workflow:
 *   1. User drops/selects portfolio CSV
 *   2. POST /api/portfolio/analyze  → returns run_id + full analysis JSON
 *   3. Render: KPI strip, allocation map, concentration, recommendations,
 *      replay alignment, security overlays
 *
 * All rendering is purely advisory — no trade execution anywhere.
 */

"use strict";

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
let _fileContent = null;
let _fileName    = null;
let _analysisResult = null;

const _STORAGE_KEY = "sih_portfolio_last_result";

// Drilldown state: per-rec toggle + sort mode
const _drilldownState = {};   // { [recId]: { rendered: bool, sortMode: string } }
const _recDataCache   = {};   // { [recId]: full rec object (with drilldown) }

const _SORT_MODES = [
  { id: "rps_desc",      label: "Highest Priority"    },
  { id: "score_asc",     label: "Lowest Score"        },
  { id: "alloc_desc",    label: "Largest Position"    },
  { id: "replay_asc",    label: "Weakest Replay"      },
  { id: "ess_asc",       label: "Weakest ESS"         },
  { id: "category_desc", label: "Highest Cat. Share"  },
  { id: "signal_asc",    label: "Weakest Signal"      },
  { id: "value_desc",    label: "Largest Value"       },
  { id: "trim_desc",     label: "Highest Trim Priority" },
  { id: "trim_asc",      label: "Strongest Retain"    },
];
// ESS / signal text → numeric weakness rank (lower = weaker)
const _SIGNAL_WEAKNESS_RANK = { BEARISH: 0, UNKNOWN: 1, NEUTRAL: 2, BULLISH: 3 };

function _saveResult(data) {
  try { localStorage.setItem(_STORAGE_KEY, JSON.stringify(data)); } catch (_) {}
}
function _loadSavedResult() {
  try { return JSON.parse(localStorage.getItem(_STORAGE_KEY)); } catch (_) { return null; }
}
function _clearSavedResult() {
  try { localStorage.removeItem(_STORAGE_KEY); } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Default date = today
  const dateInput = document.getElementById("snapshotDate");
  dateInput.value = new Date().toISOString().slice(0, 10);

  setupUploadZone();

  document.getElementById("analyzeBtn").addEventListener("click", runAnalysis);
  document.getElementById("clearBtn").addEventListener("click", clearAll);

  // Re-enable Analyze button (or prompt re-upload) when mandate changes
  document.getElementById("mandateSelect").addEventListener("change", () => {
    if (_fileContent) {
      document.getElementById("analyzeBtn").disabled = false;
      showStatus("info", "Mandate changed — click Analyze to re-run with the new mandate.");
    } else if (_analysisResult) {
      showStatus("warning", "Mandate changed — re-upload your portfolio CSV to analyze with the new mandate.");
    }
  });

  // Restore last analysis if available
  const saved = _loadSavedResult();
  if (saved) {
    _analysisResult = saved;
    const ts = saved.snapshot_date || "";
    const savedMandate = saved.mandate_type || "CONCENTRATED_ALPHA";
    // Sync mandate selector to the mandate used in the saved analysis
    const mandateSel = document.getElementById("mandateSelect");
    if (mandateSel) mandateSel.value = savedMandate;
    showStatus("info",
      `Showing last analysis — <strong>${saved.account_name || "Portfolio"}</strong> ` +
      `(${saved.holding_count} holdings, ${ts}, mandate: <strong>${savedMandate}</strong>). ` +
      `Upload a new file to re-analyze.`);
    document.getElementById("clearBtn").style.display = "inline-block";
    renderResults(saved);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Upload zone
// ─────────────────────────────────────────────────────────────────────────────
function setupUploadZone() {
  const zone  = document.getElementById("uploadZone");
  const input = document.getElementById("fileInput");

  input.addEventListener("change", () => {
    if (input.files.length) loadFile(input.files[0]);
  });

  zone.addEventListener("dragover", e => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) loadFile(e.dataTransfer.files[0]);
  });
}

function loadFile(file) {
  if (!file.name.endsWith(".csv")) {
    showStatus("error", "Only CSV files are supported.");
    return;
  }
  _fileName = file.name;
  const reader = new FileReader();
  reader.onload = e => {
    _fileContent = e.target.result;
    showStatus("success", `✓  Loaded <strong>${file.name}</strong> (${(file.size/1024).toFixed(1)} KB). Set the portfolio date and click Analyze.`);
    document.getElementById("analyzeBtn").disabled = false;
    document.getElementById("clearBtn").style.display = "inline-block";
  };
  reader.readAsText(file);
}

// ─────────────────────────────────────────────────────────────────────────────
// Run analysis
// ─────────────────────────────────────────────────────────────────────────────
async function runAnalysis() {
  if (!_fileContent) return;
  const snapshotDate = document.getElementById("snapshotDate").value || new Date().toISOString().slice(0,10);

  setLoading(true);
  showStatus("info", `<span class="spinner"></span>Analyzing portfolio — enriching holdings against SIH intelligence…`);

  try {
    const mandateType = document.getElementById("mandateSelect")?.value || "CONCENTRATED_ALPHA";
    const resp = await fetch("/api/portfolio/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio_csv: _fileContent,
        source_filename: _fileName,
        snapshot_date: snapshotDate,
        mandate_type: mandateType,
      }),
    });

    const data = await resp.json();

    if (!resp.ok || data.status === "REJECTED") {
      showStatus("error", `Ingestion failed: ${data.error || "Unknown error"}`);
      setLoading(false);
      return;
    }

    _analysisResult = data;
    setLoading(false);
    _saveResult(data);

    const warnText = data.warnings && data.warnings.length
      ? `  <br>⚠ ${data.warnings.length} normalization warning(s): ${data.warnings.join("; ")}`
      : "";
    showStatus("success",
      `✓  Analysis complete — ${data.holding_count} holdings enriched. ` +
      `Run ID: <strong>${data.run_id}</strong>${warnText}`
    );

    renderResults(data);
  } catch (err) {
    setLoading(false);
    showStatus("error", `Network error: ${err.message}`);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Clear
// ─────────────────────────────────────────────────────────────────────────────
function clearAll() {
  _fileContent = _fileName = _analysisResult = null;
  _clearSavedResult();
  document.getElementById("fileInput").value = "";
  document.getElementById("analyzeBtn").disabled = true;
  document.getElementById("clearBtn").style.display = "none";
  document.getElementById("resultsArea").style.display = "none";
  hideStatus();
}

// ─────────────────────────────────────────────────────────────────────────────
// Master render
// ─────────────────────────────────────────────────────────────────────────────
function renderResults(data) {
  document.getElementById("resultsArea").style.display = "block";
  _lastAnalysisData = data;  // Phase E: make STI profiles available to card helpers
  renderKPIs(data);
  renderMultiDimScores(data);
  renderMandatePanel(data);
  renderDeploymentQueue(data);
  renderAllocationMap(data.alignment || []);
  renderConcentration(data.concentration || {});
  renderOptimizerSummary(data.recommendations || []);  // Phase 7.3B
  renderRecommendations(data.recommendations || []);
  renderReplayAlignment(data);
  renderSecurityOverlays(data.security_overlays || []);
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI strip
// ─────────────────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const el = document.getElementById("runSummary");
  const score = data.overall_alignment_score;
  const scoreLabel = score >= 0.85 ? "Strong" : score >= 0.65 ? "Moderate" : "Needs attention";
  const concTier = data.concentration_tier || "UNKNOWN";

  el.innerHTML = `
    ${kpiCard((data.holding_count || 0).toString(), "Holdings")}
    ${kpiCard(formatMV(data.total_market_value), "Portfolio Value")}
    ${kpiCard((score * 100).toFixed(0) + "%", "Legacy Alignment", scoreLabel)}
    ${kpiCard((data.recommendation_count || 0).toString(), "Recommendations")}
    ${kpiCard(concTier, "Concentration", "", `tier-${concTier}`)}
    ${kpiCard(data.source_format || "—", "Format")}
  `;
}

function kpiCard(value, label, sub = "", extraClass = "") {
  return `<div class="kpi-card ${extraClass}">
    <div class="kpi-value">${value}</div>
    <div class="kpi-label">${label}${sub ? `<br><span style="font-size:0.7rem;color:var(--muted)">${sub}</span>` : ""}</div>
  </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6.2.2 — Multi-Dimensional Scorecards
// ─────────────────────────────────────────────────────────────────────────────
function renderMultiDimScores(data) {
  const el = document.getElementById("multiDimContainer");
  const mds = data.multi_dimensional_score;
  if (!el || !mds) { if (el) el.innerHTML = ""; return; }

  const dims = [
    { key: "allocation_alignment_score",   label: "Allocation Alignment",   tooltip: "Distance from target model allocations" },
    { key: "portfolio_quality_score",      label: "Portfolio Quality",       tooltip: "Concentration, signal quality, strategic classification" },
    { key: "implementation_quality_score", label: "Implementation Quality",  tooltip: "Vehicle suitability and operational integrity" },
    { key: "replay_alignment_score",       label: "Replay Alignment",        tooltip: "Replay-supported exposure coverage and quality" },
  ];

  const cards = dims.map(d => {
    const raw = parseFloat(mds[d.key] ?? 0);
    const pct  = Math.min(100, Math.max(0, raw));
    const color = pct >= 75 ? "var(--green)" : pct >= 50 ? "var(--accent-2)" : "var(--sev-high)";
    const label = pct >= 75 ? "Strong" : pct >= 50 ? "Moderate" : "Needs attention";
    return `<div class="multidim-card" title="${escHtml(d.tooltip)}">
      <div class="multidim-score" style="color:${color}">${pct.toFixed(0)}</div>
      <div class="multidim-label">${d.label}</div>
      <div class="multidim-sublabel">${label}</div>
      <div class="multidim-track">
        <div class="multidim-fill" style="width:${pct.toFixed(0)}%;background:${color}"></div>
      </div>
    </div>`;
  }).join("");

  el.innerHTML = `<div class="multidim-grid">${cards}</div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6.2.2 — Portfolio Mandate Assessment Panel
// ─────────────────────────────────────────────────────────────────────────────
function renderMandatePanel(data) {
  const el = document.getElementById("mandatePanelContainer");
  if (!el) return;

  const mandateDisplay = data.mandate_display_name || data.mandate_type || "—";
  const cashCtx        = data.cash_mandate_context || "";
  const asym           = data.intentional_asymmetry || {};
  const asymState      = asym.asymmetry_state || "";
  const asymScore      = parseFloat(asym.asymmetry_score ?? 0);
  const evidenceSignals = Array.isArray(asym.evidence_signals) ? asym.evidence_signals : [];

  const asymStateLabels = {
    HIGH_CONVICTION:    "High Conviction Asymmetry",
    LIKELY_INTENTIONAL: "Likely Intentional",
    ACCIDENTAL:         "Accidental / Circumstantial",
  };
  const asymBadge = asymState
    ? `<span class="asymmetry-state-badge asym-${asymState}">${asymStateLabels[asymState] || asymState}</span>`
    : "";

  const evidenceHtml = evidenceSignals.length
    ? `<div class="evidence-signals">${evidenceSignals.map(s => `<span class="evidence-chip">${escHtml(s)}</span>`).join("")}</div>`
    : "";

  const asymScorePct = (asymScore * 100).toFixed(0);

  el.innerHTML = `<div class="mandate-panel">
    <div class="mandate-panel-inner">
      <div class="mandate-header-row">
        <span class="mandate-panel-title">Portfolio Mandate Assessment</span>
        <span class="mandate-type-badge">${escHtml(mandateDisplay)}</span>
      </div>
      ${cashCtx ? `<div class="mandate-cash-context"><strong>Cash Context:</strong> ${escHtml(cashCtx)}</div>` : ""}
      ${asymState ? `<div class="asymmetry-section">
        <div class="asymmetry-label">Intentional Asymmetry</div>
        <div style="margin-bottom:6px">${asymBadge}</div>
        <div class="asymmetry-score-row">
          <span style="font-size:0.82rem;color:var(--muted)">Conviction Score:</span>
          <div class="asym-score-track">
            <div class="asym-score-fill" style="width:${asymScorePct}%"></div>
          </div>
          <span style="font-size:0.82rem;font-weight:700">${asymScorePct}%</span>
        </div>
        ${evidenceHtml}
      </div>` : ""}
    </div>
  </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Allocation map
// ─────────────────────────────────────────────────────────────────────────────
function renderAllocationMap(rows) {
  const el = document.getElementById("allocationContent");
  if (!rows.length) { el.innerHTML = emptyState("No alignment data", "Upload and analyze a portfolio to see the allocation map."); return; }

  // Sort: by depth asc, then priority asc within same depth group
  const sorted = [...rows].sort((a, b) => {
    const da = depthOf(a.node_key), db = depthOf(b.node_key);
    if (da !== db) return da - db;
    return (a.recommendation_priority || 9) - (b.recommendation_priority || 9);
  });

  const tbody = sorted.map(r => {
    const depth = depthOf(r.node_key);
    const driftN = parseFloat(r.drift_pct) || 0;
    const driftClass = driftN > 0 ? "drift-pos" : driftN < 0 ? "drift-neg" : "";
    const driftStr = driftN === 0 ? "—" : `<span class="${driftClass}">${driftN > 0 ? "+" : ""}${driftN.toFixed(1)}pp</span>`;
    const actual = parseFloat(r.effective_actual_pct ?? r.actual_pct ?? 0) || 0;
    const direct = parseFloat(r.direct_actual_pct ?? 0) || 0;
    const etf = parseFloat(r.etf_derived_actual_pct ?? 0) || 0;

    // Drift bar
    const barPct = Math.min(Math.abs(driftN) / Math.max(parseFloat(r.tactical_target_pct) || 10, 10) * 50, 50);
    const barWidth = barPct.toFixed(1);
    const barClass = driftN >= 0 ? "drift-over" : "drift-under";

    const sev = r.severity || "NONE";

    return `<tr>
      <td class="node-depth-${depth}">${r.node_label || r.node_key}</td>
      <td style="text-align:right">${direct.toFixed(1)}%</td>
      <td style="text-align:right">${etf.toFixed(1)}%</td>
      <td style="text-align:right"><strong>${actual.toFixed(1)}%</strong></td>
      <td style="text-align:right">${parseFloat(r.target_pct || 0).toFixed(1)}%</td>
      <td style="text-align:right">${driftStr}</td>
      <td>
        <div class="drift-bar-wrap">
          <div class="drift-center-line"></div>
          <div class="drift-bar ${barClass}" style="width:${barWidth}%"></div>
        </div>
      </td>
      <td><span class="sev-badge sev-${sev}">${sev}</span></td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <table class="alloc-table">
      <thead><tr>
        <th>Node</th>
        <th style="text-align:right">Direct</th>
        <th style="text-align:right">ETF-derived</th>
        <th style="text-align:right">Effective</th>
        <th style="text-align:right">Target</th>
        <th style="text-align:right">Drift</th>
        <th>Visual</th>
        <th>Severity</th>
      </tr></thead>
      <tbody>${tbody}</tbody>
    </table>`;
}

function depthOf(key) {
  return (key || "").split(".").length;
}

// ─────────────────────────────────────────────────────────────────────────────
// Concentration panel
// ─────────────────────────────────────────────────────────────────────────────
function renderConcentration(c) {
  const el = document.getElementById("concentrationContent");
  if (!c || !c.top1_symbol) { el.innerHTML = emptyState("No concentration data", ""); return; }

  const tier = c.concentration_tier || "UNKNOWN";
  const hhi = parseFloat(c.herfindahl_index || 0);

  // Alignment score ring
  const overall = _analysisResult ? _analysisResult.overall_alignment_score || 0 : 0;
  const ringHtml = scoreRing(overall);
  const hyperDirect = parseFloat(c.mega_subtier_direct_pct || 0) || 0;
  const hyperEtf = parseFloat(c.mega_subtier_etf_derived_pct || 0) || 0;
  const hyperEffective = parseFloat(c.mega_subtier_effective_pct ?? c.mega_subtier_pct ?? 0) || 0;

  el.innerHTML = `
    <div style="margin-bottom:10px">
      <span class="conc-tier-badge tier-${tier}">${tier}</span>
      &nbsp; HHI: <strong>${hhi.toFixed(3)}</strong>
      <small style="color:var(--muted);margin-left:6px">(0=perfect diversification, 1=single holding)</small>
    </div>

    ${ringHtml}

    <div class="conc-grid" style="margin-top:14px;">
      ${concStat(c.top1_symbol, "Largest Position")}
      ${concStat(pct(c.top1_pct), "Top 1 %")}
      ${concStat(pct(c.top3_pct), "Top 3 %")}
      ${concStat(pct(c.top5_pct), "Top 5 %")}
      ${concStat(pct(c.top10_pct), "Top 10 %")}
      ${concStat(pct(c.mega_subtier_pct), "Hyper Mega %")}
      ${concStat(c.single_sector_max_label || "—", "Largest Sector")}
      ${concStat(pct(c.single_sector_max_pct), "Sector Max %")}
      ${concStat(pct(c.us_pct), "US %")}
    </div>

    <div style="margin-top:10px;padding:10px 12px;background:#f7f2e8;border-radius:10px;font-size:0.84rem;line-height:1.6;">
      <strong>Hyper Mega exposure:</strong>
      Direct ${pct(hyperDirect)} · ETF-derived ${pct(hyperEtf)} · Effective ${pct(hyperEffective)}
    </div>

    <div style="margin-top:16px;">
      <div style="font-size:0.8rem;color:var(--muted);margin-bottom:6px;font-weight:600;">Geography Distribution</div>
      <div class="geo-bar-wrap">
        ${geoBar(c)}
      </div>
      <div class="geo-legend">
        <div class="geo-legend-item"><div class="geo-dot" style="background:var(--accent)"></div> US: ${pct(c.us_pct)}</div>
        <div class="geo-legend-item"><div class="geo-dot" style="background:var(--accent-2)"></div> International: ${pct(c.international_pct)}</div>
        <div class="geo-legend-item"><div class="geo-dot" style="background:#8d5a97"></div> Emerging: ${pct(c.emerging_pct)}</div>
      </div>
    </div>`;
}

function concStat(val, label) {
  return `<div class="conc-stat">
    <div class="conc-stat-val">${val}</div>
    <div class="conc-stat-lbl">${label}</div>
  </div>`;
}

function geoBar(c) {
  const total = parseFloat(c.us_pct || 0) + parseFloat(c.international_pct || 0) + parseFloat(c.emerging_pct || 0);
  if (total <= 0) return `<div class="geo-bar"><div class="geo-seg-OTHER" style="width:100%"></div></div>`;
  const usPct = (parseFloat(c.us_pct || 0) / total * 100).toFixed(1);
  const intlPct = (parseFloat(c.international_pct || 0) / total * 100).toFixed(1);
  const emPct = (parseFloat(c.emerging_pct || 0) / total * 100).toFixed(1);
  const other = Math.max(0, 100 - parseFloat(usPct) - parseFloat(intlPct) - parseFloat(emPct)).toFixed(1);
  return `<div class="geo-bar">
    <div class="geo-seg-US"    style="width:${usPct}%"></div>
    <div class="geo-seg-INTL"  style="width:${intlPct}%"></div>
    <div class="geo-seg-EM"    style="width:${emPct}%"></div>
    <div class="geo-seg-OTHER" style="width:${other}%"></div>
  </div>`;
}

function scoreRing(score) {
  const radius = 42, cx = 54, cy = 54;
  const circumference = 2 * Math.PI * radius;
  const filled = score * circumference;
  const color = score >= 0.85 ? "var(--green)" : score >= 0.65 ? "var(--accent-2)" : "var(--sev-high)";
  return `<div class="score-ring-wrap">
    <div class="score-ring">
      <svg width="108" height="108">
        <circle cx="${cx}" cy="${cy}" r="${radius}" fill="none" stroke="#e8e0d4" stroke-width="9"/>
        <circle cx="${cx}" cy="${cy}" r="${radius}" fill="none" stroke="${color}" stroke-width="9"
          stroke-dasharray="${filled.toFixed(1)} ${circumference.toFixed(1)}"
          stroke-dashoffset="${(circumference * 0.25).toFixed(1)}"
          stroke-linecap="round" transform="rotate(-90 ${cx} ${cy})"/>
      </svg>
      <div class="score-ring-value">${(score * 100).toFixed(0)}%</div>
    </div>
    <div class="score-ring-label">Overall Alignment Score</div>
  </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Drilldown intelligence — expandable recommendation panels
// ─────────────────────────────────────────────────────────────────────────────

// Phase C — toggle reasoning trace visibility
function toggleTrace(traceId) {
  const body = document.getElementById(traceId);
  const btn  = body ? body.previousElementSibling : null;
  if (!body) return;
  const open = body.classList.toggle("open");
  if (btn) btn.textContent = open ? "▾ Why this state?" : "▸ Why this state?";
}

function togglePmiMandate(pmiId) {
  const body = document.getElementById(pmiId);
  const btn  = body ? body.previousElementSibling : null;
  if (!body) return;
  const open = body.classList.toggle("open");
  if (btn) btn.innerHTML = open ? "&#9662; Portfolio Mandate View" : "&#9656; Portfolio Mandate View";
}

function toggleDrilldown(recId) {
  const panel = document.getElementById(`drilldown-panel-${recId}`);
  const btn   = document.getElementById(`drill-toggle-${recId}`);
  const rec   = _recDataCache[recId];
  if (!panel || !btn || !rec) return;

  const isOpen = panel.classList.contains("open");
  if (!isOpen) {
    // Lazy-render on first open
    if (!_drilldownState[recId] || !_drilldownState[recId].rendered) {
      renderDrilldown(rec, recId);
      if (!_drilldownState[recId]) _drilldownState[recId] = {};
      _drilldownState[recId].rendered = true;
    }
    panel.classList.add("open");
    btn.classList.add("open");
    btn.textContent = "▲ Collapse";
  } else {
    panel.classList.remove("open");
    btn.classList.remove("open");
    const n = rec.drilldown?.holdings?.length || 0;
    btn.textContent = `▼ View ${n} Holdings`;
  }
}

function renderDrilldown(rec, recId) {
  const panel = document.getElementById(`drilldown-panel-${recId}`);
  if (!panel) return;

  const dd       = rec.drilldown || {};
  const holdings = dd.holdings || [];
  const sortMode = (_drilldownState[recId] && _drilldownState[recId].sortMode) || "rps_desc";

  // Context header
  let contextHtml;
  if (dd.mode === "NODE") {
    const drift = (dd.node_drift_pct || 0);
    const driftStr = `${drift > 0 ? "+" : ""}${drift.toFixed(1)}pp`;
    const driftColor = drift > 0 ? "var(--sev-high)" : drift < 0 ? "var(--green)" : "var(--muted)";
    contextHtml = `<div class="drilldown-context">
      <span class="dd-node-label">${escHtml(dd.affected_node_label || dd.affected_node_key || "Allocation Node")}</span>
      <span class="dd-stat">Actual: <span>${(dd.node_actual_pct || 0).toFixed(1)}%</span></span>
      <span class="dd-stat">Target: <span>${(dd.node_target_pct || 0).toFixed(1)}%</span></span>
      <span class="dd-stat">Drift: <span style="color:${driftColor}">${driftStr}</span></span>
      <span class="dd-stat">${holdings.length} holdings</span>
      <span class="dd-lineage">v${dd.drilldown_version || "1.0"} · ${dd.drilldown_generated_at ? dd.drilldown_generated_at.slice(0, 10) : "—"}</span>
    </div>`;
  } else {
    contextHtml = `<div class="drilldown-context">
      <span class="dd-node-label">Affected Securities</span>
      <span class="dd-stat">${holdings.length} holdings</span>
      <span class="dd-lineage">v${dd.drilldown_version || "1.0"}</span>
    </div>`;
  }

  // Sort toolbar
  const sortBar = `<div class="sort-bar">
    <span class="sort-bar-label">Sort:</span>
    ${_SORT_MODES.map(m =>
      `<button class="sort-btn${sortMode === m.id ? " active" : ""}"
         data-sort-mode="${m.id}"
         onclick="changeDrilldownSort('${recId}', '${m.id}')">${escHtml(m.label)}</button>`
    ).join("")}
  </div>`;

  panel.innerHTML = contextHtml + sortBar +
    `<div id="holdings-tbl-${recId}"></div>` +
    `<div class="drill-footer">
      Click any row to expand the RPS breakdown.
      RPS 0–33 (green) = retain candidate &nbsp;·&nbsp; 34–66 (amber) = monitor &nbsp;·&nbsp; 67–100 (red) = reduce candidate.
      Benchmark context is derived from the SIH replay universe percentile (proxy; full price-benchmark integration is a planned enhancement).
    </div>`;

  renderHoldingsTable(holdings, `holdings-tbl-${recId}`, sortMode);
}

function changeDrilldownSort(recId, sortMode) {
  if (!_drilldownState[recId]) _drilldownState[recId] = {};
  _drilldownState[recId].sortMode = sortMode;

  // Update active button state without re-rendering the whole panel
  const panel = document.getElementById(`drilldown-panel-${recId}`);
  if (panel) {
    panel.querySelectorAll(".sort-btn").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-sort-mode") === sortMode);
    });
  }

  const rec = _recDataCache[recId];
  if (rec) renderHoldingsTable(rec.drilldown?.holdings || [], `holdings-tbl-${recId}`, sortMode);
}

function _sortHoldings(holdings, sortMode) {
  const h = [...holdings];
  const _sti = h_ => (h_.strategic_profile || {}).trim_priority_score || 0;
  switch (sortMode) {
    case "rps_desc":      return h.sort((a, b) => b.reduction_priority_score - a.reduction_priority_score);
    case "score_asc":     return h.sort((a, b) => (a.composite_score ?? 99) - (b.composite_score ?? 99));
    case "alloc_desc":    return h.sort((a, b) => (b.percent_of_portfolio || 0) - (a.percent_of_portfolio || 0));
    case "replay_asc":    return h.sort((a, b) => (a.replay_percentile ?? 0) - (b.replay_percentile ?? 0));
    case "ess_asc":       return h.sort((a, b) =>
        (_SIGNAL_WEAKNESS_RANK[a.ess_score_text] ?? 2) - (_SIGNAL_WEAKNESS_RANK[b.ess_score_text] ?? 2));
    case "category_desc": return h.sort((a, b) => (b.category_contribution_pct || 0) - (a.category_contribution_pct || 0));
    case "signal_asc":    return h.sort((a, b) =>
        (_SIGNAL_WEAKNESS_RANK[a.signal_direction] ?? 2) - (_SIGNAL_WEAKNESS_RANK[b.signal_direction] ?? 2));
    case "value_desc":    return h.sort((a, b) => (b.market_value || 0) - (a.market_value || 0));
    case "trim_desc":     return h.sort((a, b) => _sti(b) - _sti(a));
    case "trim_asc":      return h.sort((a, b) => _sti(a) - _sti(b));
    default:              return h;
  }
}

function _rpsBadge(score) {
  const cls = score >= 67 ? "rps-high" : score >= 34 ? "rps-mid" : "rps-low";
  return `<span class="rps-badge ${cls}">${score}</span>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase D — STI helper renderers
// ─────────────────────────────────────────────────────────────────────────────
function _stiBadge(classification) {
  if (!classification) return "";
  const labels = {
    HIGH_CONVICTION_RETAIN: "High Conviction",
    CORE_COMPOUNDER:        "Core Compounder",
    STRATEGIC_CORE:         "Strategic Core",
    THEMATIC_LEADER:        "Thematic Leader",
    TACTICAL_GROWTH:        "Tactical Growth",
    REDUNDANT_EXPOSURE:     "Redundant",
    CONCENTRATION_RISK:     "Concentration Risk",
    REDUCIBLE:              "Reducible",
  };
  const label = labels[classification] || classification.replace(/_/g, " ");
  return `<span class="sti-badge sti-${classification}">${label}</span>`;
}

function _trimBarHtml(score) {
  if (score == null) return "—";
  const pct = Math.min(100, Math.max(0, parseFloat(score) || 0));
  const cls  = pct >= 67 ? "trim-high" : pct >= 34 ? "trim-mid" : "trim-low";
  return `<div class="trim-bar-wrap">
    <div class="trim-bar-track"><div class="trim-bar-fill ${cls}" style="width:${pct.toFixed(0)}%"></div></div>
    <span class="trim-score-label" style="color:${pct>=67?"#e53935":pct>=34?"#ff9800":"#4caf50"}">${pct.toFixed(0)}</span>
  </div>`;
}

function toggleStiPanel(panelId) {
  const el = document.getElementById(panelId);
  const btn = el ? el.previousElementSibling : null;
  if (!el) return;
  const open = el.classList.toggle("open");
  if (btn) btn.textContent = open ? "▾ STI Profile" : "▸ STI Profile";
}

function _stiPanelHtml(sp, containerId, rowIdx) {
  if (!sp) return "";
  const panelId = `${containerId}-sti-${rowIdx}`;
  const peers   = (sp.overlap_peers || []).map(s => `<span class="sti-overlap-chip">${s}</span>`).join("");
  const themes  = (sp.thematic_overlap_clusters || []).map(t =>
    `<span class="sti-theme-chip">${t.replace(/_/g, " ")}</span>`).join("");

  // Factor breakdown rows (sorted by absolute contribution desc)
  const factors = (sp.trim_factors || []).slice().sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const factorRows = factors.map(f => {
    const pts = parseFloat(f.contribution) || 0;
    const cls = pts > 0 ? "pos" : "neg";
    const sign = pts >= 0 ? "+" : "";
    return `<div class="sti-factor-row">
      <span class="sti-factor-name">${escHtml((f.factor || "").replace(/_/g, " "))}</span>
      <span class="sti-factor-pts ${cls}">${sign}${pts.toFixed(1)}pts</span>
    </div>`;
  }).join("");

  return `<button class="sti-toggle" onclick="toggleStiPanel('${panelId}')">▸ STI Profile</button>
<div class="sti-panel" id="${panelId}">
  <div class="sti-panel-row">
    <div><div class="sti-panel-label">Importance</div>
      <div class="sti-panel-value">${escHtml(sp.strategic_importance || "—")}</div></div>
    <div><div class="sti-panel-label">Origin</div>
      <div class="sti-panel-value">${escHtml((sp.exposure_origin || "—").replace(/_/g, " "))}</div></div>
    <div><div class="sti-panel-label">Redundancy</div>
      <div class="sti-panel-value">${sp.thematic_redundancy_score != null ? parseFloat(sp.thematic_redundancy_score).toFixed(0) + "/100" : "—"}</div></div>
    <div><div class="sti-panel-label">Diversif. Contrib.</div>
      <div class="sti-panel-value">${sp.diversification_contribution != null ? parseFloat(sp.diversification_contribution).toFixed(0) + "/100" : "—"}</div></div>
  </div>
  ${themes ? `<div style="margin-bottom:6px"><span class="sti-panel-label">Themes:</span> ${themes}</div>` : ""}
  ${peers  ? `<div style="margin-bottom:6px"><span class="sti-panel-label">Overlap peers:</span> ${peers}</div>` : ""}
  ${factorRows ? `<div style="margin-top:8px;margin-bottom:4px"><strong style="font-size:0.76rem">Trim Factor Breakdown</strong></div>${factorRows}` : ""}
  ${sp.trim_rationale ? `<div class="sti-rationale-box">&#9660; ${escHtml(sp.trim_rationale)}</div>` : ""}
  ${sp.retain_rationale ? `<div class="sti-retain-box">&#9650; ${escHtml(sp.retain_rationale)}</div>` : ""}
</div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5J — Analyst Consensus helpers
// ─────────────────────────────────────────────────────────────────────────────

function _consensusLabelDisplay(label) {
  const map = {
    STRONG_BUY:    { text: "STRONG BUY",    cls: "consensus-strong-buy"    },
    BUY:           { text: "BUY",            cls: "consensus-buy"           },
    MODERATE_BUY:  { text: "MODERATE BUY",  cls: "consensus-moderate-buy"  },
    HOLD:          { text: "HOLD",           cls: "consensus-hold"          },
    SELL:          { text: "SELL",           cls: "consensus-sell"          },
    NO_CONSENSUS:  { text: "NO CONSENSUS",   cls: "consensus-none"          },
  };
  const d = map[label] || { text: label || "—", cls: "consensus-none" };
  return `<span class="consensus-label ${d.cls}">${d.text}</span>`;
}

function _conflictBadgeHtml(badge) {
  if (!badge || badge === "NO_CONSENSUS") return "";
  const map = {
    CONSENSUS_ALIGNED:    { text: "CONSENSUS ALIGNED",    cls: "badge-aligned"    },
    CONSENSUS_DIVERGENCE: { text: "CONSENSUS DIVERGENCE", cls: "badge-divergence" },
    CONSENSUS_NEUTRAL:    { text: "CONSENSUS NEUTRAL",    cls: "badge-neutral"    },
  };
  const d = map[badge] || { text: badge.replace(/_/g, " "), cls: "badge-neutral" };
  return `<span class="conflict-badge ${d.cls}">${d.text}</span>`;
}

function _computeConflictBadge(essText, consensusLabel) {
  if (!consensusLabel || consensusLabel === "NO_CONSENSUS") return "NO_CONSENSUS";
  const ess = (essText || "").toUpperCase();
  if (!ess || ess === "UNKNOWN" || ess === "NEUTRAL") return "CONSENSUS_NEUTRAL";
  const essBullish = (ess === "VERY_BULLISH" || ess === "BULLISH");
  const essBearish = (ess === "VERY_BEARISH" || ess === "BEARISH");
  const abrBuy  = (consensusLabel === "STRONG_BUY" || consensusLabel === "BUY" || consensusLabel === "MODERATE_BUY");
  const abrSell = (consensusLabel === "HOLD" || consensusLabel === "SELL");
  if ((essBullish && abrBuy) || (essBearish && abrSell)) return "CONSENSUS_ALIGNED";
  if ((essBullish && abrSell) || (essBearish && abrBuy)) return "CONSENSUS_DIVERGENCE";
  return "CONSENSUS_NEUTRAL";
}

function _consensusPanelHtml(ac, essText) {
  if (!ac) return "";
  const badge = _computeConflictBadge(essText, ac.consensus_label);
  const upsideColor = (ac.upside_pct != null)
    ? (ac.upside_pct >= 0 ? "var(--green)" : "var(--sev-high)")
    : "var(--muted)";
  const upsideStr = ac.upside_pct != null
    ? `<span style="color:${upsideColor};font-weight:700">${ac.upside_pct >= 0 ? "+" : ""}${parseFloat(ac.upside_pct).toFixed(1)}%</span>`
    : "—";
  const targetStr  = ac.price_target  != null ? `$${parseFloat(ac.price_target).toFixed(2)}`  : "—";
  const currentStr = ac.current_price != null ? `$${parseFloat(ac.current_price).toFixed(2)}` : "—";
  const abrStr     = ac.abr           != null ? parseFloat(ac.abr).toFixed(2) : "—";

  return `<div class="consensus-panel">
  <div class="consensus-panel-header">
    <strong style="font-size:0.76rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted)">Analyst Consensus</strong>
    ${_conflictBadgeHtml(badge)}
  </div>
  <div class="consensus-panel-row">
    <div class="consensus-field"><div class="consensus-field-label">Consensus</div>
      <div class="consensus-field-value">${_consensusLabelDisplay(ac.consensus_label)}</div></div>
    <div class="consensus-field"><div class="consensus-field-label">ABR</div>
      <div class="consensus-field-value" style="font-weight:700">${abrStr}</div></div>
    <div class="consensus-field"><div class="consensus-field-label">Price Target</div>
      <div class="consensus-field-value">${targetStr}</div></div>
    <div class="consensus-field"><div class="consensus-field-label">Current Price</div>
      <div class="consensus-field-value">${currentStr}</div></div>
    <div class="consensus-field"><div class="consensus-field-label">Upside</div>
      <div class="consensus-field-value">${upsideStr}</div></div>
    <div class="consensus-field"><div class="consensus-field-label">Refresh</div>
      <div class="consensus-field-value" style="color:var(--muted)">${escHtml(ac.refresh_date || "—")}</div></div>
  </div>
</div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5K — Fidelity Analyst helpers
// ─────────────────────────────────────────────────────────────────────────────

function _fidelityRatingDisplay(rating) {
  const map = {
    STRONG_BUY:  { text: "STRONG BUY",  cls: "fidelity-strong-buy"  },
    BUY:         { text: "BUY",          cls: "fidelity-buy"         },
    HOLD:        { text: "HOLD",         cls: "fidelity-hold"        },
    SELL:        { text: "SELL",         cls: "fidelity-sell"        },
    STRONG_SELL: { text: "STRONG SELL",  cls: "fidelity-strong-sell" },
  };
  const d = map[rating] || { text: rating || "—", cls: "fidelity-unknown" };
  return `<span class="fidelity-rating ${d.cls}">${d.text}</span>`;
}

function _matrixBadgeHtml(classification) {
  if (!classification) return "";
  const map = {
    FULL_ALIGNMENT_BULLISH: { text: "Full Alignment — Bullish", cls: "matrix-full-bullish" },
    FULL_ALIGNMENT_BEARISH: { text: "Full Alignment — Bearish", cls: "matrix-full-bearish" },
    PARTIAL_ALIGNMENT:      { text: "Partial Alignment",        cls: "matrix-partial"      },
    MAJOR_DIVERGENCE:       { text: "Major Divergence",         cls: "matrix-divergence"   },
    INSUFFICIENT_DATA:      { text: "Insufficient Data",        cls: "matrix-insufficient" },
  };
  const d = map[classification] || { text: classification.replace(/_/g, " "), cls: "matrix-insufficient" };
  return `<span class="matrix-badge ${d.cls}">${d.text}</span>`;
}

function _directionChip(direction) {
  if (!direction || direction === "UNKNOWN") return `<span style="color:var(--muted)">—</span>`;
  const color = direction === "BULLISH" ? "var(--green)"
              : direction === "BEARISH" ? "var(--sev-high)"
              : "var(--muted)";
  return `<span style="color:${color};font-weight:700;font-size:0.78rem">${direction}</span>`;
}

function _fidelityPanelHtml(fs) {
  if (!fs) return "";
  const matrix = fs.consensus_matrix || {};
  const scoreStr = fs.ess_numeric != null ? `${parseFloat(fs.ess_numeric).toFixed(1)} / 5` : "—";

  return `<div class="fidelity-panel">
  <div class="fidelity-panel-header">
    <strong style="font-size:0.76rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted)">Fidelity Analyst (ESS)</strong>
    ${_matrixBadgeHtml(matrix.classification)}
  </div>
  <div class="fidelity-panel-row">
    <div class="fidelity-field">
      <div class="fidelity-field-label">Rating</div>
      <div class="fidelity-field-value">${_fidelityRatingDisplay(fs.fidelity_rating)}</div>
    </div>
    <div class="fidelity-field">
      <div class="fidelity-field-label">Score</div>
      <div class="fidelity-field-value">${scoreStr}</div>
    </div>
    <div class="fidelity-field">
      <div class="fidelity-field-label">Direction</div>
      <div class="fidelity-field-value">${_directionChip(fs.fidelity_direction)}</div>
    </div>
    <div class="fidelity-field">
      <div class="fidelity-field-label">Refresh</div>
      <div class="fidelity-field-value" style="color:var(--muted)">${escHtml(fs.refresh_date || "—")}</div>
    </div>
    <div class="fidelity-field">
      <div class="fidelity-field-label">Coverage</div>
      <div class="fidelity-field-value" style="font-size:0.72rem;color:var(--muted)">${escHtml((fs.coverage_domain || "—").replace(/_/g, " "))}</div>
    </div>
  </div>
</div>`;
}

function _consensusStackHtml(fs, ac) {
  if (!fs && !ac) return "";
  const matrix = (fs || {}).consensus_matrix || {};
  const zDir   = _directionChip(matrix.zacks_direction);
  const essDir  = _directionChip(matrix.ess_direction);
  const abrDir  = _directionChip(matrix.yahoo_direction);
  const abrLabel = ac ? _consensusLabelDisplay(ac.consensus_label) : `<span style="color:var(--muted)">—</span>`;
  const zScoreRaw = matrix.zacks_direction && matrix.zacks_direction !== "UNKNOWN"
    ? `<span style="font-size:0.72rem;color:var(--muted)">(${matrix.zacks_direction})</span>` : "";

  return `<div class="consensus-stack">
  <div class="consensus-stack-header">
    <strong style="font-size:0.76rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted)">Analyst Signal Stack</strong>
    ${_matrixBadgeHtml(matrix.classification)}
  </div>
  <div class="consensus-stack-signals">
    <div class="consensus-stack-signal">
      <div class="consensus-stack-label">ESS (Fidelity)</div>
      <div>${essDir}</div>
      <div style="font-size:0.70rem;color:var(--muted)">${escHtml((fs || {}).ess_text || "—")}</div>
    </div>
    <div class="consensus-stack-signal">
      <div class="consensus-stack-label">Yahoo ABR</div>
      <div>${abrDir}</div>
      <div style="font-size:0.70rem">${abrLabel}</div>
    </div>
    <div class="consensus-stack-signal">
      <div class="consensus-stack-label">Zacks</div>
      <div>${zDir}</div>
    </div>
    <div class="consensus-stack-signal" style="margin-left:8px">
      <div class="consensus-stack-label">Signals</div>
      <div style="font-size:0.78rem;color:var(--muted)">${matrix.signals_available ?? "—"} / 3 available</div>
    </div>
  </div>
</div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5N — Signal Agreement Engine
// ─────────────────────────────────────────────────────────────────────────────

/** Convert ESS text label to BULLISH / NEUTRAL / BEARISH / UNKNOWN. */
function _essDirection(essText) {
  const t = (essText || "").toUpperCase();
  if (t === "VERY_BULLISH" || t === "BULLISH") return "BULLISH";
  if (t === "VERY_BEARISH" || t === "BEARISH") return "BEARISH";
  if (t === "NEUTRAL") return "NEUTRAL";
  return "UNKNOWN";
}

/** Convert normalized Zacks score (1–5 ascending) to direction. */
function _zacksDirection(zacksScore) {
  const z = parseFloat(zacksScore);
  if (isNaN(z)) return "UNKNOWN";
  if (z >= 4.0) return "BULLISH";
  if (z <= 2.0) return "BEARISH";
  return "NEUTRAL";
}

/** Convert Yahoo consensus_label to direction. */
function _yahooDirection(consensusLabel) {
  const l = (consensusLabel || "").toUpperCase();
  if (l === "STRONG_BUY" || l === "BUY" || l === "MODERATE_BUY") return "BULLISH";
  if (l === "HOLD") return "NEUTRAL";
  if (l === "SELL" || l === "STRONG_SELL" || l === "MODERATE_SELL") return "BEARISH";
  return "UNKNOWN";
}

/** Convert normalized Danelfin score (1–5) to direction. */
function _danelfinDirection(danelfinScore) {
  const d = parseFloat(danelfinScore);
  if (isNaN(d)) return "UNKNOWN";
  if (d >= 3.5) return "BULLISH";
  if (d <= 2.5) return "BEARISH";
  return "NEUTRAL";
}

/** Derive native Zacks rank from normalized score: rank = 6 − score. */
function _zacksNativeRank(zacksScore) {
  const z = parseFloat(zacksScore);
  if (isNaN(z)) return null;
  return Math.round(6 - z);
}

/** Map Zacks rank (1–5) to analyst language. */
function _zacksRankLabel(rank) {
  return ["", "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"][rank] || "—";
}

/** Derive native Danelfin raw score (1–10) from normalized (1–5). */
function _danelfinNativeRaw(danelfinScore) {
  const d = parseFloat(danelfinScore);
  if (isNaN(d)) return null;
  return Math.round(d * 2);
}

/**
 * Compute signal agreement summary.
 * Agreement is defined as the count of signals that are BULLISH
 * (consistent with the Objective 1 mapping). A separate ESS-override flag
 * surfaces when the primary signal (ESS, 55% weight) diverges from the majority.
 *
 * @param {object} ov  - security_overlay row
 * @param {object} ac  - analyst_consensus_by_symbol entry (may be null)
 * @param {object} fs  - fidelity_signals_by_symbol entry (may be null)
 * @returns {{ signals, bullish, total, label, confidence, essOverride }}
 */
function _computeSignalAgreement(ov, ac, fs) {
  const essDir  = _essDirection((ov && ov.ess_score_text) || (fs && fs.ess_text));
  const zDir    = _zacksDirection(ov && ov.zacks_rating);
  const yDir    = _yahooDirection(ac && ac.consensus_label);
  const danDir  = _danelfinDirection(ov && ov.danelfin_score);

  const zRank   = _zacksNativeRank(ov && ov.zacks_rating);
  const danRaw  = _danelfinNativeRaw(ov && ov.danelfin_score);
  const abrVal  = (ac && ac.abr != null) ? parseFloat(ac.abr).toFixed(2) : null;
  const essLabel = (ov && ov.ess_score_text) ? ov.ess_score_text.replace(/_/g, " ") : "—";

  const signals = [
    {
      name: "ESS",
      native: essLabel,
      sublabel: "Primary Signal (55%)",
      direction: essDir,
    },
    {
      name: "Zacks",
      native: zRank != null ? `Rank #${zRank} ${_zacksRankLabel(zRank)}` : "—",
      sublabel: zRank != null ? `Score ${parseFloat(ov.zacks_rating).toFixed(1)} / 5` : "",
      direction: zDir,
    },
    {
      name: "Yahoo ABR",
      native: abrVal != null ? `ABR ${abrVal}` : "—",
      sublabel: ac && ac.consensus_label ? ac.consensus_label.replace(/_/g, " ") : "",
      direction: yDir,
    },
    {
      name: "Danelfin",
      native: danRaw != null ? `${danRaw} / 10` : "—",
      sublabel: danRaw != null ? `Score ${parseFloat(ov.danelfin_score).toFixed(1)} / 5` : "",
      direction: danDir,
    },
  ];

  const available = signals.filter(s => s.direction !== "UNKNOWN");
  const bullish   = available.filter(s => s.direction === "BULLISH").length;
  const total     = available.length;

  let label, confidence;
  if (total === 0) {
    label = "INSUFFICIENT DATA"; confidence = "UNKNOWN";
  } else if (bullish === total) {
    label = "FULL ALIGNMENT"; confidence = "HIGH";
  } else if (bullish >= 3 && total >= 4) {
    label = "STRONG ALIGNMENT"; confidence = "HIGH";
  } else if (bullish >= 2) {
    label = "MIXED"; confidence = "MEDIUM";
  } else if (bullish === 1) {
    label = "DIVERGENT"; confidence = "LOW";
  } else {
    label = "MAJOR DIVERGENCE"; confidence = "LOW";
  }

  // ESS override flag: primary signal diverges from the majority direction
  const majorityBullish = bullish > total / 2;
  const essOverride = essDir !== "UNKNOWN" && total >= 2 &&
    ((essDir === "BEARISH" && majorityBullish) ||
     (essDir === "BULLISH" && !majorityBullish && total - bullish > bullish));

  return { signals, bullish, total, label, confidence, essOverride };
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5N — Freshness helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Classify signal freshness based on age in days relative to a reference date. */
function _freshnessStatus(dateStr, refDateStr) {
  if (!dateStr) return "UNKNOWN";
  const date = new Date(dateStr);
  const ref  = refDateStr ? new Date(refDateStr) : new Date();
  const ageDays = (ref - date) / (1000 * 60 * 60 * 24);
  if (ageDays <= 2)  return "FRESH";
  if (ageDays <= 5)  return "WARNING";
  if (ageDays <= 10) return "STALE";
  return "CRITICAL";
}

/** Render a freshness status chip. */
function _freshnessChip(status) {
  const map = {
    FRESH:    { cls: "fn-fresh",    label: "FRESH"    },
    WARNING:  { cls: "fn-warning",  label: "WARNING"  },
    STALE:    { cls: "fn-stale",    label: "STALE"    },
    CRITICAL: { cls: "fn-critical", label: "CRITICAL" },
    UNKNOWN:  { cls: "fn-unknown",  label: "—"        },
  };
  const d = map[status] || map["UNKNOWN"];
  return `<span class="fn-chip ${d.cls}">${d.label}</span>`;
}

/** Format days-ago as a compact string. */
function _ageDaysStr(dateStr, refDateStr) {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  const ref  = refDateStr ? new Date(refDateStr) : new Date();
  const age  = Math.round((ref - date) / (1000 * 60 * 60 * 24));
  return age <= 0 ? "today" : `${age}d`;
}

/** Return the "worst" freshness status across an array of statuses. */
function _worstFreshness(statuses) {
  const order = ["CRITICAL", "STALE", "WARNING", "FRESH", "UNKNOWN"];
  for (const s of order) {
    if (statuses.includes(s)) return s;
  }
  return "UNKNOWN";
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5N — Signal Agreement Panel HTML
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Build the combined Signal Agreement + Freshness panel for the breakdown row.
 * @param {object} ov  - security_overlay row
 * @param {object} ac  - analyst_consensus entry (may be null)
 * @param {object} fs  - fidelity_signals entry (may be null)
 */
function _signalAgreementPanelHtml(ov, ac, fs) {
  const meta    = (_lastAnalysisData && _lastAnalysisData.signal_source_metadata) || {};
  const refDate = (_lastAnalysisData && _lastAnalysisData.snapshot_date) || "";
  const ag      = _computeSignalAgreement(ov, ac, fs);

  // ── Agreement label styling ───────────────────────────────────────────────
  const labelColors = {
    "FULL ALIGNMENT":    "#1a7c4f",
    "STRONG ALIGNMENT":  "#2e7d52",
    "MIXED":             "#b8860b",
    "DIVERGENT":         "#c0392b",
    "MAJOR DIVERGENCE":  "#c0392b",
    "INSUFFICIENT DATA": "#999",
  };
  const labelColor = labelColors[ag.label] || "#999";

  const confCls = {
    HIGH: "sa-conf-high", MEDIUM: "sa-conf-medium", LOW: "sa-conf-low"
  }[ag.confidence] || "";

  // ── Direction icon and color ──────────────────────────────────────────────
  const dirIcon = dir => {
    if (dir === "BULLISH") return `<span style="color:var(--green);font-weight:700">✓</span>`;
    if (dir === "BEARISH") return `<span style="color:var(--sev-high);font-weight:700">✗</span>`;
    if (dir === "NEUTRAL") return `<span style="color:var(--muted)">~</span>`;
    return `<span style="color:var(--muted)">?</span>`;
  };
  const dirLabel = dir => {
    const colors = { BULLISH: "var(--green)", BEARISH: "var(--sev-high)", NEUTRAL: "var(--muted)", UNKNOWN: "var(--muted)" };
    return `<span style="color:${colors[dir] || "var(--muted)"};font-weight:600;font-size:0.80rem">${dir || "—"}</span>`;
  };

  // ── Signal rows ───────────────────────────────────────────────────────────
  const signalRows = ag.signals.map(s => `
    <tr>
      <td style="font-weight:700;font-family:monospace;font-size:0.80rem;padding:5px 8px;white-space:nowrap">${escHtml(s.name)}</td>
      <td style="font-size:0.80rem;padding:5px 8px;color:var(--muted)">${escHtml(s.native)}</td>
      <td style="padding:5px 8px">${dirLabel(s.direction)}</td>
      <td style="padding:5px 8px;text-align:center;font-size:1rem">${dirIcon(s.direction)}</td>
    </tr>`).join("");

  // ── Freshness rows ────────────────────────────────────────────────────────
  const essFreshDate   = (fs && fs.refresh_date) || "";
  const yahooFreshDate = (ac && ac.refresh_date) || "";
  const zacksFreshDate = meta.zacks_refresh_date || "";
  const danFreshDate   = meta.danelfin_refresh_date || "";

  const freshnessData = [
    { name: "ESS",      date: essFreshDate,   source: "Fidelity / StarMine" },
    { name: "Zacks",    date: zacksFreshDate,  source: "Zacks API"           },
    { name: "Danelfin", date: danFreshDate,    source: "Danelfin AI"         },
    { name: "Yahoo",    date: yahooFreshDate,  source: "Yahoo Finance"       },
  ];
  const freshnessRows = freshnessData.filter(r => r.date).map(r => {
    const status = _freshnessStatus(r.date, refDate);
    return `<tr>
      <td style="font-weight:700;font-family:monospace;font-size:0.76rem;padding:4px 8px">${r.name}</td>
      <td style="font-size:0.76rem;color:var(--muted);padding:4px 8px">${escHtml(r.source)}</td>
      <td style="font-size:0.76rem;padding:4px 8px">${escHtml(r.date)}</td>
      <td style="font-size:0.76rem;padding:4px 8px">${_ageDaysStr(r.date, refDate)}</td>
      <td style="padding:4px 8px">${_freshnessChip(status)}</td>
    </tr>`;
  }).join("");

  // ── Yahoo target divergence flag ──────────────────────────────────────────
  const yahooFlag = (ac && ac.abr != null && ac.upside_pct != null &&
      parseFloat(ac.abr) <= 2.5 && parseFloat(ac.upside_pct) < -10)
    ? `<div class="fn-target-flag">
        <span class="fn-target-icon">⚠</span>
        <strong>Analyst Target Divergence</strong>
        — Analyst consensus is bullish (ABR&nbsp;${parseFloat(ac.abr).toFixed(2)})
        but the price target implies ${parseFloat(ac.upside_pct).toFixed(1)}% upside.
        This usually indicates stale analyst targets at the source.
      </div>`
    : "";

  // ── ESS override note ─────────────────────────────────────────────────────
  const essOverrideNote = ag.essOverride
    ? `<div class="sa-ess-override">
        ⚠ <strong>ESS Primary Override:</strong>
        ESS (55% weight) is ${escHtml((ov && ov.ess_score_text || "").replace(/_/g, " "))}
        and diverges from the majority signal direction. ESS anchors the final signal direction.
      </div>`
    : "";

  return `<div class="sa-panel">
    <div class="sa-panel-header">
      <span class="sa-panel-title">Signal Agreement</span>
      <span class="sa-count">${ag.bullish}&thinsp;/&thinsp;${ag.total}</span>
      <span class="sa-label" style="color:${labelColor}">${ag.label}</span>
      <span class="sa-conf ${confCls}">Confidence: ${ag.confidence}</span>
    </div>
    <div class="sa-body">
      <table class="sa-table">
        <thead><tr>
          <th style="text-align:left;padding:5px 8px;font-size:0.66rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Signal</th>
          <th style="text-align:left;padding:5px 8px;font-size:0.66rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Native Value</th>
          <th style="text-align:left;padding:5px 8px;font-size:0.66rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Direction</th>
          <th style="text-align:center;padding:5px 8px;font-size:0.66rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Bullish?</th>
        </tr></thead>
        <tbody>${signalRows}</tbody>
      </table>
    </div>
    ${essOverrideNote}
    ${freshnessRows ? `
    <div class="sa-freshness">
      <div class="sa-freshness-header">Signal Freshness</div>
      <table style="border-collapse:collapse;width:100%;margin-top:4px">
        <thead><tr>
          <th style="text-align:left;padding:4px 8px;font-size:0.64rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Signal</th>
          <th style="text-align:left;padding:4px 8px;font-size:0.64rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Source</th>
          <th style="text-align:left;padding:4px 8px;font-size:0.64rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Updated</th>
          <th style="text-align:left;padding:4px 8px;font-size:0.64rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Age</th>
          <th style="text-align:left;padding:4px 8px;font-size:0.64rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);border-bottom:1px solid #c5cae9">Status</th>
        </tr></thead>
        <tbody>${freshnessRows}</tbody>
      </table>
    </div>` : ""}
    ${yahooFlag}
  </div>`;
}

function _actionBadge(action) {
  return `<span class="action-badge action-${action}">${(action || "").replace(/_/g, " ")}</span>`;
}

function _bmStateHtml(state) {
  const labels = {
    OUTPERFORMING:     "▲ Outperforming",
    UNDERPERFORMING:   "▼ Underperforming",
    NEUTRAL:           "→ Neutral",
    INSUFFICIENT_DATA: "—",
  };
  return `<span class="bm-${state}">${labels[state] || "—"}</span>`;
}

function renderHoldingsTable(holdings, containerId, sortMode) {
  const el = document.getElementById(containerId);
  if (!el) return;

  const sorted = _sortHoldings(holdings, sortMode);

  const rows = sorted.map((h, i) => {
    const explainId = `${containerId}-ex-${i}`;
    const stiId     = `${containerId}-sti-${i}`;
    const score     = h.composite_score != null ? parseFloat(h.composite_score).toFixed(2) : "—";
    const scoreColor = h.signal_direction === "BULLISH" ? "var(--green)"
                     : h.signal_direction === "BEARISH" ? "var(--sev-high)"
                     : "var(--muted)";
    const replayStr = h.replay_supported
      ? `✓${h.replay_percentile != null ? " " + parseFloat(h.replay_percentile).toFixed(0) + "th" : ""}`
      : "—";
    const pctile = h.rps_percentile != null
      ? ` <span style="color:var(--muted);font-size:0.68rem">(${h.rps_percentile}th)</span>`
      : "";
    const bd = h.rps_breakdown || {};
    const sp = h.strategic_profile;
    const ac = (_lastAnalysisData?.analyst_consensus_by_symbol || {})[h.symbol?.toUpperCase()];
    const fs = (_lastAnalysisData?.fidelity_signals_by_symbol  || {})[h.symbol?.toUpperCase()];

    return `
      <tr class="data-row" onclick="toggleRpsExplain('${explainId}')">
        <td>${escHtml(h.symbol)}</td>
        <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
            title="${escHtml(h.description)}">${escHtml(h.description)}</td>
        <td style="text-align:right">${pct(h.percent_of_portfolio)}</td>
        <td style="text-align:right">${h.category_contribution_pct != null ? parseFloat(h.category_contribution_pct).toFixed(1) + "%" : "—"}</td>
        <td style="text-align:right">${formatMV(h.market_value)}</td>
        <td>${escHtml(h.market_cap_bucket || "—")}</td>
        <td>${escHtml(h.geography || "—")}</td>
        <td style="max-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:0.72rem"
            title="${escHtml(h.sector)}">${escHtml(h.sector || "—")}</td>
        <td style="color:${scoreColor};font-weight:700">${score}</td>
        <td><span class="dir-${h.signal_direction}">${h.signal_direction || "—"}</span></td>
        <td style="font-size:0.73rem">${escHtml(h.ess_score_text || "—")}</td>
        <td style="font-size:0.73rem">${replayStr}</td>
        <td style="font-size:0.73rem">${_bmStateHtml(h.benchmark_relative_state)}</td>
        <td>${_actionBadge(h.suggested_action)}</td>
        <td>${_rpsBadge(h.reduction_priority_score)}${pctile}</td>
        <td>${sp ? _stiBadge(sp.strategic_classification) : "—"}</td>
        <td>${sp ? _trimBarHtml(sp.trim_priority_score) : "—"}</td>
      </tr>
      <tr class="rps-explain-row" id="${explainId}">
        <td colspan="17">
          <strong>${escHtml(h.symbol)} RPS Breakdown:</strong>
          &nbsp; Signal <strong>${bd.signal_component ?? "—"}pts</strong>
          + Score <strong>${bd.score_component ?? "—"}pts</strong>
          + Replay <strong>${bd.replay_component ?? "—"}pts</strong>
          + Category <strong>${bd.allocation_component ?? "—"}pts</strong>
          = <strong>${h.reduction_priority_score}/100</strong>
          &nbsp;·&nbsp; ${escHtml(bd.explanation || "")}
          ${sp ? _stiPanelHtml(sp, containerId, i) : ""}
          ${_fidelityPanelHtml(fs)}
          ${_consensusPanelHtml(ac, h.ess_score_text)}
          ${_consensusStackHtml(fs, ac)}
        </td>
      </tr>`;
  }).join("");

  el.innerHTML = `
    <div class="holdings-tbl-wrap">
      <table class="holdings-tbl">
        <thead><tr>
          <th>Symbol</th><th>Description</th>
          <th style="text-align:right">% Port</th>
          <th style="text-align:right">% of Cat</th>
          <th style="text-align:right">Value</th>
          <th>Cap</th><th>Geo</th><th>Sector</th>
          <th>Score</th><th>Signal</th><th>ESS</th>
          <th>Replay</th><th>vs Benchmark</th>
          <th>Action</th><th>RPS</th>
          <th>STI Class</th><th>Trim ▲</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function toggleRpsExplain(explainId) {
  const el = document.getElementById(explainId);
  if (el) el.classList.toggle("open");
}

// ─────────────────────────────────────────────────────────────────────────────
// Recommendations
// ─────────────────────────────────────────────────────────────────────────────
function renderRecommendations(recs) {
  const el = document.getElementById("recommendationsContent");
  const sepHtml = `<div class="rec-section-separator">Allocation &amp; Portfolio Observations</div>`;

  if (!recs.length) {
    el.innerHTML = sepHtml + `<div style="padding:20px;text-align:center;color:var(--muted)">
      ✓ No significant recommendations — portfolio is well-aligned.
    </div>`;
    return;
  }

  // Cache all recs by ID for later use in drilldown functions
  recs.forEach(r => { if (r.recommendation_id) _recDataCache[r.recommendation_id] = r; });

  const cards = recs.map((r, i) => {
    const symbols = (r.affected_symbols || []).map(s =>
      `<span class="rec-symbol">${s}</span>`
    ).join("");
    const typeLabel = (r.recommendation_type || "").replace(/_/g, " ");
    const driftStr = r.drift_pct != null
      ? `<span style="font-size:0.78rem;color:var(--muted)">Drift: ${parseFloat(r.drift_pct) > 0 ? "+" : ""}${parseFloat(r.drift_pct).toFixed(1)}pp</span>`
      : "";

    // Phase C — rec_state badge
    const state = r.rec_state || "ACTIVE";
    const stateLabels = {
      ACTIVE: "Active",
      DOWNGRADED: "Downgraded",
      INFORMATIONAL: "Informational",
      SUPPRESSED: "Suppressed",
    };
    const stateBadge = `<span class="rec-state-badge rec-state-${state}">${stateLabels[state] || state}</span>`;

    // Phase C — reasoning trace (collapsible)
    const traceId = `trace-${r.recommendation_id}`;
    const traceHtml = r.reasoning_trace
      ? `<button class="rec-trace-toggle" onclick="toggleTrace('${traceId}')">▸ Why this state?</button>
         <div class="rec-trace-body" id="${traceId}">${escHtml(r.reasoning_trace)}</div>`
      : "";

    // Phase C — ETF contributors
    const contributors = r.etf_contributors || [];
    const etfBarHtml = contributors.length > 0
      ? `<div class="rec-etf-bar">
           <span class="rec-etf-label">ETF contributors:</span>
           ${contributors.map(s => `<span class="rec-etf-chip">${s}</span>`).join("")}
         </div>`
      : "";

    // Phase C — exposure breakdown
    let exposureHtml = "";
    const hasExposure = (r.effective_exposure_pct != null && r.effective_exposure_pct > 0)
      || (r.direct_exposure_pct != null && r.direct_exposure_pct > 0)
      || (r.etf_derived_exposure_pct != null && r.etf_derived_exposure_pct > 0);
    if (hasExposure) {
      const eff   = parseFloat(r.effective_exposure_pct   || 0).toFixed(1);
      const dir   = parseFloat(r.direct_exposure_pct      || 0).toFixed(1);
      const deriv = parseFloat(r.etf_derived_exposure_pct || 0).toFixed(1);
      exposureHtml = `<div class="rec-exposure-row">
        <span>Exposure:</span>
        <span class="eff-pct">${eff}% effective</span>
        <span style="color:#ccc">|</span>
        <span class="direct-pct">${dir}% direct</span>
        <span style="color:#ccc">+</span>
        <span class="derived-pct">${deriv}% ETF-derived</span>
      </div>`;
    }

    // Phase E — rich narrative block (replaces simple rationale for Phase E types)
    const phaseEHtml = _buildPhaseECardExtras(r);

    // Phase 7.3B — Optimizer conflict badges and view block
    const optimizerBadgesHtml = _buildOptimizerBadges(r);
    const optimizerViewHtml   = _buildOptimizerViewBlock(r);

    // Drill-down toggle button — only shown when drilldown data exists
    const dd = r.drilldown;
    const holdingCount = dd && dd.holdings ? dd.holdings.length : 0;
    const drillBtn = holdingCount > 0
      ? `<button class="drill-toggle" id="drill-toggle-${r.recommendation_id}"
           onclick="toggleDrilldown('${r.recommendation_id}')">▼ View ${holdingCount} Holdings</button>`
      : "";

    const recType = r.recommendation_type || "";
    const isPhaseE = _PHASE_E_TYPES.has(recType);

    // Phase 22D.2 WS-C: visible blocked implementation banner (AC-C1, AC-C2).
    // Shown when an INCREASE_UNDERWEIGHT recommendation has no actionable path
    // because all vehicles failed optimizer gates or the mandate blocks deployment.
    let blockedWarningHtml = "";
    if (recType === "INCREASE_UNDERWEIGHT" && r.optimizer_metadata) {
      const decision = r.optimizer_metadata.optimizer_decision || "";
      if (decision === "NO_CANDIDATES" || decision === "MANDATE_BLOCKED") {
        const isMandate = decision === "MANDATE_BLOCKED";
        const bannerLabel = isMandate ? "Mandate Blocked" : "No Actionable Path";
        const bannerMsg   = isMandate
          ? "This increase is blocked by the active portfolio mandate. No deployment action is currently available."
          : "All implementation vehicles failed optimizer gates. No actionable implementation path is available.";
        const bannerMod   = isMandate ? " rec-blocked-banner-mandate" : "";
        blockedWarningHtml = `<div class="rec-blocked-banner${bannerMod}">
          <span class="rec-blocked-banner-label">⚑ ${escHtml(bannerLabel)}</span>
          <span>${escHtml(bannerMsg)}</span>
        </div>`;
      }
    }

    return `<div class="rec-card pri-${r.priority} state-${state} type-${recType} urgency-${r.mandate_urgency || ""}">
      ${isPhaseE ? _phaseETypeHeader(recType) : ""}
      <div class="rec-title">#${i+1} &nbsp; ${escHtml(r.title)}</div>
      <div class="rec-rationale">${escHtml(r.rationale)}</div>
      ${blockedWarningHtml}
      ${!isPhaseE && r.evidence_summary ? `<div class="rec-evidence">${escHtml(r.evidence_summary)}</div>` : ""}
      <div class="rec-meta">
        ${stateBadge}
        <span class="rec-type-badge">${typeLabel}</span>
        <span class="rec-conf-badge">Confidence: ${r.confidence || "—"}</span>
        ${r.mandate_urgency ? `<span class="mandate-urgency-badge urgency-${r.mandate_urgency}">${r.mandate_urgency}</span>` : ""}
        ${r.mandate_drift_label ? `<span class="mandate-drift-badge mdrift-${r.mandate_drift_label}">${r.mandate_drift_label.replace(/_/g, " ")}</span>` : ""}
        ${driftStr}
        ${symbols ? `<div class="rec-symbols">${symbols}</div>` : ""}
      </div>
      ${exposureHtml}
      ${etfBarHtml}
      ${r.recommendation_type === "CASH_ALLOCATION" && r.cash_mandate_context
        ? `<div class="cash-context-block"><div class="cash-context-label">Cash Mandate Context</div>${escHtml(r.cash_mandate_context)}</div>`
        : ""}
      ${phaseEHtml}
      ${traceHtml}
      ${optimizerBadgesHtml}
      ${optimizerViewHtml}
      ${r.mandate_narrative
        ? `<button class="pmi-mandate-toggle" onclick="togglePmiMandate('pmi-${r.recommendation_id}')">&#9656; Portfolio Mandate View</button>
           <div class="pmi-mandate-body" id="pmi-${r.recommendation_id}">
             <div class="pmi-narrative-text">${escHtml(r.mandate_narrative)}</div>
             ${r.mandate_rationale ? `<div class="pmi-rationale-text">${escHtml(r.mandate_rationale)}</div>` : ""}
           </div>`
        : ""}
      ${drillBtn}
      <div class="rec-drilldown" id="drilldown-panel-${r.recommendation_id}"></div>
    </div>`;
  }).join("");

  el.innerHTML = sepHtml + `<div class="rec-list">${cards}</div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase E — Card rendering helpers
// ─────────────────────────────────────────────────────────────────────────────

const _PHASE_E_TYPES = new Set([
  "PORTFOLIO_CONSTRUCTION_NARRATIVE",
  "TOP_TRIM_CANDIDATES",
  "THEMATIC_SATURATION_NARRATIVE",
  "STRATEGIC_RETAIN_NARRATIVE",
  "CONCENTRATION_ECOSYSTEM",
]);

const _PHASE_E_TYPE_META = {
  PORTFOLIO_CONSTRUCTION_NARRATIVE: { label: "Strategic Assessment",    cls: "phase-e-PCN" },
  TOP_TRIM_CANDIDATES:              { label: "Trim Candidates",          cls: "phase-e-TRIM" },
  THEMATIC_SATURATION_NARRATIVE:    { label: "Thematic Ecosystem",       cls: "phase-e-SAT" },
  STRATEGIC_RETAIN_NARRATIVE:       { label: "Strategic Retain Signal",  cls: "phase-e-RETAIN" },
  CONCENTRATION_ECOSYSTEM:          { label: "Concentration Topology",   cls: "phase-e-CONC" },
};

function _phaseETypeHeader(recType) {
  const meta = _PHASE_E_TYPE_META[recType];
  if (!meta) return "";
  return `<div class="phase-e-header">
    <span class="phase-e-type-label ${meta.cls}">${meta.label}</span>
  </div>`;
}

function _buildPhaseECardExtras(r) {
  const recType = r.recommendation_type || "";

  if (recType === "TOP_TRIM_CANDIDATES") {
    return _renderTrimCandidatesList(r);
  }
  if (recType === "STRATEGIC_RETAIN_NARRATIVE") {
    return _renderRetainHighlight(r);
  }
  if (recType === "THEMATIC_SATURATION_NARRATIVE") {
    return _renderThematicEcosystem(r);
  }
  if (recType === "PORTFOLIO_CONSTRUCTION_NARRATIVE") {
    return _renderConstructionEvidence(r);
  }
  return "";
}

function _renderTrimCandidatesList(r) {
  const syms = r.affected_symbols || [];
  if (!syms.length) return "";
  const rows = syms.slice(0, 5).map((sym, idx) => {
    // Try to get STI score from cached data
    const score = _getSymbolTrimScore(sym);
    const scorePct = score != null ? Math.min(100, Math.max(0, score)) : 0;
    const cls = scorePct >= 67 ? "trim-high" : scorePct >= 34 ? "trim-mid" : "trim-low";
    const scoreStr = score != null ? score.toFixed(0) : "—";
    return `<div class="phase-e-trim-item">
      <span class="phase-e-trim-rank">#${idx+1}</span>
      <span class="phase-e-trim-sym">${escHtml(sym)}</span>
      <div class="phase-e-trim-score-bar">
        <div class="phase-e-trim-score-fill ${cls}" style="width:${scorePct}%"></div>
      </div>
      <span class="phase-e-trim-score-num" style="color:${scorePct>=67?"#e53935":scorePct>=34?"#ff9800":"#4caf50"}">${scoreStr}</span>
    </div>`;
  }).join("");
  return `<div class="phase-e-trim-list">${rows}</div>
    <div style="margin-top:6px;font-size:0.72rem;color:var(--muted)">
      ${r.evidence_summary ? escHtml(r.evidence_summary) : ""}
    </div>`;
}

function _renderRetainHighlight(r) {
  const sym = (r.affected_symbols || [])[0] || "";
  return `<div class="phase-e-retain-highlight">
    ${sym ? `<strong>${escHtml(sym)}</strong>: ` : ""}${escHtml(r.evidence_summary || "")}
  </div>`;
}

function _renderThematicEcosystem(r) {
  const syms = r.affected_symbols || [];
  if (!syms.length) return "";
  const chips = syms.slice(0, 8).map(s => {
    const origin = _getSymbolExposureOrigin(s);
    const cls = origin === "DIRECT_INTENTIONAL" ? "origin-DIRECT"
              : origin === "ETF_THEMATIC" ? "origin-THEMATIC"
              : "origin-INHERITED";
    return `<span class="origin-chip ${cls}" title="${origin || "Unknown origin"}">${escHtml(s)}</span>`;
  }).join("");
  return `<div style="margin-top:8px">
    <span style="font-size:0.72rem;font-weight:600;color:var(--muted)">Holdings in cluster:</span>
    <div style="margin-top:4px">${chips}</div>
    <div style="margin-top:6px;font-size:0.72rem;color:var(--muted)">${escHtml(r.evidence_summary || "")}</div>
  </div>`;
}

function _renderConstructionEvidence(r) {
  return `<div style="margin-top:8px;padding:8px 10px;background:#f0f4f8;border-radius:6px;font-size:0.79rem;color:var(--muted)">
    ${escHtml(r.evidence_summary || "")}
  </div>`;
}

// Lookup STI trim score from the last analysis data
let _lastAnalysisData = null;
function _getSymbolTrimScore(sym) {
  if (!_lastAnalysisData) return null;
  const profiles = _lastAnalysisData.strategic_profiles || [];
  const p = profiles.find(x => (x.symbol || "").toUpperCase() === sym.toUpperCase());
  return p ? p.trim_priority_score : null;
}
function _getSymbolExposureOrigin(sym) {
  if (!_lastAnalysisData) return null;
  const profiles = _lastAnalysisData.strategic_profiles || [];
  const p = profiles.find(x => (x.symbol || "").toUpperCase() === sym.toUpperCase());
  return p ? p.exposure_origin : null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Replay alignment panel
// ─────────────────────────────────────────────────────────────────────────────
function renderReplayAlignment(data) {
  const el = document.getElementById("replayContent");
  const alignment = data.alignment || [];
  const overlays  = data.security_overlays || [];

  // Find replay-supported symbols
  const replayBacked = overlays.filter(o => o.replay_supported === true || o.replay_supported === "True");
  const bullish = overlays.filter(o => o.signal_direction === "BULLISH");
  const bearish  = overlays.filter(o => o.signal_direction === "BEARISH");

  // Find strongest drift items for the "watch" summary
  const highDrift = alignment
    .filter(r => r.severity === "HIGH")
    .slice(0, 5);

  const replaySymbols = replayBacked
    .sort((a, b) => parseFloat(b.percent_of_portfolio || 0) - parseFloat(a.percent_of_portfolio || 0))
    .slice(0, 12)
    .map(o => `<span class="rec-symbol" title="Replay-supported">${o.symbol}</span>`)
    .join(" ");

  const highDriftRows = highDrift.map(r => {
    const drift = parseFloat(r.drift_pct || 0);
    const dir = drift > 0 ? "▲ OW" : "▼ UW";
    const col = drift > 0 ? "var(--sev-high)" : "var(--green)";
    return `<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #ede8df;font-size:0.87rem;">
      <span>${escHtml(r.node_label || r.node_key)}</span>
      <span style="color:${col};font-weight:700">${dir} ${Math.abs(drift).toFixed(1)}pp</span>
    </div>`;
  }).join("");

  el.innerHTML = `
    <div style="margin-bottom:16px;">
      <div style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);margin-bottom:8px;">Replay-Supported Holdings</div>
      ${replaySymbols || '<span style="color:var(--muted);font-size:0.85rem">None identified in current replays</span>'}
      <div style="font-size:0.78rem;color:var(--muted);margin-top:6px;">
        ${replayBacked.length} of ${overlays.length} holdings appear in SIH replay top-N selections
      </div>
    </div>

    <div style="margin-bottom:16px;">
      <div style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);margin-bottom:6px;">Signal Summary</div>
      <div style="display:flex;gap:16px;font-size:0.9rem;">
        <div><span style="color:var(--green);font-weight:700">${bullish.length}</span> Bullish</div>
        <div><span style="color:var(--muted);">${overlays.length - bullish.length - bearish.length}</span> Neutral</div>
        <div><span style="color:var(--sev-high);font-weight:700">${bearish.length}</span> Bearish</div>
      </div>
    </div>

    ${highDrift.length ? `
    <div>
      <div style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);margin-bottom:6px;">High-Severity Drift</div>
      ${highDriftRows}
    </div>` : `<div style="color:var(--muted);font-size:0.87rem">✓ No high-severity drift detected.</div>`}
  `;
}

// ─────────────────────────────────────────────────────────────────────────────
// Security overlays table
// ─────────────────────────────────────────────────────────────────────────────
function renderSecurityOverlays(overlays) {
  const el = document.getElementById("securityContent");
  if (!overlays.length) { el.innerHTML = emptyState("No overlay data", ""); return; }

  // Sort: TRIM first, then WATCH, then by % desc
  const flagOrder = { TRIM: 0, WATCH: 1, ACCUMULATE: 2, HOLD: 3 };
  const sorted = [...overlays].sort((a, b) => {
    const fo = (flagOrder[a.opportunity_flag] || 3) - (flagOrder[b.opportunity_flag] || 3);
    if (fo !== 0) return fo;
    return parseFloat(b.percent_of_portfolio || 0) - parseFloat(a.percent_of_portfolio || 0);
  });

  const rows = sorted.map(o => {
    const replayChip = (o.replay_supported === true || o.replay_supported === "True")
      ? `<span class="replay-chip">REPLAY</span>` : "";
    const score = o.composite_score != null && o.composite_score !== ""
      ? parseFloat(o.composite_score).toFixed(2) : "—";
    const ac = (_lastAnalysisData?.analyst_consensus_by_symbol || {})[String(o.symbol || "").toUpperCase()];
    const fs = (_lastAnalysisData?.fidelity_signals_by_symbol  || {})[String(o.symbol || "").toUpperCase()];
    const badge = ac ? _computeConflictBadge(o.ess_score_text, ac.consensus_label) : null;
    const abrCell = ac
      ? `${_consensusLabelDisplay(ac.consensus_label)}&nbsp;<span style="color:var(--muted);font-size:0.72rem">${ac.abr != null ? parseFloat(ac.abr).toFixed(2) : "—"}</span>`
      : `<span style="color:var(--muted)">—</span>`;
    const matrixBadge = fs ? _matrixBadgeHtml((fs.consensus_matrix || {}).classification) : "";
    const fidRating = fs ? _fidelityRatingDisplay(fs.fidelity_rating) : `<span style="color:var(--muted)">—</span>`;

    // Phase 7.5N — agreement and freshness columns
    const ag = _computeSignalAgreement(o, ac, fs);
    const agrLabelCls = (ag.label === "FULL ALIGNMENT" || ag.label === "STRONG ALIGNMENT")
      ? "sa-agree-full" : (ag.label === "MIXED" ? "sa-agree-mixed" : "sa-agree-diverge");
    const agrCell = `<span class="sa-agree-chip ${agrLabelCls}">${ag.label}</span>
      <span style="font-size:0.72rem;color:var(--muted);white-space:nowrap"> ${ag.bullish}/${ag.total}</span>`;
    const confCls = { HIGH: "sa-conf-high", MEDIUM: "sa-conf-medium", LOW: "sa-conf-low" }[ag.confidence] || "";
    const confCell = `<span class="${confCls}">${ag.confidence}</span>`;

    const meta       = (_lastAnalysisData && _lastAnalysisData.signal_source_metadata) || {};
    const refDate    = (_lastAnalysisData && _lastAnalysisData.snapshot_date) || "";
    const allDates   = [
      (fs && fs.refresh_date) || "",
      meta.zacks_refresh_date || "",
      meta.danelfin_refresh_date || "",
      (ac && ac.refresh_date) || "",
    ].filter(Boolean);
    const allStatuses = allDates.map(d => _freshnessStatus(d, refDate));
    const worstFresh = _worstFreshness(allStatuses.length ? allStatuses : ["UNKNOWN"]);

    return `<tr>
      <td style="font-weight:600;font-family:monospace">${escHtml(o.symbol)}</td>
      <td style="text-align:right">${pct(o.percent_of_portfolio)}</td>
      <td><span class="dir-${o.signal_direction}">${o.signal_direction || "—"}</span></td>
      <td>${score}</td>
      <td>${escHtml(o.ess_score_text || "—")}</td>
      <td>${escHtml(o.zacks_rating || "—")}</td>
      <td>${abrCell}${badge ? " " + _conflictBadgeHtml(badge) : ""}</td>
      <td>${fidRating} ${matrixBadge}</td>
      <td>${agrCell}</td>
      <td>${confCell}</td>
      <td>${_freshnessChip(worstFresh)}</td>
      <td><span class="flag-${o.opportunity_flag}">${o.opportunity_flag || "—"}</span> ${replayChip}</td>
      <td style="font-size:0.8rem;color:var(--muted);max-width:200px">${escHtml(o.flag_rationale || "")}</td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <div style="overflow-x:auto;">
    <table class="overlay-table">
      <thead><tr>
        <th>Symbol</th>
        <th style="text-align:right">% Portfolio</th>
        <th>Direction</th>
        <th>Score</th>
        <th>ESS</th>
        <th>Zacks</th>
        <th>Analyst Consensus</th>
        <th>Fidelity / Matrix</th>
        <th>Agreement</th>
        <th>Confidence</th>
        <th>Freshness</th>
        <th>Flag</th>
        <th>Rationale</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
    </div>
    <div style="margin-top:10px;font-size:0.78rem;color:var(--muted);">
      <strong>Advisory only.</strong> TRIM/ACCUMULATE flags are intelligence signals — not trade instructions.
      Always apply your own judgment and consult a financial advisor.
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.3B — Optimizer Conflict Surfacing
// ─────────────────────────────────────────────────────────────────────────────

// ── Part C: Optimizer Summary Panel ─────────────────────────────────────────
function renderOptimizerSummary(recs) {
  const el = document.getElementById("optimizerSummaryContainer");
  if (!el) return;

  const withMeta = recs.filter(r => r.optimizer_metadata);
  if (!withMeta.length) { el.innerHTML = ""; return; }

  let mandateBlocked = 0;
  let etfGateFailed  = 0;
  let secSuperior    = 0;
  let noActionable   = 0;  // MANDATE_BLOCKED + NO_CANDIDATES
  let conflictCount  = 0;

  for (const r of withMeta) {
    const om       = r.optimizer_metadata;
    const decision = om.optimizer_decision || "";

    if (decision === "MANDATE_BLOCKED") { mandateBlocked++; conflictCount++; }
    else if (decision === "SECURITY_SUPERIOR") { secSuperior++; conflictCount++; }
    else if (decision === "NO_CANDIDATES")     noActionable++;

    // ETF gate failures: any ETF candidate with etf_gate not starting with PASS
    const etfFailed = (om.candidates || []).some(
      c => c.candidate_type === "ETF" && !String(c.etf_gate || "").startsWith("PASS")
    );
    if (etfFailed) { etfGateFailed++; conflictCount++; }
  }

  const noConflict = withMeta.length - conflictCount;

  el.innerHTML = `<div class="opt-summary-panel">
    <div class="opt-summary-header">
      <span class="opt-summary-title">Optimizer Status</span>
      <span class="opt-mode-badge">Parallel Mode</span>
      <span style="font-size:0.73rem;color:#4a7ca8;margin-left:4px;">
        Visibility only — legacy recommendations unchanged
      </span>
    </div>
    <div class="opt-summary-grid">
      ${_optStatCard(withMeta.length, "Recs Reviewed", "")}
      ${_optStatCard(mandateBlocked, "Mandate Blocked", mandateBlocked > 0 ? "warn" : "")}
      ${_optStatCard(etfGateFailed,  "ETF Gate Failed", etfGateFailed  > 0 ? "alert" : "")}
      ${_optStatCard(secSuperior,    "Security Superior", "")}
      ${_optStatCard(noActionable,   "No Candidates", "")}
      ${_optStatCard(noConflict,     "No Conflict", "")}
    </div>
  </div>`;
}

function _optStatCard(val, lbl, cls) {
  const clsStr = cls ? ` ${cls}` : "";
  return `<div class="opt-stat-card">
    <div class="opt-stat-val${clsStr}">${val}</div>
    <div class="opt-stat-lbl">${escHtml(lbl)}</div>
  </div>`;
}

// ── Part A: Optimizer conflict badges ────────────────────────────────────────
function _buildOptimizerBadges(r) {
  const om = r.optimizer_metadata;
  if (!om) return "";

  const decision    = om.optimizer_decision || "";
  const candidates  = om.candidates || [];
  const badges      = [];

  // Primary status badge
  if (decision === "MANDATE_BLOCKED") {
    badges.push(`<span class="opt-badge opt-badge-MANDATE_BLOCKED" title="Optimizer: deployment blocked by mandate">MANDATE_BLOCKED</span>`);
  } else if (decision === "SECURITY_SUPERIOR") {
    badges.push(`<span class="opt-badge opt-badge-SECURITY_SUPERIOR" title="Securities in target node outrank ETF vehicles">SECURITY_SUPERIOR</span>`);
  } else if (decision === "ETF_ADEQUATE") {
    badges.push(`<span class="opt-badge opt-badge-ACTIONABLE" title="ETF vehicle passes optimizer gates">ETF_ADEQUATE</span>`);
  } else if (decision === "NO_CANDIDATES") {
    badges.push(`<span class="opt-badge opt-badge-NO_CANDIDATES">NO_CANDIDATES</span>`);
  } else if (decision === "REDUCE_COHERENT") {
    badges.push(`<span class="opt-badge opt-badge-ACTIONABLE" title="Reduce action is coherent with optimizer">REDUCE_COHERENT</span>`);
  }

  // ETF gate failure flag — one badge per failed ETF vehicle
  const etfFailed = candidates.filter(
    c => c.candidate_type === "ETF" && !String(c.etf_gate || "").startsWith("PASS")
  );
  for (const c of etfFailed) {
    badges.push(
      `<span class="opt-badge opt-badge-ETF_GATE_FAILED" title="${escHtml(c.etf_gate)}">ETF_GATE_FAILED: ${escHtml(c.symbol)}</span>`
    );
  }

  // CONFLICTS_WITH_MANDATE — legacy vehicle on a mandate-blocked node
  if (om.mandate_blocked) {
    badges.push(`<span class="opt-badge opt-badge-CONFLICTS_WITH_MANDATE">CONFLICTS_WITH_MANDATE</span>`);
  }

  // WORSENS_OVERWEIGHT — any candidate worsens an existing overweight
  if (candidates.some(c => c.worsens_overweight)) {
    badges.push(`<span class="opt-badge opt-badge-WORSENS_OVERWEIGHT">WORSENS_OVERWEIGHT</span>`);
  }

  // PIS and best candidate chip
  const best = om.preferred_candidate;
  if (best) {
    badges.push(`<span class="opt-pis-chip" title="Portfolio Improvement Score for best candidate">PIS: ${best.pis}</span>`);
    badges.push(`<span class="opt-candidate-chip" title="Best optimizer candidate: ${escHtml(best.symbol)}">${escHtml(best.symbol)}</span>`);
  }

  if (!badges.length) return "";

  return `<div class="optimizer-badge-row">
    <span style="font-size:0.65rem;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:#1a5c8a;white-space:nowrap;">Optimizer:</span>
    ${badges.join("")}
  </div>`;
}

// ── Part B: Optimizer View collapsible block ─────────────────────────────────
function _buildOptimizerViewBlock(r) {
  const om = r.optimizer_metadata;
  if (!om) return "";

  const optId      = `opt-view-${r.recommendation_id}`;
  const decision   = om.optimizer_decision || "—";
  const candidates = om.candidates || [];

  // Legacy vehicles from the recommendation
  const legacyVehicles = (om.legacy_vehicles || []).join(", ") || "—";

  // Security alternatives: SECURITY candidates with positive PIS, sorted by PIS desc
  const secAlts = candidates
    .filter(c => c.candidate_type === "SECURITY" && c.pis > 0)
    .slice(0, 5);

  // ETF candidates
  const etfCandidates = candidates.filter(c => c.candidate_type === "ETF");

  // Reason text
  let reason = "";
  if (om.mandate_blocked) {
    reason = "This allocation gap is treated as intentional under the active mandate " +
             "(INFORMATIONAL / INTENTIONAL_UNDERWEIGHT). The optimizer flags no deployment " +
             "action as warranted under Concentrated Alpha.";
  } else if (etfCandidates.some(c => !String(c.etf_gate || "").startsWith("PASS"))) {
    const failSyms = etfCandidates
      .filter(c => !String(c.etf_gate || "").startsWith("PASS"))
      .map(c => `${c.symbol} (${String(c.etf_gate || "").split("[")[0].trim()})`)
      .join("; ");
    reason = `ETF gate failure: ${failSyms}. These vehicles have LOW suitability, NCS below threshold, or worsen an existing overweight.`;
  } else if (decision === "SECURITY_SUPERIOR") {
    reason = "One or more securities already in the target node score higher on PIS than the recommended ETF vehicles. Consider direct security deployment.";
  } else if (decision === "NO_CANDIDATES") {
    reason = "No candidates with positive PIS found for this target node.";
  } else {
    reason = "No optimizer conflict detected — this recommendation is consistent with optimizer analysis.";
  }

  // Decision chip class
  const decCls = decision === "MANDATE_BLOCKED" ? " optview-chip-warn"
               : decision === "SECURITY_SUPERIOR" ? " optview-chip-good"
               : etfCandidates.some(c => !String(c.etf_gate || "").startsWith("PASS")) ? " optview-chip-blocked"
               : "";

  // Security alternatives HTML
  const secAltHtml = secAlts.length
    ? secAlts.map(c =>
        `<span class="optview-chip optview-chip-good" title="PIS: ${c.pis} | ${escHtml(c.sti_tier)} | replay: ${c.replay_supported}">${escHtml(c.symbol)}</span>`
      ).join(" ")
    : `<span class="optview-muted">None identified in target node</span>`;

  // ETF assessment HTML
  const etfAssessHtml = etfCandidates.length
    ? etfCandidates.map(c => {
        const passed = String(c.etf_gate || "").startsWith("PASS");
        const chipCls = passed ? "" : " optview-chip-blocked";
        const owWarn  = c.worsens_overweight ? " &nbsp;⚠ worsens overweight" : "";
        return `<div class="optview-etf-row">
          <span class="optview-chip${chipCls}">${escHtml(c.symbol)}</span>
          <span style="font-family:monospace;font-size:0.74rem;color:#555">${escHtml(String(c.etf_gate || ""))}</span>
          &nbsp;·&nbsp; Suitability: <strong>${escHtml(c.suitability_tier)}</strong>
          &nbsp;·&nbsp; NCS: <strong>${c.ncs != null ? Number(c.ncs).toFixed(1) : "—"}%</strong>
          ${owWarn}
        </div>`;
      }).join("")
    : `<span class="optview-muted">No ETF candidates evaluated</span>`;

  return `<button class="optimizer-view-toggle" onclick="toggleOptimizerView('${optId}')">&#9656; Optimizer View</button>
  <div class="optimizer-view-body" id="${optId}">
    <div class="optview-row">
      <div class="optview-label">Legacy Recommendation</div>
      <div class="optview-val">${escHtml(legacyVehicles)}</div>
    </div>
    <div class="optview-row">
      <div class="optview-label">Optimizer Assessment</div>
      <div><span class="optview-chip${decCls}">${escHtml(decision)}</span></div>
    </div>
    <div class="optview-row">
      <div class="optview-label">Reason</div>
      <div class="optview-muted" style="font-size:0.8rem">${escHtml(reason)}</div>
    </div>
    ${secAlts.length ? `<div class="optview-row">
      <div class="optview-label">Security Alternatives</div>
      <div>${secAltHtml}</div>
    </div>` : ""}
    <div class="optview-row">
      <div class="optview-label">ETF Assessment</div>
      <div>${etfAssessHtml}</div>
    </div>
    ${_buildOptimizerPreferredPanel(r)}
    <div style="margin-top:8px;font-size:0.69rem;color:#aaa;border-top:1px solid #dde8f0;padding-top:6px;">
      Optimizer v${om.optimizer_version || "7.3C"} &nbsp;·&nbsp; Parallel Mode &nbsp;·&nbsp;
      Visibility only — no action authority. Legacy recommendations take precedence.
    </div>
  </div>`;
}

// ── Part D (7.3C): Optimizer Preferred Comparison Panel ─────────────────────
function _buildOptimizerPreferredPanel(r) {
  const om = r.optimizer_metadata;
  if (!om) return "";

  const pd = om.preferred_display;
  if (!pd) return "";

  const pref = pd.preferred_summary || {};
  const leg  = pd.legacy_summary;
  const advantages = pd.key_advantages || [];

  // Advantage chips
  const advHtml = advantages
    .map(a => `<span class="optpref-advantage">${escHtml(a)}</span>`)
    .join(" ");

  // Legacy column
  let legColHtml;
  if (leg) {
    const gateCls = !String(leg.etf_gate || "").startsWith("PASS") ? " optpref-fail" : "";
    const gateLabel = String(leg.etf_gate || "—").split("[")[0].trim();
    legColHtml = `<div class="optpref-col optpref-col-legacy">
      <div class="optpref-col-header">Legacy Recommendation</div>
      <div class="optpref-symbol">${escHtml(leg.symbol)}</div>
      <div class="optpref-type">ETF</div>
      <div class="optpref-metrics">
        <div class="optpref-metric">PIS: <strong>${leg.pis != null ? leg.pis : "—"}</strong></div>
        <div class="optpref-metric">ETF Gate: <strong class="${gateCls}">${escHtml(gateLabel)}</strong></div>
        <div class="optpref-metric">Suitability: <strong>${escHtml(leg.suitability_tier || "—")}</strong></div>
        <div class="optpref-metric">NCS: <strong>${leg.ncs != null ? Number(leg.ncs).toFixed(1) + "%" : "—"}</strong></div>
        ${leg.worsens_overweight ? `<div class="optpref-metric optpref-fail">⚠ Worsens overweight</div>` : ""}
      </div>
    </div>`;
  } else {
    legColHtml = `<div class="optpref-col optpref-col-legacy">
      <div class="optpref-col-header">Legacy Recommendation</div>
      <div class="optpref-symbol">${escHtml(pd.legacy_symbol || "—")}</div>
      <div class="optpref-type">—</div>
    </div>`;
  }

  // Preferred column
  const prefPisCls = (pref.pis != null && leg && pref.pis > leg.pis) ? " optpref-win" : "";
  const prefColHtml = `<div class="optpref-col optpref-col-preferred">
    <div class="optpref-col-header">Optimizer Preferred</div>
    <div class="optpref-symbol">${escHtml(pref.symbol || "—")}</div>
    <div class="optpref-type">SECURITY</div>
    <div class="optpref-metrics">
      <div class="optpref-metric">PIS: <strong class="${prefPisCls}">${pref.pis != null ? pref.pis : "—"}</strong></div>
      ${pref.composite_score != null ? `<div class="optpref-metric">Composite: <strong>${Number(pref.composite_score).toFixed(2)}</strong></div>` : ""}
      <div class="optpref-metric">STI: <strong>${escHtml(pref.sti_tier || "—")}</strong></div>
      <div class="optpref-metric">Replay: <strong class="${pref.replay_supported ? "optpref-win" : ""}">${pref.replay_supported ? "Yes" : "No"}</strong></div>
      ${pref.ess_score ? `<div class="optpref-metric">ESS: <strong>${escHtml(pref.ess_score)}</strong></div>` : ""}
    </div>
  </div>`;

  const deltaHtml = pd.pis_delta != null && pd.pis_delta > 0
    ? `<span class="optpref-delta">+${pd.pis_delta} PIS advantage</span>`
    : "";

  return `<div class="optpref-panel">
    <div class="optpref-header">
      <span class="optpref-title">Optimizer Preferred Alternative</span>
      ${deltaHtml}
    </div>
    <div class="optpref-comparison">
      ${legColHtml}
      <div class="optpref-vs">vs</div>
      ${prefColHtml}
    </div>
    ${advantages.length ? `<div class="optpref-advantages">
      <span class="optpref-advantages-label">Key advantages:</span>
      ${advHtml}
    </div>` : ""}
    <div class="optpref-footnote">
      Visibility only — optimizer preferred is not a trade instruction.
      Legacy recommendation takes precedence until Phase 7.3D.
    </div>
  </div>`;
}

function toggleOptimizerView(optId) {
  const body = document.getElementById(optId);
  const btn  = body ? body.previousElementSibling : null;
  if (!body) return;
  const open = body.classList.toggle("open");
  if (btn) btn.innerHTML = open ? "&#9662; Optimizer View" : "&#9656; Optimizer View";
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5C — Capital Deployment Queue
// ─────────────────────────────────────────────────────────────────────────────

// State for view-all toggle and breakdown expansion
let _dqShowAll = false;
const DQ_DEFAULT_ROWS = 10;

function renderDeploymentQueue(data) {
  const el = document.getElementById("deploymentQueueContainer");
  if (!el) return;

  const dq = data.deployment_queue;
  if (!dq || !Array.isArray(dq.queue) || dq.queue.length === 0) {
    el.innerHTML = "";
    return;
  }

  _dqShowAll = false;  // reset on each render

  const queue   = dq.queue;
  const cashCtx = dq.cash_context || {};
  const top     = queue[0] || {};

  // Phase 7.5F — Build deployment plan lookup (available when plan is pre-loaded)
  const plan = data.deployment_plan || {};
  const planRecs = plan.recommendations || [];
  const _dpBySymbol = {};
  for (const r of planRecs) _dpBySymbol[r.symbol] = r;
  const hasPlan = planRecs.length > 0;

  // Phase 22D.6 — Cash context breakdown (Current / Target / Excess / Deployable)
  const _cashCurrentPct  = cashCtx.cash_pct               != null ? parseFloat(cashCtx.cash_pct).toFixed(2)               : "—";
  const _cashTargetPct   = cashCtx.mandate_cash_target_pct != null ? parseFloat(cashCtx.mandate_cash_target_pct).toFixed(1) : "—";
  const _cashExcessPct   = cashCtx.excess_pct              != null ? parseFloat(cashCtx.excess_pct).toFixed(2)              : "—";
  const _cashExcessMv    = cashCtx.excess_mv               != null ? formatMV(cashCtx.excess_mv)                           : "—";
  const _excessIsNeg     = cashCtx.excess_pct != null && parseFloat(cashCtx.excess_pct) < 0;
  const _excessLabel     = _excessIsNeg ? `${_cashExcessPct}% (${_cashExcessMv})` : `+${_cashExcessPct}% (${_cashExcessMv})`;
  const _excessClass     = _excessIsNeg ? "dq-cash-ctx-deficit" : "dq-cash-ctx-excess";

  // Phase 22D.10 — Settlement adjustment disclosure
  const _hasSettlement   = cashCtx.settlement_adjustment != null && parseFloat(cashCtx.settlement_adjustment) > 0;
  const _settlementAdj   = _hasSettlement ? parseFloat(cashCtx.settlement_adjustment) : 0;
  const _adjDeployableMv = _hasSettlement && cashCtx.adjusted_deployable_mv != null
    ? parseFloat(cashCtx.adjusted_deployable_mv)
    : (cashCtx.deployable_mv != null ? parseFloat(cashCtx.deployable_mv) : 0);
  const _reportedDeployableMv = cashCtx.deployable_mv != null ? parseFloat(cashCtx.deployable_mv) : 0;

  const settlementDisclosureHtml = _hasSettlement ? `
    <div class="dq-settlement-strip">
      <div class="dq-settlement-icon">⚠</div>
      <div class="dq-settlement-body">
        <div class="dq-settlement-title">Settlement Adjustment Applied</div>
        <div class="dq-settlement-detail">
          Pending purchase settlement of ${formatMV(_settlementAdj)} is excluded from the deployment budget.
          This cash is already economically committed and will be debited at T+1 settlement.
        </div>
        <div class="dq-settlement-row">
          <span class="dq-settlement-item">Reported Deployable: <strong>${formatMV(_reportedDeployableMv)}</strong></span>
          <span class="dq-settlement-sep">−</span>
          <span class="dq-settlement-item dq-settlement-neg">Settlement Obligation: <strong>${formatMV(_settlementAdj)}</strong></span>
          <span class="dq-settlement-sep">=</span>
          <span class="dq-settlement-item dq-settlement-adj">Adjusted Deployable: <strong>${formatMV(_adjDeployableMv)}</strong></span>
        </div>
      </div>
    </div>` : "";

  const cashContextHtml = `<div class="dq-cash-context-strip">
    <div class="dq-cash-ctx-card">
      <div class="dq-cash-ctx-val">${_cashCurrentPct}%</div>
      <div class="dq-cash-ctx-lbl">Current Cash</div>
    </div>
    <div class="dq-cash-ctx-card dq-cash-ctx-target">
      <div class="dq-cash-ctx-val">${_cashTargetPct}%</div>
      <div class="dq-cash-ctx-lbl">Mandate Target</div>
    </div>
    <div class="dq-cash-ctx-card ${_excessClass}">
      <div class="dq-cash-ctx-val">${_excessLabel}</div>
      <div class="dq-cash-ctx-lbl">Excess vs Target</div>
    </div>
    ${_hasSettlement ? `
    <div class="dq-cash-ctx-card dq-cash-ctx-reported">
      <div class="dq-cash-ctx-val">${formatMV(_reportedDeployableMv)}</div>
      <div class="dq-cash-ctx-lbl">Reported Deployable</div>
    </div>
    <div class="dq-cash-ctx-card dq-cash-ctx-settlement-neg">
      <div class="dq-cash-ctx-val">−${formatMV(_settlementAdj)}</div>
      <div class="dq-cash-ctx-lbl">Settlement Adj.</div>
    </div>
    <div class="dq-cash-ctx-card dq-cash-ctx-deployable">
      <div class="dq-cash-ctx-val dq-gold">${formatMV(_adjDeployableMv)}</div>
      <div class="dq-cash-ctx-lbl">Adj. Deployable</div>
    </div>` : `
    <div class="dq-cash-ctx-card dq-cash-ctx-deployable">
      <div class="dq-cash-ctx-val dq-gold">${formatMV(cashCtx.deployable_mv)}</div>
      <div class="dq-cash-ctx-lbl">Deployable</div>
    </div>`}
  </div>
  ${settlementDisclosureHtml}`;

  // Summary strip
  const summaryHtml = `<div class="dq-summary-strip">
    <div class="dq-summary-card dq-cash">
      <div class="dq-summary-val dq-gold">${formatMV(_adjDeployableMv)}</div>
      <div class="dq-summary-lbl">${_hasSettlement ? "Adj. Deployable Cash" : "Deployable Cash"}</div>
    </div>
    <div class="dq-summary-card">
      <div class="dq-summary-val">${dq.candidate_count || queue.length}</div>
      <div class="dq-summary-lbl">Eligible Candidates</div>
    </div>
    <div class="dq-summary-card">
      <div class="dq-summary-val" style="font-size:1rem;padding-top:4px">${escHtml(dq.queue_version || "CW-DAS-1.0")}</div>
      <div class="dq-summary-lbl">Queue Version</div>
    </div>
    <div class="dq-summary-card dq-accent">
      <div class="dq-summary-val dq-green" style="font-size:1.25rem;font-family:monospace">${escHtml(top.symbol || "—")}</div>
      <div class="dq-summary-lbl">Top Candidate</div>
    </div>
    <div class="dq-summary-card dq-accent">
      <div class="dq-summary-val dq-green">${top.deployment_score != null ? parseFloat(top.deployment_score).toFixed(1) : "—"}</div>
      <div class="dq-summary-lbl">Top Score</div>
    </div>
  </div>`;

  // Phase 7.5F — Cash deployment summary (only when plan is loaded)
  const cashSummaryHtml = hasPlan ? _daCashSummaryHtml(plan) : "";

  // Phase 7.5F — Action cards for top 10 (only when plan is loaded)
  const actionCardsHtml = hasPlan
    ? _daRenderActionCards(queue, _dpBySymbol, 10)
    : `<div class="da-no-plan-hint">
        No deployment plan loaded — click ▶ Generate Deployment Plan to see recommended purchase amounts.
      </div>`;

  // Build the initial 10 rows
  const tableId = "dq-queue-table-body";
  const tableHtml = `<div class="dq-table-wrap">
    <table class="dq-table">
      <thead><tr>
        <th>Rank</th>
        <th>Symbol</th>
        <th>CW-DAS</th>
        <th>Tier</th>
        <th>Wt% / Proj</th>
        <th>Composite</th>
        <th>Replay</th>
        <th>Add $</th>
        <th>Status</th>
      </tr></thead>
      <tbody id="${tableId}"></tbody>
    </table>
  </div>
  <button class="dq-view-all-btn" id="dq-view-all-btn" onclick="_dqToggleViewAll()">
    ▼ View all ${queue.length} candidates
  </button>`;

  // Blocked conviction panel
  const blocked = queue.filter(c => {
    const bd = c.score_breakdown || {};
    return bd.redundancy_pen > 0 || bd.conc_pen > 0;
  });
  const blockedHtml = blocked.length > 0 ? `<div class="dq-blocked-panel">
    <button class="dq-blocked-toggle" onclick="_dqToggleBlocked()">
      ▸ Blocked Conviction Opportunities (${blocked.length})
    </button>
    <div class="dq-blocked-body" id="dq-blocked-body">
      <div class="dq-blocked-intro">
        Strong conviction holdings intentionally suppressed by mandate constraints.
        These are not deployment candidates under current allocations but remain in the
        analytical universe. No action is implied — shown for situational awareness only.
      </div>
      <table class="dq-blocked-table">
        <thead><tr>
          <th>Symbol</th><th>Tier</th><th>Score</th>
          <th>Penalty</th><th>Reason</th>
        </tr></thead>
        <tbody>
          ${blocked.map(c => {
            const bd = c.score_breakdown || {};
            const penParts = [];
            if (bd.redundancy_pen > 0) penParts.push(`OW node −${bd.redundancy_pen.toFixed(0)}`);
            if (bd.conc_pen > 0) penParts.push(`conc −${bd.conc_pen.toFixed(0)}`);
            const reason = c.notes || "—";
            const tierShort = c.narrative_tier === "CORE_CONVICTION_LEADER" ? "CCL" : "HCA";
            return `<tr>
              <td style="font-family:monospace;font-weight:700">${escHtml(c.symbol)}</td>
              <td><span class="dq-tier dq-tier-${tierShort}">${tierShort}</span></td>
              <td style="font-weight:600;color:var(--muted)">${parseFloat(c.deployment_score).toFixed(1)}</td>
              <td style="color:var(--sev-high);font-weight:600">${penParts.join(", ")}</td>
              <td style="font-size:0.8rem;color:var(--muted)">${escHtml(reason)}</td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>
    </div>
  </div>` : "";

  el.innerHTML = `<div class="dq-panel">
    <div class="dq-section-header">
      <span class="dq-section-title">Capital Deployment Queue</span>
      <span class="dq-version-badge">${escHtml(dq.queue_version || "CW-DAS-1.0")}</span>
      <span class="dq-advisory-note">Guidance only — not a trade instruction</span>
    </div>
    ${summaryHtml}
    ${cashContextHtml}
    ${cashSummaryHtml}
    <div class="da-action-section">
      <div class="da-action-section-header">Recommended Actions — Top 10</div>
      ${actionCardsHtml}
    </div>
    ${tableHtml}
    ${blockedHtml}
    <div class="dp-generate-row">
      <button class="dp-generate-btn" id="dp-generate-btn" onclick="_dpGeneratePlan()">
        ↺ Recalculate with Custom Cash Amount
      </button>
      <span class="dp-generate-hint">Override: allocate custom amount instead of ${formatMV(_adjDeployableMv)}</span>
    </div>
  </div>`;

  // Render initial rows
  _dqRenderTableRows(queue, tableId, DQ_DEFAULT_ROWS);
}

// Phase 7.5F — Cash deployment summary strip
function _daCashSummaryHtml(plan) {
  const pi    = plan.portfolio_impact || {};
  const recs  = plan.recommendations  || [];
  const posWithAlloc = recs.filter(r => (r.suggested_add || 0) > 0).length;
  const t1    = (plan.tier_summaries || []).find(t => t.tier === "TIER_1") || {};
  const t2    = (plan.tier_summaries || []).find(t => t.tier === "TIER_2") || {};
  const t3    = (plan.tier_summaries || []).find(t => t.tier === "TIER_3") || {};

  return `<div class="da-cash-summary">
    <div class="da-cash-label">Deployment Plan — Cash Allocation</div>
    <div class="da-cash-row">
      <div class="da-cash-card da-cash-avail">
        <div class="da-cash-val">${formatMV(plan.deployable_cash)}</div>
        <div class="da-cash-lbl">Available to Deploy</div>
      </div>
      <div class="da-cash-card da-cash-deployed">
        <div class="da-cash-val">${formatMV(pi.total_deployed)}</div>
        <div class="da-cash-lbl">Allocated</div>
      </div>
      <div class="da-cash-card da-cash-remaining">
        <div class="da-cash-val">${formatMV(pi.unallocated_cash)}</div>
        <div class="da-cash-lbl">Remaining</div>
      </div>
      <div class="da-cash-card">
        <div class="da-cash-val">${posWithAlloc}</div>
        <div class="da-cash-lbl">Positions Allocated</div>
      </div>
      <div class="da-cash-card">
        <div class="da-cash-val">${pi.cash_before_pct != null ? parseFloat(pi.cash_before_pct).toFixed(1) : "—"}% → ${pi.cash_after_pct != null ? parseFloat(pi.cash_after_pct).toFixed(1) : "—"}%</div>
        <div class="da-cash-lbl">Cash Wt Before → After</div>
      </div>
    </div>
    <div class="da-tier-row">
      ${t1.candidate_count ? `<span class="da-tier-badge da-tier-t1">T1 ${t1.candidate_count} pos ${formatMV(t1.total_allocated)} (${t1.pct_of_plan.toFixed(0)}%)</span>` : ""}
      ${t2.candidate_count ? `<span class="da-tier-badge da-tier-t2">T2 ${t2.candidate_count} pos ${formatMV(t2.total_allocated)} (${t2.pct_of_plan.toFixed(0)}%)</span>` : ""}
      ${t3.candidate_count ? `<span class="da-tier-badge da-tier-t3">T3 ${t3.candidate_count} pos ${formatMV(t3.total_allocated)} (${t3.pct_of_plan.toFixed(0)}%)</span>` : ""}
    </div>
  </div>`;
}

// Phase 7.5F — Action cards for top N deployment candidates
function _daRenderActionCards(queue, dpBySymbol, limit) {
  const _ucfBySymbol = (_analysisResult && _analysisResult.ucf_verdicts_by_symbol) || {};
  // Use plan recs sorted by rank for card order; fill up to limit
  const planRecs = Object.values(dpBySymbol).sort((a, b) => a.rank - b.rank).slice(0, limit);

  if (planRecs.length === 0) return `<div class="da-no-plan-hint">No recommended actions available.</div>`;

  const cards = planRecs.map(rec => {
    const sym  = rec.symbol;
    const cand = queue.find(c => c.symbol === sym) || {};
    const ucf  = _ucfBySymbol[sym] || {};

    const tierShort = _dqTierShort(cand.narrative_tier || "");
    const tierDp    = rec.deployment_tier || "TIER_3";
    const dpTierLabel = tierDp === "TIER_1" ? "DP·T1" : tierDp === "TIER_2" ? "DP·T2" : "DP·T3";

    const addAmt = rec.suggested_add || 0;
    const curWt  = rec.current_weight_pct  != null ? parseFloat(rec.current_weight_pct).toFixed(2)  : "—";
    const projWt = rec.projected_weight_pct != null ? parseFloat(rec.projected_weight_pct).toFixed(2) : "—";
    const curMV  = rec.current_market_value  != null ? formatMV(rec.current_market_value)  : "—";
    const projMV = rec.projected_market_value != null ? formatMV(rec.projected_market_value) : "—";

    // Reason chips
    const reasons = [];
    if ((cand.narrative_tier || "").includes("CORE")) reasons.push({t:"CORE CONVICTION", cls:"da-reason-ccl"});
    else if ((cand.narrative_tier || "").includes("HIGH")) reasons.push({t:"HIGH CONVICTION", cls:"da-reason-hca"});
    if (cand.replay_supported) reasons.push({t:"Replay Backed", cls:"da-reason-pos"});
    if ((parseFloat(cand.trim_score) || 99) <= 20) reasons.push({t:"Low Trim Pressure", cls:"da-reason-pos"});
    if (ucf.ucf_label === "CORE_CONVICTION_LEADER") reasons.push({t:"UCF: CCL", cls:"da-reason-ucf"});
    const bd = cand.score_breakdown || {};
    if (!bd.conc_pen && !bd.redundancy_pen) reasons.push({t:"No Conflicts", cls:"da-reason-pos"});

    const reasonsHtml = reasons.slice(0, 4).map(r =>
      `<span class="da-reason-chip ${r.cls}">${escHtml(r.t)}</span>`
    ).join("");

    const rankBadge = rec.rank <= 2 ? " da-card-top" : "";

    return `<div class="da-action-card${rankBadge}">
      <div class="da-card-header">
        <span class="da-card-action">BUY</span>
        <span class="da-card-sym">${escHtml(sym)}</span>
        <span class="da-card-badges">
          <span class="dq-tier dq-tier-${tierShort}">${tierShort}</span>
          <span class="da-dp-tier">${dpTierLabel}</span>
        </span>
      </div>
      <div class="da-card-amount">+${formatMV(addAmt)}</div>
      <div class="da-card-weights">
        <span class="da-wt-cur">${curWt}%</span>
        <span class="da-wt-arrow">→</span>
        <span class="da-wt-proj">${projWt}%</span>
      </div>
      <div class="da-card-mv">${curMV} → ${projMV}</div>
      <div class="da-card-reasons">${reasonsHtml}</div>
    </div>`;
  }).join("");

  return `<div class="da-action-grid">${cards}</div>`;
}

function _dqStatus(cand) {
  const bd = cand.score_breakdown || {};
  const blocked = parseFloat(cand.current_weight_pct) >= 6.0 || bd.conc_pen > 0;
  const owNode  = bd.redundancy_pen > 0;
  if (blocked && owNode) return "BLOCKED";
  if (owNode)  return "OW_NODE";
  if (blocked) return "BLOCKED";
  return "DEPLOYABLE";
}

function _dqStatusLabel(status) {
  if (status === "OW_NODE")    return "OW NODE";
  if (status === "BLOCKED")    return "BLOCKED";
  return "DEPLOYABLE";
}

function _dqTierShort(tier) {
  if (tier === "CORE_CONVICTION_LEADER") return "CCL";
  if (tier === "HIGH_CONVICTION_ANCHOR") return "HCA";
  return tier || "—";
}

function _dqScoreClass(score) {
  if (score >= 85) return "dq-score-high";
  if (score >= 70) return "dq-score-mid";
  return "dq-score-low";
}

function _dqRenderTableRows(queue, tbodyId, limit) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;

  // Phase 7.5E — Build signal lookup maps for the transparency panel
  const _ucfBySymbol = (_analysisResult && _analysisResult.ucf_verdicts_by_symbol) || {};
  const _ovBySymbol  = {};
  // Use _lastAnalysisData for overlays — it has the full set of enriched fields (danelfin_score, etc.)
  const _ovSource = (_lastAnalysisData && _lastAnalysisData.security_overlays) ||
                    (_analysisResult  && _analysisResult.security_overlays) || [];
  for (const ov of _ovSource) {
    _ovBySymbol[ov.symbol] = ov;
  }
  // Phase 7.5F — deployment plan lookup for action columns
  const _dpBySymbol = {};
  for (const r of (((_analysisResult && _analysisResult.deployment_plan) || {}).recommendations || [])) {
    _dpBySymbol[r.symbol] = r;
  }
  // Phase 7.5N — consensus and fidelity lookups for agreement panel
  const _consBySymbol = (_lastAnalysisData && _lastAnalysisData.analyst_consensus_by_symbol) || {};
  const _fidBySymbol2 = (_lastAnalysisData && _lastAnalysisData.fidelity_signals_by_symbol) || {};

  const rows = queue.slice(0, limit).map((c, i) => {
    const bdId    = `dq-bd-${i}`;
    const status  = _dqStatus(c);
    const tierShort = _dqTierShort(c.narrative_tier);
    const score   = parseFloat(c.deployment_score);
    const rankCls = c.rank === 1 ? " dq-row-rank1" : "";
    const rankNumCls = c.rank === 1 ? " rank1" : "";
    const bd      = c.score_breakdown || {};

    // Phase 7.5F — action column: Add $ and Wt% → Proj
    const sym = c.symbol;
    const dp  = _dpBySymbol[sym] || null;
    const addAmt    = dp ? parseFloat(dp.suggested_add || 0) : null;
    const curWtDisp = c.current_weight_pct != null ? parseFloat(c.current_weight_pct).toFixed(1) + "%" : "—";
    const projWtDisp = dp && dp.projected_weight_pct != null
      ? parseFloat(dp.projected_weight_pct).toFixed(1) + "%"
      : null;
    const addAmtDisp = addAmt != null && addAmt > 0
      ? `<span class="da-add-amt">+${formatMV(addAmt)}</span>`
      : (status === "DEPLOYABLE" ? `<span class="da-add-na">—</span>` : `<span class="da-add-blocked">✕</span>`);
    const wtDisp = projWtDisp
      ? `${curWtDisp}<span class="da-wt-arr"> → </span>${projWtDisp}`
      : curWtDisp;

    // Phase 7.5E — Signal profile data
    const ucf = _ucfBySymbol[sym] || {};
    const ov  = _ovBySymbol[sym]  || {};
    const ucfScore   = ucf.ucf_score  != null ? parseFloat(ucf.ucf_score).toFixed(1) : "—";
    const ucfRank    = ucf.ucf_rank   != null ? "#" + ucf.ucf_rank : "—";
    const ucfLabel   = ucf.ucf_label  || "—";
    const ucfLabelShort = ucfLabel.replace(/_/g, " ");
    const ucfSummary = ucf.signal_summary || "";
    const essText    = ov.ess_score_text  || c.ess_score_text  || "—";
    const zacks      = ov.zacks_rating    || c.zacks_rating    || "—";
    const danelfin   = ov.danelfin_score  || "—";
    const replayPct  = ov.replay_percentile != null ? parseFloat(ov.replay_percentile).toFixed(0) + "th" : "—";
    const compScore  = c.composite_score  != null ? parseFloat(c.composite_score).toFixed(2) : "—";
    const projWt     = dp && dp.projected_weight_pct != null
                       ? parseFloat(dp.projected_weight_pct).toFixed(2) + "%"
                       : (c.current_weight_pct != null ? pct(c.current_weight_pct) + " (cur)" : "—");
    const trim = parseFloat(c.trim_score || 0);

    // Phase 7.5N — native value labels for signal cards
    const ac2 = _consBySymbol[sym] || _consBySymbol[(sym || "").toUpperCase()] || null;
    const fs2 = _fidBySymbol2[sym] || _fidBySymbol2[(sym || "").toUpperCase()] || null;
    const zRank2 = _zacksNativeRank(zacks);
    const danRaw2 = _danelfinNativeRaw(danelfin);
    const essNative   = essText !== "—" ? essText.replace(/_/g, " ") : "—";
    const zacksNative = zRank2 != null
      ? `#${zRank2} ${_zacksRankLabel(zRank2)}`
      : (zacks !== "—" ? zacks : "—");
    const danNative  = danRaw2 != null ? `${danRaw2} / 10` : (danelfin !== "—" ? danelfin : "—");
    const abrNative2 = ac2 && ac2.abr != null
      ? `ABR ${parseFloat(ac2.abr).toFixed(2)}${ac2.consensus_label ? " · " + ac2.consensus_label.replace(/_/g, " ") : ""}`
      : null;

    return `<tr class="dq-data-row${rankCls}" onclick="_dqToggleBreakdown('${bdId}')">
      <td><span class="dq-rank-num${rankNumCls}">#${c.rank}</span></td>
      <td><span class="dq-sym">${escHtml(c.symbol)}</span></td>
      <td><span class="dq-score-val ${_dqScoreClass(score)}">${score.toFixed(1)}</span></td>
      <td><span class="dq-tier dq-tier-${tierShort}">${tierShort}</span></td>
      <td style="text-align:right;white-space:nowrap">${wtDisp}</td>
      <td style="text-align:right;font-weight:600">${c.composite_score != null ? parseFloat(c.composite_score).toFixed(2) : "—"}</td>
      <td><span class="${c.replay_supported ? "dq-replay-yes" : "dq-replay-no"}">${c.replay_supported ? "YES" : "NO"}</span></td>
      <td style="text-align:right">${addAmtDisp}</td>
      <td><span class="dq-status dq-status-${status}">${_dqStatusLabel(status)}</span></td>
    </tr>
    <tr class="dq-breakdown-row" id="${bdId}">
      <td colspan="9">
        <div class="dq-signal-profile-header">Signal Profile — ${escHtml(sym)}</div>
        <div class="dq-signal-grid">
          <div class="dq-sig-card dq-sig-ucf">
            <div class="dq-sig-val">${escHtml(ucfScore)}</div>
            <div class="dq-sig-lbl">UCF Score</div>
          </div>
          <div class="dq-sig-card dq-sig-ucf">
            <div class="dq-sig-val dq-sig-rank">${escHtml(ucfRank)}</div>
            <div class="dq-sig-lbl">UCF Rank</div>
          </div>
          <div class="dq-sig-card">
            <div class="dq-sig-val dq-sig-label">${escHtml(ucfLabelShort)}</div>
            <div class="dq-sig-lbl">UCF Label</div>
          </div>
          <div class="dq-sig-card">
            <div class="dq-sig-val">${escHtml(compScore)}</div>
            <div class="dq-sig-lbl">Composite</div>
          </div>
          <div class="dq-sig-card">
            <div class="dq-sig-val">${escHtml(essText)}</div>
            <div class="dq-sig-sublabel">Primary Signal (55%)</div>
            <div class="dq-sig-lbl">ESS</div>
          </div>
          <div class="dq-sig-card">
            <div class="dq-sig-val">${escHtml(danNative)}</div>
            <div class="dq-sig-sublabel">${danRaw2 != null ? "AI Score" : "Normalized 1–5"}</div>
            <div class="dq-sig-lbl">Danelfin</div>
          </div>
          <div class="dq-sig-card">
            <div class="dq-sig-val">${escHtml(zacksNative)}</div>
            <div class="dq-sig-sublabel">Normalized ${zacks !== "—" ? parseFloat(zacks).toFixed(1) + " / 5" : "—"}</div>
            <div class="dq-sig-lbl">Zacks</div>
          </div>
          ${abrNative2 != null ? `<div class="dq-sig-card">
            <div class="dq-sig-val" style="font-size:0.80rem">${escHtml(abrNative2)}</div>
            <div class="dq-sig-sublabel">Not in v1 composite</div>
            <div class="dq-sig-lbl">Yahoo ABR</div>
          </div>` : ""}
          <div class="dq-sig-card">
            <div class="dq-sig-val">${escHtml(replayPct)}</div>
            <div class="dq-sig-lbl">Replay Pctile</div>
          </div>
          <div class="dq-sig-card">
            <div class="dq-sig-val">${escHtml(projWt)}</div>
            <div class="dq-sig-lbl">Proj. Weight</div>
          </div>
        </div>
        ${ucfSummary ? `<div class="dq-signal-summary">${escHtml(ucfSummary)}</div>` : ""}
        ${_signalAgreementPanelHtml(ov, ac2, fs2)}
        <div class="dq-breakdown-header">CW-DAS Score Breakdown — ${escHtml(c.symbol)}</div>
        <div class="dq-breakdown-grid">
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.signal != null ? bd.signal.toFixed(1) : "—"}</div>
            <div class="dq-bd-lbl">Signal<br>/30</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.replay != null ? bd.replay.toFixed(0) : "—"}</div>
            <div class="dq-bd-lbl">Replay<br>/20</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.conviction != null ? bd.conviction.toFixed(0) : "—"}</div>
            <div class="dq-bd-lbl">Conviction<br>/35</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.sizing != null ? bd.sizing.toFixed(1) : "—"}</div>
            <div class="dq-bd-lbl">Sizing<br>/8</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.momentum != null ? bd.momentum.toFixed(1) : "—"}</div>
            <div class="dq-bd-lbl">Momentum<br>/10</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val${bd.redundancy_pen > 0 ? " dq-penalty" : ""}">${bd.redundancy_pen != null ? "−" + bd.redundancy_pen.toFixed(0) : "—"}</div>
            <div class="dq-bd-lbl">Redund.<br>Pen</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val${bd.conc_pen > 0 ? " dq-penalty" : ""}">${bd.conc_pen != null ? "−" + bd.conc_pen.toFixed(0) : "—"}</div>
            <div class="dq-bd-lbl">Conc.<br>Pen</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${trim.toFixed(0)}</div>
            <div class="dq-bd-lbl">Trim<br>Score</div>
          </div>
        </div>
        <div class="dq-breakdown-notes">${escHtml(c.notes || "")}</div>
      </td>
    </tr>`;
  }).join("");

  tbody.innerHTML = rows;
}

function _dqToggleBreakdown(bdId) {
  const row = document.getElementById(bdId);
  if (row) row.classList.toggle("open");
}

function _dqToggleViewAll() {
  const dq = _analysisResult && _analysisResult.deployment_queue;
  if (!dq || !Array.isArray(dq.queue)) return;

  _dqShowAll = !_dqShowAll;
  const limit = _dqShowAll ? dq.queue.length : DQ_DEFAULT_ROWS;
  _dqRenderTableRows(dq.queue, "dq-queue-table-body", limit);

  const btn = document.getElementById("dq-view-all-btn");
  if (btn) {
    btn.textContent = _dqShowAll
      ? `▲ Show top ${DQ_DEFAULT_ROWS} only`
      : `▼ View all ${dq.queue.length} candidates`;
  }
}

function _dqToggleBlocked() {
  const body = document.getElementById("dq-blocked-body");
  const btn  = body ? body.previousElementSibling : null;
  if (!body) return;
  const open = body.classList.toggle("open");
  if (btn) btn.textContent = (open ? "▾" : "▸") + btn.textContent.slice(1);
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5D — Capital Deployment Plan
// ─────────────────────────────────────────────────────────────────────────────

let _dpPlanVisible = false;

function _dpGeneratePlan() {
  // Use pre-computed plan if embedded in current analysis result
  const plan = _analysisResult && _analysisResult.deployment_plan;
  if (plan && plan.recommendations && plan.recommendations.length > 0) {
    _dpRenderPlan(plan);
    return;
  }
  // Fallback: fetch on-demand from backend
  const run_id = _analysisResult && _analysisResult.run_id;
  if (!run_id) return;

  const btn = document.getElementById("dp-generate-btn");
  if (btn) btn.disabled = true;

  fetch("/api/portfolio/deployment-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      _dpRenderPlan(data);
    })
    .catch(err => {
      const el = document.getElementById("deploymentPlanContainer");
      if (el) {
        el.style.display = "block";
        el.innerHTML = `<div class="dq-panel"><p style="color:var(--sev-high);padding:1rem">
          Failed to generate deployment plan: ${escHtml(String(err))}</p></div>`;
      }
    })
    .finally(() => { if (btn) btn.disabled = false; });
}

function _dpRenderPlan(plan) {
  const el = document.getElementById("deploymentPlanContainer");
  if (!el) return;

  _dpPlanVisible = !_dpPlanVisible;

  if (!_dpPlanVisible) {
    el.style.display = "none";
    const btn = document.getElementById("dp-generate-btn");
    if (btn) btn.textContent = "▶ Generate Deployment Plan";
    return;
  }

  const btn = document.getElementById("dp-generate-btn");
  if (btn) btn.textContent = "▲ Hide Deployment Plan";

  const impact = plan.portfolio_impact || {};
  const recs   = plan.recommendations || [];
  const tiers  = plan.tier_summaries  || [];

  // Portfolio impact strip
  const impactHtml = `<div class="dp-impact-strip">
    <div class="dp-impact-card">
      <div class="dp-impact-val dp-gold">${formatMV(plan.total_allocated)}</div>
      <div class="dp-impact-lbl">Total Allocated</div>
    </div>
    <div class="dp-impact-card">
      <div class="dp-impact-val">${pct(impact.cash_before_pct)} → <span class="dp-green">${pct(impact.cash_after_pct)}</span></div>
      <div class="dp-impact-lbl">Cash %  (before → after)</div>
    </div>
    <div class="dp-impact-card">
      <div class="dp-impact-val">${impact.positions_at_warn_before} → ${impact.positions_at_warn_after}</div>
      <div class="dp-impact-lbl">Positions ≥ ${WARN_POSITION_PCT || 6}% (warn)</div>
    </div>
    <div class="dp-impact-card">
      <div class="dp-impact-val${impact.unallocated_cash > 100 ? "" : " dp-green"}">${formatMV(impact.unallocated_cash)}</div>
      <div class="dp-impact-lbl">Unallocated Cash</div>
    </div>
  </div>`;

  // Tier summary pills
  const tierLabels = { TIER_1: "Tier 1 — CCL (Highest)", TIER_2: "Tier 2 — HCA Top", TIER_3: "Tier 3 — Optional" };
  const tierBadge  = { TIER_1: "dq-tier-CCL", TIER_2: "dq-tier-HCA", TIER_3: "dp-tier-T3" };

  let tiersHtml = "";
  for (const t of tiers) {
    if (!t.candidate_count) continue;
    const label = tierLabels[t.tier] || t.tier;
    const badge = tierBadge[t.tier] || "";
    const tierRecs = recs.filter(r => r.deployment_tier === t.tier && r.suggested_add > 0);

    tiersHtml += `<div class="dp-tier-section">
      <div class="dp-tier-header">
        <span class="dq-tier ${badge}">${t.tier.replace("_", " ")}</span>
        <span class="dp-tier-label">${escHtml(label)}</span>
        <span class="dp-tier-total">${formatMV(t.total_allocated)}</span>
        <span class="dp-tier-pct">${t.pct_of_plan.toFixed(1)}% of plan</span>
      </div>
      <table class="dp-table">
        <thead><tr>
          <th>Rank</th><th>Symbol</th><th>Current $</th><th>Current %</th>
          <th>Suggested Add</th><th>Projected $</th><th>Projected %</th>
          <th>Headroom Left</th><th>Status</th>
        </tr></thead>
        <tbody>
          ${tierRecs.map(r => `<tr>
            <td><span class="dq-rank-num${r.rank === 1 ? " rank1" : ""}">#${r.rank}</span></td>
            <td><span class="dq-sym">${escHtml(r.symbol)}</span></td>
            <td style="text-align:right">${formatMV(r.current_market_value)}</td>
            <td style="text-align:right">${pct(r.current_weight_pct)}</td>
            <td style="text-align:right;font-weight:700;color:var(--accent-gold)">${formatMV(r.suggested_add)}</td>
            <td style="text-align:right">${formatMV(r.projected_market_value)}</td>
            <td style="text-align:right;font-weight:600;${r.projected_weight_pct >= 6 ? "color:var(--sev-med)" : "color:var(--accent-green)"}">${pct(r.projected_weight_pct)}</td>
            <td style="text-align:right">${formatMV(r.headroom_to_warn)}</td>
            <td><span class="dq-status dq-status-${r.constraint_status}">${r.constraint_status.replace("_", " ")}</span></td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
  }

  el.innerHTML = `<div class="dq-panel">
    <div class="dq-section-header">
      <span class="dq-section-title">Capital Deployment Plan</span>
      <span class="dq-version-badge">${escHtml(plan.planner_version || "DP-1.0")}</span>
      <span class="dq-advisory-note">Guidance only — not a trade instruction</span>
    </div>
    ${impactHtml}
    <div class="dp-advisory">${escHtml(plan.plan_advisory || "")}</div>
    ${tiersHtml}
  </div>`;
  el.style.display = "block";
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────
function setLoading(on) {
  document.getElementById("analyzeBtn").disabled = on;
}

function showStatus(type, html) {
  const el = document.getElementById("statusBar");
  el.className = `status-bar ${type}`;
  el.innerHTML = html;
  el.style.display = "block";
}

function hideStatus() {
  document.getElementById("statusBar").style.display = "none";
}

function emptyState(title, sub) {
  return `<div class="empty-state">
    <div class="empty-state-icon">📊</div>
    <h3>${escHtml(title)}</h3>
    <p style="margin:0">${escHtml(sub)}</p>
  </div>`;
}

function escHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function pct(v) {
  const n = parseFloat(v || 0);
  if (isNaN(n)) return "—";
  return n.toFixed(1) + "%";
}

function formatMV(v) {
  const n = parseFloat(v || 0);
  if (isNaN(n)) return "—";
  if (n >= 1_000_000) return "$" + (n / 1_000_000).toFixed(2) + "M";
  if (n >= 1_000)     return "$" + (n / 1_000).toFixed(1) + "K";
  return "$" + n.toFixed(0);
}
