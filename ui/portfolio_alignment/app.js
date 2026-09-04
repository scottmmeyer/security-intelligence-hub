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

// Phase 23.0A — tax operator state
let _taxState = {
  net_realized_ytd: null,
  potential_additional_losses: null,
  capital_loss_carryforward: null,
  tax_year: new Date().getFullYear(),
};

// Phase 23.0C — strategic exit state
let _strategicExitSymbols = [];  // persisted via /api/operator/strategic-exits

// Phase 23.2 — operator policy state
let _operatorPolicies = {};  // { [symbol]: { policy_type, policy_annotation, status, ... } }

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
  try {
    const stored = localStorage.getItem(_STORAGE_KEY);
    _debugLog("localStorage.getItem() returned: " + (stored ? "YES (data exists)" : "NO (null)"));
    const result = stored ? JSON.parse(stored) : null;
    _debugLog("Parsed result: " + (result ? "OK" : "NO"));
    return result;
  } catch (err) {
    _debugLog("_loadSavedResult() error: " + err.message);
    return null;
  }
}
function _clearSavedResult() {
  try { localStorage.removeItem(_STORAGE_KEY); } catch (_) {}
}

// Phase 23.2D — Backend fallback for browser storage durability
// If localStorage is empty, restore from canonical backend run.
async function _loadLatestRunFromBackend() {
  try {
    _debugLog("🔄 localStorage empty; fetching run list from backend...");
    const manifestResp = await fetch("/api/portfolio/runs");
    if (!manifestResp.ok) {
      _debugLog("⚠ /api/portfolio/runs returned " + manifestResp.status);
      return null;
    }
    const manifest = await manifestResp.json();
    if (!manifest.portfolios || !Array.isArray(manifest.portfolios) || manifest.portfolios.length === 0) {
      _debugLog("ℹ No runs in manifest (empty backend)");
      return null;
    }
    // Find latest by created_at_utc (ISO string comparison works lexicographically)
    let latest = null;
    for (const run of manifest.portfolios) {
      if (!latest || (run.created_at_utc > latest.created_at_utc)) {
        latest = run;
      }
    }
    if (!latest) {
      _debugLog("ℹ Could not determine latest run");
      return null;
    }
    _debugLog("✓ Latest run: " + latest.run_id + " (created: " + latest.created_at_utc + ")");
    // Fetch full run data
    return await _loadRunFromBackend(latest.run_id);
  } catch (err) {
    _debugLog("✗ Backend fallback error: " + err.message);
    return null;
  }
}

async function _loadRunFromBackend(runId) {
  try {
    _debugLog("📥 Fetching run " + runId + " from backend...");
    const runResp = await fetch("/api/portfolio/runs/" + encodeURIComponent(runId));
    if (!runResp.ok) {
      _debugLog("⚠ /api/portfolio/runs/" + runId + " returned " + runResp.status);
      return null;
    }
    const runData = await runResp.json();
    _debugLog("✓ Loaded run " + runId + " from backend (" + (runData.holding_count || "?") + " holdings)");
    return runData;
  } catch (err) {
    _debugLog("✗ Failed to load run: " + err.message);
    return null;
  }
}

function _safeVersionedValue(data, key) {
  if (!data || typeof data !== "object") return undefined;
  const snapshot = data.snapshot && typeof data.snapshot === "object" ? data.snapshot : null;
  const runMetadata = data.run_metadata && typeof data.run_metadata === "object" ? data.run_metadata : null;
  const candidates = [
    data[key],
    snapshot && snapshot[key],
    runMetadata && runMetadata[key],
  ];
  for (const candidate of candidates) {
    if (candidate !== undefined && candidate !== null && candidate !== "" && candidate !== "null" && candidate !== "undefined") {
      return candidate;
    }
  }
  return undefined;
}

function _normalizeRestoredRunData(data) {
  if (!data || typeof data !== "object") return data;

  const snapshot = data.snapshot && typeof data.snapshot === "object" ? data.snapshot : {};
  const runMetadata = data.run_metadata && typeof data.run_metadata === "object" ? data.run_metadata : {};
  const concentration = data.concentration && typeof data.concentration === "object" ? data.concentration : {};

  const pickFirst = (...values) => {
    for (const value of values) {
      if (value !== undefined && value !== null && value !== "" && value !== "null" && value !== "undefined") {
        return value;
      }
    }
    return undefined;
  };

  const toFiniteNumber = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  const normalized = { ...data };

  normalized.run_id = pickFirst(normalized.run_id, snapshot.run_id, runMetadata.run_id, data.analysis_id, data.id) || normalized.run_id || "";
  normalized.snapshot_date = pickFirst(normalized.snapshot_date, snapshot.snapshot_date, runMetadata.snapshot_date, data.snapshotDate, snapshot.snapshotDate) || "";
  normalized.account_name = pickFirst(normalized.account_name, snapshot.account_name, runMetadata.account_name, data.accountName, snapshot.accountName) || "Portfolio";
  normalized.holding_count = pickFirst(normalized.holding_count, normalized.holdings_count, snapshot.holding_count, snapshot.holdings_count, runMetadata.holding_count, runMetadata.holdings_count, data.holdings, data.holdings_count);
  normalized.holding_count = normalized.holding_count != null ? toFiniteNumber(normalized.holding_count) ?? normalized.holding_count : normalized.holding_count;
  normalized.recommendation_count = pickFirst(
    normalized.recommendation_count,
    snapshot.recommendation_count,
    runMetadata.recommendation_count,
    Array.isArray(data.recommendations) ? data.recommendations.length : undefined,
    data.recommendationCount,
    snapshot.recommendationCount,
    runMetadata.recommendationCount,
  );
  normalized.recommendation_count = normalized.recommendation_count != null ? toFiniteNumber(normalized.recommendation_count) ?? normalized.recommendation_count : normalized.recommendation_count;
  normalized.total_market_value = pickFirst(normalized.total_market_value, snapshot.total_market_value, runMetadata.total_market_value, data.portfolio_value, snapshot.portfolio_value, runMetadata.portfolio_value);
  normalized.overall_alignment_score = pickFirst(normalized.overall_alignment_score, snapshot.overall_alignment_score, runMetadata.overall_alignment_score, data.alignment_score, snapshot.alignment_score, runMetadata.alignment_score);
  normalized.concentration_tier = pickFirst(normalized.concentration_tier, concentration.concentration_tier, snapshot.concentration_tier, runMetadata.concentration_tier, data.concentration_tier, data.mandate_type, snapshot.mandate_type, runMetadata.mandate_type);
  normalized.mandate_type = pickFirst(normalized.mandate_type, normalized.mandate, snapshot.mandate_type, snapshot.mandate, runMetadata.mandate_type, runMetadata.mandate, data.mandate_type, data.mandate);
  normalized.source_format = pickFirst(normalized.source_format, snapshot.source_format, runMetadata.source_format, data.sourceFormat, snapshot.sourceFormat, runMetadata.sourceFormat) || "CSV";

  if (!Array.isArray(normalized.alignment) && Array.isArray(data.alignment_snapshot)) {
    normalized.alignment = data.alignment_snapshot;
  }
  if (!Array.isArray(normalized.recommendations) && Array.isArray(data.recommendations_snapshot)) {
    normalized.recommendations = data.recommendations_snapshot;
  }
  if (!Array.isArray(normalized.security_overlays) && Array.isArray(data.security_overlays_snapshot)) {
    normalized.security_overlays = data.security_overlays_snapshot;
  }

  return normalized;
}

function _getAccountName(data) {
  return _safeVersionedValue(data, "account_name") || "Portfolio";
}

function _getPortfolioDate(data) {
  return _safeVersionedValue(data, "snapshot_date") || "";
}

function _getHoldingCount(data) {
  const value = _safeVersionedValue(data, "holding_count");
  return value != null ? Number(value) : undefined;
}

function _getPortfolioValue(data) {
  return _safeVersionedValue(data, "total_market_value");
}

function _getAlignmentScore(data) {
  return _safeVersionedValue(data, "overall_alignment_score");
}

function _getRecommendationCount(data) {
  const value = _safeVersionedValue(data, "recommendation_count");
  return value != null ? Number(value) : undefined;
}

function _getConcentrationLabel(data) {
  const value = _safeVersionedValue(data, "concentration_tier");
  return value != null ? String(value) : "UNKNOWN";
}

function _getFormatLabel(data) {
  const value = _safeVersionedValue(data, "source_format");
  return value != null ? String(value) : "—";
}

function _getMandateLabel(data) {
  const selected = document.getElementById("mandateSelect") && document.getElementById("mandateSelect").value;
  const value = _safeVersionedValue(data, "mandate") || _safeVersionedValue(data, "mandate_type") || selected || "CONCENTRATED_ALPHA";
  return value != null && value !== "" && value !== "null" && value !== "undefined" ? String(value) : "CONCENTRATED_ALPHA";
}

