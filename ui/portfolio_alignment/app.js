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
  if (!recs.length) {
    el.innerHTML = `<div style="padding:20px;text-align:center;color:var(--muted)">
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

    return `<div class="rec-card pri-${r.priority} state-${state} type-${recType} urgency-${r.mandate_urgency || ""}">
      ${isPhaseE ? _phaseETypeHeader(recType) : ""}
      <div class="rec-title">#${i+1} &nbsp; ${escHtml(r.title)}</div>
      <div class="rec-rationale">${escHtml(r.rationale)}</div>
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

  el.innerHTML = `<div class="rec-list">${cards}</div>`;
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
    return `<tr>
      <td style="font-weight:600;font-family:monospace">${escHtml(o.symbol)}</td>
      <td style="text-align:right">${pct(o.percent_of_portfolio)}</td>
      <td><span class="dir-${o.signal_direction}">${o.signal_direction || "—"}</span></td>
      <td>${score}</td>
      <td>${escHtml(o.ess_score_text || "—")}</td>
      <td>${escHtml(o.zacks_rating || "—")}</td>
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
    <div style="margin-top:8px;font-size:0.69rem;color:#aaa;border-top:1px solid #dde8f0;padding-top:6px;">
      Optimizer v${om.optimizer_version || "7.3A"} &nbsp;·&nbsp; Parallel Mode &nbsp;·&nbsp;
      Visibility only — no action authority. Legacy recommendations take precedence.
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