function _debugLog(msg) {
  console.log("[APP DEBUG]", msg);
  // Fallback to direct DOM manipulation
  const content = document.getElementById("debugContent");
  if (content) {
    content.textContent = (content.textContent || "") + "\n" + msg;
    const lines = content.textContent.split("\n").filter(l => l.trim());
    if (lines.length > 15) {
      content.textContent = lines.slice(-15).join("\n");
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  try {
    _debugLog("📍 DOMContentLoaded fired");

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

    // Phase 23.0A — load persisted tax state
    loadTaxState();

    // Phase 23.0C — load persisted strategic exits
    loadStrategicExits();

    // Phase 23.2 — load persisted operator policies
    loadOperatorPolicies();

    // Tax input live-compute
    ["taxNetRealizedYTD", "taxPotentialLosses", "taxCarryforward"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("input", updateTaxComputed);
    });

    // Restore last analysis if available
    const saved = _normalizeRestoredRunData(_loadSavedResult());
    _debugLog("Attempting to render saved result...");
    if (saved) {
      _debugLog("✓ Saved result found, rendering...");
      _analysisResult = saved;
      const ts = _getPortfolioDate(saved);
      const savedMandate = _getMandateLabel(saved);
      const mandateSel = document.getElementById("mandateSelect");
      if (mandateSel) mandateSel.value = savedMandate;
      showStatus("info",
        `Showing last analysis — <strong>${_getAccountName(saved)}</strong> ` +
        `(${_getHoldingCount(saved) ?? "—"} holdings, ${ts}, mandate: <strong>${savedMandate}</strong>). ` +
        `Upload a new file to re-analyze.`);
      document.getElementById("clearBtn").style.display = "inline-block";
      try {
        renderResults(saved);
        _debugLog("✓ renderResults() completed");
      } catch (err) {
        _debugLog("✗ renderResults() error: " + err.message);
      }
    } else {
      _debugLog("ℹ localStorage empty; trying backend fallback...");
      const backendRun = _normalizeRestoredRunData(await _loadLatestRunFromBackend());
      if (backendRun) {
        _debugLog("✓ Backend run restored: " + (backendRun.run_id || "unknown"));
        _analysisResult = backendRun;
        const ts = _getPortfolioDate(backendRun);
        const restoredMandate = _getMandateLabel(backendRun);
        const mandateSel = document.getElementById("mandateSelect");
        if (mandateSel) mandateSel.value = restoredMandate;
        showStatus("info",
          `Showing restored analysis — <strong>${_getAccountName(backendRun)}</strong> ` +
          `(${_getHoldingCount(backendRun) ?? "—"} holdings, ${ts}, mandate: <strong>${restoredMandate}</strong>). ` +
          `Upload a new file to re-analyze.`);
        document.getElementById("clearBtn").style.display = "inline-block";
        try {
          renderResults(backendRun);
          _debugLog("✓ renderResults() completed");
        } catch (err) {
          _debugLog("✗ renderResults() error: " + err.message);
        }
      } else {
        _debugLog("ℹ No backend run available; showing empty state");
      }
    }
  } catch (err) {
    _debugLog("✗ BOOT ERROR: " + err.message);
    console.error("Boot error:", err);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// Upload zone
// ─────────────────────────────────────────────────────────────────────────────
function setupUploadZone() {
  const zone = document.getElementById("uploadZone");
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
    showStatus("success", `✓  Loaded <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB). Set the portfolio date and click Analyze.`);
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

    _analysisResult = _normalizeRestoredRunData(data);
    setLoading(false);
    _saveResult(_analysisResult);

    const warnText = data.warnings && data.warnings.length
      ? `  <br>⚠ ${data.warnings.length} normalization warning(s): ${data.warnings.join("; ")}`
      : "";
    showStatus("success",
      `✓  Analysis complete — ${data.holding_count} holdings enriched. ` +
      `Run ID: <strong>${data.run_id}</strong>${warnText}`
    );

    renderResults(_analysisResult);
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
  const taxSection = document.getElementById("taxActionSection");
  if (taxSection) taxSection.style.display = "none";
  const pipelineSection = document.getElementById("portfolioActionPipelineSection");
  if (pipelineSection) pipelineSection.style.display = "none";
  hideStatus();
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 23.0A — Tax Position Panel
// ─────────────────────────────────────────────────────────────────────────────

function toggleTaxPanel() {
  const body    = document.getElementById("taxPanelBody");
  const chevron = document.getElementById("taxPanelChevron");
  if (!body) return;
  const open = body.classList.toggle("open");
  if (chevron) chevron.classList.toggle("open", open);
}

async function loadTaxState() {
  try {
    const resp = await fetch("/api/operator/tax-state");
    if (!resp.ok) return;
    const data = await resp.json();
    if (data && typeof data === "object" && !data.error) {
      _taxState = { ..._taxState, ...data };
      _populateTaxFields();
      updateTaxComputed();
    }
  } catch (_) { /* best-effort */ }
}

function _populateTaxFields() {
  const map = {
    taxNetRealizedYTD:      "net_realized_ytd",
    taxPotentialLosses:     "potential_additional_losses",
    taxCarryforward:        "capital_loss_carryforward",
    taxYear:                "tax_year",
  };
  for (const [elId, key] of Object.entries(map)) {
    const el = document.getElementById(elId);
    if (el && _taxState[key] != null) el.value = _taxState[key];
  }
}

function updateTaxComputed() {
  const ytd      = parseFloat(document.getElementById("taxNetRealizedYTD")?.value ?? "") || 0;
  const addl     = Math.abs(parseFloat(document.getElementById("taxPotentialLosses")?.value ?? "") || 0);
  const carry    = Math.abs(parseFloat(document.getElementById("taxCarryforward")?.value ?? "") || 0);

  // Losses already realized shield future gains
  const available  = Math.max(0, -ytd + carry);
  const projected  = available + addl;

  const elA = document.getElementById("taxAvailableCapacity");
  const elP = document.getElementById("taxProjectedCapacity");
  if (elA) elA.textContent = _formatTaxDollar(available);
  if (elP) elP.textContent = _formatTaxDollar(projected);
}

function _formatTaxDollar(v) {
  if (v === null || v === undefined || isNaN(v)) return "—";
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return (v < 0 ? "-$" : "$") + (abs / 1_000_000).toFixed(2) + "M";
  if (abs >= 100_000)   return (v < 0 ? "-$" : "$") + (abs / 1_000).toFixed(1) + "K";
  return (v < 0 ? "-$" : "$") + abs.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function _readTaxInputs() {
  return {
    net_realized_ytd:              parseFloat(document.getElementById("taxNetRealizedYTD")?.value ?? "") || 0,
    potential_additional_losses:   Math.abs(parseFloat(document.getElementById("taxPotentialLosses")?.value ?? "") || 0),
    capital_loss_carryforward:     Math.abs(parseFloat(document.getElementById("taxCarryforward")?.value ?? "") || 0),
    tax_year:                      parseInt(document.getElementById("taxYear")?.value ?? new Date().getFullYear(), 10),
  };
}

async function saveTaxState() {
  const inputs   = _readTaxInputs();
  const statusEl = document.getElementById("taxSaveStatus");

  try {
    const resp = await fetch("/api/operator/tax-state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(inputs),
    });
    const data = await resp.json();
    if (resp.ok && data.ok) {
      _taxState = { ..._taxState, ...inputs };
      updateTaxComputed();
      if (statusEl) {
        statusEl.className = "tax-save-status";
        statusEl.textContent = "✓ Saved";
        setTimeout(() => { statusEl.textContent = ""; }, 3000);
      }
      // Re-render pipeline if analysis is loaded
      if (_analysisResult) renderPortfolioActionPipeline(_analysisResult);
    } else {
      if (statusEl) {
        statusEl.className = "tax-save-status error";
        statusEl.textContent = "Save failed: " + (data.error || "unknown error");
      }
    }
  } catch (err) {
    if (statusEl) {
      statusEl.className = "tax-save-status error";
      statusEl.textContent = "Network error: " + err.message;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 23.0C — Strategic Exit Management
// ─────────────────────────────────────────────────────────────────────────────

async function loadStrategicExits() {
  try {
    const resp = await fetch("/api/operator/strategic-exits");
    if (!resp.ok) return;
    const data = await resp.json();
    if (data && Array.isArray(data.strategic_exit_symbols)) {
      _strategicExitSymbols = data.strategic_exit_symbols.map(s => s.toUpperCase());
      _renderStrategicExitList();
    }
  } catch (_) { /* best-effort */ }
}

function _renderStrategicExitList() {
  const el = document.getElementById("strategicExitList");
  if (!el) return;
  if (!_strategicExitSymbols.length) {
    el.innerHTML = `<span style="color:var(--muted);font-style:italic;font-size:0.82rem;">No strategic exits configured.</span>`;
    return;
  }
  el.innerHTML = _strategicExitSymbols.map(sym =>
    `<span class="se-chip">
       <span class="se-chip-sym">${escHtml(sym)}</span>
       <button class="se-chip-rm" title="Remove ${escHtml(sym)}" onclick="removeStrategicExit('${escHtml(sym)}')">✕</button>
     </span>`
  ).join("");
}

async function addStrategicExit() {
  const input = document.getElementById("strategicExitInput");
  if (!input) return;
  const sym = input.value.trim().toUpperCase();
  if (!sym || !/^[A-Z0-9.]{1,12}$/.test(sym)) {
    _setSeStatus("Invalid symbol.", "error");
    return;
  }
  if (_strategicExitSymbols.includes(sym)) {
    _setSeStatus(`${sym} already in list.`, "warn");
    return;
  }
  try {
    const resp = await fetch("/api/operator/strategic-exits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "add", symbol: sym }),
    });
    const data = await resp.json();
    if (resp.ok && data.ok) {
      _strategicExitSymbols = data.strategic_exit_symbols || [];
      input.value = "";
      _renderStrategicExitList();
      _setSeStatus(`✓ ${sym} added.`, "ok");
      if (_analysisResult) renderPortfolioActionPipeline(_analysisResult);
    } else {
      _setSeStatus("Save failed: " + (data.error || "unknown"), "error");
    }
  } catch (err) {
    _setSeStatus("Network error: " + err.message, "error");
  }
}

async function removeStrategicExit(sym) {
  try {
    const resp = await fetch("/api/operator/strategic-exits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "remove", symbol: sym }),
    });
    const data = await resp.json();
    if (resp.ok && data.ok) {
      _strategicExitSymbols = data.strategic_exit_symbols || [];
      _renderStrategicExitList();
      _setSeStatus(`${sym} removed.`, "ok");
      if (_analysisResult) renderPortfolioActionPipeline(_analysisResult);
    }
  } catch (_) {}
}

function _setSeStatus(msg, type) {
  const el = document.getElementById("seStatus");
  if (!el) return;
  el.textContent = msg;
  el.className = "se-status se-status-" + type;
  setTimeout(() => { el.textContent = ""; el.className = "se-status"; }, 3500);
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 23.2 — Operator Policy Layer
// ─────────────────────────────────────────────────────────────────────────────

async function loadOperatorPolicies() {
  try {
    const resp = await fetch("/api/operator/policies");
    if (!resp.ok) return;
    const data = await resp.json();
    _operatorPolicies = {};
    for (const p of (data.policies || [])) {
      _operatorPolicies[p.symbol] = p;
    }
    _renderPolicyList();
  } catch (_) {}
}

function _policyBadgeClass(policyType) {
  if (!policyType) return "policy-badge";
  const map = {
    DO_NOT_SELL: "policy-badge policy-badge-do-not-sell",
    SELL_LAST: "policy-badge policy-badge-sell-last",
    CORE_ANCHOR: "policy-badge policy-badge-core-anchor",
    PREFERRED_ACCUMULATION: "policy-badge policy-badge-preferred",
  };
  return map[policyType] || "policy-badge";
}

function _policyBadgeLabel(policyType) {
  const map = {
    DO_NOT_SELL: "🔒 DO_NOT_SELL",
    SELL_LAST: "⏸ SELL_LAST",
    CORE_ANCHOR: "⚓ CORE_ANCHOR",
    PREFERRED_ACCUMULATION: "⭐ PREFERRED_ACCUMULATION",
  };
  return map[policyType] || policyType;
}

function _renderPolicyList() {
  const container = document.getElementById("policyListContainer");
  if (!container) return;
  const policies = Object.values(_operatorPolicies).filter(p => p.status === "ACTIVE");
  if (!policies.length) {
    container.innerHTML = '<div style="color:var(--muted); font-size:0.82rem; padding:6px 0;">No active policies.</div>';
    return;
  }
  container.innerHTML = policies.map(p => `
    <div class="policy-row">
      <span class="policy-row-symbol">${p.symbol}</span>
      <span class="${_policyBadgeClass(p.policy_type)}">${_policyBadgeLabel(p.policy_type)}</span>
      <span class="policy-row-rationale">${p.rationale || ''}</span>
      <button class="policy-row-revoke" onclick="revokeOperatorPolicy('${p.symbol}')">Revoke</button>
    </div>
  `).join("");
}

async function addOperatorPolicy() {
  const symbol = (document.getElementById("policySymbolInput")?.value || "").trim().toUpperCase();
  const policyType = document.getElementById("policyTypeSelect")?.value || "";
  const rationale = (document.getElementById("policyRationaleInput")?.value || "").trim();
  if (!symbol || !policyType) {
    _setPolicyStatus("Symbol and policy type are required.", "error");
    return;
  }
  try {
    const resp = await fetch("/api/operator/policies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, policy_type: policyType, rationale }),
    });
    const data = await resp.json();
    if (resp.status === 409) {
      _setPolicyStatus(`Conflict: ${data.error}`, "error");
      return;
    }
    if (!resp.ok) {
      _setPolicyStatus(data.error || "Error adding policy.", "error");
      return;
    }
    _operatorPolicies[symbol] = data.policy;
    _renderPolicyList();
    document.getElementById("policySymbolInput").value = "";
    document.getElementById("policyTypeSelect").value = "";
    document.getElementById("policyRationaleInput").value = "";
    _setPolicyStatus(`${symbol} → ${policyType} policy added.`, "ok");
  } catch (e) {
    _setPolicyStatus("Network error.", "error");
  }
}

async function revokeOperatorPolicy(sym) {
  try {
    const resp = await fetch("/api/operator/policies/revoke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: sym }),
    });
    const data = await resp.json();
    if (resp.ok && data.ok) {
      delete _operatorPolicies[sym];
      _renderPolicyList();
      _setPolicyStatus(`${sym} policy revoked.`, "ok");
    }
  } catch (_) {}
}

function togglePolicyPanel() {
  const body = document.getElementById("policyPanelBody");
  const chevron = document.getElementById("policyPanelChevron");
  if (!body) return;
  const isOpen = body.style.display !== "none";
  body.style.display = isOpen ? "none" : "block";
  if (chevron) chevron.textContent = isOpen ? "▼" : "▲";
}

function _setPolicyStatus(msg, type) {
  const el = document.getElementById("policyStatus");
  if (!el) return;
  el.textContent = msg;
  el.style.color = type === "error" ? "#c0392b" : "#2e7d32";
  setTimeout(() => { el.textContent = ""; }, 3500);
}



// Conviction tiers that are PROTECTED — never appear as funding sources
const _PROTECTED_CONVICTION_TIERS = new Set([
  "HIGH_CONVICTION_ANCHOR",
  "CORE_CONVICTION_LEADER",
]);

/**
 * Build the four-category Portfolio Action Pipeline from analysis data.
 * Returns { cat1, cat2, cat3, cat4 } arrays.
 *
 * Cat 1 — Signal Deterioration: holdings with BEARISH/VERY_BEARISH signal
 * Cat 2 — Strategic Exit:       operator-designated symbols
 * Cat 3 — Allocation Reduction: holdings mapped to REDUCE_OVERWEIGHT nodes
 * Cat 4 — Funding Sources:      low-conviction, non-protected holdings
 */
function _computePortfolioActions(data) {
  const overlays       = data.security_overlays || [];
  const recommendations = data.recommendations || [];
  const deploymentQueue = data.deployment_queue || {};
  const dqEntries      = deploymentQueue.queue || [];

  // Build conviction tier map from deployment_queue entries
  const convictionTierBySymbol = {};
  for (const entry of dqEntries) {
    if (entry.symbol && entry.narrative_tier) {
      convictionTierBySymbol[entry.symbol.toUpperCase()] = entry.narrative_tier;
    }
  }

  // Build overlay map: symbol → overlay
  const overlayBySymbol = {};
  for (const ov of overlays) {
    if (ov.symbol) overlayBySymbol[ov.symbol.toUpperCase()] = ov;
  }

  // Collect REDUCE_OVERWEIGHT nodes and their constituent symbols
  const reduceNodes = [];
  for (const rec of recommendations) {
    if (rec.recommendation_type === "REDUCE_OVERWEIGHT") {
      const nodeKey   = rec.affected_node_key || "";
      const nodeLabel = (rec.drilldown && rec.drilldown.affected_node_label) || nodeKey;
      const drift     = rec.drift_pct || 0;
      const syms      = (rec.affected_symbols || []).map(s => s.toUpperCase());
      if (nodeKey && syms.length) {
        reduceNodes.push({ nodeKey, nodeLabel, drift, symbols: syms });
      }
    }
  }
  // For each symbol, find the node it belongs to (pick highest absolute drift node)
  const reduceNodeBySymbol = {};
  for (const node of reduceNodes) {
    for (const sym of node.symbols) {
      const existing = reduceNodeBySymbol[sym];
      if (!existing || Math.abs(node.drift) > Math.abs(existing.drift)) {
        reduceNodeBySymbol[sym] = node;
      }
    }
  }

  // ── Category 1: Signal Deterioration ──────────────────────────────────────
  const cat1 = [];
  // ── Category 5: Policy-Suppressed Actions ─────────────────────────────────
  const cat5 = [];
  for (const ov of overlays) {
    const sym    = (ov.symbol || "").toUpperCase();
    if (!sym) continue;
    const flag   = ov.opportunity_flag || "";   // C1 FIX: was ov.recommended_action
    const signal = ov.signal_direction || "UNKNOWN";
    const ess    = ov.ess_score_text || "";
    const tier   = convictionTierBySymbol[sym] || "";
    const execState   = ov.execution_state || "EXECUTABLE";
    const effAction   = ov.effective_action || flag || "HOLD";
    const policyType  = ov.policy_type || "";
    const policyBadge = ov.policy_annotation || "";

    const isSignalDeteriorated = (
      signal === "BEARISH" ||
      ess === "VERY_BEARISH" ||
      ess === "BEARISH" ||
      flag === "TRIM"
    );
    if (!isSignalDeteriorated) continue;

    // BLOCKED_BY_POLICY items are removed from the executable pipeline
    // and recorded in Cat 5 (Policy-Suppressed Actions) instead
    if (execState === "BLOCKED_BY_POLICY") {
      cat5.push({
        symbol:          sym,
        ess,
        signal,
        flag,
        original_action: flag,
        policy_type:     policyType,
        policy_badge:    policyBadge,
        effective_action: effAction,
        percent_of_portfolio: parseFloat(ov.percent_of_portfolio || 0),
        composite_score:      parseFloat(ov.composite_score || 0),
      });
      continue;
    }

    const priority = flag === "TRIM" ? "HIGH" : (ess === "VERY_BEARISH" ? "HIGH" : "MEDIUM");
    cat1.push({
      symbol:   sym,
      flag,
      signal,
      ess,
      conviction_tier: tier,
      percent_of_portfolio: parseFloat(ov.percent_of_portfolio || 0),
      composite_score:      parseFloat(ov.composite_score || 0),
      replay_supported:     ov.replay_supported === true || ov.replay_supported === "True",
      replay_percentile:    ov.replay_percentile != null ? parseFloat(ov.replay_percentile) : null,
      priority,
      rationale: ov.flag_rationale || "",
      execution_state:  execState,
      effective_action: effAction,
      policy_type:      policyType,
      policy_badge:     policyBadge,
    });
  }
  // Sort: DEFERRED_BY_POLICY last, then HIGH priority, then by composite_score asc (weakest first)
  cat1.sort((a, b) => {
    const aDeferred = a.execution_state === "DEFERRED_BY_POLICY" ? 1 : 0;
    const bDeferred = b.execution_state === "DEFERRED_BY_POLICY" ? 1 : 0;
    if (aDeferred !== bDeferred) return aDeferred - bDeferred;
    if (a.priority !== b.priority) return a.priority === "HIGH" ? -1 : 1;
    return a.composite_score - b.composite_score;
  });

  // ── Category 2: Strategic Exit ─────────────────────────────────────────────
  const cat2 = [];
  for (const sym of _strategicExitSymbols) {
    const ov = overlayBySymbol[sym];
    cat2.push({
      symbol:   sym,
      priority: "HIGH",
      reason:   "Operator Designated Exit",
      ov_flag:  ov ? (ov.opportunity_flag || "") : "",
      ov_signal: ov ? (ov.signal_direction || "") : "",
      percent_of_portfolio: ov ? parseFloat(ov.percent_of_portfolio || 0) : null,
      composite_score:      ov ? parseFloat(ov.composite_score || 0) : null,
    });
  }

  // ── Category 3: Allocation Reduction ──────────────────────────────────────
  const cat3 = [];
  const cat3Syms = new Set();
  // Get the reduce node symbols that are actually in the portfolio overlay
  for (const node of reduceNodes) {
    const nodeSeverityScore = Math.abs(node.drift);
    for (const sym of node.symbols) {
      if (cat3Syms.has(sym)) continue;
      const ov = overlayBySymbol[sym];
      if (!ov) continue;  // Not in portfolio
      const tier = convictionTierBySymbol[sym] || "";
      // Include even protected tiers in allocation reduction (strategic context)
      // but mark them as protected so UI can render with appropriate context
      cat3Syms.add(sym);
      cat3.push({
        symbol:   sym,
        node_key:   node.nodeKey,
        node_label: node.nodeLabel,
        drift_pct:  node.drift,
        severity:   nodeSeverityScore >= 5 ? "HIGH" : "MEDIUM",
        priority:   nodeSeverityScore >= 5 ? "HIGH" : "MEDIUM",
        conviction_tier: tier,
        is_protected: _PROTECTED_CONVICTION_TIERS.has(tier),
        ov_flag:  ov.opportunity_flag || "",
        ov_signal: ov.signal_direction || "",
        percent_of_portfolio: parseFloat(ov.percent_of_portfolio || 0),
        composite_score:      parseFloat(ov.composite_score || 0),
      });
    }
  }
  // Sort: higher drift (more overweight) first, then alpha
  cat3.sort((a, b) => Math.abs(b.drift_pct) - Math.abs(a.drift_pct) || a.symbol.localeCompare(b.symbol));

  // ── Category 4: Funding Sources ────────────────────────────────────────────
  const cat4 = [];
  const cat4Excl = new Set();
  // Exclude anything in Cat 1 (signal deterioration) that's already a clear exit
  // Exclude protected tiers
  for (const ov of overlays) {
    const sym  = (ov.symbol || "").toUpperCase();
    if (!sym) continue;
    const tier = convictionTierBySymbol[sym] || "";
    if (_PROTECTED_CONVICTION_TIERS.has(tier)) continue;

    // Only include holdings with meaningful size
    const pct = parseFloat(ov.percent_of_portfolio || 0);
    if (pct < 0.05) continue;

    // Exclude cash-equivalents, money market
    const flag   = ov.opportunity_flag || "";
    const signal = ov.signal_direction || "UNKNOWN";
    const score  = parseFloat(ov.composite_score || 0);
    if (!score) continue;  // No signal data

    // Exclude ACCUMULATE holdings that aren't already in Cat1
    // Funding sources = HOLD, WATCH, TRIM — not ACCUMULATE unless also cat1
    const isCat1 = cat1.some(c => c.symbol === sym);
    if (flag === "ACCUMULATE" && !isCat1) continue;
    if (cat4Excl.has(sym)) continue;

    // Compute a funding priority score: lower composite = better funding candidate
    // Also penalize if already in Cat3 (allocation reduction — useful cross-reference)
    const isCat3 = cat3.some(c => c.symbol === sym);
    const fundingReason = isCat1 ? "Signal Deterioration" : isCat3 ? "Allocation Reduction" : "Low Conviction";

    cat4.push({
      symbol:   sym,
      flag,
      signal,
      composite_score: score,
      percent_of_portfolio: pct,
      conviction_tier: tier,
      replay_supported: ov.replay_supported === true || ov.replay_supported === "True",
      primary_category: isCat1 ? "SIGNAL_DETERIORATION" : isCat3 ? "ALLOCATION_REDUCTION" : null,
      funding_reason: fundingReason,
      priority: isCat1 ? "HIGH" : isCat3 ? "MEDIUM" : "LOW",
    });
  }
  // Sort: Cat1 cross-refs first (HIGH), then Cat3 cross-refs (MEDIUM), then by score asc
  cat4.sort((a, b) => {
    const priorityOrder = { HIGH: 0, MEDIUM: 1, LOW: 2 };
    const po = (priorityOrder[a.priority] ?? 2) - (priorityOrder[b.priority] ?? 2);
    if (po !== 0) return po;
    return a.composite_score - b.composite_score;
  });

  return { cat1, cat2, cat3, cat4, cat5 };
}

function renderPortfolioActionPipeline(data) {
  const section   = document.getElementById("portfolioActionPipelineSection");
  const container = document.getElementById("portfolioActionPipelineContent");
  if (!section || !container) return;

  const { cat1, cat2, cat3, cat4, cat5 } = _computePortfolioActions(data);

  const totalActions = cat1.length + cat2.length + cat3.length + cat4.length;
  const categoriesActive = [cat1, cat2, cat3, cat4].filter(c => c.length > 0).length;

  // Update header badge
  const badge = document.getElementById("pipelineActionCount");
  if (badge) badge.textContent = totalActions;
  const catBadge = document.getElementById("pipelineCategoryCount");
  if (catBadge) catBadge.textContent = categoriesActive;

  if (totalActions === 0) {
    section.style.display = "block";
    container.innerHTML = `<div class="pap-empty">No portfolio actions identified. Portfolio is within signal and allocation parameters.</div>`;
    return;
  }

  section.style.display = "block";

  const html = [];

  // ── Cat 1: Signal Deterioration ────────────────────────────────────────────
  if (cat1.length > 0) {
    const hasHigh = cat1.some(c => c.priority === "HIGH");
    html.push(`
      <div class="pap-category ${hasHigh ? "pap-auto-expand" : ""}">
        <div class="pap-cat-header" onclick="this.closest('.pap-category').classList.toggle('pap-expanded')">
          <span class="pap-cat-num">1</span>
          <span class="pap-cat-label">Signal Deterioration</span>
          <span class="pap-cat-count">${cat1.length} holding${cat1.length !== 1 ? "s" : ""}</span>
          <span class="pap-cat-chevron">▾</span>
        </div>
        <div class="pap-cat-body">
          <table class="pap-tbl">
            <thead><tr>
              <th>Symbol</th><th>ESS Signal</th><th>Flag</th>
              <th>Score</th><th>% Port</th><th>Priority</th><th>Policy</th><th>Effective Action</th><th>Rationale</th>
            </tr></thead>
            <tbody>
              ${cat1.map(c => `<tr class="pap-row ${c.priority === "HIGH" && c.execution_state !== "DEFERRED_BY_POLICY" ? "pap-row-high" : ""} ${c.execution_state === "DEFERRED_BY_POLICY" ? "pap-row-deferred" : ""} ${c.execution_state === "INFORMATIONAL_ONLY" ? "pap-row-info-only" : ""}">
                <td><span class="pap-sym">${escHtml(c.symbol)}</span></td>
                <td><span class="ess-badge ess-${escHtml(c.ess || c.signal)}">${escHtml(c.ess || c.signal)}</span></td>
                <td><span class="flag-${escHtml(c.flag)}">${escHtml(c.flag || "—")}</span></td>
                <td>${c.composite_score.toFixed(2)}</td>
                <td>${c.percent_of_portfolio.toFixed(2)}%</td>
                <td><span class="pap-pri pap-pri-${c.priority}">${c.priority}</span></td>
                <td>${c.policy_badge ? `<span class="policy-badge ${_policyBadgeClass(c.policy_type)}">${escHtml(c.policy_badge)}</span>` : '<span style="color:var(--muted);font-size:0.75rem">—</span>'}</td>
                <td><span class="pap-exec-action pap-exec-${escHtml(c.execution_state)}">${escHtml(c.effective_action || c.flag || "—")}</span></td>
                <td style="font-size:0.78rem;color:var(--muted)">${escHtml(c.rationale || "Signal below threshold")}</td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`);
  }

  // ── Cat 2: Strategic Exit ───────────────────────────────────────────────────
  if (cat2.length > 0 || true) {  // Always show C2 (has management UI)
    html.push(`
      <div class="pap-category pap-auto-expand">
        <div class="pap-cat-header" onclick="this.closest('.pap-category').classList.toggle('pap-expanded')">
          <span class="pap-cat-num">2</span>
          <span class="pap-cat-label">Strategic Exit</span>
          <span class="pap-cat-count">${cat2.length} holding${cat2.length !== 1 ? "s" : ""}</span>
          <span class="pap-cat-chevron">▾</span>
        </div>
        <div class="pap-cat-body">
          ${cat2.length === 0 ? '<div class="pap-cat-empty">No strategic exits designated.</div>' : `
          <table class="pap-tbl">
            <thead><tr>
              <th>Symbol</th><th>Reason</th><th>Signal</th><th>Flag</th><th>% Port</th><th>Priority</th>
            </tr></thead>
            <tbody>
              ${cat2.map(c => `<tr class="pap-row pap-row-high">
                <td><span class="pap-sym">${escHtml(c.symbol)}</span></td>
                <td style="font-size:0.82rem;color:var(--muted)">${escHtml(c.reason)}</td>
                <td>${c.ov_signal ? `<span class="ess-badge ess-${escHtml(c.ov_signal)}">${escHtml(c.ov_signal)}</span>` : "—"}</td>
                <td>${c.ov_flag ? `<span class="flag-${escHtml(c.ov_flag)}">${escHtml(c.ov_flag)}</span>` : "—"}</td>
                <td>${c.percent_of_portfolio != null ? c.percent_of_portfolio.toFixed(2) + "%" : "—"}</td>
                <td><span class="pap-pri pap-pri-HIGH">HIGH</span></td>
              </tr>`).join("")}
            </tbody>
          </table>`}
          <div class="pap-se-manager">
            <span class="pap-se-manager-label">Manage Strategic Exits</span>
            <div class="pap-se-row">
              <div id="strategicExitList" class="pap-se-chips"></div>
            </div>
            <div class="pap-se-add-row">
              <input id="strategicExitInput" class="pap-se-input" type="text"
                placeholder="Symbol (e.g. FIS)" maxlength="12"
                onkeydown="if(event.key==='Enter')addStrategicExit()">
              <button class="pap-se-btn" onclick="addStrategicExit()">Add</button>
              <span id="seStatus" class="se-status"></span>
            </div>
          </div>
        </div>
      </div>`);
  }

  // ── Cat 3: Allocation Reduction ─────────────────────────────────────────────
  if (cat3.length > 0) {
    const hasHigh = cat3.some(c => c.severity === "HIGH");
    html.push(`
      <div class="pap-category ${hasHigh ? "pap-auto-expand" : ""}">
        <div class="pap-cat-header" onclick="this.closest('.pap-category').classList.toggle('pap-expanded')">
          <span class="pap-cat-num">3</span>
          <span class="pap-cat-label">Allocation Reduction</span>
          <span class="pap-cat-count">${cat3.length} holding${cat3.length !== 1 ? "s" : ""}</span>
          <span class="pap-cat-chevron">▾</span>
        </div>
        <div class="pap-cat-body">
          <table class="pap-tbl">
            <thead><tr>
              <th>Symbol</th><th>Overweight Node</th><th>Drift</th>
              <th>Signal</th><th>% Port</th><th>Priority</th><th>Note</th>
            </tr></thead>
            <tbody>
              ${cat3.map(c => `<tr class="pap-row ${c.severity === "HIGH" ? "pap-row-high" : ""}">
                <td><span class="pap-sym">${escHtml(c.symbol)}</span>
                    ${c.is_protected ? '<span class="pap-protected-badge" title="Protected conviction tier">🔒</span>' : ""}
                </td>
                <td style="font-size:0.8rem">${escHtml(c.node_label || c.node_key)}</td>
                <td><span class="pap-drift">+${Math.abs(c.drift_pct).toFixed(1)}pp</span></td>
                <td>${c.ov_signal ? `<span class="ess-badge ess-${escHtml(c.ov_signal)}">${escHtml(c.ov_signal)}</span>` : "—"}</td>
                <td>${c.percent_of_portfolio.toFixed(2)}%</td>
                <td><span class="pap-pri pap-pri-${c.severity}">${c.severity}</span></td>
                <td style="font-size:0.78rem;color:var(--muted)">${c.is_protected ? "Protected — consider reducing via index vehicles" : "Node overweight reduction candidate"}</td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`);
  }

  // ── Cat 4: Funding Sources ──────────────────────────────────────────────────
  if (cat4.length > 0) {
    html.push(`
      <div class="pap-category">
        <div class="pap-cat-header" onclick="this.closest('.pap-category').classList.toggle('pap-expanded')">
          <span class="pap-cat-num">4</span>
          <span class="pap-cat-label">Funding Sources</span>
          <span class="pap-cat-count">${cat4.length} holding${cat4.length !== 1 ? "s" : ""}</span>
          <span class="pap-cat-chevron">▾</span>
        </div>
        <div class="pap-cat-body">
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:8px;padding:6px 0;">
            Holdings that can fund higher-conviction opportunities. Conviction anchors (🔒) are excluded.
          </div>
          <table class="pap-tbl">
            <thead><tr>
              <th>Symbol</th><th>Flag</th><th>Signal</th>
              <th>Score</th><th>% Port</th><th>Priority</th><th>Cross-Reference</th>
            </tr></thead>
            <tbody>
              ${cat4.map(c => `<tr class="pap-row ${c.priority === "HIGH" ? "pap-row-high" : c.priority === "MEDIUM" ? "pap-row-med" : ""}">
                <td><span class="pap-sym">${escHtml(c.symbol)}</span></td>
                <td><span class="flag-${escHtml(c.flag)}">${escHtml(c.flag || "—")}</span></td>
                <td>${c.signal ? `<span class="ess-badge ess-${escHtml(c.signal)}">${escHtml(c.signal)}</span>` : "—"}</td>
                <td>${c.composite_score.toFixed(2)}</td>
                <td>${c.percent_of_portfolio.toFixed(2)}%</td>
                <td><span class="pap-pri pap-pri-${c.priority}">${c.priority}</span></td>
                <td style="font-size:0.78rem;color:var(--muted)">
                  ${c.primary_category
                    ? `<span class="pap-xref pap-xref-${c.primary_category}">${escHtml(c.funding_reason)}</span>`
                    : `<span style="color:var(--muted)">${escHtml(c.funding_reason)}</span>`}
                </td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`);
  }

  // ── Cat 5: Policy-Suppressed Actions ───────────────────────────────────────
  if (cat5.length > 0) {
    html.push(`
      <div class="pap-category pap-cat-suppressed pap-auto-expand">
        <div class="pap-cat-header" onclick="this.closest('.pap-category').classList.toggle('pap-expanded')">
          <span class="pap-cat-num pap-cat-num-suppressed">🔒</span>
          <span class="pap-cat-label">Policy-Suppressed Actions</span>
          <span class="pap-cat-count">${cat5.length} holding${cat5.length !== 1 ? "s" : ""}</span>
          <span class="pap-cat-chevron">▾</span>
        </div>
        <div class="pap-cat-body">
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:8px;padding:6px 0;border-bottom:1px solid var(--border)">
            These positions have intelligence signals that would normally trigger action,
            but are blocked by operator policy. No execution action should be taken.
            Intelligence is preserved for monitoring purposes only.
          </div>
          <table class="pap-tbl">
            <thead><tr>
              <th>Symbol</th><th>ESS Signal</th><th>Original Action</th>
              <th>Policy</th><th>Effective Action</th><th>Score</th><th>% Port</th>
            </tr></thead>
            <tbody>
              ${cat5.map(c => `<tr class="pap-row pap-row-suppressed">
                <td><span class="pap-sym">${escHtml(c.symbol)}</span></td>
                <td><span class="ess-badge ess-${escHtml(c.ess || c.signal)}">${escHtml(c.ess || c.signal)}</span></td>
                <td><span class="flag-${escHtml(c.original_action)}">${escHtml(c.original_action || "—")}</span></td>
                <td><span class="policy-badge ${_policyBadgeClass(c.policy_type)}">${escHtml(c.policy_badge || c.policy_type)}</span></td>
                <td><span class="pap-exec-action pap-exec-BLOCKED_BY_POLICY">${escHtml(c.effective_action)}</span></td>
                <td>${c.composite_score.toFixed(2)}</td>
                <td>${c.percent_of_portfolio.toFixed(2)}%</td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`);
  }

  container.innerHTML = html.join("\n");

  // Re-render strategic exit chips (they live inside Cat 2's HTML)
  _renderStrategicExitList();
}

// ─────────────────────────────────────────────────────────────────────────────
// Master render
// ─────────────────────────────────────────────────────────────────────────────
function renderResults(data) {
  document.getElementById("resultsArea").style.display = "block";
  _lastAnalysisData = data;  // Phase E: make STI profiles available to card helpers
  loadMarketRegimeGuardrail(data);
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
  renderPortfolioActionPipeline(data);
}

async function loadMarketRegimeGuardrail(data) {
  const el = document.getElementById("marketContextContainer");
  if (!el) return;

  el.innerHTML = `
    <div id="marketRegimeCardSlot" class="mrg-card"><div class="mrg-loading">Loading market regime guardrail…</div></div>
    <div id="macroLiquidityCardSlot" class="mrg-card"><div class="mrg-loading">…</div></div>
  `;

  const regimeSlot = document.getElementById("marketRegimeCardSlot");
  const macroSlot = document.getElementById("macroLiquidityCardSlot");

  try {
    const runId = (data && data.run_id) ? String(data.run_id).trim() : "";
    const url = runId
      ? `/api/market-regime-guardrail/latest?run_id=${encodeURIComponent(runId)}`
      : "/api/market-regime-guardrail/latest";

    const resp = await fetch(url);
    const payload = await resp.json();
    if (!resp.ok || !payload || typeof payload !== "object") {
      throw new Error("guardrail payload unavailable");
    }
    if (regimeSlot) regimeSlot.outerHTML = renderMarketRegimeGuardrailCard(payload);
  } catch (_) {
    if (regimeSlot) regimeSlot.outerHTML = renderMarketRegimeGuardrailCard({
      regime: "UNKNOWN",
      severity: "LOW",
      deployment_posture: "CAUTION_DEPLOY",
      trim_posture: "REVIEW_OVERWEIGHTS",
      cash_posture: "HOLD_EXCESS",
      operator_summary: "Market regime guardrail unavailable. Use conservative display-only posture.",
      evidence: ["Endpoint unavailable."],
      recommended_operator_checks: [
        "Confirm proxy freshness before changing posture.",
        "Use conservative deployment discipline until data recovers.",
      ],
      data_freshness: {
        market_proxies_ts: null,
        portfolio_snapshot_ts: null,
        freshness_status: "UNKNOWN",
        proxy_lag_days: null,
        freshness_threshold_days: 2,
        operator_action: "VERIFY_TIMESTAMP_FORMATS",
      },
      confidence: "LOW",
      safe_to_deploy: false,
      scoring_impact: "none",
    });
  }

  try {
    const runId = (data && data.run_id) ? String(data.run_id).trim() : "";
    const url = runId
      ? `/api/portfolio/macro-liquidity-context?run_id=${encodeURIComponent(runId)}`
      : "/api/portfolio/macro-liquidity-context";
    const resp = await fetch(url);
    const payload = await resp.json();
    if (!resp.ok || !payload || typeof payload !== "object") {
      throw new Error("macro liquidity context unavailable");
    }
    if (macroSlot) macroSlot.outerHTML = renderMacroLiquidityContextCard(payload);
  } catch (_) {
    if (macroSlot) {
      macroSlot.outerHTML = renderMacroLiquidityContextCard({
        title: "Macro & Liquidity Context",
        subtitle: "Display-only confirmation of rates, credit, liquidity, volatility, breadth, and known event risk.",
        sections: {
          rates: [],
          credit_funding: [],
          liquidity: [],
          market_confirmation: { availability: "UNAVAILABLE" },
          event_window: { events: [], availability: "UNAVAILABLE", notes: ["Event calendar unavailable."] },
        },
        current_portfolio_posture: {
          regime: "UNKNOWN",
          safe_to_deploy: false,
          deployment: "CAUTION_DEPLOY",
          cash: "HOLD_EXCESS",
        },
        how_to_read_macro_stress: {
          lines: [
            "Rates rising alone = tighter financial conditions, but not systemic confirmation.",
            "Rates rising + credit widening = stronger stress confirmation.",
            "Rates rising + credit widening + funding/liquidity deterioration = materially stronger defensive evidence.",
            "Add deteriorating breadth / Momentum = market internals are confirming macro pressure.",
            "Stable credit + stable funding + improving breadth = macro narrative may not be translating into systemic market stress.",
          ],
        },
      });
    }
  }
}

function renderMarketRegimeGuardrailCard(g) {
  const regime = escHtml(g.regime || "UNKNOWN");
  const severity = escHtml(g.severity || "LOW");
  const confidence = escHtml(g.confidence || "LOW");
  const deploy = escHtml(g.deployment_posture || "CAUTION_DEPLOY");
  const trim = escHtml(g.trim_posture || "REVIEW_OVERWEIGHTS");
  const cash = escHtml(g.cash_posture || "HOLD_EXCESS");
  const summary = escHtml(g.operator_summary || "No market regime summary available.");
  const evidence = Array.isArray(g.evidence) ? g.evidence : [];
  const checks = Array.isArray(g.recommended_operator_checks) ? g.recommended_operator_checks : [];
  const freshness = g.data_freshness || {};
  const inputSourceRaw = String(g.input_source || "unknown");
  const inputSourceLabel = inputSourceRaw === "dedicated_market_regime_price_history"
    ? "Dedicated Market Regime Proxy"
    : (inputSourceRaw === "legacy_yahoo_snapshot_fallback"
      ? "Legacy Yahoo Snapshot Fallback"
      : (inputSourceRaw === "legacy_replay_fallback" ? "Legacy Replay Fallback" : inputSourceRaw));
  const marketTs = escHtml(freshness.market_proxies_ts || "unavailable");
  const snapTs = escHtml(freshness.portfolio_snapshot_ts || "unknown");
  const freshnessStatus = escHtml(freshness.freshness_status || "UNKNOWN");
  const lagRaw = (freshness.market_proxy_age_days === 0 || freshness.market_proxy_age_days)
    ? freshness.market_proxy_age_days
    : freshness.proxy_lag_days;
  const lagDays = (lagRaw === 0 || lagRaw)
    ? escHtml(String(lagRaw))
    : "unknown";
  const lagThreshold = (freshness.freshness_threshold_days === 0 || freshness.freshness_threshold_days)
    ? escHtml(String(freshness.freshness_threshold_days))
    : "2";
  const operatorAction = escHtml(freshness.operator_action || "VERIFY_TIMESTAMP_FORMATS");
  const actionRaw = String(freshness.operator_action || "").toUpperCase();
  const freshnessRaw = String(freshness.freshness_status || "").toUpperCase();
  const operatorGuidance = (actionRaw === "REFRESH_MARKET_PROXIES" || freshnessRaw === "STALE")
    ? "Run Refresh Current Holdings + Buy Candidates to refresh market-regime proxy inputs before reviewing posture changes."
    : "";
  const safeText = g.safe_to_deploy ? "Yes" : "No";

  return `
    <div class="mrg-card">
      <div class="mrg-header">
        <div class="mrg-title">Market Regime Guardrail</div>
        <span class="mrg-badge">Display-only</span>
      </div>
      <div class="mrg-warning">No automatic scoring, ranking, allocation, sizing, or execution changes</div>
      <div class="mrg-summary">${summary}</div>
      <div class="mrg-grid">
        <div><span class="mrg-k">Regime</span><span class="mrg-v">${regime}</span></div>
        <div><span class="mrg-k">Severity</span><span class="mrg-v">${severity}</span></div>
        <div><span class="mrg-k">Confidence</span><span class="mrg-v">${confidence}</span></div>
        <div><span class="mrg-k">Safe to Deploy</span><span class="mrg-v">${safeText}</span></div>
        <div><span class="mrg-k">Deployment</span><span class="mrg-v">${deploy}</span></div>
        <div><span class="mrg-k">Trim</span><span class="mrg-v">${trim}</span></div>
        <div><span class="mrg-k">Cash</span><span class="mrg-v">${cash}</span></div>
        <div><span class="mrg-k">Scoring Impact</span><span class="mrg-v">${escHtml(g.scoring_impact || "none")}</span></div>
        <div><span class="mrg-k">Input Source</span><span class="mrg-v">${escHtml(inputSourceLabel)}</span></div>
      </div>
      <div class="mrg-freshness">Proxy TS: ${marketTs} · Portfolio TS: ${snapTs}</div>
      <div class="mrg-freshness">Freshness Status: ${freshnessStatus} · Lag: ${lagDays} day(s) · Threshold: ${lagThreshold}</div>
      <div class="mrg-freshness">Operator Action: ${operatorAction}</div>
      ${operatorGuidance ? `<div class="mrg-freshness">Action Guidance: ${escHtml(operatorGuidance)}</div>` : ""}
      ${evidence.length ? `<ul class="mrg-list">${evidence.slice(0, 4).map(e => `<li>${escHtml(String(e))}</li>`).join("")}</ul>` : ""}
      ${checks.length ? `<ul class="mrg-checks">${checks.slice(0, 4).map(c => `<li>${escHtml(String(c))}</li>`).join("")}</ul>` : ""}
    </div>
  `;
}

function _macroCell(v) {
  const raw = String(v == null ? "UNAVAILABLE" : v).trim();
  return escHtml(raw || "UNAVAILABLE");
}

function _macroIndicatorRowHtml(indicator) {
  const name = escHtml(String(indicator && indicator.name ? indicator.name : "UNAVAILABLE"));
  const value = _macroCell(indicator && indicator.current_value);
  const c1 = _macroCell(indicator && indicator.change_1d);
  const c5 = _macroCell(indicator && indicator.change_5d);
  const c20 = _macroCell(indicator && indicator.change_20d);
  const asOf = _macroCell(indicator && indicator.as_of);
  const freshness = _macroCell(indicator && indicator.freshness);
  const source = _macroCell(indicator && indicator.source);
  const provenance = _macroCell(indicator && indicator.provenance);
  const availability = _macroCell(indicator && indicator.availability);
  const note = _macroCell(indicator && indicator.note);

  return `
    <tr>
      <td>${name}</td>
      <td>${value}</td>
      <td>${c1}</td>
      <td>${c5}</td>
      <td>${c20}</td>
      <td>${asOf}</td>
      <td>${freshness}</td>
      <td>${source}</td>
      <td>${provenance}</td>
      <td>${availability}</td>
      <td>${note}</td>
    </tr>
  `;
}

function _macroUnavailableRowHtml(indicator) {
  const name = escHtml(String(indicator && indicator.name ? indicator.name : "UNAVAILABLE"));
  const availability = _macroCell(indicator && indicator.availability);
  const reason = _macroCell(indicator && indicator.note);
  const requiredSource = _macroCell(indicator && indicator.source);

  return `
    <tr class="mlc-row-unavailable">
      <td>${name}</td>
      <td colspan="10">
        <div><strong>Status:</strong> ${availability}</div>
        <div><strong>Reason:</strong> ${reason}</div>
        <div><strong>Required Source / Series:</strong> ${requiredSource}</div>
      </td>
    </tr>
  `;
}

function _macroTableHtml(title, rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  return `
    <div class="mlc-section">
      <div class="mlc-section-title">${escHtml(title)}</div>
      <div class="mlc-table-wrap">
        <table class="mlc-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Current Value</th>
              <th>Change 1D</th>
              <th>Change 5D</th>
              <th>Change 20D</th>
              <th>As Of</th>
              <th>Freshness</th>
              <th>Source</th>
              <th>Provenance</th>
              <th>Availability</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            ${safeRows.length ? safeRows.map((row) => {
              const availability = String((row && row.availability) || "").toUpperCase();
              return availability === "UNAVAILABLE" ? _macroUnavailableRowHtml(row) : _macroIndicatorRowHtml(row);
            }).join("") : `<tr><td colspan="11">UNAVAILABLE</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function _macroMarketConfirmationHtml(m) {
  const row = (k, v) => `<div><span class="mlc-k">${escHtml(k)}</span><span class="mlc-v">${_macroCell(v)}</span></div>`;
  const summaryRecency = (m && (m.summary_recency || m.freshness)) || "UNAVAILABLE";
  const evidence = (m && m.evidence_freshness) || {};
  const evidenceStatus = evidence.status || "UNAVAILABLE";
  const evidenceOldest = evidence.oldest_effective_date || "UNAVAILABLE";
  const evidenceNewest = evidence.newest_effective_date || "UNAVAILABLE";
  const coverage = (m && m.coverage) || {};
  const coverageState = coverage.state || (m && m.portfolio_momentum_condition) || "UNAVAILABLE";
  const coverageWeight = Number.isFinite(Number(coverage.evaluable_weight_pct))
    ? `${Number(coverage.evaluable_weight_pct).toFixed(2)}%`
    : "-";
  const coverageDisplay = coverageWeight === "-" ? coverageState : `${coverageState} (${coverageWeight})`;
  return `
    <div class="mlc-section">
      <div class="mlc-section-title">Market Confirmation</div>
      <div class="mlc-grid">
        ${row("Market State", m && m.market_state)}
        ${row("Broad Market Relative Level", m && m.broad_market_relative_level)}
        ${row("Broad Market Relative Change", m && m.broad_market_relative_change)}
        ${row("Broad Market Breadth", m && m.broad_market_breadth)}
        ${row("Fixed Income State", m && m.fixed_income_state)}
        ${row("Fixed Income Change", m && m.fixed_income_change)}
        ${row("Technology Breadth", m && m.technology_breadth)}
        ${row("Coverage", coverageDisplay)}
        ${row("As Of", m && m.as_of)}
        ${row("Summary Recency", summaryRecency)}
        ${row("Evidence Freshness", evidenceStatus)}
        ${row("Evidence Window", `${evidenceOldest} -> ${evidenceNewest}`)}
        ${row("Source", m && m.source)}
        ${row("Provenance", m && m.provenance)}
      </div>
      <div class="mlc-footnote">${_macroCell(m && m.note)}</div>
    </div>
  `;
}

function _macroEventWindowHtml(ev) {
  const rows = Array.isArray(ev && ev.events) ? ev.events : [];
  const notes = Array.isArray(ev && ev.notes) ? ev.notes : [];
  return `
    <div class="mlc-section">
      <div class="mlc-section-title">Event Window</div>
      <div class="mlc-table-wrap">
        <table class="mlc-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Date</th>
              <th>Mechanism</th>
              <th>Source</th>
              <th>Status</th>
              <th>Provenance</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map((r) => `
              <tr>
                <td>${_macroCell(r.event)}</td>
                <td>${_macroCell(r.date)}</td>
                <td>${_macroCell(r.mechanism)}</td>
                <td>${_macroCell(r.source)}</td>
                <td>${_macroCell(r.status)}</td>
                <td>${_macroCell(r.provenance)}</td>
              </tr>
            `).join("") : `<tr><td colspan="6">UNAVAILABLE</td></tr>`}
          </tbody>
        </table>
      </div>
      <div class="mlc-footnote">As Of: ${_macroCell(ev && ev.as_of)} · Window End: ${_macroCell(ev && ev.window_end)} · Source: ${_macroCell(ev && ev.source)}</div>
      ${notes.length ? `<ul class="mlc-notes">${notes.map((n) => `<li>${escHtml(String(n))}</li>`).join("")}</ul>` : ""}
      <div class="mlc-footnote">Large tax-payment dates can temporarily move cash into the Treasury General Account and tighten private-system liquidity. The event alone does not predict market direction.</div>
    </div>
  `;
}

function renderMacroLiquidityContextCard(payload) {
  const title = escHtml(String(payload && payload.title ? payload.title : "Macro & Liquidity Context"));
  const subtitle = escHtml(String(payload && payload.subtitle ? payload.subtitle : "Display-only confirmation of rates, credit, liquidity, volatility, breadth, and known event risk."));
  const sections = (payload && payload.sections) || {};
  const rates = Array.isArray(sections.rates) ? sections.rates : [];
  const creditFunding = Array.isArray(sections.credit_funding) ? sections.credit_funding : [];
  const liquidity = Array.isArray(sections.liquidity) ? sections.liquidity : [];
  const marketConfirmation = sections.market_confirmation || {};
  const eventWindow = sections.event_window || {};
  const posture = (payload && payload.current_portfolio_posture) || {};
  const guidance = (payload && payload.how_to_read_macro_stress) || {};
  const guidanceLines = Array.isArray(guidance.lines) ? guidance.lines : [];

  return `
    <div class="mlc-card">
      <div class="mlc-header">
        <div class="mlc-title">${title}</div>
        <span class="mlc-badge">Display-only</span>
      </div>
      <div class="mlc-subtitle">${subtitle}</div>
      <div class="mlc-warning">Narrative context only. No automatic scoring, recommendation, CW-DAS, deployment, allocation, or execution changes.</div>

      <div class="mlc-section">
        <div class="mlc-section-title">Current Portfolio Posture</div>
        <div class="mlc-grid">
          <div><span class="mlc-k">Regime</span><span class="mlc-v">${_macroCell(posture.regime)}</span></div>
          <div><span class="mlc-k">Safe to Deploy</span><span class="mlc-v">${posture.safe_to_deploy ? "Yes" : "No"}</span></div>
          <div><span class="mlc-k">Deployment</span><span class="mlc-v">${_macroCell(posture.deployment)}</span></div>
          <div><span class="mlc-k">Cash</span><span class="mlc-v">${_macroCell(posture.cash)}</span></div>
          <div><span class="mlc-k">Source</span><span class="mlc-v">${_macroCell(posture.source)}</span></div>
        </div>
      </div>

      ${_macroTableHtml("Rates", rates)}
      ${_macroTableHtml("Credit / Funding", creditFunding)}
      ${_macroTableHtml("Liquidity", liquidity)}
      ${_macroMarketConfirmationHtml(marketConfirmation)}
      ${_macroEventWindowHtml(eventWindow)}

      <div class="mlc-section">
        <div class="mlc-section-title">How to Read Macro Stress</div>
        <ul class="mlc-notes">
          ${guidanceLines.map((line) => `<li>${escHtml(String(line))}</li>`).join("")}
        </ul>
        <div class="mlc-footnote">${_macroCell(guidance.governance)}</div>
      </div>
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI strip
// ─────────────────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const el = document.getElementById("runSummary");
  const scoreRaw = _getAlignmentScore(data);
  const score = Number(scoreRaw);
  const scoreLabel = Number.isFinite(score) ? (score >= 0.85 ? "Strong" : score >= 0.65 ? "Moderate" : "Needs attention") : "Unavailable";
  const holdingCount = _getHoldingCount(data);
  const portfolioValue = _getPortfolioValue(data);
  const recommendationCount = _getRecommendationCount(data);
  const concTier = _getConcentrationLabel(data);
  const formatLabel = _getFormatLabel(data);

  el.innerHTML = `
    ${kpiCard(holdingCount != null ? String(holdingCount) : "—", "Holdings")}
    ${kpiCard(portfolioValue != null ? formatMV(portfolioValue) : "—", "Portfolio Value")}
    ${kpiCard(Number.isFinite(score) ? `${(score * 100).toFixed(0)}%` : "—", "Legacy Alignment", scoreLabel)}
    ${kpiCard(recommendationCount != null ? String(recommendationCount) : "—", "Recommendations")}
    ${kpiCard(concTier, "Concentration", "", `tier-${concTier}`)}
    ${kpiCard(formatLabel, "Format")}
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

  const overlays = Array.isArray(data.security_overlays) ? data.security_overlays : [];
  const replaySupported = overlays.filter(o => o.replay_supported === true || o.replay_supported === "True");
  const replayPercentiles = overlays.filter(o => o.replay_percentile != null && String(o.replay_percentile).trim() && !["None","null","nan","N/A"].includes(String(o.replay_percentile).trim()));
  const replayAvailableExplicit = Object.prototype.hasOwnProperty.call(mds, "replay_alignment_available")
    ? Boolean(mds.replay_alignment_available)
    : (replaySupported.length > 0 && replayPercentiles.length > 0);

  const dims = [
    { key: "allocation_alignment_score",   label: "Allocation Alignment",   tooltip: "Distance from target model allocations" },
    { key: "portfolio_quality_score",      label: "Portfolio Quality",       tooltip: "Concentration, signal quality, strategic classification" },
    { key: "implementation_quality_score", label: "Implementation Quality",  tooltip: "Vehicle suitability and operational integrity" },
    { key: "replay_alignment_score",       label: "Replay Alignment",        tooltip: "Replay-supported exposure coverage and quality" },
  ];

  const cards = dims.map(d => {
    const raw = parseFloat(mds[d.key] ?? 0);
    const isReplay = d.key === "replay_alignment_score";
    const showUnavailable = isReplay && !replayAvailableExplicit;
    const pct = Math.min(100, Math.max(0, raw));
    const color = pct >= 75 ? "var(--green)" : pct >= 50 ? "var(--accent-2)" : "var(--sev-high)";
    const label = showUnavailable ? "Unavailable" : (pct >= 75 ? "Strong" : pct >= 50 ? "Moderate" : "Needs attention");
    const displayValue = showUnavailable ? "Unavailable" : `${pct.toFixed(0)}`;
    return `<div class="multidim-card" title="${escHtml(d.tooltip)}">
      <div class="multidim-score" style="color:${showUnavailable ? "var(--muted)" : color}">${displayValue}</div>
      <div class="multidim-label">${d.label}</div>
      <div class="multidim-sublabel">${label}</div>
      <div class="multidim-track">
        <div class="multidim-fill" style="width:${showUnavailable ? "100" : pct.toFixed(0)}%;background:${showUnavailable ? "var(--muted)" : color}"></div>
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

  const mandateDisplay = _getMandateLabel(data);
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
  const overallRaw = _getAlignmentScore(_analysisResult);
  const overall = Number.isFinite(Number(overallRaw)) ? Number(overallRaw) : 0;
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

    // Phase 23.5 — Block Diagnostics + Next Best Action panel
    // Replaces the old simple banner for MANDATE_BLOCKED / NO_CANDIDATES cases.
    const blockDiagnosticsHtml = _renderBlockDiagnosticsPanel(r);

    // Drill-down toggle button — only shown when drilldown data exists
    const dd = r.drilldown;
    const holdingCount = dd && dd.holdings ? dd.holdings.length : 0;
    const drillBtn = holdingCount > 0
      ? `<button class="drill-toggle" id="drill-toggle-${r.recommendation_id}"
           onclick="toggleDrilldown('${r.recommendation_id}')">▼ View ${holdingCount} Holdings</button>`
      : "";

    const recType = r.recommendation_type || "";
    const isPhaseE = _PHASE_E_TYPES.has(recType);

    // Phase 22D.2 WS-C: Legacy simple banner kept only for NON-INCREASE_UNDERWEIGHT blocked recs.
    // For INCREASE_UNDERWEIGHT, the full Block Diagnostics panel (blockDiagnosticsHtml) is used.
    let blockedWarningHtml = "";
    if (recType !== "INCREASE_UNDERWEIGHT" && r.optimizer_metadata) {
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
      ${blockDiagnosticsHtml}
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
// Phase 23.5 — Block Diagnostics + Next Best Action panel
// Presentation-layer only. No optimizer scores, CW-DAS scores, or mandate
// logic is modified. All functions are additive display helpers.
// ─────────────────────────────────────────────────────────────────────────────

function _buildNextBestAction(rec) {
  // Returns an NBA object or null if not applicable.
  const om      = rec.optimizer_metadata || {};
  const decision = om.optimizer_decision || "";
  const recType  = rec.recommendation_type || "";

  if (recType !== "INCREASE_UNDERWEIGHT") return null;
  if (decision !== "MANDATE_BLOCKED" && decision !== "NO_CANDIDATES") return null;

  const targetNode  = om.target_node || "";
  const mandateType = om.mandate_type || "";
  const concTol     = om.concentration_tolerance;

  // Pull deployment queue from shared analysis result (set before renderRecommendations)
  const dqEntries = (
    _lastAnalysisData &&
    _lastAnalysisData.deployment_queue &&
    _lastAnalysisData.deployment_queue.queue
  ) || [];

  // Filter to candidates whose allocation_node matches the target node
  let alternatives = dqEntries.filter(e => {
    const eNode = (e.allocation_node || "").toUpperCase();
    const tNode = targetNode.toUpperCase();
    return eNode === tNode || eNode.startsWith(tNode + ".");
  });
  const nodeFiltered = alternatives.length > 0;
  // Fallback: top-5 overall if no node-matched candidates
  if (!nodeFiltered) alternatives = dqEntries.slice(0, 5);
  alternatives = alternatives.slice(0, 5);

  if (decision === "MANDATE_BLOCKED") {
    const tolStr = concTol != null ? (concTol * 100).toFixed(0) + "%" : "—";
    return {
      priority:     "HIGH",
      headline:     "Mandate Block — INTENTIONAL_UNDERWEIGHT",
      reason:       `Active mandate (${mandateType || "—"}) classifies this underweight as intentional at ` +
                    `${tolStr} concentration tolerance. No deployment action is currently warranted.`,
      action:       alternatives.length
        ? "Deploy capital into top-ranked equity candidates in this node instead of legacy ETF vehicles."
        : "No deployment queue candidates match this node. Review mandate parameters or widen portfolio coverage.",
      alternatives,
      nodeFiltered,
      blockerType: "MANDATE_BLOCKED",
    };
  } else {
    // NO_CANDIDATES — all ETF vehicles failed optimizer gates
    const failedEtfs = (om.candidates || []).filter(
      c => c.candidate_type === "ETF" && !String(c.etf_gate || "").startsWith("PASS")
    );
    const failSyms = failedEtfs.map(c => c.symbol).join(", ") || "—";
    return {
      priority:    "MEDIUM",
      headline:    "ETF Gate Failure — No Actionable Vehicle",
      reason:      `All implementation vehicles failed optimizer gates: ${failSyms}.`,
      action:      alternatives.length
        ? "Consider direct equity deployment into top-ranked candidates in this node from the deployment queue."
        : "No deployment queue candidates found for this node. Review portfolio coverage gaps.",
      alternatives,
      nodeFiltered,
      blockerType: "NO_CANDIDATES",
    };
  }
}

function _renderBlockDiagnosticsPanel(rec) {
  const om      = rec.optimizer_metadata || {};
  const decision = om.optimizer_decision || "";
  const recType  = rec.recommendation_type || "";

  if (recType !== "INCREASE_UNDERWEIGHT") return "";
  if (decision !== "MANDATE_BLOCKED" && decision !== "NO_CANDIDATES") return "";

  const nba = _buildNextBestAction(rec);
  if (!nba) return "";

  const panelId     = `nba-panel-${rec.recommendation_id}`;
  const priorityCls = `nba-priority-${nba.priority.toLowerCase()}`;

  // Alternatives table rows
  const altRows = nba.alternatives.length
    ? nba.alternatives.map((e, idx) => {
        const tier     = e.narrative_tier || "—";
        const score    = typeof e.deployment_score === "number" ? e.deployment_score.toFixed(2) : "—";
        const headroom = typeof e.headroom_pct     === "number" ? e.headroom_pct.toFixed(0) + "%" : "—";
        const policy   = e.policy_annotation
          ? `<span class="nba-policy-tag">${escHtml(e.policy_annotation)}</span>`
          : "";
        const tierShort = tier === "CORE_CONVICTION_LEADER" ? "CCL"
                        : tier === "HIGH_CONVICTION_ANCHOR"  ? "HCA"
                        : tier;
        const tierCls   = tier === "CORE_CONVICTION_LEADER" ? "nba-tier-ccl"
                        : tier === "HIGH_CONVICTION_ANCHOR"  ? "nba-tier-hca"
                        : "nba-tier-tgc";
        return `<tr class="nba-alt-row">
          <td class="nba-alt-rank">#${idx + 1}</td>
          <td class="nba-alt-sym"><strong>${escHtml(e.symbol || "—")}</strong></td>
          <td class="nba-alt-tier"><span class="nba-tier-badge ${tierCls}">${escHtml(tierShort)}</span></td>
          <td class="nba-alt-score">${score}</td>
          <td class="nba-alt-headroom">${headroom}</td>
          <td>${policy}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="6" class="nba-alt-empty">No deployment queue candidates available for this node.</td></tr>`;

  const nodeNote = !nba.nodeFiltered
    ? `<div class="nba-caveat">⚠ No node-matched candidates found — showing top-ranked portfolio alternatives.</div>`
    : "";

  const evidenceHtml  = _buildBlockEvidence(rec);
  const howToHtml     = _buildBlockHowToUnblock(rec);

  return `<div class="nba-block-panel ${priorityCls}" id="${panelId}">
    <div class="nba-panel-header">
      <span class="nba-header-icon">⊘</span>
      <span class="nba-header-label">${escHtml(nba.headline)}</span>
      <span class="nba-header-priority">${escHtml(nba.priority)}</span>
    </div>
    <div class="nba-panel-body">
      <div class="nba-reason">${escHtml(nba.reason)}</div>
      <div class="nba-action-label">Next Best Action</div>
      <div class="nba-action-text">${escHtml(nba.action)}</div>
      ${nba.alternatives.length ? `<div class="nba-alternatives-section">
        <div class="nba-section-title">Deployment Queue Alternatives</div>
        ${nodeNote}
        <table class="nba-alternatives-table">
          <thead><tr>
            <th></th><th>Symbol</th><th>Tier</th><th>CW-DAS</th><th>Headroom</th><th>Policy</th>
          </tr></thead>
          <tbody>${altRows}</tbody>
        </table>
      </div>` : ""}
      ${evidenceHtml}
      ${howToHtml}
    </div>
  </div>`;
}

function _buildBlockEvidence(rec) {
  const om          = rec.optimizer_metadata || {};
  const decision    = om.optimizer_decision || "";
  const mandateType = om.mandate_type || "";
  const concTol     = om.concentration_tolerance;
  const targetNode  = om.target_node || "";
  const legVehicles = (om.legacy_vehicles || []).join(", ") || "—";
  const candidates  = om.candidates || [];

  const rows = [];
  rows.push(`<tr><td class="ev-label">Target Node</td><td class="ev-val">${escHtml(targetNode || "—")}</td></tr>`);
  rows.push(`<tr><td class="ev-label">Legacy Vehicles</td><td class="ev-val">${escHtml(legVehicles)}</td></tr>`);

  if (decision === "MANDATE_BLOCKED" && mandateType) {
    rows.push(`<tr><td class="ev-label">Active Mandate</td><td class="ev-val">${escHtml(mandateType)}</td></tr>`);
    if (concTol != null) {
      rows.push(`<tr><td class="ev-label">Concentration Tolerance</td><td class="ev-val">${(concTol * 100).toFixed(0)}%</td></tr>`);
    }
    rows.push(`<tr><td class="ev-label">Block Reason</td><td class="ev-val">INTENTIONAL_UNDERWEIGHT — mandate treats this gap as within policy bounds.</td></tr>`);
  }

  const failedEtfs = candidates.filter(
    c => c.candidate_type === "ETF" && !String(c.etf_gate || "").startsWith("PASS")
  );
  if (failedEtfs.length) {
    const etfDetail = failedEtfs.map(c => {
      const gateReason = String(c.etf_gate || "").replace(/^FAIL\s*\[?/, "").replace(/\]$/, "");
      const ncsStr     = c.ncs != null ? ` · NCS ${Number(c.ncs).toFixed(1)}%` : "";
      const owStr      = c.worsens_overweight ? " · ⚠ worsens OW" : "";
      return `${escHtml(c.symbol)}: ${escHtml(gateReason)}${ncsStr}${owStr}`;
    }).join("<br>");
    rows.push(`<tr><td class="ev-label">ETF Gate Failures</td><td class="ev-val">${etfDetail}</td></tr>`);
  }

  if (om.ow_node_key) {
    rows.push(`<tr><td class="ev-label">Overweight Node</td><td class="ev-val">${escHtml(om.ow_node_key)}</td></tr>`);
  }
  if (om.overlap_with_ow_pct) {
    rows.push(`<tr><td class="ev-label">OW Overlap</td><td class="ev-val">${Number(om.overlap_with_ow_pct).toFixed(1)}% of ETF exposure lands in overweight node</td></tr>`);
  }

  if (!rows.length) return "";

  const evId = `nba-ev-${rec.recommendation_id}`;
  return `<div class="nba-collapsible-section">
    <button class="nba-section-toggle" onclick="toggleNbaSection('${evId}')">&#9658; Block Evidence</button>
    <div class="nba-section-body" id="${evId}" style="display:none">
      <table class="nba-evidence-table"><tbody>${rows.join("")}</tbody></table>
    </div>
  </div>`;
}

function _buildBlockHowToUnblock(rec) {
  const om       = rec.optimizer_metadata || {};
  const decision = om.optimizer_decision || "";
  const mandate  = om.mandate_type || "UNKNOWN";

  let steps = [];
  if (decision === "MANDATE_BLOCKED") {
    steps = [
      `Review whether the active mandate (${mandate}) remains appropriate for current portfolio objectives.`,
      "If the underweight represents a genuine gap, change the mandate type to one with lower concentration tolerance.",
      "Alternatively, deploy directly into equities within the target node — deployment queue provides ranked candidates above.",
      "Legacy ETF vehicles remain held; no forced action is required by this block.",
    ];
  } else {
    steps = [
      "ETF vehicles for this node are blocked due to overweight worsening, NCS below threshold, or LOW suitability.",
      "Use the deployment queue alternatives above to identify direct equity opportunities in the target node.",
      "If concentration is reduced (via trimming overweight positions), ETF gates may pass in a future run.",
      "No action is required — this is a guidance flag, not a trade mandate.",
    ];
  }

  const howId = `nba-how-${rec.recommendation_id}`;
  return `<div class="nba-collapsible-section">
    <button class="nba-section-toggle" onclick="toggleNbaSection('${howId}')">&#9658; How to Unblock</button>
    <div class="nba-section-body" id="${howId}" style="display:none">
      <ol class="nba-unblock-list">
        ${steps.map(s => `<li>${escHtml(s)}</li>`).join("")}
      </ol>
    </div>
  </div>`;
}

function toggleNbaSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const isOpen = el.style.display !== "none";
  el.style.display = isOpen ? "none" : "block";
  const btn = el.previousElementSibling;
  if (btn) {
    const label = btn.textContent.slice(2);
    btn.innerHTML = (isOpen ? "&#9658; " : "&#9660; ") + label;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7.5C — Capital Deployment Queue
// ─────────────────────────────────────────────────────────────────────────────

// State for view-all toggle and breakdown expansion
let _dqShowAll = false;
const DQ_DEFAULT_ROWS = 10;
let _dqMomentumBySymbol = null;
let _dqTrendBySymbol = null;
let _dqMomentumMeta = null;
let _dqMomentumFetchInFlight = false;
let _dqMomentumStatus = "idle";

function _dqMomentumParDate(data) {
  const v = _safeVersionedValue(data || {}, "snapshot_date");
  const s = v != null ? String(v).trim() : "";
  return s || null;
}

function _dqMomentumContextKey(data) {
  const runId = String((data && data.run_id) || "").trim() || "NO_RUN_ID";
  const parDate = _dqMomentumParDate(data) || "NO_PAR_DATE";
  return `${runId}|${parDate}`;
}

function _dqMomentumConfidence(row) {
  const horizons = (((row || {}).absolute_security_momentum || {}).horizons) || {};
  for (const h of ["1M", "3M", "1W", "6M", "12M"]) {
    const c = horizons[h] && horizons[h].confidence;
    if (c && c !== "UNAVAILABLE") return String(c);
  }
  return "UNAVAILABLE";
}

function _dqMomentumAsOf(row) {
  const horizons = (((row || {}).absolute_security_momentum || {}).horizons) || {};
  const dates = [];
  for (const h of ["1W", "1M", "3M", "6M", "12M"]) {
    const d = horizons[h] && horizons[h].as_of_date;
    if (d) dates.push(String(d));
  }
  if (!dates.length) return "UNAVAILABLE";
  dates.sort();
  return dates[dates.length - 1];
}

function _dqMomentumState(row) {
  if (!row || typeof row !== "object") return "UNAVAILABLE";
  const abs = String((((row.absolute_security_momentum || {}).state) || "")).toUpperCase();
  if (abs && abs !== "UNAVAILABLE") return abs;
  const rel = String(row.relative_momentum_change || "").toUpperCase();
  return rel || "UNAVAILABLE";
}

function _dqMomentumLevel(row) {
  if (!row || typeof row !== "object") return "UNAVAILABLE";
  const level = String((((row.absolute_security_momentum || {}).state) || "")).toUpperCase();
  return level || "UNAVAILABLE";
}

function _dqMomentumChange(row) {
  if (!row || typeof row !== "object") return "UNAVAILABLE";
  const change = String(row.relative_momentum_change || "").toUpperCase();
  return change || "UNAVAILABLE";
}

function _dqMomentumDisplayField(value) {
  const v = String(value || "").toUpperCase();
  return (v && v !== "UNAVAILABLE") ? v : "—";
}

function _dqTimingPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (n > 0) return `+${n.toFixed(1)}%`;
  if (n < 0) return `${n.toFixed(1)}%`;
  return "0.0%";
}

function _dqTrendCompactDisplay(trend) {
  if (!trend || typeof trend !== "object") return "UNAVAILABLE";
  const historyStatus = String(trend.history_status || "UNAVAILABLE").toUpperCase();
  if (historyStatus.startsWith("INSUFFICIENT_")) {
    return "50D — · 200D —";
  }
  if (historyStatus !== "AVAILABLE") {
    return "UNAVAILABLE";
  }
  const v50 = _dqTimingPct(trend.price_vs_sma50_pct);
  const v200 = _dqTimingPct(trend.price_vs_sma200_pct);
  return `50D ${v50} · 200D ${v200}`;
}

function _dqMomentumBadge(symbol) {
  if (_dqMomentumStatus === "loading" || _dqMomentumStatus === "idle") {
    return `<span class="dq-status" title="Momentum context is loading.">…</span>`;
  }

  if (_dqMomentumStatus === "unavailable" && _dqMomentumMeta && _dqMomentumMeta.compatible === false) {
    const parDate = _dqMomentumMeta.par_portfolio_date || "UNAVAILABLE";
    const momDate = _dqMomentumMeta.snapshot_date || "UNAVAILABLE";
    const tooltip = `Momentum unavailable for this run due to provenance mismatch.\nPAR portfolio date: ${parDate}\nMomentum snapshot date: ${momDate}\n\nMomentum is timing/confirmation context only and does not affect CW-DAS ranking or allocation.`;
    return `<span class="dq-status dq-status-OW_NODE" title="${escHtml(tooltip)}">UNAVAILABLE</span>`;
  }

  if (_dqMomentumStatus === "unavailable") {
    return `<span class="dq-status dq-status-OW_NODE" title="Momentum unavailable for current symbol in canonical momentum summary.">UNAVAILABLE</span>`;
  }

  const trend = _dqTrendBySymbol && _dqTrendBySymbol[String(symbol || "").toUpperCase()];
  if (trend && typeof trend === "object") {
    const historyStatus = String(trend.history_status || "UNAVAILABLE").toUpperCase();
    const currentness = String(trend.currentness_state || trend.freshness_status || "MISSING").toUpperCase();
    const asOf = String(trend.latest_price_date || "UNAVAILABLE");
    const latestPrice = trend.latest_price != null ? Number(trend.latest_price).toFixed(4) : "UNAVAILABLE";
    const sma50 = trend.sma50 != null ? Number(trend.sma50).toFixed(4) : "UNAVAILABLE";
    const sma200 = trend.sma200 != null ? Number(trend.sma200).toFixed(4) : "UNAVAILABLE";
    const d50 = _dqTimingPct(trend.price_vs_sma50_pct);
    const d200 = _dqTimingPct(trend.price_vs_sma200_pct);
    const c50 = _dqTimingPct(trend.sma50_change_20d_pct);
    const c200 = _dqTimingPct(trend.sma200_change_20d_pct);
    const source = String(trend.source || trend.provenance || "UNAVAILABLE");
    const display = _dqTrendCompactDisplay(trend);
    const cls = historyStatus === "AVAILABLE" ? "dq-status-DEPLOYABLE" : "dq-status-OW_NODE";
    const tooltip = `Trend Structure\n\nvs 50DMA: ${d50}\nvs 200DMA: ${d200}\n50DMA 20D: ${c50}\n200DMA 20D: ${c200}\nPrice data: ${currentness}\nAs of: ${asOf}\nHistory: ${historyStatus}\nLatest price: ${latestPrice}\nSMA50: ${sma50}\nSMA200: ${sma200}\nSource: ${source}\n\n50DMA and 200DMA are reporting-only timing context.\nThey do not alter SIH scores, rankings, recommendations,\nallocation, or deployment eligibility.`;
    return `<span class="dq-status ${cls}" title="${escHtml(tooltip)}">${escHtml(display)}</span>`;
  }

  const momentumRow = _dqMomentumBySymbol && _dqMomentumBySymbol[String(symbol || "").toUpperCase()];
  if (!momentumRow) {
    return `<span class="dq-status dq-status-OW_NODE" title="Momentum unavailable for current symbol in canonical momentum summary.">UNAVAILABLE</span>`;
  }

  const level = _dqMomentumLevel(momentumRow);
  const change = _dqMomentumChange(momentumRow);
  const state = _dqMomentumState(momentumRow);
  const confirmation = String(momentumRow.confirmation_state || "UNAVAILABLE");
  const extension = String(momentumRow.extension_state || "UNAVAILABLE");
  const trajectory = String(momentumRow.relative_momentum_change || "UNAVAILABLE");
  const confidence = _dqMomentumConfidence(momentumRow);
  const asOf = _dqMomentumAsOf(momentumRow);
  const provenance = String(momentumRow.history_label || momentumRow.evaluation_status || ((_dqMomentumMeta || {}).provenance) || "UNAVAILABLE");

  const isPositiveLevel = ["STRONG", "IMPROVING", "POSITIVE"].includes(level);
  const isNegativeLevel = ["WEAK", "WEAKENING", "NEGATIVE"].includes(level);
  const isDeterioratingChange = ["FADING", "WEAKENING", "NEGATIVE", "REVERSING"].includes(change);
  const hasLevel = level !== "UNAVAILABLE";
  const hasChange = change !== "UNAVAILABLE";
  const cls = (!hasLevel && !hasChange)
    ? "dq-status-OW_NODE"
    : ((isPositiveLevel && !isDeterioratingChange)
      ? "dq-replay-yes"
      : (isNegativeLevel ? "dq-replay-no" : "dq-status-DEPLOYABLE"));

  const compactDisplay = `${_dqMomentumDisplayField(level)} · ${_dqMomentumDisplayField(change)}`;

  const tooltip = `State is the canonical relative-strength level selected from available relative context; Change is the canonical relative-momentum change. State is not necessarily market-relative.\n\nMomentum State: ${level}\nMomentum Change: ${change}\nExtension: ${extension}\nConfirmation: ${confirmation}\nConfidence: ${confidence}\nAs-of: ${asOf}\nProvenance: ${provenance}\nTrajectory: ${trajectory}\n\nMomentum is timing/confirmation context only and does not affect CW-DAS ranking or allocation.`;
  return `<span class="${cls}" title="${escHtml(tooltip)}">${escHtml(compactDisplay)}</span>`;
}

function _dqEnsureMomentumContext(queueForRender, tbodyId) {
  if (_dqMomentumStatus === "ready" && _dqMomentumBySymbol) return;
  if (_dqMomentumStatus === "unavailable") return;
  if (_dqMomentumFetchInFlight) return;
  _dqMomentumFetchInFlight = true;
  _dqMomentumStatus = "loading";
  const contextKey = (_dqMomentumMeta && _dqMomentumMeta.context_key) || _dqMomentumContextKey(_analysisResult || {});

  const rerender = () => {
    if (Array.isArray(queueForRender)) {
      const limit = _dqShowAll ? queueForRender.length : DQ_DEFAULT_ROWS;
      _dqRenderTableRows(queueForRender, tbodyId || "dq-queue-table-body", limit);
      return;
    }
    const dq = _analysisResult && _analysisResult.deployment_queue;
    if (dq && Array.isArray(dq.queue)) {
      const limit = _dqShowAll ? dq.queue.length : DQ_DEFAULT_ROWS;
      _dqRenderTableRows(dq.queue, "dq-queue-table-body", limit);
    }
  };

  fetch("/api/pis/momentum/summary")
    .then(resp => resp.ok ? resp.json() : Promise.resolve(null))
    .then(summary => {
      const parDate = _dqMomentumParDate(_analysisResult);
      const momDateRaw = summary && summary.snapshot_date != null ? String(summary.snapshot_date).trim() : "";
      const momDate = momDateRaw || null;
      const compatible = !!parDate && !!momDate && parDate === momDate;

      const rows = (((summary || {}).portfolio_momentum_map || {}).holdings) || [];
      const trendRows = (((summary || {}).entry_timing_context || {}).holdings) || [];
      const map = {};
      const trendMap = {};
      if (compatible) {
        for (const row of rows) {
          const sym = String((row || {}).symbol || "").trim().toUpperCase();
          if (!sym) continue;
          map[sym] = row;
        }
        for (const row of trendRows) {
          const sym = String((row || {}).symbol || "").trim().toUpperCase();
          const trend = row && row.trend_structure_context;
          if (!sym || !trend || typeof trend !== "object") continue;
          trendMap[sym] = trend;
        }
        _dqMomentumStatus = "ready";
      } else {
        _dqMomentumStatus = "unavailable";
      }
      _dqMomentumBySymbol = map;
      _dqTrendBySymbol = trendMap;
      _dqMomentumMeta = {
        context_key: contextKey,
        snapshot_date: momDate,
        par_portfolio_date: parDate,
        generated_at_utc: (summary || {}).generated_at_utc || null,
        provenance: "CURRENT_RUNTIME",
        compatible,
      };
      rerender();
    })
    .catch(() => {
      _dqMomentumBySymbol = {};
      _dqTrendBySymbol = {};
      _dqMomentumStatus = "unavailable";
      _dqMomentumMeta = {
        context_key: contextKey,
        provenance: "UNAVAILABLE",
        par_portfolio_date: _dqMomentumParDate(_analysisResult),
        snapshot_date: null,
        compatible: false,
      };
      rerender();
    })
    .finally(() => {
      _dqMomentumFetchInFlight = false;
    });
}

function _dqEmptyStateHtml(data, dq, plan, queue) {
  const planRecs = plan.recommendations || [];
  const candidateCount = dq.candidate_count != null ? dq.candidate_count : queue.length;
  const queueRowCount = queue.length;
  const planRecommendationCount = planRecs.length;
  const preflight = data.analysis_preflight || {};
  const preflightStatus = preflight.status || (dq.suppressed_by_preflight ? "BLOCKED" : "DEGRADED");
  const reasonCodes = [];
  for (const code of (preflight.reason_codes || [])) reasonCodes.push(code);
  for (const code of (dq.preflight_reason_codes || [])) reasonCodes.push(code);
  for (const code of (plan.preflight_reason_codes || [])) reasonCodes.push(code);
  const uniqueReasonCodes = [...new Set(reasonCodes.filter(Boolean).map(code => String(code)))];
  const suppressedByPreflight = dq.suppressed_by_preflight != null
    ? dq.suppressed_by_preflight
    : (plan.suppressed_by_preflight != null ? plan.suppressed_by_preflight : null);

  const reasonHtml = uniqueReasonCodes.length > 0 ? `
    <div class="dq-empty-reason-block">
      <div class="dq-empty-reason-title">Gate summary</div>
      <div class="dq-empty-reason-chips">
        ${uniqueReasonCodes.map(code => `<span class="dq-empty-reason-chip">${escHtml(code)}</span>`).join("")}
      </div>
    </div>` : "";

  const suppressedHtml = suppressedByPreflight != null ? `
    <div class="dq-empty-field">
      <span class="dq-empty-field-label">Suppressed by preflight</span>
      <span class="dq-empty-field-value">${suppressedByPreflight ? "YES" : "NO"}</span>
    </div>` : "";

  return `<div class="dq-empty-state">
    <div class="dq-empty-state-lead">No canonical deployment candidates today.</div>
    <div class="dq-empty-state-sub">Reason: no securities currently satisfy the canonical deployment-eligibility gates.</div>
    <div class="dq-empty-metrics">
      <div class="dq-empty-metric">
        <span class="dq-empty-metric-label">Queue candidates</span>
        <span class="dq-empty-metric-value">${candidateCount}</span>
      </div>
      <div class="dq-empty-metric">
        <span class="dq-empty-metric-label">Queue rows</span>
        <span class="dq-empty-metric-value">${queueRowCount}</span>
      </div>
      <div class="dq-empty-metric">
        <span class="dq-empty-metric-label">Planned recommendations</span>
        <span class="dq-empty-metric-value">${planRecommendationCount}</span>
      </div>
      <div class="dq-empty-metric">
        <span class="dq-empty-metric-label">Preflight</span>
        <span class="dq-empty-metric-value">${escHtml(preflightStatus)}</span>
      </div>
      ${suppressedHtml}
    </div>
    ${reasonHtml}
    <div class="dq-empty-note">
      Portfolio Action Pipeline contains broader HOLD / WATCH / TRIM / allocation guidance and is separate from the ranked deployment queue.
      <a href="#portfolioActionPipelineSection">Jump to Portfolio Action Pipeline</a>.
    </div>
  </div>`;
}

function renderDeploymentQueue(data) {
  const el = document.getElementById("deploymentQueueContainer");
  if (!el) return;

  const dq = data.deployment_queue || {};
  const queue = Array.isArray(dq.queue) ? dq.queue : [];
  const plan = data.deployment_plan || {};
  const planRecs = plan.recommendations || [];
  const hasQueue = queue.length > 0;

  const momentumContextKey = _dqMomentumContextKey(data);
  const priorContextKey = (_dqMomentumMeta && _dqMomentumMeta.context_key) || null;
  if (priorContextKey !== momentumContextKey) {
    _dqMomentumBySymbol = null;
    _dqTrendBySymbol = null;
    _dqMomentumStatus = "idle";
    _dqMomentumMeta = {
      context_key: momentumContextKey,
      par_portfolio_date: _dqMomentumParDate(data),
      snapshot_date: null,
      generated_at_utc: null,
      provenance: "PENDING",
      compatible: false,
    };
  }

  if (!hasQueue) {
    el.innerHTML = `<div class="dq-panel">
      <div class="dq-section-header">
        <span class="dq-section-title">Top Trades to Consider</span>
        <span class="dq-version-badge">${escHtml(dq.queue_version || "CW-DAS-1.0")}</span>
        <span class="dq-advisory-note">Canonical deployment candidates · Guidance only</span>
      </div>
      ${_dqEmptyStateHtml(data, dq, plan, queue)}
    </div>`;
    return;
  }

  _dqShowAll = false;  // reset on each render

  const cashCtx = dq.cash_context || {};
  const top     = queue[0] || {};

  // Phase 7.5F — Build deployment plan lookup (available when plan is pre-loaded)
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
        <th>Momentum<br><span style="font-size:0.68rem;color:var(--muted);font-weight:600">State / Change</span></th>
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
      <span class="dq-section-title">Top Trades to Consider</span>
      <span class="dq-version-badge">${escHtml(dq.queue_version || "CW-DAS-1.0")}</span>
      <span class="dq-advisory-note">Canonical deployment candidates · Guidance only</span>
    </div>
    ${summaryHtml}
    ${cashContextHtml}
    ${cashSummaryHtml}
    <div class="da-action-section">
      <div class="da-action-section-header">Recommended Actions — Top 10</div>
      ${actionCardsHtml}
    </div>
    <div style="font-size:0.75rem;color:var(--muted);margin:6px 0 2px 0;">Momentum is timing/confirmation context only and does not affect CW-DAS ranking or allocation.</div>
    <div style="font-size:0.75rem;color:var(--muted);margin:2px 0 4px 0;">50DMA and 200DMA are reporting-only timing context. They do not alter SIH scores, rankings, recommendations, allocation, or deployment eligibility.</div>
    <details style="margin:6px 0 8px 0;font-size:0.75rem;color:var(--muted);">
      <summary style="cursor:pointer;color:var(--accent);font-weight:700;">How to Read Momentum (Buy-Timing Context)</summary>
      <div style="margin-top:6px;line-height:1.5;">
        <div><strong>State / Change field contract:</strong> First value is the canonical absolute momentum <strong>state</strong>; second value is canonical relative momentum <strong>change</strong>.</div>
        <div><strong>STRONG + IMPROVING</strong>: Strong leadership getting stronger. Most favorable buying confirmation when valuation, portfolio headroom, and other canonical evidence also agree.</div>
        <div><strong>STRONG + NEUTRAL/STABLE</strong>: Healthy leadership without improving slope. Selective buying, no urgency to chase.</div>
        <div><strong>STRONG + FADING/WEAKENING</strong>: Strong current leadership but deteriorating timing. Exercise caution on new buys and prefer pullback/reset or renewed improvement.</div>
        <div><strong>WEAK + IMPROVING</strong>: Early turn or improving setup, but leadership is not yet strong. Wait for confirmation or use greater caution.</div>
        <div><strong>WEAK + NEUTRAL/STABLE</strong>: Limited momentum support for a new entry.</div>
        <div><strong>WEAK + FADING/WEAKENING</strong>: Poor timing confirmation for a new buy.</div>
        <div><strong>EXTENDED</strong>: Increase chase-risk caution regardless of strong current leadership.</div>
        <div style="margin-top:4px;"><strong>Rule:</strong> Momentum should influence timing/aggressiveness, not underlying conviction.</div>
      </div>
    </details>
    ${tableHtml}
    ${blockedHtml}
    <div class="dp-generate-row">
      <button class="dp-generate-btn" id="dp-generate-btn" onclick="_dpGeneratePlan()">
        ↺ Recalculate with Custom Cash Amount
      </button>
      <span class="dp-generate-hint">Override: allocate custom amount instead of ${formatMV(_adjDeployableMv)}</span>
    </div>
  </div>`;

  // Render initial rows with explicit loading state while momentum context is in flight.
  _dqEnsureMomentumContext(queue, tableId);
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
      <td><span class="dq-rank-num${rankNumCls}">#${c.rank}${c.policy_rank_boost ? '<span title="Preferred Accumulation rank boost" style="font-size:0.7rem;margin-left:2px">⭐</span>' : ''}</span></td>
      <td><span class="dq-sym">${escHtml(c.symbol)}</span>${c.policy_annotation ? `<br><span class="${_policyBadgeClass(c.policy_type)}" style="margin-top:2px">${escHtml(c.policy_annotation)}</span>` : ''}</td>
      <td><span class="dq-score-val ${_dqScoreClass(score)}">${score.toFixed(1)}</span></td>
      <td><span class="dq-tier dq-tier-${tierShort}">${tierShort}</span></td>
      <td style="text-align:right;white-space:nowrap">${wtDisp}</td>
      <td style="text-align:right;font-weight:600">${c.composite_score != null ? parseFloat(c.composite_score).toFixed(2) : "—"}</td>
      <td>${_dqMomentumBadge(sym)}</td>
      <td><span class="${c.replay_supported ? "dq-replay-yes" : "dq-replay-no"}">${c.replay_supported ? "YES" : "NO"}</span></td>
      <td style="text-align:right">${addAmtDisp}</td>
      <td><span class="dq-status dq-status-${status}">${_dqStatusLabel(status)}</span></td>
    </tr>
    <tr class="dq-breakdown-row" id="${bdId}">
      <td colspan="10">
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
