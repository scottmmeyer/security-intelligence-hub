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

  // Phase 23.0A — load persisted tax state
  loadTaxState();

  // Phase 23.0C — load persisted strategic exits
  loadStrategicExits();

  // Phase 23.2 — load persisted operator policies
  loadOperatorPolicies();

  // Tax input live-compute
  ["taxNetRealizedYTD","taxPotentialLosses","taxCarryforward"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", updateTaxComputed);
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

// PRA-IMPL-05: FVI advisory badge HTML
function _fviBadgeHtml(fvi, showDetail = false) {
  if (!fvi || !fvi.fvi_tier) return "";
  const tier = fvi.fvi_tier;
  const badge = `<span class="fvi-badge fvi-${tier}" title="${escHtml(fvi.peer_group || "")}">FVI: ${tier}</span>`;
  if (!showDetail) return badge;
  const retainCls = fvi.retain_advisory ? "fvi-retain" : "fvi-reduce";
  const retainTxt = fvi.retain_advisory ? "↑ Retain preferred" : "↓ Reduction candidate";
  const detail = `<span class="fvi-detail">${escHtml(fvi.peer_group || "")} · <span class="${retainCls}">${retainTxt}</span></span>`;
  return badge + detail;
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
  // PRA-IMPL-05: FVI advisory data (keyed by uppercase symbol)
  const fviData        = data.fvi_data || {};

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

      // PA-004 FIX: Apply policy gate for Cat 3 (reduction context).
      // ov.policy_type is used directly because ov.execution_state reflects
      // the overlay's opportunity_flag context (e.g. HOLD → EXECUTABLE), not
      // the reduction context Cat 3 implies for every symbol here.
      const ovPolicyType3 = ov.policy_type || "";
      if (ovPolicyType3 === "DO_NOT_SELL") {
        // Block: add to cat5 for operator transparency
        cat5.push({
          symbol:           sym,
          ess:              ov.ess_score_text || "",
          signal:           ov.signal_direction || "",
          flag:             "REDUCE",
          original_action:  "REDUCE",
          policy_type:      ovPolicyType3,
          policy_badge:     ov.policy_annotation || "🔒 Operator Protected",
          effective_action: "MONITOR_ONLY",
          percent_of_portfolio: parseFloat(ov.percent_of_portfolio || 0),
          composite_score:      parseFloat(ov.composite_score || 0),
          source_lane: "cat3",
        });
        cat3Syms.add(sym);
        continue;
      }

      // SELL_LAST: include but deferred, tail-ranked
      const cat3ExecState = ovPolicyType3 === "SELL_LAST" ? "DEFERRED_BY_POLICY" : "EXECUTABLE";
      const cat3EffAction = ovPolicyType3 === "SELL_LAST" ? "REDUCE_SELL_LAST"   : "REDUCE";
      const cat3Priority  = ovPolicyType3 === "SELL_LAST" ? "LOW"
                          : (nodeSeverityScore >= 5 ? "HIGH" : "MEDIUM");

      // Include even protected tiers in allocation reduction (strategic context)
      // but mark them as protected so UI can render with appropriate context
      cat3Syms.add(sym);
      cat3.push({
        symbol:   sym,
        node_key:   node.nodeKey,
        node_label: node.nodeLabel,
        drift_pct:  node.drift,
        severity:   nodeSeverityScore >= 5 ? "HIGH" : "MEDIUM",
        priority:   cat3Priority,
        conviction_tier: tier,
        is_protected: _PROTECTED_CONVICTION_TIERS.has(tier),
        ov_flag:  ov.opportunity_flag || "",
        ov_signal: ov.signal_direction || "",
        percent_of_portfolio: parseFloat(ov.percent_of_portfolio || 0),
        composite_score:      parseFloat(ov.composite_score || 0),
        execution_state:  cat3ExecState,
        effective_action: cat3EffAction,
        policy_type:      ovPolicyType3,
        policy_badge:     ov.policy_annotation || "",
        fvi: fviData[sym] || null,  // PRA-IMPL-05: FVI advisory record
      });
    }
  }
  // Sort: DEFERRED_BY_POLICY last, then higher drift first, then alpha
  cat3.sort((a, b) => {
    const aDeferred = (a.execution_state === "DEFERRED_BY_POLICY") ? 1 : 0;
    const bDeferred = (b.execution_state === "DEFERRED_BY_POLICY") ? 1 : 0;
    if (aDeferred !== bDeferred) return aDeferred - bDeferred;
    return Math.abs(b.drift_pct) - Math.abs(a.drift_pct) || a.symbol.localeCompare(b.symbol);
  });

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

    // PA-004 FIX: Apply policy gate for Cat 4 (funding source context is always sell-context)
    const ovPolicyType4 = ov.policy_type || "";
    if (ovPolicyType4 === "DO_NOT_SELL") continue;  // Never a funding source
    const isLastResort = ovPolicyType4 === "SELL_LAST";  // Must be last priority

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
    const fundingReason = isCat1 ? "Signal Deterioration" : isCat3 ? "Allocation Reduction" : "Opportunity Cost";

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
      priority: isLastResort ? "LAST_RESORT" : (isCat1 ? "HIGH" : isCat3 ? "MEDIUM" : "LOW"),
      policy_type:  ovPolicyType4,
      policy_badge: ov.policy_annotation || "",
      fvi: fviData[sym] || null,  // PRA-IMPL-05: FVI advisory record
    });
  }
  // Sort: LAST_RESORT (SELL_LAST) always at end, then HIGH/MEDIUM/LOW, then score asc
  cat4.sort((a, b) => {
    const priorityOrder = { HIGH: 0, MEDIUM: 1, LOW: 2, LAST_RESORT: 3 };
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
              <th>Signal</th><th>% Port</th><th>Priority</th><th>FVI</th><th>Note</th>
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
                <td>${_fviBadgeHtml(c.fvi, true)}</td>
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
              <th>Score</th><th>% Port</th><th>Priority</th><th>FVI</th><th>Cross-Reference</th>
            </tr></thead>
            <tbody>
              ${cat4.map(c => `<tr class="pap-row ${c.priority === "HIGH" ? "pap-row-high" : c.priority === "MEDIUM" ? "pap-row-med" : ""}">
                <td><span class="pap-sym">${escHtml(c.symbol)}</span></td>
                <td><span class="flag-${escHtml(c.flag)}">${escHtml(c.flag || "—")}</span></td>
                <td>${c.signal ? `<span class="ess-badge ess-${escHtml(c.signal)}">${escHtml(c.signal)}</span>` : "—"}</td>
                <td>${c.composite_score.toFixed(2)}</td>
                <td>${c.percent_of_portfolio.toFixed(2)}%</td>
                <td><span class="pap-pri pap-pri-${c.priority}">${c.priority}</span></td>
                <td>${_fviBadgeHtml(c.fvi, false)}</td>
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
  renderKPIs(data);
  renderPortfolioConstructionStyle(data);   // UI Clarity Sprint — Problem 5
  renderMarketContext(data);                // MARKET-CONTEXT-01
  renderNarrativeSummary(data);      // UX-PA-09
  renderMultiDimScores(data);
  renderMandatePanel(data);
  renderReconciliationPanel(data);   // UX-PA-02
  renderDeploymentQueue(data);
  renderReductionQueuePlaceholder(); // ARCH-02: placeholder until CRA loads
  renderDislocationWatchlist(data);  // ISSUE-04C
  renderAllocationMap(data.alignment || []);
  renderConcentration(data.concentration || {});
  renderOptimizerSummary(data.recommendations || []);  // Phase 7.3B
  renderRecommendations(data.recommendations || []);
  renderReplayAlignment(data);
  renderSecurityOverlays(data.security_overlays || []);
  renderPortfolioActionPipeline(data);
  // Phase 23.6B — Capital Rotation Advisor (auto-load after analysis)
  loadCRAProposal();
  // Phase 8.0B.X — load company context metadata (non-blocking)
  _loadSecurityMetadata();
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
    ${kpiCard((score * 100).toFixed(0) + "%", "Allocation Alignment", scoreLabel)}
    ${_kpiTypedRecommendations(data.recommendations || [])}
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

// ─── PRA-IMPL-03: Lane count computation ─────────────────────────────────────

const _CONVICTION_ANCHOR_TYPES = new Set([
  "STRATEGIC_RETAIN_SIGNAL",
  "STRATEGIC_RETAIN_NARRATIVE",
  "CONVICTION_EXPLAINABILITY_CARD",
]);
const _NARRATIVE_TYPES = new Set([
  "PORTFOLIO_CONSTRUCTION_NARRATIVE",
  "THEMATIC_SATURATION_NARRATIVE",
]);
const _EXPLAINABILITY_TYPES = new Set([
  "REPLAY_ALIGNMENT_CONTEXT",
]);

function computeLaneCounts(recs) {
  let action = 0, blocked = 0, anchor = 0, narrative = 0, explainability = 0, observation = 0;
  for (const r of recs) {
    const ct  = r.card_type        || "DIAGNOSTIC";
    const es  = r.execution_state  || "EXECUTABLE";
    const rt  = r.recommendation_type || "";
    if (_CONVICTION_ANCHOR_TYPES.has(rt))  { anchor++; }
    else if (_NARRATIVE_TYPES.has(rt))     { narrative++; }
    else if (_EXPLAINABILITY_TYPES.has(rt)){ explainability++; }
    else if (ct === "ACTION") {
      if (es === "BLOCKED_BY_POLICY" || es === "DEFERRED_BY_POLICY") { blocked++; }
      else { action++; }
    } else { observation++; }
  }
  return { action, blocked, anchor, narrative, explainability, observation, total: recs.length };
}

function _kpiTypedRecommendations(recs) {
  const c = computeLaneCounts(recs);
  const chip = (num, label, cls) =>
    `<div class="rec-kpi-chip"><span class="chip-num ${cls}">${num}</span><span class="chip-label">${label}</span></div>`;
  return `<div class="kpi-card" style="min-width:220px;">
    <div class="kpi-label" style="margin-bottom:6px;font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted)">Recommendations</div>
    <div class="rec-kpi-typed">
      ${chip(c.action,      "Actions",     "chip-action")}
      ${c.blocked  ? chip(c.blocked,   "Blocked",     "chip-blocked")  : ""}
      ${chip(c.anchor,      "Anchors",     "chip-anchor")}
      ${c.narrative    ? chip(c.narrative,   "Narratives",  "chip-narrative") : ""}
      ${c.explainability ? chip(c.explainability, "Explain", "chip-explain") : ""}
    </div>
    <div style="font-size:0.65rem;color:var(--muted)">Total cards: ${c.total}</div>
  </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 6.2.2 — Multi-Dimensional Scorecards
// ─────────────────────────────────────────────────────────────────────────────
// MARKET-CONTEXT-01 — Deployment Timing & Macro Event Awareness
// Presentation-only. No changes to scores, rankings, recommendations, or
// any scoring system. Operator timing awareness only.
// ─────────────────────────────────────────────────────────────────────────────
function renderMarketContext(data) {
  const el = document.getElementById("marketContextContainer");
  if (!el) return;

  const mc = data.market_context;
  if (!mc) { el.innerHTML = ""; return; }

  const posture     = mc.timing_posture  || "NORMAL";
  const total7d     = mc.total_events_7d || 0;
  const events7d    = mc.events_7d       || 0;
  const earnings7d  = mc.earnings_7d     || 0;
  const macroEvents = mc.macro_events    || [];
  const portEvents  = mc.portfolio_events || [];

  // ── Deployment Timing Banner ───────────────────────────────────────────────
  const postureConfig = {
    EVENT_DENSE:       { cls: "mctx-posture-dense",    icon: "⚡", label: "EVENT-DENSE PERIOD",
      msg: `${total7d} major market events within the next 7 days. Operator may wish to consider staged deployment.` },
    MODERATE_ACTIVITY: { cls: "mctx-posture-moderate", icon: "◈",  label: "MODERATE ACTIVITY",
      msg: `${total7d} notable market events approaching in the next 7 days.` },
    NORMAL:            { cls: "mctx-posture-normal",   icon: "◎",  label: "NORMAL ENVIRONMENT",
      msg: total7d === 0
        ? "No major market events scheduled in the next 7 days."
        : `${total7d} event in the next 7 days — no unusual market density.` },
  };
  const pc = postureConfig[posture] || postureConfig.NORMAL;

  const bannerHtml = `<div class="mctx-timing-banner ${escHtml(pc.cls)}">
    <span class="mctx-posture-icon">${pc.icon}</span>
    <div class="mctx-posture-body">
      <span class="mctx-posture-label">${escHtml(pc.label)}</span>
      <span class="mctx-posture-msg">${escHtml(pc.msg)}</span>
    </div>
    <span class="mctx-posture-advisory">Informational only — no scoring or recommendation effect.</span>
  </div>`;

  // ── Helper: days-away badge ────────────────────────────────────────────────
  function _daysBadge(d) {
    const cls = d <= 3 ? "mctx-days-urgent" : d <= 7 ? "mctx-days-near" : "mctx-days-far";
    return `<span class="mctx-days-badge ${cls}">${d === 0 ? "TODAY" : d === 1 ? "Tomorrow" : `${d}d`}</span>`;
  }

  // ── Macro Events table ─────────────────────────────────────────────────────
  const catIcons = { FED: "🏛", OPTIONS: "📋", INDEX: "📊" };
  const macroRows = macroEvents.length
    ? macroEvents.map(e => `<tr>
        <td class="mctx-td-event">${catIcons[e.category] || "●"} ${escHtml(e.event)}</td>
        <td class="mctx-td-date">${escHtml(e.date)}</td>
        <td class="mctx-td-days">${_daysBadge(e.days_away)}</td>
      </tr>`).join("")
    : `<tr><td colspan="3" class="mctx-empty">No macro events in the next 14 days.</td></tr>`;

  // ── Portfolio Earnings table ───────────────────────────────────────────────
  const contextLabels = {
    TOP_DEPLOYMENT_CANDIDATE:   { cls: "mctx-ctx-deploy",  label: "Deploy Candidate" },
    REDUCTION_CANDIDATE:        { cls: "mctx-ctx-reduce",  label: "Reduction Target" },
    DEPLOYMENT_AND_REDUCTION:   { cls: "mctx-ctx-both",    label: "Deploy + Reduce" },
    CURRENT_HOLDING:            { cls: "mctx-ctx-holding", label: "Holding" },
  };
  const portRows = portEvents.length
    ? portEvents.map(e => {
        const ctxCfg = contextLabels[e.context] || { cls: "", label: e.context };
        return `<tr>
          <td class="mctx-td-sym"><strong>${escHtml(e.symbol)}</strong></td>
          <td class="mctx-td-ctx"><span class="mctx-ctx-badge ${ctxCfg.cls}">${escHtml(ctxCfg.label)}</span></td>
          <td class="mctx-td-date">${escHtml(e.date)}</td>
          <td class="mctx-td-days">${_daysBadge(e.days_away)}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="4" class="mctx-empty">No earnings in the next 30 days for tracked symbols.</td></tr>`;

  // ── Collapsible sections ───────────────────────────────────────────────────
  const macroId  = "mctx-macro-body";
  const portId   = "mctx-port-body";

  el.innerHTML = `<div class="mctx-card">
    <div class="mctx-header">
      <span class="mctx-title">Market Context</span>
      <span class="mctx-subtitle">Deployment Timing Awareness — ${escHtml(mc.as_of_date || "—")}</span>
    </div>
    ${bannerHtml}
    <div class="mctx-sections">
      <div class="mctx-section">
        <button class="mctx-section-toggle" onclick="(function(b){const d=document.getElementById('${macroId}');if(d){d.classList.toggle('mctx-open');b.textContent=d.classList.contains('mctx-open')?'▾ Macro Events':'▸ Macro Events';}}).call(this, this)">
          ▸ Macro Events <span class="mctx-count-badge">${macroEvents.length} in 14d</span>
        </button>
        <div class="mctx-section-body" id="${macroId}">
          <table class="mctx-table">
            <thead><tr><th>Event</th><th>Date</th><th>Days Away</th></tr></thead>
            <tbody>${macroRows}</tbody>
          </table>
        </div>
      </div>
      <div class="mctx-section">
        <button class="mctx-section-toggle" onclick="(function(b){const d=document.getElementById('${portId}');if(d){d.classList.toggle('mctx-open');b.textContent=d.classList.contains('mctx-open')?'▾ Portfolio Earnings':'▸ Portfolio Earnings';}}).call(this, this)">
          ▸ Portfolio Earnings <span class="mctx-count-badge">${portEvents.length} in 30d</span>
        </button>
        <div class="mctx-section-body" id="${portId}">
          <table class="mctx-table">
            <thead><tr><th>Symbol</th><th>Role</th><th>Date</th><th>Days Away</th></tr></thead>
            <tbody>${portRows}</tbody>
          </table>
        </div>
      </div>
    </div>
    <div class="mctx-governance">Market Context is informational only. Events do not influence scores, rankings, recommendations, CRA, PAP, or DIL posture.</div>
  </div>`;

  // Auto-expand macro events section if there are urgent events (≤3 days)
  if (macroEvents.some(e => e.days_away <= 3)) {
    const bd = document.getElementById(macroId);
    if (bd) bd.classList.add("mctx-open");
  }
  // Auto-expand portfolio earnings if any within 7 days
  if (portEvents.some(e => e.days_away <= 7)) {
    const bd = document.getElementById(portId);
    if (bd) bd.classList.add("mctx-open");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Clarity Sprint — Problem 5: Portfolio Construction Style framing card
// Presentation-only. No changes to scoring, recommendations, or mandate logic.
// ─────────────────────────────────────────────────────────────────────────────
function renderPortfolioConstructionStyle(data) {
  const el = document.getElementById("portfolioConstructionStyleContainer");
  if (!el) return;

  const allocScore  = parseFloat(data.overall_alignment_score ?? 0);
  const mds         = data.multi_dimensional_score || {};
  const convScore   = parseFloat(mds.portfolio_quality_score ?? mds.conviction_score ?? 0);
  const asym        = data.intentional_asymmetry || {};
  const asymState   = asym.asymmetry_state || "";

  const allocPct    = (allocScore * 100).toFixed(0);
  const convPct     = (convScore  * 100).toFixed(0);

  // Style label based on asymmetry state
  const styleLabels = {
    HIGH_CONVICTION:    "Intentional Conviction-Weighted",
    LIKELY_INTENTIONAL: "Active Conviction Tilt",
    ACCIDENTAL:         "Passive Drift Detected",
  };
  const styleLabel = styleLabels[asymState] || "Active Equity Portfolio";

  // Interpretation text
  let interpText = "";
  if (asymState === "HIGH_CONVICTION") {
    interpText = `This portfolio is intentionally asymmetric. Allocation gaps reflect deliberate conviction weighting — not tracking error. ` +
      `Under the active mandate, higher-conviction positions receive larger weights, independent of classical index targets.`;
  } else if (asymState === "LIKELY_INTENTIONAL") {
    interpText = `Moderate conviction tilt detected. Some allocation divergence reflects active positioning. ` +
      `Review mandate parameters to confirm intentionality.`;
  } else if (asymState === "ACCIDENTAL") {
    interpText = `Allocation asymmetry appears circumstantial rather than planned. ` +
      `Review whether current weights reflect active conviction or passive drift.`;
  } else {
    interpText = `Portfolio construction posture is being assessed. Load a PAR to see alignment metrics.`;
  }

  el.innerHTML = `<div class="pcs-card">
    <div class="pcs-header">
      <span class="pcs-title">Portfolio Construction Style</span>
      <span class="pcs-style-badge">${escHtml(styleLabel)}</span>
    </div>
    <div class="pcs-metrics-row">
      <div class="pcs-metric">
        <div class="pcs-metric-val">${allocPct}%</div>
        <div class="pcs-metric-label">Allocation Discipline</div>
        <div class="pcs-metric-sub">Classical model alignment</div>
      </div>
      <div class="pcs-metric-divider">vs.</div>
      <div class="pcs-metric">
        <div class="pcs-metric-val">${convPct}%</div>
        <div class="pcs-metric-label">Conviction Discipline</div>
        <div class="pcs-metric-sub">Portfolio quality score</div>
      </div>
    </div>
    <div class="pcs-interpretation">${escHtml(interpText)}</div>
    <div class="pcs-governance-note">Display-only framing — no scoring influence.</div>
  </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// UX-PA-09 — "What matters right now" portfolio narrative summary
// ─────────────────────────────────────────────────────────────────────────────
function renderNarrativeSummary(data) {
  const el = document.getElementById("narrativeSummaryContainer");
  if (!el) return;

  const recs = data.recommendations || [];
  const alignment = data.alignment || [];
  const score = parseFloat(data.overall_alignment_score ?? 0);

  // Build top 3 observations
  const obs = [];

  // Stale PAR advisory
  if (data.policy_is_stale) {
    obs.push({ type: "warn", text: "Policy replay applied — viewed PAR pre-dates a policy change. Recommendations updated to reflect current policy." });
  }

  // Reconciliation issue
  const reconFailed = (data.reconciliation_checks_failed || 0) > 0;
  const reconWarned = (data.reconciliation_checks_warned || 0) > 0;
  if (reconFailed) {
    const nFail = data.reconciliation_checks_failed;
    obs.push({ type: "warn", text: `${nFail} reconciliation check${nFail > 1 ? "s" : ""} failed — some holdings may be unclassified and excluded from allocation scoring.` });
  } else if (reconWarned) {
    obs.push({ type: "warn", text: `Reconciliation advisory: ${data.reconciliation_checks_warned} check(s) with non-critical warnings.` });
  }

  // Overall alignment
  if (score < 0.50) {
    obs.push({ type: "act", text: `Allocation alignment is ${(score * 100).toFixed(0)}% — portfolio is materially off target. High-priority rebalancing needed.` });
  } else if (score < 0.70) {
    obs.push({ type: "obs", text: `Allocation alignment is ${(score * 100).toFixed(0)}% — moderate deviation from target. Review overweight nodes.` });
  } else {
    obs.push({ type: "ok", text: `Allocation alignment is ${(score * 100).toFixed(0)}% — portfolio is broadly on target.` });
  }

  // Blocked actions
  const blocked = recs.filter(r => r.execution_state === "BLOCKED_BY_POLICY");
  if (blocked.length > 0) {
    const syms = [...new Set(blocked.flatMap(r => r.affected_symbols || []))].slice(0, 3).join(", ");
    obs.push({ type: "obs", text: `${blocked.length} action${blocked.length > 1 ? "s" : ""} blocked by operator policy (${syms}). Review if policy intent remains current.` });
  }

  // Overweight nodes
  const overweight = alignment.filter(r => parseFloat(r.drift_pct || 0) > 2 && r.severity && r.severity !== "NONE").slice(0, 2);
  if (overweight.length > 0) {
    obs.push({ type: "obs", text: `Largest overweight: ${overweight.map(r => `${r.node_label || r.node_key} (+${parseFloat(r.drift_pct).toFixed(1)}pp)`).join(", ")}.` });
  }

  const topObs = obs.slice(0, 3);

  // Build top 3 actionable items
  const acts = [];
  const actionRecs = recs.filter(r => r.card_type === "ACTION" && r.execution_state === "EXECUTABLE").slice(0, 3);
  for (const r of actionRecs) {
    const syms = (r.affected_symbols || []).slice(0, 2).join(", ");
    acts.push({ type: "act", text: `${r.title || r.recommendation_type}${syms ? ` — ${syms}` : ""}` });
  }
  if (acts.length === 0) {
    acts.push({ type: "ok", text: "No immediately executable actions. Portfolio is stable or all sell-context actions are policy-blocked." });
  }
  const topActs = acts.slice(0, 3);

  const dotClass = { obs: "narrative-dot-obs", act: "narrative-dot-act", ok: "narrative-dot-ok", warn: "narrative-dot-act" };

  const staleBadge = data.policy_is_stale
    ? `<div class="narrative-stale-badge">&#9888; Policy replay applied — stale PAR corrected to current policy</div>`
    : "";

  el.innerHTML = `
    <div class="narrative-summary">
      ${staleBadge}
      <div class="narrative-summary-title">&#9679; What matters right now</div>
      <div class="narrative-cols">
        <div>
          <div class="narrative-col-title">Observations</div>
          ${topObs.map(o => `
            <div class="narrative-item">
              <div class="narrative-dot ${dotClass[o.type] || 'narrative-dot-obs'}"></div>
              <span>${escHtml(o.text)}</span>
            </div>`).join("")}
        </div>
        <div>
          <div class="narrative-col-title">Actionable Items</div>
          ${topActs.map(a => `
            <div class="narrative-item">
              <div class="narrative-dot ${dotClass[a.type] || 'narrative-dot-act'}"></div>
              <span>${escHtml(a.text)}</span>
            </div>`).join("")}
        </div>
      </div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// UX-PA-02 — Reconciliation FAIL explainability panel
// ─────────────────────────────────────────────────────────────────────────────
function renderReconciliationPanel(data) {
  const el = document.getElementById("reconciliationContainer");
  if (!el) return;

  const status = data.reconciliation_status || "";
  const cert   = data.reconciliation_certification || "";
  const checks = data.reconciliation_checks || [];

  // Only show if there's a FAIL or WARN — hide on PASS to reduce clutter
  const hasFail = checks.some(c => c.status === "FAIL");
  const hasWarn = checks.some(c => c.status === "WARN");
  if (!hasFail && !hasWarn && status === "PASS") { el.innerHTML = ""; return; }

  const panelId = "reconBodyPanel";
  const toggleId = "reconToggleBtn";

  const nonPassChecks = checks.filter(c => c.status !== "PASS");

  const rows = nonPassChecks.map(c => {
    const subSummary = (c.sub_checks || []).length > 0
      ? `<div class="recon-symbols">${(c.sub_checks).slice(0,5).map(s =>
          `${escHtml(s.symbol || s.node || "")}${s.root_cause ? ` (${escHtml(s.root_cause)})` : ""}`
        ).join(" · ")}</div>`
      : "";
    const affectsRecs = c.affects_recommendations != null
      ? (c.affects_recommendations
          ? `<span class="recon-affect-recs-warn">&#9888; May affect recommendations</span>`
          : `<span class="recon-affect-recs-ok">&#10003; Recommendations unaffected</span>`)
      : `<span class="recon-affect-recs-ok">&#10003; Recommendations unaffected</span>`;

    return `<tr>
      <td><span class="recon-status-${c.status}">${c.status}</span></td>
      <td>
        <strong>${escHtml(c.name || c.check_id)}</strong>
        <div class="recon-impact">${escHtml(c.detail ? (Array.isArray(c.detail) ? c.detail[0] : c.detail) : "")}</div>
        ${subSummary}
      </td>
      <td style="text-align:right;white-space:nowrap">${escHtml(c.expected || "")}</td>
      <td style="text-align:right;white-space:nowrap">${escHtml(c.actual || "")}</td>
      <td>
        <div class="recon-guidance">${escHtml(c.operator_guidance || (c.status === "FAIL" ? "Resolve classification gap before acting on affected allocations." : "Advisory only — no action required."))}</div>
        ${affectsRecs}
      </td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <div class="recon-panel">
      <div class="recon-header" onclick="document.getElementById('${panelId}').classList.toggle('recon-body-hidden');document.getElementById('${toggleId}').textContent=document.getElementById('${panelId}').classList.contains('recon-body-hidden')?'▸ Show':'▾ Hide'">
        <span class="recon-title">Reconciliation &amp; Data Quality</span>
        <span class="recon-badge recon-badge-${status || 'UNKNOWN'}">${status || '—'}</span>
        <span class="recon-cert">${escHtml(cert)}</span>
        <span class="recon-toggle" id="${toggleId}">▾ Hide</span>
      </div>
      <div class="recon-body" id="${panelId}">
        <table class="recon-table">
          <thead><tr>
            <th style="width:60px">Status</th>
            <th>Check / Detail</th>
            <th style="text-align:right">Expected</th>
            <th style="text-align:right">Actual</th>
            <th>Guidance</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

function renderMultiDimScores(data) {
  const el = document.getElementById("multiDimContainer");
  const mds = data.multi_dimensional_score;
  if (!el || !mds) { if (el) el.innerHTML = ""; return; }

  const dims = [
    {
      key: "allocation_alignment_score", label: "Allocation Alignment",
      tooltip: "Distance from target model allocations", anchor: "allocationPanel",
      defn: "How close the portfolio is to its target asset class weights. 100 = perfectly on target; lower = larger gaps from mandate.",
    },
    {
      key: "portfolio_quality_score", label: "Portfolio Quality",
      tooltip: "Concentration, signal quality, strategic classification", anchor: "deploymentQueueContainer",
      defn: "Signal strength, concentration risk, and strategic profile of holdings. Low score = weak signals or concentrated exposure.",
    },
    {
      key: "implementation_quality_score", label: "Implementation Quality",
      tooltip: "Vehicle suitability and operational integrity", anchor: "portfolioActionPipelineSection",
      defn: "How well each position is implemented — direct stock vs ETF, liquidity, and operational hygiene.",
    },
    {
      key: "replay_alignment_score", label: "Replay Alignment",
      tooltip: "Replay-supported exposure coverage and quality", anchor: "replayPanel",
      defn: "How much of the portfolio has replay evidence backing it. Low = limited historical outcome data for current holdings.",
    },
  ];

  const cards = dims.map(d => {
    const raw = parseFloat(mds[d.key] ?? 0);
    const pct  = Math.min(100, Math.max(0, raw));
    const color = pct >= 75 ? "var(--green)" : pct >= 50 ? "var(--accent-2)" : "var(--sev-high)";
    const label = pct >= 75 ? "Strong" : pct >= 50 ? "Moderate" : "Needs attention";
    const navHtml = d.anchor
      ? `<div class="multidim-nav" onclick="(function(){const el=document.getElementById('${d.anchor}');if(el){el.scrollIntoView({behavior:'smooth',block:'start'});}})()" title="Jump to section">&#8595; View</div>`
      : "";
    return `<div class="multidim-card" title="${escHtml(d.tooltip)}">
      <div class="multidim-score" style="color:${color}">${pct.toFixed(0)}</div>
      <div class="multidim-label">${d.label}</div>
      <div class="multidim-sublabel">${label}</div>
      <div class="multidim-track">
        <div class="multidim-fill" style="width:${pct.toFixed(0)}%;background:${color}"></div>
      </div>
      <div class="multidim-defn">${escHtml(d.defn)}</div>
      ${navHtml}
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

  // ── UX-PA-05: Top allocation drivers summary ──────────────────────────────
  const l1Rows = sorted.filter(r => depthOf(r.node_key) === 1 && r.node_key !== "CASH");
  const withDrift = l1Rows.map(r => ({
    label: r.node_label || r.node_key,
    drift: parseFloat(r.drift_pct) || 0,
    actual: parseFloat(r.effective_actual_pct ?? r.actual_pct ?? 0) || 0,
    target: parseFloat(r.target_pct || 0),
  })).filter(r => r.actual > 0 || Math.abs(r.drift) > 0);

  const overweights = [...withDrift].sort((a, b) => b.drift - a.drift).filter(r => r.drift > 0.5).slice(0, 3);
  const underweights = [...withDrift].sort((a, b) => a.drift - b.drift).filter(r => r.drift < -0.5).slice(0, 3);
  const gaps = [...withDrift].sort((a, b) => Math.abs(b.drift) - Math.abs(a.drift)).slice(0, 3);

  const driverItem = (label, drift, cls) =>
    `<div class="alloc-driver-item">
      <span class="alloc-driver-sym">${escHtml(label)}</span>
      <span class="alloc-driver-pct ${cls}">${drift > 0 ? "+" : ""}${drift.toFixed(1)}pp</span>
    </div>`;

  const driversHtml = `
    <div class="alloc-driver-strip">
      <div class="alloc-driver-card">
        <div class="alloc-driver-title">Largest Overweights</div>
        ${overweights.length ? overweights.map(r => driverItem(r.label, r.drift, "alloc-driver-pct-pos")).join("") : '<div class="alloc-driver-item" style="color:var(--muted);font-size:0.72rem">None above threshold</div>'}
      </div>
      <div class="alloc-driver-card">
        <div class="alloc-driver-title">Largest Underweights</div>
        ${underweights.length ? underweights.map(r => driverItem(r.label, r.drift, "alloc-driver-pct-neg")).join("") : '<div class="alloc-driver-item" style="color:var(--muted);font-size:0.72rem">None below threshold</div>'}
      </div>
      <div class="alloc-driver-card">
        <div class="alloc-driver-title">Largest Alignment Gaps</div>
        ${gaps.length ? gaps.map(r => driverItem(r.label, r.drift, "alloc-driver-pct-gap")).join("") : '<div class="alloc-driver-item" style="color:var(--muted);font-size:0.72rem">No gaps</div>'}
      </div>
    </div>`;

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

  el.innerHTML = driversHtml + `
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

// PRA-IMPL-03 — Lane collapse/expand toggle
function _toggleLane(bodyId, btn) {
  const body = document.getElementById(bodyId);
  if (!body) return;
  const collapsed = body.classList.toggle("lane-collapsed");
  btn.textContent = collapsed ? "Show ▾" : "Hide ▴";
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

  // ── PRA-IMPL-03: Partition recs into lanes ──────────────────────────────
  const laneAction   = [];
  const laneBlocked  = [];
  const laneAnchor   = [];
  const laneNarrative = [];
  const laneExplain  = [];
  const laneObs      = [];

  recs.forEach(r => {
    const ct = r.card_type       || "DIAGNOSTIC";
    const es = r.execution_state || "EXECUTABLE";
    const rt = r.recommendation_type || "";
    if (_CONVICTION_ANCHOR_TYPES.has(rt))   { laneAnchor.push(r); }
    else if (_NARRATIVE_TYPES.has(rt))      { laneNarrative.push(r); }
    else if (_EXPLAINABILITY_TYPES.has(rt)) { laneExplain.push(r); }
    else if (ct === "ACTION") {
      if (es === "BLOCKED_BY_POLICY" || es === "DEFERRED_BY_POLICY") { laneBlocked.push(r); }
      else { laneAction.push(r); }
    } else { laneObs.push(r); }
  });

  // ── Card builder (same logic as before, reused for all lanes) ──────────
  const buildCard = (r, i) => {
    const symbols = (r.affected_symbols || []).map(s =>
      `<span class="rec-symbol">${s}</span>`
    ).join("");
    const typeLabel = (r.recommendation_type || "").replace(/_/g, " ");
    const driftStr = r.drift_pct != null
      ? `<span style="font-size:0.78rem;color:var(--muted)">Drift: ${parseFloat(r.drift_pct) > 0 ? "+" : ""}${parseFloat(r.drift_pct).toFixed(1)}pp</span>`
      : "";

    // Policy execution state badge (PRA-IMPL-02 / ARCH-04 per-symbol)
    const execState = r.execution_state || "";
    const symStates = r.symbol_execution_states || {};
    let policyBadgeHtml = "";
    if (execState === "BLOCKED_BY_POLICY") {
      // All symbols blocked — find the blocked one for the unblock hint
      const blockedSym = Object.keys(symStates).find(s => symStates[s].execution_state === "BLOCKED_BY_POLICY") || (r.affected_symbols || [])[0] || "";
      const unblockHint = blockedSym
        ? `<span class="rec-unblock-hint">To unblock: remove DO_NOT_SELL policy on ${escHtml(blockedSym)}.</span>`
        : "";
      policyBadgeHtml = `<span class="rec-policy-badge policy-blocked">🔒 Operator Protected — not executable</span>${unblockHint}`;
    } else if (execState === "DEFERRED_BY_POLICY") {
      // All symbols deferred — find the deferred one for the hint
      const deferredSym = Object.keys(symStates).find(s => symStates[s].execution_state === "DEFERRED_BY_POLICY") || (r.affected_symbols || []).find(s => s) || "";
      const deferHint = deferredSym
        ? `<span class="rec-unblock-hint">To prioritize: remove SELL_LAST policy on ${escHtml(deferredSym)}.</span>`
        : "";
      policyBadgeHtml = `<span class="rec-policy-badge policy-deferred">⏸ Sell Last — deferred</span>${deferHint}`;
    } else if (execState === "EXECUTABLE" && Object.keys(symStates).length > 0) {
      // ARCH-04: rec is executable but some symbols may still be individually constrained — show compact per-symbol badges
      const constrainedSyms = Object.entries(symStates).filter(([, v]) => v.execution_state !== "EXECUTABLE");
      if (constrainedSyms.length > 0) {
        const symBadges = constrainedSyms.map(([sym, v]) => {
          if (v.execution_state === "BLOCKED_BY_POLICY") {
            return `<span class="rec-policy-badge policy-blocked" title="To unblock: remove DO_NOT_SELL policy on ${escHtml(sym)}">🔒 ${escHtml(sym)}: Blocked</span>`;
          }
          if (v.execution_state === "DEFERRED_BY_POLICY") {
            return `<span class="rec-policy-badge policy-deferred" title="To prioritize: remove SELL_LAST policy on ${escHtml(sym)}">⏸ ${escHtml(sym)}: Sell Last</span>`;
          }
          return "";
        }).filter(Boolean).join(" ");
        policyBadgeHtml = symBadges ? `<div class="rec-sym-policy-strip">${symBadges}</div>` : "";
      }
    }

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
      ${policyBadgeHtml}
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
  };

  // ── Lane section builder ────────────────────────────────────────────────
  let globalIdx = 0;
  const buildLane = (items, laneClass, label, collapsedByDefault = false) => {
    if (!items.length) return "";
    const bodyId = `lane-body-${laneClass}`;
    const bodyClass = collapsedByDefault ? "rec-lane-body lane-collapsed" : "rec-lane-body";
    const toggleLabel = collapsedByDefault ? "Show ▾" : "Hide ▴";
    const cards = items.map(r => buildCard(r, ++globalIdx)).join("");
    return `<div class="rec-lane">
      <div class="rec-lane-header lane-${laneClass}">
        <span class="lane-label">${label}</span>
        <span class="lane-count">${items.length}</span>
        <button class="rec-lane-toggle" onclick="_toggleLane('${bodyId}', this)">${toggleLabel}</button>
      </div>
      <div class="${bodyClass}" id="${bodyId}">
        ${cards}
      </div>
    </div>`;
  };

  // ── PRA-IMPL-06: Conviction Anchors — ranked Top 5 + full registry ─────
  const buildConvictionAnchorLane = (items) => {
    if (!items.length) return "";

    // Ranking: tier → composite score → replay → portfolio weight
    const _TIER_ORDER = {
      CORE_CONVICTION_LEADER: 0,
      HIGH_CONVICTION_ANCHOR: 1,
      TACTICAL_GROWTH_CANDIDATE: 2,
      WATCH_TRIM_CANDIDATE: 3,
    };
    const _tierShort = t =>
      t === "CORE_CONVICTION_LEADER" ? "CCL"
      : t === "HIGH_CONVICTION_ANCHOR" ? "HCA"
      : t === "TACTICAL_GROWTH_CANDIDATE" ? "TGC"
      : t === "WATCH_TRIM_CANDIDATE" ? "WTC" : "—";

    // Build per-symbol deduplicated list (prefer CONVICTION_EXPLAINABILITY_CARD for info depth)
    const bySymbol = {};
    for (const r of items) {
      const sym = (r.affected_symbols || [])[0] || r.recommendation_id;
      if (!bySymbol[sym] || r.recommendation_type === "CONVICTION_EXPLAINABILITY_CARD") {
        bySymbol[sym] = r;
      }
    }
    const unique = Object.values(bySymbol);

    // Sort unique symbols by tier → composite → replay → weight using drilldown data
    unique.sort((a, b) => {
      // Extract tier from reasoning_trace or title (available from card data)
      const getTier = r => {
        const trace = r.reasoning_trace || r.title || "";
        if (trace.includes("CORE_CONVICTION_LEADER")) return 0;
        if (trace.includes("HIGH_CONVICTION_ANCHOR"))  return 1;
        if (trace.includes("TACTICAL_GROWTH_CANDIDATE")) return 2;
        if (trace.includes("WATCH_TRIM_CANDIDATE")) return 3;
        // Fallback: priority field (lower = better conviction)
        return (r.priority || 9);
      };
      const getComposite = r => {
        const dd = r.drilldown || {};
        const holdings = dd.holdings || [];
        if (holdings.length) return parseFloat(holdings[0].composite_score || 0);
        return 0;
      };
      const getReplay = r => {
        const dd = r.drilldown || {};
        const holdings = dd.holdings || [];
        return holdings.some(h => h.replay_supported === true || h.replay_supported === "True") ? 0 : 1;
      };
      const getWeight = r => {
        const dd = r.drilldown || {};
        const holdings = dd.holdings || [];
        return holdings.reduce((s, h) => s + parseFloat(h.percent_of_portfolio || 0), 0);
      };
      const ta = getTier(a), tb = getTier(b);
      if (ta !== tb) return ta - tb;
      const ca = getComposite(a), cb = getComposite(b);
      if (Math.abs(ca - cb) > 0.001) return cb - ca;
      const ra = getReplay(a), rb = getReplay(b);
      if (ra !== rb) return ra - rb;
      return getWeight(b) - getWeight(a);
    });

    const TOP_N = 5;
    const top5   = unique.slice(0, TOP_N);
    const restAll = items; // full original list for registry

    // Build Top 5 compact cards
    const buildTopCard = (r, idx) => {
      const sym = (r.affected_symbols || [])[0] || "—";
      const trace = r.reasoning_trace || r.title || "";
      let tier = "—", tierCls = "tier-none";
      if (trace.includes("CORE_CONVICTION_LEADER"))     { tier = "CCL"; tierCls = "anchor-tier-ccl"; }
      else if (trace.includes("HIGH_CONVICTION_ANCHOR"))  { tier = "HCA"; tierCls = "anchor-tier-hca"; }
      else if (trace.includes("TACTICAL_GROWTH_CANDIDATE")) { tier = "TGC"; tierCls = "anchor-tier-tgc"; }

      const dd = r.drilldown || {};
      const holdings = dd.holdings || [];
      const composite = holdings.length ? parseFloat(holdings[0].composite_score || 0) : 0;
      const compStr = composite > 0 ? composite.toFixed(3) : "—";

      // Pull a short rationale from the first sentence of the narrative
      const rationale = (r.rationale || "").split(".")[0].trim();
      const shortRationale = rationale.length > 100 ? rationale.slice(0, 97) + "…" : rationale;

      return `<div class="anchor-top-card" onclick="document.getElementById('lane-body-anchor-full').classList.remove('lane-collapsed');document.querySelector('#lane-body-anchor-full .rec-lane-toggle')&&(document.querySelector('#lane-body-anchor-full .rec-lane-toggle').textContent='Hide ▴')">
        <div class="anchor-top-header">
          <span class="anchor-top-sym">${sym}</span>
          <span class="anchor-tier-badge ${tierCls}">${tier}</span>
          ${composite > 0 ? `<span class="anchor-top-score">${compStr}</span>` : ""}
        </div>
        <div class="anchor-top-rationale">${shortRationale || r.title || ""}</div>
      </div>`;
    };

    const top5Html = top5.map((r, i) => buildTopCard(r, i)).join("");

    // Full registry: all original cards (deduplicated by symbol for count display, full for cards)
    const registryBodyId = "lane-body-anchor-full";
    const registryCards = restAll.map(r => buildCard(r, ++globalIdx)).join("");

    return `<div class="rec-lane">
      <div class="rec-lane-header lane-anchor">
        <span class="lane-label">Conviction Anchors</span>
        <span class="lane-count">${items.length}</span>
        <button class="rec-lane-toggle" onclick="_toggleLane('lane-body-anchor-full', this)">Show all ▾</button>
      </div>
      <div class="anchor-top-section">
        <div class="anchor-top-label">Top Conviction Anchors</div>
        <div class="anchor-top-grid">${top5Html}</div>
      </div>
      <div class="rec-lane-body lane-collapsed" id="${registryBodyId}">
        ${registryCards}
      </div>
    </div>`;
  };

  const html = [
    buildLane(laneAction,    "action",    "Actions",              false),
    buildLane(laneBlocked,   "blocked",   "Blocked / Deferred",   false),
    buildLane(laneObs,       "anchor",    "Observations",         false),
    buildConvictionAnchorLane(laneAnchor),
    buildLane(laneNarrative, "narrative", "Portfolio Narrative",  true),
    buildLane(laneExplain,   "explain",   "Explainability",       true),
  ].join("");

  el.innerHTML = sepHtml + html;
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
      ${_optStatCard(etfGateFailed,  "Superior Security Available", etfGateFailed  > 0 ? "alert" : "")}
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
      `<span class="opt-badge opt-badge-ETF_GATE_FAILED" title="${escHtml(c.etf_gate)}">SUPERIOR_SECURITY_AVAILABLE: ${escHtml(c.symbol)}</span>`
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

  // Mandate dual-view framing block (Problem 1 — UI Clarity Sprint)
  // Only shown when mandate_blocked: explains the classical-vs-policy divergence.
  const mandateDualViewHtml = om.mandate_blocked
    ? `<div class="optview-mandate-dualview">
        <div class="optview-dualview-row">
          <span class="optview-view-badge optview-view-classical">CLASSICAL ALLOCATION VIEW</span>
          <span class="optview-dualview-text">
            Allocation gap detected in <strong>${escHtml(om.target_node || "—")}</strong>.
            A standard model would treat this as underweight and recommend ETF deployment to close the gap.
          </span>
        </div>
        <div class="optview-dualview-row optview-dualview-override-row">
          <span class="optview-view-badge optview-view-override">CONCENTRATED ALPHA POLICY OVERRIDE</span>
          <span class="optview-dualview-text">
            This underweight is <strong>intentional</strong> under the active mandate
            (<strong>${escHtml(om.mandate_type || "—")}</strong>).
            Deployment into generic ETF vehicles is not warranted.
            Recommended action: deploy capital into higher-conviction individual securities in this node.
          </span>
        </div>
      </div>`
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
    ${mandateDualViewHtml}
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

// ISSUE-05 — Deployment Queue filter state
let _dqFilterThesis      = new Set(["INTACT","QUESTIONABLE","DETERIORATING"]);
let _dqFilterConsistency = new Set(["CONSISTENT","MIXED","CONTRADICTORY","DATA_ANOMALY"]);
let _dqFilterModifier    = "ALL";  // "ALL" | "POSITIVE" | "NEUTRAL" | "NEGATIVE"
let _dqOutsideClickBound = false;

function renderDeploymentQueue(data) {
  const el = document.getElementById("deploymentQueueContainer");
  if (!el) return;

  const dq = data.deployment_queue;
  if (!dq || !Array.isArray(dq.queue) || dq.queue.length === 0) {
    el.innerHTML = "";
    return;
  }

  _dqShowAll = false;  // reset on each render
  // ISSUE-05: reset filters to "All" defaults on each new analysis load
  _dqFilterThesis      = new Set(["INTACT","QUESTIONABLE","DETERIORATING"]);
  _dqFilterConsistency = new Set(["CONSISTENT","MIXED","CONTRADICTORY","DATA_ANOMALY"]);
  _dqFilterModifier    = "ALL";

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
      <div class="dq-summary-sublbl" title="Excess above ${_cashTargetPct}% mandate floor. Full cash: ${formatMV(cashCtx.cash_mv || 0)}. Floor reserve: ${formatMV(cashCtx.floor_mv || 0)}.">Excess above ${_cashTargetPct}% mandate floor ⓘ</div>
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
      <div class="dq-filters" id="dq-filters" onclick="event.stopPropagation()">
        <div class="dq-filter-group">
          <button class="dq-filter-btn" id="dq-fb-thesis" onclick="_dqToggleFilterPanel(event,'thesis')">Thesis &#9662;</button>
          <div class="dq-filter-panel" id="dq-fp-thesis">
            <label><input type="checkbox" checked onchange="_dqThesisChange('INTACT',this.checked)"> INTACT</label>
            <label><input type="checkbox" checked onchange="_dqThesisChange('QUESTIONABLE',this.checked)"> QUESTIONABLE</label>
            <label><input type="checkbox" checked onchange="_dqThesisChange('DETERIORATING',this.checked)"> DETERIORATING</label>
          </div>
        </div>
        <div class="dq-filter-group">
          <button class="dq-filter-btn" id="dq-fb-consistency" onclick="_dqToggleFilterPanel(event,'consistency')">Consistency &#9662;</button>
          <div class="dq-filter-panel" id="dq-fp-consistency">
            <label><input type="checkbox" checked onchange="_dqConsistencyChange('CONSISTENT',this.checked)"> CONSISTENT</label>
            <label><input type="checkbox" checked onchange="_dqConsistencyChange('MIXED',this.checked)"> MIXED</label>
            <label><input type="checkbox" checked onchange="_dqConsistencyChange('CONTRADICTORY',this.checked)"> CONTRADICTORY</label>
            <label><input type="checkbox" checked onchange="_dqConsistencyChange('DATA_ANOMALY',this.checked)"> DATA ANOMALY</label>
          </div>
        </div>
        <div class="dq-filter-group">
          <button class="dq-filter-btn" id="dq-fb-modifier" onclick="_dqToggleFilterPanel(event,'modifier')">Modifier &#9662;</button>
          <div class="dq-filter-panel" id="dq-fp-modifier">
            <label><input type="radio" name="dq-mod-radio" value="ALL" checked onchange="_dqModifierChange('ALL')"> All</label>
            <label><input type="radio" name="dq-mod-radio" value="POSITIVE" onchange="_dqModifierChange('POSITIVE')"> Positive (&gt;0)</label>
            <label><input type="radio" name="dq-mod-radio" value="NEUTRAL" onchange="_dqModifierChange('NEUTRAL')"> Neutral (0)</label>
            <label><input type="radio" name="dq-mod-radio" value="NEGATIVE" onchange="_dqModifierChange('NEGATIVE')"> Negative (&lt;0)</label>
          </div>
        </div>
      </div>
      <span class="dq-filtered-count" id="dq-filtered-count"></span>
      <span class="dq-advisory-note">Guidance only &#8212; not a trade instruction</span>
    </div>
    ${summaryHtml}
    ${cashContextHtml}
    ${cashSummaryHtml}
    <div class="da-action-section">
      <div class="da-action-section-header">Deployment Candidates — Top 10</div>
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

  // Render initial rows — apply filters (default = all pass)
  _dqRenderTableRows(_dqApplyFilters(queue), tableId, DQ_DEFAULT_ROWS);
  // Attach outside-click handler once to close open filter panels
  if (!_dqOutsideClickBound) {
    document.addEventListener("click", function() {
      document.querySelectorAll(".dq-filter-panel.open").forEach(p => p.classList.remove("open"));
    });
    _dqOutsideClickBound = true;
  }
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

    // DIL Phase 1 — Deployment candidate intelligence panel
    const _acBySymDQ   = (_lastAnalysisData && _lastAnalysisData.analyst_consensus_by_symbol) || {};
    const _fssBySymDQ  = (_lastAnalysisData && _lastAnalysisData.fidelity_signals_by_symbol)  || {};
    const _ucfBySymDQ  = (_analysisResult   && _analysisResult.ucf_verdicts_by_symbol)        || {};
    const _fmpBySymDQ  = (_lastAnalysisData && _lastAnalysisData.fmp_data_by_symbol)           || {};
    const _pcBySymDQ   = (_lastAnalysisData && _lastAnalysisData.price_context_by_symbol)      || {};
    const _ovBySymDQ2  = {};
    for (const ov2 of ((_lastAnalysisData && _lastAnalysisData.security_overlays) || [])) {
      if (ov2 && ov2.symbol) _ovBySymDQ2[(ov2.symbol || "").toUpperCase()] = ov2;
    }
    const _dilDQ = computeDIL(
      sym,
      _acBySymDQ[sym.toUpperCase()] || {},
      _fssBySymDQ[sym.toUpperCase()] || {},
      _fmpBySymDQ[sym.toUpperCase()] || null,
      _ucfBySymDQ[sym.toUpperCase()] || {},
      _ovBySymDQ2[sym.toUpperCase()] || {},
      { isReduction: false, isDeployment: true, category: cand.narrative_tier || "" },
      _pcBySymDQ[sym.toUpperCase()] || null
    );
    const _dilDQId = `da-intel-${rec.rank}`;
    const _dilBtnHtml = `<button class="da-intel-btn" onclick="(function(){const p=document.getElementById('${_dilDQId}');if(p){p.classList.toggle('dil-open');this.textContent=p.classList.contains('dil-open')?'▲ Intel':'⚡ Intel';}}).call(this)">⚡ Intel</button>
      <div class="da-intel-panel" id="${_dilDQId}">${_dilHtml(_dilDQ)}</div>`;

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
      ${_dilBtnHtml}
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
        ${_dqAnalystTargetHtml(ac2)}
        <div class="dq-breakdown-header">CW-DAS Score Breakdown — ${escHtml(c.symbol)} <span style="font-size:0.68rem;color:var(--muted);font-weight:400">(CW-DAS v${escHtml(c.cw_das_version||'1.1')})</span></div>
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
          ${(bd.fundamental_modifier != null && bd.fundamental_modifier !== 0) ? `<div class="dq-bd-card">
            <div class="dq-bd-val${bd.fundamental_modifier > 0 ? ' dq-score-high' : ' dq-penalty'}">${bd.fundamental_modifier > 0 ? '+' : ''}${bd.fundamental_modifier.toFixed(1)}</div>
            <div class="dq-bd-lbl">Fund.<br>Mod</div>
          </div>` : ''}
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.sizing != null ? bd.sizing.toFixed(1) : "—"}</div>
            <div class="dq-bd-lbl">Sizing<br>/8</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${bd.momentum != null ? bd.momentum.toFixed(1) : "—"}</div>
            <div class="dq-bd-lbl">Momentum<br>/10</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val${bd.redundancy_pen > 0 ? " dq-penalty" : ""}">${bd.redundancy_pen != null ? "\u2212" + bd.redundancy_pen.toFixed(0) : "\u2014"}</div>
            <div class="dq-bd-lbl">Redund.<br>Pen</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val${bd.conc_pen > 0 ? " dq-penalty" : ""}">${bd.conc_pen != null ? "\u2212" + bd.conc_pen.toFixed(0) : "\u2014"}</div>
            <div class="dq-bd-lbl">Conc.<br>Pen</div>
          </div>
          <div class="dq-bd-card">
            <div class="dq-bd-val">${trim.toFixed(0)}</div>
            <div class="dq-bd-lbl">Trim<br>Score</div>
          </div>
        </div>
        <div class="dq-breakdown-notes">${escHtml(c.notes || "")}</div>
        ${_dqCompanySnapshotHtml(sym, _securityMetadata)}
        ${_dqFundamentalSnapshotHtml(sym, _securityMetadata, ov)}
        ${_dqWhySIHLikesItHtml(c, ucf, ov, bd, dp, trim)}
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
  const filtered = _dqApplyFilters(dq.queue);
  const limit = _dqShowAll ? filtered.length : DQ_DEFAULT_ROWS;
  _dqRenderTableRows(filtered, "dq-queue-table-body", limit);

  const btn = document.getElementById("dq-view-all-btn");
  if (btn) {
    btn.textContent = _dqShowAll
      ? `\u25b2 Show top ${DQ_DEFAULT_ROWS} only`
      : `\u25bc View all ${filtered.length} candidates`;
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
// ISSUE-05 — Deployment Queue Filters (Thesis / Consistency / Modifier)
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// ISSUE-04C — Dislocation Watchlist Panel
// Governance: display-only. Backend payload authoritative. No scoring influence.
// ─────────────────────────────────────────────────────────────────────────────
// ARCH-02 — Reduction Queue
// Sibling to the Deployment Queue. Shows top 10 CRA capital sources ranked by
// the existing CRA priority system (URGENT > HIGH > MODERATE > LOW > DEFER).
// Data source: _craProposal.sources (loaded by loadCRAProposal).
// No CW-DAS normalization. No cross-system score merging.
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// DIL Phase 1 — Decision Intelligence Layer
// Interpretive posture engine. Display-only. No scoring or ranking influence.
// Every output cites its signal source and date. Operator remains decision maker.
// ─────────────────────────────────────────────────────────────────────────────

function computeDIL(sym, ac, fs, fmpEntry, ucf, ov, context, priceCtx) {
  // context = { isReduction: bool, isDeployment: bool, category: string }
  // priceCtx = { return_1d, return_5d, return_1m, pct_52w_range, next_earnings_date, ... } (optional, display-only)
  const today_str = new Date().toISOString().split("T")[0];

  // Signal extraction
  const fsObj     = fs  || {};
  const ovObj     = ov  || {};
  const acObj     = ac  || {};
  const ucfObj    = ucf || {};
  const fmpObj    = fmpEntry || {};

  const essText   = fsObj.ess_text    || ovObj.ess_score_text || "";
  const fidRating = fsObj.fidelity_rating || "";
  const consMat   = fsObj.consensus_matrix || {};
  const matrixClass = consMat.classification || "";

  const abr        = acObj.abr != null ? parseFloat(acObj.abr) : null;
  const analystCnt = acObj.analyst_count || 0;
  const consLabel  = acObj.consensus_label || "";
  const upsidePct  = acObj.upside_pct != null ? parseFloat(acObj.upside_pct) : null;
  const consRefresh = acObj.refresh_date || null;

  const zacks    = ovObj.zacks_rating  != null ? parseFloat(ovObj.zacks_rating)  : null;
  const danelfin = ovObj.danelfin_score != null ? parseFloat(ovObj.danelfin_score) : null;
  const composite = ovObj.composite_score != null ? parseFloat(ovObj.composite_score) : null;
  const replayPct = ovObj.replay_percentile != null ? parseFloat(ovObj.replay_percentile) : null;

  const ucfLabel = ucfObj.ucf_label || "";
  const ucfScore = ucfObj.ucf_score != null ? parseFloat(ucfObj.ucf_score) : null;
  const ucfSummary = ucfObj.signal_summary || "";

  const category = context.category || "";

  // FMP fundamentals
  const epsSurprise = fmpObj.latest_eps_surprise_pct != null ? parseFloat(fmpObj.latest_eps_surprise_pct) : null;
  const beatRate    = fmpObj.beat_rate_8q != null ? parseFloat(fmpObj.beat_rate_8q) : null;
  const revGrowth   = fmpObj.revenue_growth_q1_yoy != null ? parseFloat(fmpObj.revenue_growth_q1_yoy) : null;
  const revAccel    = fmpObj.revenue_acceleration != null ? parseFloat(fmpObj.revenue_acceleration) : null;
  const fmpDate     = fmpObj.fmp_sourced_date || null;
  const fmpCovered  = (fmpObj.fmp_coverage_status || "NO_DATA") !== "NO_DATA";

  // Signal direction flags
  const isESSBearish  = essText.includes("BEARISH") || fidRating === "SELL" || fidRating === "STRONG_SELL";
  const isESSBullish  = essText.includes("BULLISH") || fidRating === "STRONG_BUY" || fidRating === "BUY";
  const isStreetBullish = abr !== null && abr <= 2.5 && consLabel.includes("BUY");
  const isStreetBearish = (abr !== null && abr >= 3.5) || consLabel.includes("SELL");
  const isETFNoSignal   = !essText && !composite && category === "LOW_CONVICTION_REDUCTION";

  // Signal alignment
  let alignment = matrixClass;
  if (!alignment) {
    if (isESSBearish && isStreetBullish)  alignment = "MAJOR_DIVERGENCE";
    else if (isESSBullish && !isStreetBearish) alignment = "FULL_ALIGNMENT_BULLISH";
    else if (isESSBearish && !isStreetBullish) alignment = "FULL_ALIGNMENT_BEARISH";
    else alignment = "PARTIAL_ALIGNMENT";
  }

  // Earnings context classification (FMP)
  let earningsCtx = "EARNINGS_CONTEXT_UNKNOWN";
  if (fmpCovered && beatRate !== null && epsSurprise !== null) {
    if (beatRate < 0.5 && revGrowth !== null && revGrowth < 0) earningsCtx = "FUNDAMENTAL_DETERIORATION";
    else if (beatRate > 0.70 && epsSurprise < -20)             earningsCtx = "SINGLE_QUARTER_MISS";
    else if (beatRate > 0.75 && revGrowth !== null && revGrowth > 0.1) earningsCtx = "STRONG_FUNDAMENTAL";
    else                                                        earningsCtx = "IN_LINE_FUNDAMENTAL";
  }

  // Stale data check
  const isConvictionProtected = ucfLabel === "CORE_CONVICTION_LEADER" || ucfLabel === "HIGH_CONVICTION_ANCHOR";

  // ── Posture determination ────────────────────────────────────────────────
  let posture, postureClass, rationale, keyPoints = [], evidence = [];

  if (context.isReduction) {
    // --- PASSIVE REDUCTION (ETF / no ESS signal)
    if (isETFNoSignal) {
      posture = "PASSIVE REDUCTION"; postureClass = "dil-passive";
      rationale = `${escHtml(sym)} is held as a passive allocation vehicle. No individual ESS signal data exists. Reduction frees capital for higher-conviction direct holdings under the Concentrated Alpha mandate.`;
      keyPoints = ["No individual ESS coverage — ETF or passive fund", "Reduction is portfolio construction, not signal-driven", "FVI tier reflects vehicle quality (independent of conviction)"];
    }
    // --- UCF CONVICTION ANCHOR — floor at INVESTIGATE
    else if (isConvictionProtected && isESSBearish) {
      posture = "INVESTIGATE BEFORE ACTING"; postureClass = "dil-investigate";
      rationale = `${escHtml(sym)} carries a UCF conviction classification of ${escHtml(ucfLabel)}. Despite the bearish ESS, reducing a conviction anchor requires a higher evidence standard. Investigate before proceeding.`;
      keyPoints = [`UCF ${escHtml(ucfLabel)} — high strategic portfolio importance`, "Bearish ESS alone insufficient for conviction-anchor reduction", earningsCtx !== "EARNINGS_CONTEXT_UNKNOWN" ? `Earnings context: ${earningsCtx.replace(/_/g," ")}` : ""].filter(Boolean);
    }
    // --- FULL ALIGNMENT BEARISH + FUNDAMENTAL DETERIORATION
    else if ((alignment.includes("FULL_ALIGNMENT_BEARISH") || (!isStreetBullish && isESSBearish)) && earningsCtx === "FUNDAMENTAL_DETERIORATION") {
      posture = "HIGH CONFIDENCE REDUCTION"; postureClass = "dil-high-confidence-red";
      rationale = `${escHtml(sym)}: All signals agree — ESS bearish, analyst consensus bearish, and FMP fundamentals show persistent earnings weakness with declining revenue. Multi-source confirmed reduction signal.`;
      keyPoints = ["Full signal alignment: ESS + analysts + FMP all confirm", beatRate !== null ? `Beat rate 8Q: ${(beatRate*100).toFixed(0)}% (weak earnings track record)` : "", revGrowth !== null ? `Revenue growth: ${(revGrowth*100).toFixed(1)}% YoY` : "", "Multiple independent sources confirm deterioration"].filter(Boolean);
    }
    // --- SINGLE QUARTER MISS (PRIM pattern)
    else if (earningsCtx === "SINGLE_QUARTER_MISS" && isESSBearish && isStreetBullish) {
      posture = "INVESTIGATE BEFORE ACTING"; postureClass = "dil-investigate";
      const beatStr = beatRate !== null ? `${(beatRate*100).toFixed(0)}%` : "—";
      const missStr = epsSurprise !== null ? `${Math.abs(epsSurprise).toFixed(1)}%` : "—";
      const revStr  = revGrowth  !== null ? `${(revGrowth*100).toFixed(1)}%` : "—";
      rationale = `${escHtml(sym)}'s bearish ESS conflicts with street consensus (${escHtml(consLabel)}, ${analystCnt} analysts). Historical beat rate is ${beatStr} over 8 quarters, but the most recent quarter missed by ${missStr}. Revenue remains positive (+${revStr} YoY). This pattern suggests a single-quarter operational miss, not a fundamental deterioration. Analyst targets may be pre-revision.`;
      keyPoints = [`ESS BEARISH — likely momentum from the EPS miss`, `Street: ${escHtml(consLabel)} (${analystCnt} analysts${upsidePct !== null ? ", " + upsidePct.toFixed(1) + "% upside" : ""})`, `Beat rate 8Q: ${beatStr} — historically strong executor`, `EPS miss: −${missStr} (one-quarter outlier)`, `Revenue growth: +${revStr} YoY — business still growing`, "Recommended: wait 3–5 days for post-earnings analyst revisions"];
    }
    // --- MAJOR DIVERGENCE + STRONG FUNDAMENTAL
    else if (alignment === "MAJOR_DIVERGENCE" && earningsCtx === "STRONG_FUNDAMENTAL") {
      posture = "CONFLICTING EVIDENCE"; postureClass = "dil-conflict";
      rationale = `${escHtml(sym)} shows major signal divergence. ESS is bearish while fundamentals are strong and analysts are bullish. The ESS may be capturing short-term momentum rather than fundamental weakness. Operator judgment required — do not act mechanically.`;
      keyPoints = ["⚠ MAJOR DIVERGENCE: ESS bearish vs. Street bullish", beatRate !== null ? `FMP: beat rate ${(beatRate*100).toFixed(0)}% (strong)` : "", revGrowth !== null ? `Revenue growth: +${(revGrowth*100).toFixed(1)}%` : "", "ESS is momentum-based; may not reflect forward fundamentals", "Consider: is the price move temporary or thesis-breaking?"].filter(Boolean);
    }
    // --- ACTIONABLE (bearish + some corroboration)
    else if (isESSBearish) {
      const corroborated = zacks !== null && zacks >= 3.5 || danelfin !== null && danelfin <= 3;
      if (corroborated || alignment.includes("FULL_ALIGNMENT_BEARISH")) {
        posture = "ACTIONABLE"; postureClass = "dil-actionable";
        rationale = `${escHtml(sym)}: Bearish ESS corroborated by at least one additional signal (Zacks/Danelfin). Reduction signal has multi-source support. ${earningsCtx !== "EARNINGS_CONTEXT_UNKNOWN" ? "Earnings context: " + earningsCtx.replace(/_/g," ") + "." : ""}`;
        keyPoints = [`ESS: ${escHtml(essText || fidRating || "BEARISH")}`, zacks !== null ? `Zacks: ${zacks.toFixed(1)} (corroborates)` : "", composite !== null ? `Composite: ${composite.toFixed(2)}` : ""].filter(Boolean);
      } else {
        posture = "INVESTIGATE BEFORE ACTING"; postureClass = "dil-investigate";
        rationale = `${escHtml(sym)}: Bearish ESS signal is not strongly corroborated by other sources. ${isStreetBullish ? "Street analysts are bullish — divergence detected." : ""} Investigate before acting.`;
        keyPoints = ["ESS BEARISH — single-source signal", isStreetBullish ? `Street: ${escHtml(consLabel)} (${analystCnt} analysts) — disagrees with ESS` : "", earningsCtx !== "EARNINGS_CONTEXT_UNKNOWN" ? `Earnings context: ${earningsCtx.replace(/_/g," ")}` : ""].filter(Boolean);
      }
    }
    // --- DEFAULT MONITOR
    else {
      posture = "MONITOR"; postureClass = "dil-monitor";
      rationale = `${escHtml(sym)}: Reduction is driven by ${escHtml(category.replace(/_/g," "))} rather than signal deterioration. Signal picture does not provide strong independent confirmation.`;
      keyPoints = [`Category: ${escHtml(category.replace(/_/g," "))}`, isESSBullish ? "Note: ESS is bullish — this is an allocation-driven reduction, not signal-driven" : ""].filter(Boolean);
    }
  }

  // ── DEPLOYMENT posture ──────────────────────────────────────────────────
  else if (context.isDeployment) {
    if (alignment === "FULL_ALIGNMENT_BULLISH" && (earningsCtx === "STRONG_FUNDAMENTAL" || earningsCtx === "IN_LINE_FUNDAMENTAL")) {
      posture = "HIGH CONFIDENCE BUY"; postureClass = "dil-high-confidence-buy";
      rationale = `${escHtml(sym)}: All signals aligned bullish — ESS, analyst consensus, and FMP fundamentals all support this deployment candidate.`;
      keyPoints = ["Full signal alignment: ESS + Street + FMP all bullish", beatRate !== null ? `Beat rate 8Q: ${(beatRate*100).toFixed(0)}%` : "", revGrowth !== null ? `Revenue growth: +${(revGrowth*100).toFixed(1)}% YoY` : "", ucfLabel ? `UCF: ${escHtml(ucfLabel)}` : ""].filter(Boolean);
    } else if (isESSBullish && alignment !== "MAJOR_DIVERGENCE") {
      posture = "ACTIONABLE"; postureClass = "dil-actionable";
      rationale = `${escHtml(sym)}: Bullish ESS signal with ${alignment === "FULL_ALIGNMENT_BULLISH" ? "full" : "partial"} signal agreement. CW-DAS conviction ranking supported by signal evidence.`;
      keyPoints = [`ESS: ${escHtml(essText || fidRating || "BULLISH")}`, isStreetBullish ? `Street: ${escHtml(consLabel)} (${analystCnt} analysts)` : "Street consensus: neutral/mixed", replayPct !== null && replayPct > 50 ? `Replay: ${replayPct.toFixed(0)}th percentile` : "", earningsCtx !== "EARNINGS_CONTEXT_UNKNOWN" ? `Earnings context: ${earningsCtx.replace(/_/g," ")}` : ""].filter(Boolean);
    } else if (alignment === "MAJOR_DIVERGENCE") {
      posture = "CONFLICTING EVIDENCE"; postureClass = "dil-conflict";
      rationale = `${escHtml(sym)}: CW-DAS model is bullish based on conviction tier and replay, but external signals diverge. Verify before deploying.`;
      keyPoints = ["⚠ Signal divergence detected", "CW-DAS conviction supported; external signals mixed"];
    } else {
      posture = "ACTIONABLE"; postureClass = "dil-actionable";
      rationale = `${escHtml(sym)}: CW-DAS deployment candidate. Conviction tier and replay support the recommendation.`;
      keyPoints = [ucfLabel ? `UCF: ${escHtml(ucfLabel)}` : "", replayPct !== null ? `Replay: ${replayPct.toFixed(0)}th pct` : ""].filter(Boolean);
    }
  }

  // ── Evidence list (always cited with source + date) ──────────────────────
  if (essText || fidRating)
    evidence.push(`${escHtml(fidRating || essText || "—")} [Fidelity StarMine, ${today_str}]`);
  if (zacks != null)
    evidence.push(`Zacks: ${zacks.toFixed(1)} [Zacks, ${today_str}]`);
  if (abr != null)
    evidence.push(`ABR: ${abr.toFixed(2)} (${escHtml(consLabel)}, ${analystCnt} analysts) [Yahoo, ${escHtml(consRefresh || "—")}]`);
  if (epsSurprise != null)
    evidence.push(`EPS surprise: ${epsSurprise.toFixed(1)}% [FMP, ${escHtml(fmpDate || "—")}]`);
  if (beatRate != null)
    evidence.push(`Beat rate 8Q: ${(beatRate*100).toFixed(0)}% [FMP, ${escHtml(fmpDate || "—")}]`);
  if (revGrowth != null)
    evidence.push(`Revenue growth Q1 YoY: ${(revGrowth*100).toFixed(1)}% [FMP, ${escHtml(fmpDate || "—")}]`);
  if (matrixClass)
    evidence.push(`Signal alignment: ${escHtml(matrixClass.replace(/_/g," "))} [Computed, ${today_str}]`);
  if (ucfLabel)
    evidence.push(`UCF: ${escHtml(ucfLabel)} [Computed, PAR time]`);

  // DIL Phase 2 — price context (display-only; no scoring influence)
  const pcObj = priceCtx || {};
  let priceContextDisplay = null;
  if (pcObj.return_1d != null || pcObj.return_5d != null || pcObj.pct_52w_range != null) {
    const fmt = v => v != null ? `${v > 0 ? "+" : ""}${Number(v).toFixed(2)}%` : "—";
    const r1d = pcObj.return_1d != null ? fmt(pcObj.return_1d) : "—";
    const r5d = pcObj.return_5d != null ? fmt(pcObj.return_5d) : "—";
    const r1m = pcObj.return_1m != null ? fmt(pcObj.return_1m) : "—";
    const w52 = pcObj.pct_52w_range != null ? `${Number(pcObj.pct_52w_range).toFixed(0)}th %ile` : "—";
    const earningsNote = pcObj.next_earnings_date
      ? `Next earnings: ${escHtml(pcObj.next_earnings_date)}`
      : "";
    priceContextDisplay = { r1d, r5d, r1m, w52, earningsNote };
  }

  return { posture, postureClass, rationale, keyPoints: keyPoints.filter(Boolean), evidence, priceContextDisplay };
}

function _dilHtml(dilResult) {
  if (!dilResult || !dilResult.posture) return "";
  const { posture, postureClass, rationale, keyPoints, evidence, priceContextDisplay } = dilResult;

  const kpHtml = keyPoints.length > 0
    ? `<ul class="dil-key-points">${keyPoints.map(p => `<li>${p}</li>`).join("")}</ul>`
    : "";

  const evHtml = evidence.length > 0
    ? `<div class="dil-evidence">
        <div class="dil-evidence-title">Signal Evidence</div>
        <ul>${evidence.map(e => {
          const parts = e.match(/^(.*)\s\[([^,\]]+),\s*([^\]]+)\]$/);
          return parts
            ? `<li>${escHtml(parts[1])} <span class="dil-src">[${escHtml(parts[2])}, ${escHtml(parts[3])}]</span></li>`
            : `<li>${e}</li>`;
        }).join("")}</ul>
      </div>`
    : "";

  const pcHtml = priceContextDisplay
    ? `<div class="dil-price-context">
        <div class="dil-price-ctx-title">Price Context <span class="dil-price-ctx-note">(display-only)</span></div>
        <div class="dil-price-ctx-grid">
          <div class="dil-price-ctx-cell"><span class="dil-pc-label">1D</span><span class="dil-pc-val">${priceContextDisplay.r1d}</span></div>
          <div class="dil-price-ctx-cell"><span class="dil-pc-label">5D</span><span class="dil-pc-val">${priceContextDisplay.r5d}</span></div>
          <div class="dil-price-ctx-cell"><span class="dil-pc-label">1M</span><span class="dil-pc-val">${priceContextDisplay.r1m}</span></div>
          <div class="dil-price-ctx-cell"><span class="dil-pc-label">52W</span><span class="dil-pc-val">${priceContextDisplay.w52}</span></div>
        </div>
        ${priceContextDisplay.earningsNote ? `<div class="dil-earnings-note">${priceContextDisplay.earningsNote}</div>` : ""}
      </div>`
    : "";

  return `<div class="dil-section">
    <div class="dil-section-title">⚡ Decision Intelligence</div>
    <div class="dil-posture ${escHtml(postureClass)}">${escHtml(posture)}</div>
    <div class="dil-rationale-text">${rationale}</div>
    ${kpHtml}
    ${evHtml}
    ${pcHtml}
    <div class="dil-advisory">Advisory only — all postures are interpretive. Operator remains the decision maker.</div>
  </div>`;
}

function renderReductionQueuePlaceholder() {
  const el = document.getElementById("reductionQueueContainer");
  if (!el) return;
  el.innerHTML = `<div class="rq-section"><div class="rq-panel">
    <div class="rq-header">
      <span class="rq-title">Reduction Queue — Top 10</span>
      <span class="rq-advisory">Loading capital source data…</span>
    </div>
    <div class="rq-loading">Waiting for CRA capital sources…</div>
  </div></div>`;
}

const _RQ_PRIORITY_ORDER = { URGENT: 0, HIGH: 1, MODERATE: 2, LOW: 3, DEFER: 4 };
const _RQ_CATEGORY_LABELS = {
  SIGNAL_DETERIORATION:   "Signal Deterioration",
  STRATEGIC_EXIT:         "Strategic Exit",
  OVERWEIGHT_REDUCTION:   "Overweight Reduction",
  TAX_AWARE_EXIT:         "Tax-Aware Exit",
  LOW_CONVICTION_REDUCTION: "Passive Exposure",
};

function renderReductionQueue(sources, totalPool, fviData, overlayBySymbol, ucfBySymbol, fidBySymbol) {
  const el = document.getElementById("reductionQueueContainer");
  if (!el) return;

  // Normalise lookup maps (may be null/undefined from caller)
  overlayBySymbol = overlayBySymbol || {};
  ucfBySymbol     = ucfBySymbol     || {};
  fidBySymbol     = fidBySymbol     || {};

  if (!sources || sources.length === 0) {
    el.innerHTML = `<div class="rq-section"><div class="rq-panel">
      <div class="rq-header">
        <span class="rq-title">Reduction Queue — Top 10</span>
      </div>
      <div class="rq-no-data">No capital sources identified. Portfolio may be fully deployed or all candidates are below the minimum proceeds threshold.</div>
    </div></div>`;
    return;
  }

  // Sort: priority ascending (URGENT first), then proceeds descending
  const sorted = [...sources].sort((a, b) => {
    const pa = _RQ_PRIORITY_ORDER[a.priority] ?? 9;
    const pb = _RQ_PRIORITY_ORDER[b.priority] ?? 9;
    if (pa !== pb) return pa - pb;
    return (b.estimated_proceeds || 0) - (a.estimated_proceeds || 0);
  });

  const top10 = sorted.slice(0, 10);

  // Pool summary (exclude BLOCKED + DEFER from pool)
  const poolSources = sources.filter(s => !s.blocked_by_policy && s.priority !== "DEFER");
  const poolTotal = totalPool != null ? totalPool : poolSources.reduce((sum, s) => sum + (s.estimated_proceeds || 0), 0);
  const blockedCount = sources.filter(s => s.blocked_by_policy).length;

  const rows = top10.map((s, idx) => {
    const blocked = s.blocked_by_policy;
    const deferred = s.policy_type === "SELL_LAST";
    const reviewRequired = s.operator_review_required;
    const rowClass = blocked ? " rq-row-blocked" : "";

    // Priority badge
    const pri = s.priority || "LOW";
    const priBadge = `<span class="rq-pri rq-pri-${pri}">${escHtml(pri)}</span>`;

    // Proceeds + sizing
    const proceeds = s.estimated_proceeds || 0;
    const sizing = s.sizing_pct != null ? Math.round(s.sizing_pct * 100) + "%" : "—";
    const proceedsHtml = `<span class="rq-proceeds">${formatMV(proceeds)}</span><br><span class="rq-sizing">${sizing} of ${formatMV(s.current_value_usd || 0)}</span>`;

    // Policy state badge
    let policyBadge = "";
    if (blocked) {
      policyBadge = `<span class="rq-policy-blocked">🔒 Blocked</span>`;
    } else if (deferred) {
      policyBadge = `<span class="rq-policy-deferred">⏸ Sell Last</span>`;
    } else if (reviewRequired) {
      policyBadge = `<span class="rq-policy-review">⚠ Review</span>`;
    }

    // FVI tier
    let fviBadge = "";
    if (fviData) {
      const fvi = fviData[s.symbol] || fviData[(s.symbol || "").toUpperCase()];
      if (fvi && fvi.fvi_tier) {
        const tier = fvi.fvi_tier;
        fviBadge = `<span class="rq-fvi fvi-${tier}" title="Fund Vehicle Intelligence: ${tier}">${tier}</span>`;
      }
    }

    const catLabel = _RQ_CATEGORY_LABELS[s.category] || escHtml(s.category || "—");
    const essText = s.ess_score_text ? `<span class="ess-text ess-${(s.ess_score_text || '').toLowerCase().replace('_','-')}" style="font-size:0.68rem">${escHtml(s.ess_score_text)}</span>` : "";

    // ── ARCH-05: Intelligence Profile ──────────────────────────────────────
    const profileId = `rq-profile-${idx}`;
    const sym = s.symbol || "";
    const symUpper = sym.toUpperCase();

    // Overlay signals (security_overlays)
    const ov  = overlayBySymbol[symUpper] || {};
    const ucf = ucfBySymbol[symUpper]     || {};
    const fid = fidBySymbol[symUpper]     || {};
    const ac  = (renderReductionQueue._consBySymbol || {})[symUpper] || {};

    const composite    = parseFloat(ov.composite_score || fid.composite_score || 0);
    const essOv        = ov.ess_score_text || "";
    const sigDir       = ov.signal_direction || "";
    const zacks        = ov.zacks_rating  || fid.zacks_rating  || "";
    const danelfin     = ov.danelfin_score || fid.danelfin_score || "";
    const replayPct    = ov.replay_percentile  != null ? parseFloat(ov.replay_percentile) : null;
    const portPct      = parseFloat(ov.percent_of_portfolio || s.current_value_usd / 4650 || 0);
    const ucfLabel     = ucf.ucf_label  || "";
    const ucfRank      = ucf.ucf_rank   || "";
    const ucfScore     = ucf.ucf_score  != null ? parseFloat(ucf.ucf_score) : null;
    const sigSummary   = ucf.signal_summary || s.evidence_summary || "";

    // Analyst consensus (Yahoo supplemental)
    const abr           = ac.abr           != null ? parseFloat(ac.abr).toFixed(2) : null;
    const analystCount  = ac.analyst_count || null;
    const priceTarget   = ac.price_target  != null ? parseFloat(ac.price_target).toFixed(2) : null;
    const upsidePct     = ac.upside_pct    != null ? parseFloat(ac.upside_pct).toFixed(1) : null;
    const consLabel     = ac.consensus_label || null;
    const consStrength  = ac.consensus_strength || null;
    const consRefresh   = ac.refresh_date   || null;

    // Fidelity StarMine rating + consensus matrix alignment
    const fidRating     = fid.fidelity_rating    || null;
    const fidDirection  = fid.fidelity_direction || null;
    const consMat       = fid.consensus_matrix   || {};
    const consMatClass  = consMat.classification || null;  // FULL_ALIGNMENT_BULLISH / MAJOR_DIVERGENCE / PARTIAL_ALIGNMENT
    const essDir        = consMat.ess_direction    || null;
    const yahooDir      = consMat.yahoo_direction  || null;
    const zacksDir      = consMat.zacks_direction  || null;
    const sigCount      = consMat.signals_available || 0;

    const _valClass = (v, good, bad) => {
      if (!v) return "";
      const u = String(v).toUpperCase();
      if (u.includes(good)) return "val-bullish";
      if (u.includes(bad)) return "val-bearish";
      return "val-neutral";
    };

    const profileItem = (lbl, val, cls) =>
      val !== null && val !== undefined && String(val).trim() !== ""
        ? `<div class="rq-profile-row-item"><span class="rq-profile-lbl">${lbl}</span><span class="rq-profile-val ${cls || ''}">${escHtml(String(val))}</span></div>`
        : "";

    // Suggested reduction weight
    const currentMV  = s.current_value_usd || 0;
    const proceedsEst = proceeds;
    const suggestedMV = Math.max(0, currentMV - proceedsEst);
    const totalPortMV = (_lastAnalysisData && _lastAnalysisData.total_market_value) || 0;
    const suggestedPct = totalPortMV > 0 ? (suggestedMV / totalPortMV * 100).toFixed(2) + "%" : "—";

    // Human rationale: use evidence_summary from CRA source if available, otherwise build one
    let rationale = "";
    if (sigSummary) {
      rationale = sigSummary;
    } else if (s.category === "LOW_CONVICTION_REDUCTION") {
      rationale = `${escHtml(sym)} is held as a passive allocation vehicle with no individual ESS signal data. Under the Concentrated Alpha mandate, this position represents an opportunity cost — capital that could fund a higher-conviction direct holding.`;
    } else if (s.category === "OVERWEIGHT_REDUCTION") {
      rationale = `${escHtml(sym)} is in an allocation node that is overweight vs. the mandate target. Partial reduction brings the portfolio back toward strategic alignment.`;
    } else if (s.category === "TAX_AWARE_EXIT") {
      rationale = `${escHtml(sym)} has an unrealized loss position. Tax-aware exit may improve after-tax returns.`;
    } else if (s.category === "SIGNAL_DETERIORATION") {
      rationale = `${escHtml(sym)} shows deteriorating signal quality (${escHtml(essOv || 'BEARISH')}). ESS and conviction scores have weakened. Priority reduction candidate.`;
    } else {
      rationale = s.evidence_summary ? escHtml(s.evidence_summary) : `${escHtml(sym)}: ${catLabel}`;
    }

    // Fidelity deep-link
    const fidelityUrl = `https://digital.fidelity.com/prgw/digital/research/quote/dashboard/ratings-sentiment?symbol=${encodeURIComponent(sym)}`;
    const fidelityLink = `<a class="rq-fidelity-link" href="${fidelityUrl}" target="_blank" rel="noopener noreferrer">&#128279; Fidelity Ratings</a>`;

    const profileHtml = `
      <div class="rq-profile-grid">
        <div>
          <div class="rq-profile-section-title">Signal Intelligence</div>
          ${profileItem("ESS (StarMine)", fidRating || essOv || "—", _valClass(fidRating || essOv, "BULLISH", "BEARISH"))}
          ${profileItem("Signal Direction", sigDir || "—", _valClass(sigDir, "BULLISH", "BEARISH"))}
          ${profileItem("Zacks Rating", zacks || "—", "")}
          ${profileItem("Danelfin Score", danelfin || "—", "")}
          ${profileItem("Composite Score", composite > 0 ? composite.toFixed(2) : "—", composite > 3 ? "val-bullish" : composite > 0 && composite < 2.5 ? "val-bearish" : "val-neutral")}
          ${replayPct != null ? profileItem("Replay Percentile", replayPct.toFixed(0) + "th", replayPct >= 50 ? "val-bullish" : "val-bearish") : ""}
        </div>
        <div>
          <div class="rq-profile-section-title">Analyst Consensus &amp; Validation</div>
          ${consLabel ? profileItem("Consensus", consLabel.replace(/_/g, " "), _valClass(consLabel, "BUY", "SELL")) : ""}
          ${abr ? profileItem("ABR", abr + (analystCount ? " (" + analystCount + " analysts)" : ""), parseFloat(abr) <= 2 ? "val-bullish" : parseFloat(abr) >= 3.5 ? "val-bearish" : "val-neutral") : ""}
          ${priceTarget ? profileItem("Price Target", "$" + priceTarget, "") : ""}
          ${upsidePct != null ? profileItem("Upside vs Target", upsidePct + "%", parseFloat(upsidePct) > 15 ? "val-bullish" : parseFloat(upsidePct) < -5 ? "val-bearish" : "val-neutral") : ""}
          ${consRefresh ? `<div style="font-size:0.65rem;color:var(--muted);margin-top:4px;">Consensus as of ${escHtml(consRefresh)}</div>` : ""}
          ${consMatClass ? `
          <div class="rq-profile-section-title" style="margin-top:10px;">Signal Agreement</div>
          <div class="rq-profile-row-item">
            <span class="rq-profile-lbl">Alignment</span>
            <span class="rq-profile-val ${_valClass(consMatClass, 'BULLISH', 'DIVERGENCE')}" style="font-size:0.7rem">${escHtml(consMatClass.replace(/_/g,' '))}</span>
          </div>
          ${essDir   ? profileItem("ESS direction",   essDir,   _valClass(essDir,   "BULLISH", "BEARISH")) : ""}
          ${yahooDir ? profileItem("Yahoo consensus", yahooDir, _valClass(yahooDir, "BULLISH", "BEARISH")) : ""}
          ${zacksDir ? profileItem("Zacks direction", zacksDir, _valClass(zacksDir, "BULLISH", "BEARISH")) : ""}
          ` : ""}
        </div>
        <div>
          <div class="rq-profile-section-title">Portfolio Context</div>
          ${profileItem("Current Weight", portPct.toFixed(2) + "%", "")}
          ${profileItem("Current Value", formatMV(currentMV), "")}
          ${profileItem("Est. Proceeds", formatMV(proceedsEst), "")}
          ${profileItem("Suggested Weight", suggestedPct, "")}
          ${profileItem("Reduction Category", catLabel, "")}
          ${ucfLabel ? profileItem("UCF Label", ucfLabel, _valClass(ucfLabel, "CONVICTION", "TRIM_WATCH")) : ""}
          ${ucfScore != null ? profileItem("UCF Score", ucfScore.toFixed(1), ucfScore >= 60 ? "val-bullish" : ucfScore < 30 ? "val-bearish" : "val-neutral") : ""}
          ${ucfRank ? profileItem("UCF Rank", "#" + ucfRank + " of portfolio", "") : ""}
          ${fviBadge ? `<div class="rq-profile-row-item"><span class="rq-profile-lbl">FVI Tier</span><span class="rq-profile-val">${fviBadge}</span></div>` : ""}
          ${profileItem("Policy State", blocked ? "🔒 DO_NOT_SELL" : deferred ? "⏸ SELL_LAST" : "Executable", blocked ? "val-bearish" : "")}
          <div style="margin-top:8px;">${fidelityLink}</div>
        </div>
        <div class="rq-rationale" style="grid-column:1/-1;">
          <strong>Reduction Rationale:</strong> ${rationale}
        </div>
      </div>`;

    // ── DIL Phase 1: compute and inject decision intelligence panel ──────────
    const _fmpBySymDIL = (_lastAnalysisData && _lastAnalysisData.fmp_data_by_symbol) || {};
    const _pcBySymDIL  = (_lastAnalysisData && _lastAnalysisData.price_context_by_symbol) || {};
    const _dilResult = computeDIL(
      sym,
      (renderReductionQueue._consBySymbol || {})[symUpper] || {},
      fidBySymbol[symUpper] || {},
      _fmpBySymDIL[symUpper] || null,
      ucfBySymbol[symUpper] || {},
      overlayBySymbol[symUpper] || {},
      { isReduction: true, isDeployment: false, category: s.category || "" },
      _pcBySymDIL[symUpper] || null
    );
    const dilPanelHtml = _dilHtml(_dilResult);

    const mainRow = `<tr class="rq-row${rowClass}">
      <td class="rq-rank">${idx + 1}</td>
      <td>
        <div class="rq-sym">${escHtml(sym)}</div>
        <div class="rq-cat">${catLabel} ${essText}</div>
        <button class="rq-expand-btn" onclick="(function(){const p=document.getElementById('${profileId}');if(p){p.classList.toggle('rq-open');this.textContent=p.classList.contains('rq-open')?'▲ Less':'▼ Profile';}}).call(this)">▼ Profile</button>
      </td>
      <td>${priBadge}</td>
      <td>${proceedsHtml}</td>
      <td>${policyBadge || '<span style="color:var(--muted);font-size:0.72rem">—</span>'}${fviBadge ? '<br>' + fviBadge : ''}</td>
    </tr>`;

    const profileRow = `<tr class="rq-profile-row" id="${profileId}">
      <td></td>
      <td class="rq-profile-cell" colspan="4">${profileHtml}${dilPanelHtml}</td>
    </tr>`;

    return mainRow + profileRow;
  }).join("");

  const blockedNote = blockedCount > 0
    ? `<span style="font-size:0.7rem;color:var(--muted);margin-left:8px">${blockedCount} blocked by policy</span>`
    : "";

  el.innerHTML = `<div class="rq-section"><div class="rq-panel">
    <div class="rq-header">
      <span class="rq-title">Reduction Queue — Top 10</span>
      <span class="rq-pool-badge">${formatMV(poolTotal)} est. pool</span>
      ${blockedNote}
      <span class="rq-advisory">Source capital — guidance only, not trade instructions</span>
    </div>
    <table class="rq-table">
      <thead><tr>
        <th style="width:28px">Rank</th>
        <th>Symbol / Reason</th>
        <th>Priority</th>
        <th>Est. Proceeds</th>
        <th>Policy / FVI</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </div></div>`;
}

// ─────────────────────────────────────────────────────────────────────────────

let _disShowWatch = false;  // WATCH tier visibility toggle

function renderDislocationWatchlist(data) {
  const el = document.getElementById("dislocationWatchlistContainer");
  if (!el) return;

  const disMap = data.dislocation_by_symbol || {};
  if (!Object.keys(disMap).length) { el.style.display = "none"; return; }

  // Filter to non-NONE entries
  const all = Object.values(disMap).filter(d => d.tier !== "NONE");
  if (!all.length) { el.style.display = "none"; return; }

  el.style.display = "";

  // Count by tier
  const hcCount   = all.filter(d => d.tier === "HIGH_CONVICTION").length;
  const modCount  = all.filter(d => d.tier === "MODERATE").length;
  const watchCount = all.filter(d => d.tier === "WATCH").length;

  // Get overlay lookup for thesis/consistency columns
  const overlays = (data.security_overlays || []);
  const ovBySymbol = {};
  for (const ov of overlays) {
    const s = (ov.symbol || ov.Symbol || "").toUpperCase();
    if (s) ovBySymbol[s] = ov;
  }

  _disShowWatch = false;   // reset on each render

  el.innerHTML = `<div class="dq-panel dis-panel">
    <div class="dis-section-header">
      <span class="dis-section-title">Dislocation Watchlist</span>
      <span class="dis-version-badge">A1 v${escHtml(all[0]?.version || "1.0")}</span>
      <span class="dis-advisory-note">Guidance only — not a trade instruction</span>
    </div>
    <div class="dis-subtitle">Evidence of divergence between verified fundamentals and current market signals.</div>
    <div class="dis-advisory-strip">
      ⚠ Evidence of divergence only — no action implied. Operator judgment required.
    </div>
    <div class="dis-controls">
      <label class="dis-toggle-label">
        <input type="checkbox" id="dis-show-watch" onchange="_disToggleWatch()" ${_disShowWatch ? "checked" : ""}>
        Include WATCH
      </label>
      <div class="dis-summary-chips">
        ${hcCount    ? `<span class="dis-chip dis-chip-hc">${hcCount} HIGH CONVICTION</span>` : ""}
        ${modCount   ? `<span class="dis-chip dis-chip-mod">${modCount} MODERATE</span>` : ""}
        ${watchCount ? `<span class="dis-chip dis-chip-watch">${watchCount} WATCH</span>` : ""}
      </div>
    </div>
    <div class="dis-table-wrap">
      <table class="dis-table">
        <thead><tr>
          <th>Symbol</th>
          <th>Tier</th>
          <th>Class</th>
          <th>Evidence</th>
        </tr></thead>
        <tbody id="dis-table-body"></tbody>
      </table>
    </div>
  </div>`;

  _disRenderRows(all, ovBySymbol);
}

function _disRenderRows(all, ovBySymbol) {
  const tbody = document.getElementById("dis-table-body");
  if (!tbody) return;

  const visible = _disShowWatch
    ? all
    : all.filter(d => d.tier === "HIGH_CONVICTION" || d.tier === "MODERATE");

  visible.sort((a, b) => {
    const order = { HIGH_CONVICTION: 0, MODERATE: 1, WATCH: 2 };
    return (order[a.tier] ?? 3) - (order[b.tier] ?? 3);
  });

  if (!visible.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="dis-empty">No ${_disShowWatch ? "" : "HIGH CONVICTION or MODERATE "}dislocation detected in current portfolio.</td></tr>`;
    return;
  }

  tbody.innerHTML = visible.map((d, i) => {
    const exId = `dis-ex-${i}`;
    const tierLabel = d.tier.replace(/_/g, " ");
    const classShort = (d.dislocation_class || "").replace("A1_", "").replace(/_/g, " ").toLowerCase();
    const evCount = (d.evidence || []).length;
    const evList  = (d.evidence || []).map(e => `<li>${escHtml(e)}</li>`).join("");

    return `<tr class="dis-data-row" onclick="_disToggleExpand('${exId}')">
      <td><span class="dq-sym">${escHtml(d.symbol)}</span></td>
      <td><span class="dis-tier dis-tier-${d.tier}">${tierLabel}</span></td>
      <td><span class="dis-class-badge">${escHtml(classShort)}</span></td>
      <td><span class="dis-evidence-count">${evCount} signals</span></td>
    </tr>
    <tr class="dis-expand-row" id="${exId}">
      <td colspan="4">
        <div class="dis-expand-header">${tierLabel} — ${escHtml(d.symbol)}</div>
        <ul class="dis-evidence-list">${evList}</ul>
      </td>
    </tr>`;
  }).join("");
}

function _disToggleExpand(id) {
  const row = document.getElementById(id);
  if (row) row.classList.toggle("open");
}

function _disToggleWatch() {
  const cb = document.getElementById("dis-show-watch");
  _disShowWatch = cb ? cb.checked : false;
  const data = _lastAnalysisData || _analysisResult;
  if (!data) return;
  const disMap = data.dislocation_by_symbol || {};
  const all = Object.values(disMap).filter(d => d.tier !== "NONE");
  const overlays = data.security_overlays || [];
  const ovBySymbol = {};
  for (const ov of overlays) {
    const s = (ov.symbol || "").toUpperCase();
    if (s) ovBySymbol[s] = ov;
  }
  _disRenderRows(all, ovBySymbol);
}

// ─────────────────────────────────────────────────────────────────────────────
// ISSUE-10 — Analyst Target Intelligence block (CII-005 / Layer 1 transparency)
// Governance: display-only. No scoring, CW-DAS, CRA, or ranking influence.
// ─────────────────────────────────────────────────────────────────────────────

function _dqAnalystTargetHtml(ac) {
  // Only render when we have at least a price target or upside
  if (!ac || (ac.price_target == null && ac.upside_pct == null)) return "";

  const targetStr  = ac.price_target != null
    ? `$${parseFloat(ac.price_target).toFixed(2)}`
    : "—";

  const upsideVal  = ac.upside_pct != null ? parseFloat(ac.upside_pct) : null;
  const upsideStr  = upsideVal != null
    ? `<span class="dq-ati-upside ${upsideVal >= 0 ? 'dq-ati-positive' : 'dq-ati-negative'}">${upsideVal >= 0 ? '+' : ''}${upsideVal.toFixed(1)}%</span>`
    : "—";

  // analyst_count: hide entirely when null (ISSUE-08 dependency — graceful degrade)
  const countHtml  = (ac.analyst_count != null && ac.analyst_count > 0)
    ? `<span class="dq-ati-item"><span class="dq-ati-lbl">Coverage</span><span class="dq-ati-val">${ac.analyst_count} analysts</span></span>`
    : "";

  const dateStr    = ac.refresh_date ? escHtml(ac.refresh_date) : "—";

  return `<div class="dq-analyst-target-block">
    <div class="dq-ati-header">Analyst Target Intelligence</div>
    <div class="dq-ati-row">
      <span class="dq-ati-item">
        <span class="dq-ati-lbl">Target</span>
        <span class="dq-ati-val">${targetStr}</span>
      </span>
      <span class="dq-ati-item">
        <span class="dq-ati-lbl">Upside</span>
        <span class="dq-ati-val">${upsideStr}</span>
      </span>
      ${countHtml}
      <span class="dq-ati-item dq-ati-date">
        <span class="dq-ati-lbl">Sourced</span>
        <span class="dq-ati-val">${dateStr}</span>
      </span>
    </div>
    <div class="dq-ati-advisory">⚠ Guidance only — analyst targets are opinions, not price forecasts. Do not use as trade triggers.</div>
  </div>`;
}

const _DQ_THESIS_OPTIONS      = new Set(["INTACT","QUESTIONABLE","DETERIORATING"]);
const _DQ_CONSISTENCY_OPTIONS = new Set(["CONSISTENT","MIXED","CONTRADICTORY","DATA_ANOMALY"]);

function _dqApplyFilters(queue) {
  const allThesis      = _dqFilterThesis.size === _DQ_THESIS_OPTIONS.size;
  const allConsistency = _dqFilterConsistency.size === _DQ_CONSISTENCY_OPTIONS.size;
  const allModifier    = _dqFilterModifier === "ALL";
  if (allThesis && allConsistency && allModifier) return queue;

  return queue.filter(c => {
    const bd          = c.score_breakdown || {};
    const thesis      = bd.thesis_integrity || "";
    const consistency = bd.fundamental_consistency || "";
    const mod         = parseFloat(bd.fundamental_modifier) || 0;

    // Only filter on known values — unknown / empty data passes through
    if (!allThesis && _DQ_THESIS_OPTIONS.has(thesis) && !_dqFilterThesis.has(thesis)) return false;
    if (!allConsistency && _DQ_CONSISTENCY_OPTIONS.has(consistency) && !_dqFilterConsistency.has(consistency)) return false;

    if (_dqFilterModifier === "POSITIVE" && mod <= 0) return false;
    if (_dqFilterModifier === "NEUTRAL"  && mod !== 0) return false;
    if (_dqFilterModifier === "NEGATIVE" && mod >= 0) return false;

    return true;
  });
}

function _dqToggleFilterPanel(e, which) {
  e.stopPropagation();
  ["thesis","consistency","modifier"].forEach(k => {
    const p = document.getElementById(`dq-fp-${k}`);
    if (p) { k === which ? p.classList.toggle("open") : p.classList.remove("open"); }
  });
}

function _dqThesisChange(val, checked) {
  if (checked) _dqFilterThesis.add(val); else _dqFilterThesis.delete(val);
  _dqUpdateFilterBadge("thesis", _dqFilterThesis.size < _DQ_THESIS_OPTIONS.size);
  _dqRefreshTable();
}

function _dqConsistencyChange(val, checked) {
  if (checked) _dqFilterConsistency.add(val); else _dqFilterConsistency.delete(val);
  _dqUpdateFilterBadge("consistency", _dqFilterConsistency.size < _DQ_CONSISTENCY_OPTIONS.size);
  _dqRefreshTable();
}

function _dqModifierChange(val) {
  _dqFilterModifier = val;
  _dqUpdateFilterBadge("modifier", val !== "ALL");
  _dqRefreshTable();
}

function _dqUpdateFilterBadge(which, active) {
  const btn = document.getElementById(`dq-fb-${which}`);
  if (btn) btn.classList.toggle("dq-filter-active", active);
}

function _dqRefreshTable() {
  const dq = _analysisResult && _analysisResult.deployment_queue;
  if (!dq || !Array.isArray(dq.queue)) return;

  const filtered = _dqApplyFilters(dq.queue);
  const limit    = _dqShowAll ? filtered.length : DQ_DEFAULT_ROWS;
  _dqRenderTableRows(filtered, "dq-queue-table-body", limit);

  // Update view-all button
  const btn = document.getElementById("dq-view-all-btn");
  if (btn) {
    if (filtered.length <= DQ_DEFAULT_ROWS) {
      btn.style.display = "none";
    } else {
      btn.style.display = "";
      btn.textContent = _dqShowAll
        ? `▲ Show top ${DQ_DEFAULT_ROWS} only`
        : `▼ View all ${filtered.length} candidates`;
    }
  }

  // Update filtered count badge
  const countEl = document.getElementById("dq-filtered-count");
  if (countEl) {
    const total = dq.queue.length;
    const shown = filtered.length;
    countEl.textContent = shown < total ? `${shown} of ${total}` : "";
  }
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

// ─────────────────────────────────────────────────────────────────────────────
// Phase 8.0B.X — Company Context Enrichment
// ─────────────────────────────────────────────────────────────────────────────

let _securityMetadata = {};   // {symbol → {sector, industry, country, quote_type}}

// Called once after analysis loads — non-blocking
async function _loadSecurityMetadata() {
  try {
    const resp = await fetch("/api/security-metadata");
    if (resp.ok) {
      _securityMetadata = await resp.json();
    }
  } catch (_) {
    // Fail-open: snapshot degrades to "—" for all fields
  }
}

// Clean Fidelity-style security description into a readable company name
function _cleanCompanyName(desc, symbol) {
  if (!desc || !desc.trim()) return symbol;
  return desc
    .replace(/\s+SPON(?:SORED)?\s+ADS?.*$/i, " (ADR)")
    .replace(/\s+DEP(?:OSITORY)?\s+REC(?:EIPT)?.*$/i, " (ADR)")
    .replace(/\s+EACH\s+REP.*$/i, "")
    .replace(/\s+ORD\s+[A-Z]{2,3}\s*\d*$/i, "")
    .replace(/\s+COM(?:MON)?\s+(?:STK|STOCK|SH(?:ARES?)?)(?:\s+USD\d+)?$/i, "")
    .replace(/\s+CL(?:ASS)?\s+[A-Z]$/i, "")
    .replace(/\s+INC(?:ORPORATED)?\.?\s*$/i, " Inc.")
    .replace(/\s+CORP(?:ORATION)?\.?\s*$/i, " Corp.")
    .replace(/\s+HOLDINGS?\s+CO(?:MPANY)?$/i, " Holdings")
    .replace(/\s+CO(?:MPANY)?\.?\s*$/i, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

// ── Fundamental Snapshot (FMP Diagnostic Overlay — Phase 8.0B.1B.5) ──────────
// Display-only: NO scoring, NO ranking, NO recommendation changes.

function _fmpF(meta, key) {
  // Return float or null from metadata FMP field
  const v = meta[key];
  if (v === undefined || v === null || v === "") return null;
  const n = parseFloat(v);
  return isNaN(n) ? null : n;
}

// ── Thesis Integrity ──────────────────────────────────────────────────────────
// INTACT / QUESTIONABLE / DETERIORATING / INSUFFICIENT_DATA
function _fmpThesisIntegrity(meta) {
  const cov = meta.fmp_coverage || "";
  if (!cov || cov === "NO_DATA" || cov === "ETF_NOT_APPLICABLE") {
    return { label: "INSUFFICIENT_DATA", cls: "nodata", evidence: [] };
  }

  const rev   = _fmpF(meta, "fmp_revenue_growth");
  const beat  = _fmpF(meta, "fmp_beat_rate");
  const accel = _fmpF(meta, "fmp_revenue_accel");

  if (rev === null && beat === null) {
    return { label: "INSUFFICIENT_DATA", cls: "nodata", evidence: [] };
  }

  const evidence = [];
  if (rev   !== null) evidence.push("Rev " + (rev >= 0 ? "+" : "") + (rev * 100).toFixed(1) + "%");
  if (beat  !== null) evidence.push("Beat " + Math.round(beat * 100) + "%");
  if (accel !== null) evidence.push("Accel " + (accel >= 0 ? "+" : "") + (accel * 100).toFixed(1) + "pp");

  // DETERIORATING: revenue declining AND (beat weak OR strong deceleration)
  const isDeteriorating =
    (rev !== null && rev < -0.02 && beat !== null && beat < 0.65) ||
    (rev !== null && rev < -0.02 && accel !== null && accel < -0.50);

  // INTACT: positive revenue + decent beat + not heavily decelerating
  const isIntact =
    (rev === null || rev >= 0) &&
    (beat === null || beat >= 0.625) &&
    (accel === null || accel >= -0.20);

  if (isDeteriorating) return { label: "DETERIORATING",    cls: "deteriorating", evidence };
  if (isIntact)        return { label: "INTACT",           cls: "intact",        evidence };
  return                      { label: "QUESTIONABLE",     cls: "questionable",  evidence };
}

// ── Fundamental Consistency ───────────────────────────────────────────────────
// CONSISTENT / MIXED / CONTRADICTORY / DATA_ANOMALY
function _fmpFundamentalConsistency(meta, ov, thesis) {
  const cov = meta.fmp_coverage || "";
  if (!cov || cov === "NO_DATA" || cov === "ETF_NOT_APPLICABLE") {
    return { label: "INSUFFICIENT_DATA", cls: "nodata", evidence: [] };
  }

  const ess    = ((ov && ov.ess_score_text) || "").toUpperCase();
  const dan    = ov ? parseFloat(ov.danelfin_score || 0) || 0 : 0;
  const ev     = _fmpF(meta, "fmp_ev_ebitda");
  const rev    = _fmpF(meta, "fmp_revenue_growth");

  const signalBullish = ess.includes("BULLISH") && !ess.includes("BEARISH");
  const signalBearish = ess.includes("BEARISH");

  const evidence = [];
  if (ess)    evidence.push("ESS " + ess.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase()));
  if (dan > 0) evidence.push("Danelfin " + dan.toFixed(1));

  // DATA_ANOMALY: extreme valuation with declining revenue
  if (ev !== null && ev > 80 && rev !== null && rev < -0.02) {
    return { label: "DATA_ANOMALY", cls: "anomaly",
      evidence: [...evidence, "EV/EBITDA " + ev.toFixed(1) + "x with declining revenue"] };
  }

  const thesisLabel = thesis.label;

  // CONSISTENT: signals and fundamentals agree
  if ((signalBullish && thesisLabel === "INTACT") ||
      (signalBearish && thesisLabel === "DETERIORATING")) {
    return { label: "CONSISTENT", cls: "consistent", evidence };
  }

  // CONTRADICTORY: strongly bullish signals + deteriorating fundamentals + weak beat
  const beat = _fmpF(meta, "fmp_beat_rate");
  if (signalBullish && thesisLabel === "DETERIORATING" && (beat === null || beat < 0.60)) {
    return { label: "CONTRADICTORY", cls: "contradictory",
      evidence: [...evidence, "Bullish signals vs. deteriorating fundamentals"] };
  }

  // MIXED: partial alignment
  return { label: "MIXED", cls: "mixed", evidence };
}

// ── Dislocation Detection ─────────────────────────────────────────────────────
// NONE / POTENTIAL / HIGH CONVICTION
function _fmpDislocationType(meta, ov, thesis, consistency) {
  const cov = meta.fmp_coverage || "";
  if (!cov || cov === "NO_DATA" || cov === "ETF_NOT_APPLICABLE") {
    return { label: "N/A", cls: "nodata", evidence: [] };
  }

  const thesisLabel = thesis.label;
  const beat  = _fmpF(meta, "fmp_beat_rate");
  const dan   = ov ? parseFloat(ov.danelfin_score || 0) || 0 : 0;
  const ess   = ((ov && ov.ess_score_text) || "").toUpperCase();
  const signalBearishOrNeutral = ess.includes("BEARISH") || ess === "NEUTRAL" || ess === "";

  // HIGH CONVICTION dislocation: intact thesis + strong beats + signal weakness
  if (thesisLabel === "INTACT" && beat !== null && beat >= 0.875 &&
      (signalBearishOrNeutral || dan < 1.5)) {
    return { label: "HIGH CONVICTION", cls: "high-conviction",
      evidence: ["Intact thesis with bearish/neutral signals"] };
  }

  // POTENTIAL dislocation: intact thesis + decent beats but AI signal modest
  if (thesisLabel === "INTACT" && beat !== null && beat >= 0.75 && dan < 3.0) {
    return { label: "POTENTIAL", cls: "potential",
      evidence: ["Intact thesis, Danelfin " + dan.toFixed(1) + " (moderate signal)"] };
  }

  return { label: "NONE", cls: "none", evidence: [] };
}

// ISSUE-04C: adapter — converts backend DislocationType dict to the {label, cls, evidence}
// shape expected by _dqFundamentalSnapshotHtml().
function _disFromBackend(d) {
  if (!d || d.tier === "NONE" || d.tier === "none") {
    return { label: "NONE", cls: "none", evidence: [] };
  }
  const tierMap = {
    HIGH_CONVICTION: { label: "HIGH CONVICTION", cls: "high-conviction" },
    MODERATE:        { label: "MODERATE",         cls: "potential" },    // reuse "potential" CSS for amber
    WATCH:           { label: "WATCH",            cls: "watch" },
  };
  const mapped = tierMap[d.tier] || { label: d.tier.replace(/_/g," "), cls: "none" };
  return { label: mapped.label, cls: mapped.cls, evidence: Array.isArray(d.evidence) ? d.evidence : [] };
}

// ── Fundamental Snapshot HTML ─────────────────────────────────────────────────

function _dqFundamentalSnapshotHtml(sym, metadataMap, ov) {
  const meta = metadataMap[(sym || "").toUpperCase()] || {};
  const cov  = meta.fmp_coverage || "";

  // Suppress entirely if no FMP data and not an ETF
  if (!cov || cov === "NO_DATA") return "";

  const thesis      = _fmpThesisIntegrity(meta);
  const consistency = _fmpFundamentalConsistency(meta, ov, thesis);

  // ISSUE-04C: use backend-computed dislocation when available; fall back to JS heuristic
  const _disBackend = (_lastAnalysisData?.dislocation_by_symbol || {})[String(sym || "").toUpperCase()];
  const dislocation = _disBackend
    ? _disFromBackend(_disBackend)
    : _fmpDislocationType(meta, ov, thesis, consistency);

  const rev    = _fmpF(meta, "fmp_revenue_growth");
  const roic   = _fmpF(meta, "fmp_roic");
  const fcf    = _fmpF(meta, "fmp_fcf_yield");
  const beat   = _fmpF(meta, "fmp_beat_rate");
  const ev     = _fmpF(meta, "fmp_ev_ebitda");
  const netBuy = _fmpF(meta, "fmp_net_buy_score");
  const cons   = meta.fmp_consensus || "";

  function fmtPct(v) { if (v === null) return "—"; return (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "%"; }
  function fmtX(v)   { if (v === null) return "—"; return v.toFixed(1) + "x"; }
  function fmtF(v)   { if (v === null) return "—"; return (v * 100).toFixed(1) + "%"; }
  function fmtBeat(v){ if (v === null) return "—"; return Math.round(v * 100) + "% (" + (meta.fmp_beats_8q || "?") + "/8q)"; }
  function cls(v, pos, neg) { if (v === null) return ""; return v > pos ? " pos" : v < neg ? " neg" : ""; }

  // ETF: show brief note
  if (cov === "ETF_NOT_APPLICABLE") {
    return `<div class="dq-fundamental-snapshot">
      <div class="dq-fs-title">Fundamental Snapshot</div>
      <div style="font-size:0.78rem;color:var(--muted);font-style:italic">ETF — fundamental analysis not applicable.</div>
    </div>`;
  }

  const revCls  = cls(rev,  0.05, -0.02);
  const roicCls = cls(roic, 0.10,  0.04);
  const fcfCls  = cls(fcf,  0.03,  0);

  return `<div class="dq-fundamental-snapshot">
    <div class="dq-fs-title">Fundamental Snapshot</div>
    <div class="dq-fs-grid">
      <div class="dq-fs-lbl">Revenue Growth</div>
      <div class="dq-fs-val${revCls}">${fmtPct(rev)}</div>
      <div class="dq-fs-lbl">ROIC</div>
      <div class="dq-fs-val${roicCls}">${fmtF(roic)}</div>
      <div class="dq-fs-lbl">FCF Yield</div>
      <div class="dq-fs-val${fcfCls}">${fmtF(fcf)}</div>
      <div class="dq-fs-lbl">EV / EBITDA</div>
      <div class="dq-fs-val">${fmtX(ev)}</div>
      <div class="dq-fs-lbl">Beat Rate</div>
      <div class="dq-fs-val">${fmtBeat(beat)}</div>
      ${netBuy !== null || cons ? `<div class="dq-fs-lbl">Analyst Consensus</div>
      <div class="dq-fs-val">${cons ? escHtml(cons) : "—"}${netBuy !== null ? ' <span style="font-size:0.72rem;color:var(--muted)">(net buy ' + (netBuy >= 0 ? "+" : "") + Math.round(netBuy) + ')</span>' : ''}</div>` : ""}
    </div>
    <div class="dq-fs-badges">
      <div class="dq-fs-badge-row">
        <div class="dq-fs-badge-lbl">Thesis Integrity</div>
        <span class="dq-fs-badge ${thesis.cls}">${escHtml(thesis.label.replace(/_/g," "))}</span>
        ${thesis.evidence.length ? '<span style="font-size:0.72rem;color:var(--muted)">' + thesis.evidence.map(escHtml).join(" · ") + '</span>' : ''}
      </div>
      <div class="dq-fs-badge-row">
        <div class="dq-fs-badge-lbl">Fundamental Consistency</div>
        <span class="dq-fs-badge ${consistency.cls}">${escHtml(consistency.label)}</span>
        ${consistency.evidence.length > 2 ? '<span style="font-size:0.72rem;color:var(--muted)">' + escHtml(consistency.evidence[2] || "") + '</span>' : ''}
      </div>
      <div class="dq-fs-badge-row">
        <div class="dq-fs-badge-lbl">Dislocation</div>
        <span class="dq-fs-badge ${dislocation.cls}">${escHtml(dislocation.label)}</span>
        ${dislocation.evidence.length ? '<span style="font-size:0.72rem;color:var(--muted)">' + dislocation.evidence.map(escHtml).join(" · ") + '</span>' : ''}
      </div>
    </div>
  </div>`;
}

// ── Why SIH Likes It ─────────────────────────────────────────────────────────

function _dqWhySIHLikesItHtml(c, ucf, ov, bd, dp, trim) {
  const bullets = [];
  const rank       = c.rank;
  const ucfLabel   = (ucf.ucf_label  || "").toUpperCase();
  const ucfRank    = ucf.ucf_rank  != null ? parseInt(ucf.ucf_rank) : null;
  const essText    = (ov.ess_score_text  || c.ess_score_text  || "").toUpperCase();
  const replayOn   = c.replay_supported || ov.replay_supported;
  const replayPct  = ov.replay_percentile != null ? parseFloat(ov.replay_percentile) : null;
  const dan        = ov.danelfin_score  != null ? parseFloat(ov.danelfin_score)  : null;
  const zacks      = ov.zacks_rating    != null ? parseFloat(ov.zacks_rating)    : null;
  const redPen     = bd.redundancy_pen  != null ? parseFloat(bd.redundancy_pen)  : null;
  const concPen    = bd.conc_pen        != null ? parseFloat(bd.conc_pen)        : null;
  const suggestedAdd = dp && dp.suggested_add != null ? parseFloat(dp.suggested_add) : 0;
  const isOver     = ov.is_overweight_vs_target;
  const portfolioPct = ov.percent_of_portfolio != null ? parseFloat(ov.percent_of_portfolio) : null;

  // 1. Rank
  if (rank === 1)      bullets.push("#1 CW-DAS deployment priority");
  else if (rank <= 3)  bullets.push(`Top-${rank} CW-DAS deployment candidate`);

  // 2. UCF conviction
  if (ucfLabel.includes("CORE"))        bullets.push("Core Conviction Leader");
  else if (ucfLabel.includes("HIGH"))   bullets.push("High Conviction Anchor");
  else if (ucfLabel.includes("STRONG")) bullets.push("Strong signal conviction");

  // 3. UCF universe rank
  if (ucfRank != null && ucfRank <= 25 && !ucfLabel.includes("CORE") && !ucfLabel.includes("HIGH")) {
    bullets.push(`Top-25 universe conviction rank (#${ucfRank})`);
  }

  // 4. ESS signal
  if (essText.includes("VERY_BULLISH") || essText.includes("STRONG_BULLISH")) {
    bullets.push("Very Bullish ESS signal");
  } else if (essText.includes("BULLISH")) {
    bullets.push("Bullish ESS signal");
  }

  // 5. Replay
  if (replayOn) {
    if (replayPct != null && replayPct >= 80) {
      bullets.push(`Elite replay backing — ${Math.round(replayPct)}th percentile`);
    } else if (replayPct != null && replayPct >= 60) {
      bullets.push(`Replay-backed thesis — ${Math.round(replayPct)}th percentile`);
    } else {
      bullets.push("Replay-backed thesis");
    }
  }

  // 6. Danelfin AI signal
  if (dan != null && dan >= 4.5) {
    bullets.push(`Strong AI signal (Danelfin ${dan.toFixed(1)})`);
  }

  // 7. Zacks
  if (zacks != null && zacks <= 1.5)       bullets.push("Zacks Strong Buy rating");
  else if (zacks != null && zacks <= 2.5)  bullets.push("Zacks Buy rating");

  // 8. No conflicts
  if (redPen === 0 && concPen === 0) {
    bullets.push("No concentration conflicts");
  }

  // 9. Fundamental modifier context (ISSUE-07)
  const fundMod = bd.fundamental_modifier != null ? parseFloat(bd.fundamental_modifier) : 0;
  if (fundMod >= 2.0)  bullets.push(`Fundamental bonus +${fundMod.toFixed(1)} (strong business quality)`);
  else if (fundMod >= 1.0) bullets.push(`Fundamental bonus +${fundMod.toFixed(1)} (solid fundamentals)`);
  else if (fundMod <= -3.0) bullets.push(`Fundamental penalty ${fundMod.toFixed(1)} (thesis deterioration)`);
  else if (fundMod <= -1.5) bullets.push(`Fundamental penalty ${fundMod.toFixed(1)} (inconsistent fundamentals)`);

  // 10. Low trim / sizing
  if (trim <= 20) {
    bullets.push("Low trim pressure");
  }
  if (suggestedAdd > 0) {
    bullets.push("Actionable — new capital can deploy");
  } else if (!isOver && portfolioPct != null && portfolioPct < 3) {
    bullets.push("Underweight vs. target — sizing opportunity");
  }

  // Suppress if fewer than 2 bullets (edge case: ETFs, funds, sparse data)
  if (bullets.length < 2) return "";

  const items = bullets.slice(0, 5).map(b => `<li>${escHtml(b)}</li>`).join("");
  return `<div class="dq-why-sih">
    <div class="dq-why-sih-title">Why SIH Likes It</div>
    <ul class="dq-why-sih-bullets">${items}</ul>
  </div>`;
}

// ── Company Snapshot helpers ──────────────────────────────────────────────────

// Clean Yahoo investor-language business summary into operator language
function _cleanBusinessSummary(raw) {
  if (!raw) return "";
  let s = raw
    .replace(/,?\s+together with its subsidiaries,?/gi, "")
    .replace(/^[A-Z][^.]{8,90}?(?:Inc\.|Corp\.|Corporation|Company|Limited|Ltd\.|Holdings?\s*Co\.?|PLC|N\.V\.|AG|LLC|Co\.?)\s+(?:designs(?:,?\s+develops)?|operates as a[n]?|engages in|provides|builds and deploys|manufactures|develops|sources and engineers),?\s*/i, "")
    .replace(/,?\s+(?:and internationally|in (?:the United States?|North America|the Americas|Europe|the Middle East|Africa|Asia|Taiwan|China|Japan|Korea|Australia|Germany|the United Kingdom|internationally|Canada)[^.]*)/gi, "")
    .trim();
  if (s && s[0] === s[0].toLowerCase() && s[0] !== s[0].toUpperCase()) {
    s = s[0].toUpperCase() + s.slice(1);
  }
  s = s.replace(/[.,…]+$/, "").trim();
  if (s.length > 10) s += ".";
  return s.length > 15 ? s : raw;
}

// Why It Matters: deterministic sector+industry → operator theme string
const _WHY_IT_MATTERS_MAP = {
  "Technology|Semiconductors":                      "Critical chipmaker supplying AI, mobile, cloud, and automotive compute.",
  "Technology|Semiconductor Equipment & Materials": "Sole-source supplier of advanced chip manufacturing equipment.",
  "Technology|Computer Hardware":                   "Enterprise servers, storage, and compute infrastructure.",
  "Technology|Electronic Components":               "Technology component distribution enabling global electronics supply chains.",
  "Technology|Information Technology Services":     "IT services and solutions driving enterprise digital transformation.",
  "Technology|Software—Application":                "Enterprise software with recurring revenue and platform lock-in.",
  "Technology|Software—Infrastructure":             "Infrastructure software underpinning cloud and enterprise systems.",
  "Technology|Communication Equipment":             "Network infrastructure for enterprise, carrier, and data-center connectivity.",
  "Technology|Scientific & Technical Instruments":  "Precision instruments and measurement technology for industrial and lab markets.",
  "Industrials|Electrical Equipment & Parts":       "Benefits from AI data-center buildout, electrification, and grid modernization.",
  "Industrials|Engineering & Construction":         "Infrastructure construction tied to energy, industrial, and utilities investment.",
  "Industrials|Specialty Industrial Machinery":     "Industrial machinery serving diverse manufacturing end markets.",
  "Industrials|Aerospace & Defense":               "Defense systems and aerospace with government-contract revenue stability.",
  "Industrials|Metal Fabrication":                 "Metal fabrication serving construction, manufacturing, and energy markets.",
  "Healthcare|Medical Distribution":               "Essential pharmaceutical and medical supply distribution to healthcare systems.",
  "Healthcare|Biotechnology":                      "Drug pipeline exposure to biotech innovation cycles and FDA approvals.",
  "Healthcare|Drug Manufacturers—General":         "Diversified pharmaceutical manufacturer with branded and generic drug exposure.",
  "Healthcare|Medical Devices":                    "Medical device supplier serving surgical, diagnostic, and therapeutic markets.",
  "Healthcare|Medical Care Facilities":            "Healthcare services provider with volume and reimbursement rate exposure.",
  "Energy|Oil & Gas Integrated":                   "Exposure to crude production, refining margins, and downstream fuel demand.",
  "Energy|Oil & Gas E&P":                          "Direct commodity price exposure through exploration and production operations.",
  "Energy|Oil & Gas Refining & Marketing":         "Refining margin and fuel distribution exposure.",
  "Energy|Solar":                                  "Clean energy exposure through solar manufacturing and project development.",
  "Financial Services|Asset Management":           "Fee-based revenue tied to assets under management and market performance.",
  "Financial Services|Banks—Regional":             "Lending and deposit business with local economic and rate-cycle exposure.",
  "Financial Services|Insurance—Property & Casualty": "P&C underwriter with premium income and catastrophe loss exposure.",
  "Financial Services|Capital Markets":            "Capital markets revenue tied to deal flow, trading, and market activity.",
  "Consumer Cyclical|Auto Manufacturers":          "EV manufacturing with exposure to energy policy, autonomy, and consumer demand.",
  "Consumer Cyclical|Specialty Retail":            "Specialty retailer with consumer spending and brand loyalty exposure.",
  "Consumer Defensive|Household & Personal Products": "Consumer staples with stable demand and pricing power.",
  "Basic Materials|Steel":                         "Domestic steel production tied to construction, manufacturing, and trade policy.",
  "Basic Materials|Gold":                          "Gold mining with direct commodity and safe-haven demand exposure.",
  "Basic Materials|Copper":                        "Copper mining with exposure to electrification and infrastructure demand.",
  "Communication Services|Internet Content & Information": "Digital platform monetizing user engagement through advertising and subscriptions.",
  "Communication Services|Telecom Services":       "Telecom services with subscription revenue and network infrastructure exposure.",
  "Utilities|Utilities—Regulated Electric":        "Regulated electric utility with stable yield and rate-cycle sensitivity.",
  "Real Estate|REIT—Industrial":                   "Industrial REIT with rent exposure to e-commerce and logistics demand.",
};
const _WHY_SECTOR_FALLBACK = {
  "Technology":             "Technology business operating in enterprise, cloud, or semiconductor markets.",
  "Healthcare":             "Healthcare company with pharmaceutical, device, or distribution exposure.",
  "Energy":                 "Energy company with commodity price and infrastructure exposure.",
  "Industrials":            "Industrial manufacturer or services provider.",
  "Financial Services":     "Financial services business with market-sensitive or fee-based revenue.",
  "Consumer Cyclical":      "Consumer-facing business tied to discretionary spending trends.",
  "Consumer Defensive":     "Defensive consumer business with stable demand and brand loyalty.",
  "Basic Materials":        "Materials producer with commodity cycle and supply-demand exposure.",
  "Communication Services": "Communications or media business with user engagement and ad-revenue exposure.",
  "Utilities":              "Regulated utility with stable yield and interest rate sensitivity.",
  "Real Estate":            "Real estate business with asset value and rate-cycle exposure.",
};

function _getWhyItMatters(sector, industry) {
  if (!sector) return "";
  return _WHY_IT_MATTERS_MAP[`${sector}|${industry}`] || _WHY_SECTOR_FALLBACK[sector] || "";
}

// Business model tags
const _TAGS_PRIMARY = {
  "Technology|Semiconductors":                      ["SEMICONDUCTOR"],
  "Technology|Semiconductor Equipment & Materials": ["SEMICONDUCTOR"],
  "Technology|Computer Hardware":                   ["ENTERPRISE IT"],
  "Technology|Electronic Components":               ["TECH DISTRIBUTION"],
  "Technology|Information Technology Services":     ["ENTERPRISE IT"],
  "Technology|Software—Application":                ["SOFTWARE"],
  "Technology|Software—Infrastructure":             ["SOFTWARE"],
  "Technology|Communication Equipment":             ["NETWORKING"],
  "Industrials|Electrical Equipment & Parts":       ["INDUSTRIALS"],
  "Industrials|Engineering & Construction":         ["INDUSTRIALS"],
  "Industrials|Specialty Industrial Machinery":     ["INDUSTRIALS"],
  "Industrials|Aerospace & Defense":                ["AEROSPACE", "DEFENSE"],
  "Industrials|Metal Fabrication":                  ["MATERIALS"],
  "Healthcare|Medical Distribution":                ["HEALTHCARE"],
  "Healthcare|Biotechnology":                       ["BIOTECH"],
  "Healthcare|Drug Manufacturers—General":          ["PHARMA"],
  "Healthcare|Medical Devices":                     ["HEALTHCARE"],
  "Healthcare|Medical Care Facilities":             ["HEALTHCARE"],
  "Energy|Oil & Gas Integrated":                    ["ENERGY"],
  "Energy|Oil & Gas E&P":                           ["ENERGY"],
  "Energy|Oil & Gas Refining & Marketing":          ["ENERGY"],
  "Energy|Solar":                                   ["CLEAN ENERGY"],
  "Financial Services|Asset Management":            ["FINANCIALS"],
  "Financial Services|Banks—Regional":              ["BANKING"],
  "Financial Services|Insurance—Property & Casualty": ["INSURANCE"],
  "Financial Services|Capital Markets":             ["FINANCIALS"],
  "Consumer Cyclical|Auto Manufacturers":           ["EV"],
  "Basic Materials|Steel":                          ["STEEL"],
  "Basic Materials|Gold":                           ["GOLD"],
  "Communication Services|Internet Content & Information": ["DIGITAL MEDIA"],
};
const _TAG_KEYWORD_BOOSTS = [
  [/\bAI\b|artificial intelligence/i,    "AI"],
  [/data.?cent(?:er|re)/i,               "DATA CENTER"],
  [/nuclear|SMR\b/i,                     "NUCLEAR"],
  [/\bdefense\b|intelligence community|counterterrorism/i, "DEFENSE"],
  [/\belectric vehicle|EV\b/i,           "EV"],
  [/\blithography|chip manufactur/i,     "SEMICONDUCTOR"],
  [/\bsemiconductor/i,                   "SEMICONDUCTOR"],
];

function _getBusinessTags(sector, industry, bizDesc) {
  const base = (_TAGS_PRIMARY[`${sector}|${industry}`] || []).slice();
  const tagSet = new Set(base);
  if (bizDesc) {
    for (const [rx, tag] of _TAG_KEYWORD_BOOSTS) {
      if (rx.test(bizDesc) && !tagSet.has(tag)) tagSet.add(tag);
    }
  }
  return [...tagSet].slice(0, 3);
}

// Build Company Snapshot HTML for a single symbol
function _dqCompanySnapshotHtml(sym, metadataMap) {
  const meta = metadataMap[(sym || "").toUpperCase()] || {};

  const companyName = meta.long_name    || sym || "Unknown";
  const hq          = meta.hq           || "Unknown";
  const sector      = meta.sector       || "";
  const industry    = meta.industry     || "";
  const country     = meta.country      || "—";
  const capTier     = meta.market_cap_bucket || "";
  const rawBiz      = meta.business_summary || "";
  const secType     = meta.quote_type || meta.security_type || "";

  const bizDesc    = _cleanBusinessSummary(rawBiz);
  const whyMatters = _getWhyItMatters(sector, industry);
  const tags       = _getBusinessTags(sector, industry, rawBiz);

  // ETF / Fund special handling
  const isEtf = secType === "ETF" || secType === "MUTUALFUND" || secType === "FUND";
  const sectorDisplay   = (isEtf && !sector) ? "Exchange-Traded Fund" : (sector || "—");
  const industryDisplay = industry || "—";

  const hasAny = sector || industry || country !== "—" || meta.long_name || isEtf;
  if (!hasAny) return "";

  const tagHtml = tags.length
    ? `<div class="dq-cs-tags">${tags.map(t => `<span class="dq-cs-tag">${escHtml(t)}</span>`).join("")}</div>`
    : "";

  return `<div class="dq-company-snapshot">
    <div class="dq-cs-title">Company Snapshot</div>
    ${tagHtml}<div class="dq-cs-grid">
      <div class="dq-cs-lbl">Company</div>
      <div class="dq-cs-val">${escHtml(companyName)}</div>
      <div class="dq-cs-lbl">Headquarters</div>
      <div class="dq-cs-val">${escHtml(hq)}</div>
      <div class="dq-cs-lbl">Sector</div>
      <div class="dq-cs-val">${escHtml(sectorDisplay)}</div>
      <div class="dq-cs-lbl">Industry</div>
      <div class="dq-cs-val">${escHtml(industryDisplay)}</div>
      ${bizDesc ? `<div class="dq-cs-lbl dq-cs-business-lbl">What They Do</div>
      <div class="dq-cs-val dq-cs-business">${escHtml(bizDesc)}</div>` : ""}
      ${whyMatters ? `<div class="dq-cs-lbl dq-cs-business-lbl">Why It Matters</div>
      <div class="dq-cs-val dq-cs-why">${escHtml(whyMatters)}</div>` : ""}
      <div class="dq-cs-lbl">Country</div>
      <div class="dq-cs-val">${escHtml(country)}</div>
      ${capTier ? `<div class="dq-cs-lbl">Cap Tier</div>
      <div class="dq-cs-val"><span class="dq-cs-badge">${escHtml(capTier)}</span></div>` : ""}
    </div>
  </div>`;
}

// Category metadata
let _craProposal = null;   // ISSUE-09 fix: restored missing declaration
const _CRA_CATEGORIES = [
  { key: "SIGNAL_DETERIORATION",   label: "Signal Deterioration",    num: 1 },
  { key: "STRATEGIC_EXIT",         label: "Strategic Exit",           num: 2 },
  { key: "OVERWEIGHT_REDUCTION",   label: "Exposure Reduction",       num: 3 },
  { key: "TAX_AWARE_EXIT",         label: "Tax-Aware Exit",           num: 4 },
  { key: "LOW_CONVICTION_REDUCTION", label: "Opportunity Cost Reduction", num: 5 },
];

async function loadCRAProposal() {
  const section = document.getElementById("craSection");
  const content = document.getElementById("craContent");
  if (!section || !content) return;

  content.innerHTML = `<div class="cra-loading">Loading Capital Rotation Advisor…</div>`;
  section.style.display = "block";

  const btn = document.getElementById("craRefreshBtn");
  if (btn) btn.disabled = true;

  try {
    const resp = await fetch("/api/cra/proposal");
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: "Network error" }));
      content.innerHTML = `<div class="cra-error">${escHtml(err.error || "Failed to load CRA proposal")}</div>`;
      return;
    }
    _craProposal = await resp.json();
    _renderCRAProposal(_craProposal);
    _craEnableButtons(true);

    // ARCH-02: Render Reduction Queue from CRA capital sources
    // ARCH-05: Pass signal intelligence data for per-candidate profiles
    const fviData      = (_lastAnalysisData && _lastAnalysisData.fvi_data) || null;
    const _ovBySymArch = {};
    for (const ov of ((_lastAnalysisData && _lastAnalysisData.security_overlays) || [])) {
      if (ov && ov.symbol) _ovBySymArch[(ov.symbol || "").toUpperCase()] = ov;
    }
    const _consBySymArch = (_lastAnalysisData && _lastAnalysisData.analyst_consensus_by_symbol) || {};
    renderReductionQueue._consBySymbol = _consBySymArch;  // pass via function property (avoids signature change)
    renderReductionQueue(
      _craProposal.sources || [],
      _craProposal.total_capital_pool,
      fviData,
      _ovBySymArch,
      (_lastAnalysisData && _lastAnalysisData.ucf_verdicts_by_symbol) || {},
      (_lastAnalysisData && _lastAnalysisData.fidelity_signals_by_symbol) || {}
    );

    // Check for stale draft with matching run_id for Include/Skip restore
    _craCheckDraft(_craProposal.run_id);
  } catch (e) {
    content.innerHTML = `<div class="cra-error">CRA error: ${escHtml(String(e))}</div>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── CRA Persistence & Export ──────────────────────────────────────────────────

function _craEnableButtons(on) {
  for (const id of ["craSaveBtn","craExportCsvBtn","craExportMdBtn","craCopyBtn"]) {
    const el = document.getElementById(id);
    if (el) el.disabled = !on;
  }
}

async function _craSaveDraft() {
  if (!_craProposal) return;
  const saveBtn = document.getElementById("craSaveBtn");
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = "Saving…"; }

  // Collect current Include/Skip state
  const operatorIncludeMap = {};
  const skipCheckboxes = document.querySelectorAll(".cra-check-skip");
  skipCheckboxes.forEach(cb => {
    // id is "cra-skp-SYMBOL" — extract symbol
    const sym = (cb.id || "").replace(/^cra-skp-/, "").toUpperCase();
    if (sym) operatorIncludeMap[sym] = !cb.checked; // checked = skip → not included
  });

  const payload = { ..._craProposal, operator_include_map: operatorIncludeMap };

  try {
    const resp = await fetch("/api/cra/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      if (saveBtn) {
        saveBtn.textContent = "✓ Saved";
        saveBtn.classList.add("cra-btn-saved");
        setTimeout(() => {
          saveBtn.textContent = "✎ Save";
          saveBtn.classList.remove("cra-btn-saved");
          saveBtn.disabled = false;
        }, 2500);
      }
    } else {
      const err = await resp.json().catch(() => ({}));
      alert("Save failed: " + (err.error || resp.status));
      if (saveBtn) { saveBtn.textContent = "✎ Save"; saveBtn.disabled = false; }
    }
  } catch (e) {
    alert("Save error: " + e);
    if (saveBtn) { saveBtn.textContent = "✎ Save"; saveBtn.disabled = false; }
  }
}

async function _craLoadDraft() {
  try {
    const resp = await fetch("/api/cra/draft");
    if (!resp.ok) {
      alert("No saved draft found. Generate and save a proposal first.");
      return;
    }
    const draft = await resp.json();
    if (draft.run_id === (_craProposal && _craProposal.run_id)) {
      // Same run — restore include/skip and re-render
      _craProposal = draft;
      _renderCRAProposal(draft);
      _craRestoreIncludeMap(draft.operator_include_map || {});
      _craEnableButtons(true);
      const banner = document.getElementById("craDraftBanner");
      if (banner) banner.style.display = "none";
    } else {
      // Different run — load as new base proposal
      _craProposal = draft;
      _renderCRAProposal(draft);
      _craRestoreIncludeMap(draft.operator_include_map || {});
      _craEnableButtons(true);
      const msg = document.getElementById("craDraftBannerMsg");
      const banner = document.getElementById("craDraftBanner");
      if (msg) msg.textContent = `Loaded draft from ${draft.as_of_date || "previous session"} (different run — selections may not match current portfolio).`;
      if (banner) banner.style.display = "flex";
    }
  } catch (e) {
    alert("Load error: " + e);
  }
}

async function _craCheckDraft(currentRunId) {
  try {
    const resp = await fetch("/api/cra/draft");
    if (!resp.ok) return;
    const draft = await resp.json();
    if (!draft || !draft.operator_include_map) return;
    if (draft.run_id === currentRunId) {
      // Same run — silently restore selections
      _craRestoreIncludeMap(draft.operator_include_map);
    } else {
      // Stale draft — show banner
      const msg = document.getElementById("craDraftBannerMsg");
      const banner = document.getElementById("craDraftBanner");
      if (msg) msg.textContent = `Saved draft from ${draft.as_of_date || "previous session"} available.`;
      if (banner) banner.style.display = "flex";
    }
  } catch (_) { /* best-effort */ }
}

function _craApplyDraft() {
  if (!_craProposal) return;
  fetch("/api/cra/draft")
    .then(r => r.ok ? r.json() : null)
    .then(draft => {
      if (draft && draft.operator_include_map) {
        _craRestoreIncludeMap(draft.operator_include_map);
      }
      const banner = document.getElementById("craDraftBanner");
      if (banner) banner.style.display = "none";
    })
    .catch(() => {});
}

function _craRestoreIncludeMap(map) {
  if (!map || typeof map !== "object") return;
  Object.entries(map).forEach(([sym, included]) => {
    const cb = document.getElementById(`cra-skp-${sym}`);
    if (cb) {
      cb.checked = !included; // included=false → skip checked
      _craSkipToggle(sym);
    }
  });
}

function _craExportCsv() {
  window.location.href = "/api/cra/draft/export?format=csv";
}

function _craExportMd() {
  window.location.href = "/api/cra/draft/export?format=md";
}

async function _craCopySummary() {
  if (!_craProposal) return;
  const p = _craProposal;
  const lines = [
    `CRA Proposal — ${p.as_of_date || ""}`,
    `Status: ${p.proposal_status || "—"}`,
    "",
    `CAPITAL SOURCES ($${_craFmt(p.total_capital_pool)} est. pool)`,
  ];
  (p.sources || []).forEach(s => {
    if (!s.blocked_by_policy) {
      lines.push(`• ${s.symbol} — ${s.category.replace(/_/g, " ")} — ${s.priority} — Tax ${s.tax_bucket || "—"}`);
    }
  });
  lines.push("", "DEPLOYMENT TARGETS");
  (p.deployments || []).forEach(t => {
    const tier = t.narrative_tier.includes("CORE") ? "CCL" : "HCA";
    const proj = (parseFloat(t.projected_weight_pct || 0) * 100).toFixed(1);
    lines.push(`• #${t.rank} ${t.symbol} — Add ${_craFmt(t.suggested_amount)} → ${proj}% proj. — ${tier}`);
  });
  const imp = p.impact || {};
  if (imp.impact_narrative) {
    lines.push("", "ESTIMATED IMPACT", `• ${imp.impact_narrative}`);
  }
  lines.push("", "Advisory only — not trade instructions.", "Generated by Security Intelligence Hub");

  const text = lines.join("\n");
  try {
    await navigator.clipboard.writeText(text);
    const btn = document.getElementById("craCopyBtn");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "✓ Copied";
      setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }
  } catch (e) {
    // Fallback: show in a textarea for manual copy
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;top:10%;left:10%;width:80%;height:60%;z-index:9999;font-size:0.85rem;padding:10px;";
    document.body.appendChild(ta);
    ta.select();
    const close = document.createElement("button");
    close.textContent = "Close";
    close.style.cssText = "position:fixed;top:calc(10% - 30px);left:10%;z-index:9999;padding:4px 12px;";
    close.onclick = () => { document.body.removeChild(ta); document.body.removeChild(close); };
    document.body.appendChild(close);
  }
}

function _renderCRAProposal(p) {
  const content = document.getElementById("craContent");
  if (!content) return;

  // Status badge
  const statusBadge = document.getElementById("craStatusBadge");
  if (statusBadge) {
    const statusLabel = p.proposal_status === "OPERATOR_REVIEW_REQUIRED"
      ? "Operator Review Required"
      : p.proposal_status === "READY" ? "Ready" : "Draft";
    statusBadge.className = `cra-status-badge cra-status-${p.proposal_status}`;
    statusBadge.textContent = statusLabel;
  }

  // Review flags
  const flagsEl = document.getElementById("craReviewFlags");
  if (flagsEl) {
    if (p.review_flags && p.review_flags.length > 0) {
      flagsEl.style.display = "block";
      flagsEl.innerHTML = `<strong>⚠ Operator Review Required:</strong>
        <ul>${p.review_flags.map(f => `<li>${escHtml(f)}</li>`).join("")}</ul>`;
    } else {
      flagsEl.style.display = "none";
    }
  }

  content.innerHTML = `
    ${_craBuildRotationObjectiveBanner(p)}
    <div class="cra-columns">
      ${_craBuildSourcesCol(p)}
      ${_craBuildRotationMapCol(p)}
      ${_craBuildImpactCol(p)}
    </div>`;

  // Expand first non-empty category automatically
  const firstGroup = content.querySelector(".cra-cat-group");
  if (firstGroup) _craCatToggle(firstGroup);
}

// ─────────────────────────────────────────────────────────────────────────────
// CRA Rotation Objective Banner (UI Clarity Sprint — Problem 3)
// Presentation-only — auto-classifies based on source category distribution.
// No changes to CRA logic, scoring, or proposal generation.
// ─────────────────────────────────────────────────────────────────────────────
function _craBuildRotationObjectiveBanner(p) {
  const sources = (p.sources || []).filter(s => !s.blocked_by_policy && s.priority !== "DEFER");
  if (!sources.length) return "";

  const counts = {};
  for (const s of sources) {
    const cat = s.category || "UNKNOWN";
    counts[cat] = (counts[cat] || 0) + 1;
  }
  const total = sources.length;

  const sigDet  = counts["SIGNAL_DETERIORATION"]    || 0;
  const owRed   = counts["OVERWEIGHT_REDUCTION"]     || 0;
  const taxExit = counts["TAX_AWARE_EXIT"]           || 0;
  const lowConv = counts["LOW_CONVICTION_REDUCTION"] || 0;
  const stratEx = counts["STRATEGIC_EXIT"]           || 0;

  let objective, objectiveCls, objectiveDesc;
  const majorityThreshold = total * 0.5;

  if (sigDet + stratEx >= majorityThreshold) {
    objective     = "HIGHER CONVICTION";
    objectiveCls  = "cra-obj-conviction";
    objectiveDesc = "Primary driver: rotate out of deteriorating signals into higher-conviction positions.";
  } else if (owRed >= majorityThreshold) {
    objective     = "ALLOCATION REPAIR";
    objectiveCls  = "cra-obj-allocation";
    objectiveDesc = "Primary driver: reduce overweight nodes to restore mandate-aligned allocation.";
  } else if (taxExit >= majorityThreshold) {
    objective     = "TAX HARVESTING";
    objectiveCls  = "cra-obj-tax";
    objectiveDesc = "Primary driver: exit tax-inefficient positions to improve after-tax returns.";
  } else if (lowConv >= majorityThreshold) {
    objective     = "OPPORTUNITY COST REDUCTION";
    objectiveCls  = "cra-obj-oppcost";
    objectiveDesc = "Primary driver: replace passive exposure with higher-conviction equity candidates.";
  } else {
    objective     = "MIXED OBJECTIVE";
    objectiveCls  = "cra-obj-mixed";
    objectiveDesc = "Multiple drivers: signal deterioration, allocation repair, and/or tax considerations present.";
  }

  const catChips = [
    sigDet  ? `<span class="cra-obj-chip">Signal Det. ×${sigDet}</span>`  : "",
    stratEx ? `<span class="cra-obj-chip">Strategic ×${stratEx}</span>`   : "",
    owRed   ? `<span class="cra-obj-chip">OW Reduction ×${owRed}</span>`  : "",
    taxExit ? `<span class="cra-obj-chip">Tax Exit ×${taxExit}</span>`    : "",
    lowConv ? `<span class="cra-obj-chip">Opp. Cost ×${lowConv}</span>`   : "",
  ].filter(Boolean).join("");

  return `<div class="cra-rotation-objective-banner ${objectiveCls}">
    <div class="cra-obj-left">
      <div class="cra-obj-label">Rotation Objective</div>
      <div class="cra-obj-value">${escHtml(objective)}</div>
    </div>
    <div class="cra-obj-right">
      <div class="cra-obj-desc">${escHtml(objectiveDesc)}</div>
      <div class="cra-obj-chips">${catChips}</div>
    </div>
  </div>`;
}

// ── Column 1: Capital Sources ────────────────────────────────────────────────

function _craBuildSourcesCol(p) {
  const sources = p.sources || [];
  const includedPool = sources
    .filter(s => !s.blocked_by_policy && s.priority !== "DEFER")
    .reduce((sum, s) => sum + (s.estimated_proceeds || 0), 0);

  const poolHtml = `<div class="cra-pool-strip">
    <div>
      <div class="cra-pool-val">${_craFmt(includedPool)}</div>
      <div class="cra-pool-lbl">Est. Capital Pool (${sources.filter(s => !s.blocked_by_policy && s.priority !== "DEFER").length} sources)</div>
    </div>
    <div>
      <div class="cra-pool-val" style="color:var(--muted)">${_craFmt(p.portfolio_mv)}</div>
      <div class="cra-pool-lbl">Portfolio MV</div>
    </div>
  </div>`;

  const catGroupsHtml = _CRA_CATEGORIES.map(cat => {
    const catSources = sources.filter(s => s.category === cat.key);
    const catId = `cra-cat-${cat.key.toLowerCase()}`;
    const count = catSources.length;

    const cardsHtml = count > 0
      ? catSources.map(s => _craBuildSourceCard(s)).join("")
      : `<div class="cra-empty-cat">No ${cat.label.toLowerCase()} candidates identified.</div>`;

    return `<div class="cra-cat-group" id="${catId}">
      <div class="cra-cat-header" onclick="_craCatToggle(document.getElementById('${catId}'))">
        <span class="cra-cat-num">${cat.num}</span>
        <span class="cra-cat-label">${escHtml(cat.label)}</span>
        <span class="cra-cat-count">${count} position${count !== 1 ? "s" : ""}</span>
        <span style="font-size:0.7rem;color:var(--muted);margin-left:4px">▾</span>
      </div>
      <div class="cra-cat-body">${cardsHtml}</div>
    </div>`;
  }).join("");

  return `<div>
    <div class="cra-col-header">Capital Sources — What to Sell</div>
    <div class="cra-col-body">
      ${poolHtml}
      ${catGroupsHtml}
    </div>
  </div>`;
}

function _craBuildSourceCard(s) {
  const blocked = s.blocked_by_policy;
  const cardClass = blocked ? "cra-source-card cra-blocked" : "cra-source-card";

  // Priority badge
  const priClass = `cra-pri-${s.priority || "LOW"}`;
  const priBadge = `<span class="cra-pri ${priClass}">${escHtml(s.priority || "")}</span>`;

  // Tax badge
  const taxBadge = s.tax_bucket
    ? `<span class="cra-tax-badge cra-tax-${s.tax_bucket}">Tax ${escHtml(s.tax_bucket)}</span>`
    : `<span class="cra-tax-badge cra-tax-unknown">Tax ?</span>`;

  // Policy badge
  let policyBadge = "";
  if (s.policy_type === "DO_NOT_SELL") {
    policyBadge = `<span class="cra-policy-badge cra-policy-DNS">🔒 DO NOT SELL</span>`;
  } else if (s.policy_type === "SELL_LAST") {
    policyBadge = `<span class="cra-policy-badge cra-policy-SL">⏸ SELL LAST</span>`;
  } else if (s.policy_type === "CORE_ANCHOR") {
    policyBadge = `<span class="cra-policy-badge cra-policy-CA">⚓ CORE ANCHOR</span>`;
  }

  // Monitor-only badge for blocked
  const monitorBadge = blocked
    ? `<span class="cra-monitor-badge">MONITOR ONLY</span>`
    : "";

  // Proceeds row
  const proceedsHtml = !blocked
    ? `<span class="cra-proceeds-val">${_craFmt(s.estimated_proceeds)}</span>
       <span style="color:var(--muted)"> of ${_craFmt(s.current_value_usd)} (${Math.round((s.sizing_pct || 0) * 100)}%)</span>`
    : `<span style="color:var(--muted);font-style:italic">Blocked — not in capital pool</span>`;

  // Tax note
  const taxNote = s.tax_annotation
    ? `<div class="cra-tax-note">${escHtml(s.tax_annotation)}</div>`
    : "";

  // Include / Skip checkbox (disabled for blocked)
  const checkboxHtml = blocked
    ? `<label class="cra-check-label" style="opacity:0.5;cursor:not-allowed;">
        <input type="checkbox" disabled> Include in rotation
       </label>`
    : `<label class="cra-check-label">
        <input type="checkbox" class="cra-check-include"
               id="cra-inc-${escHtml(s.symbol)}"
               checked
               onchange="_craUpdatePool()">
        Include
       </label>
       <label class="cra-check-label">
        <input type="checkbox" class="cra-check-skip"
               id="cra-skp-${escHtml(s.symbol)}"
               onchange="_craSkipToggle('${escHtml(s.symbol)}')">
        Skip
       </label>`;

  // Review required indicator
  const reviewHtml = s.operator_review_required && !blocked
    ? `<span style="font-size:0.7rem;color:#856404;font-weight:700">⚠ Review required</span>`
    : "";

  return `<div class="${cardClass}" id="cra-src-${escHtml(s.symbol)}">
    <div class="cra-source-row1">
      <span class="cra-sym">${escHtml(s.symbol)}</span>
      ${priBadge}
      ${taxBadge}
      ${policyBadge}
      ${monitorBadge}
      ${reviewHtml}
    </div>
    <div class="cra-source-row2">${proceedsHtml}</div>
    <div class="cra-source-evidence">${escHtml(s.evidence_summary || "")}</div>
    ${taxNote}
    <div class="cra-source-actions">${checkboxHtml}</div>
  </div>`;
}

function _craCatToggle(groupEl) {
  if (!groupEl) return;
  groupEl.classList.toggle("cra-cat-expanded");
}

function _craSkipToggle(symbol) {
  const skipCb  = document.getElementById(`cra-skp-${symbol}`);
  const inclCb  = document.getElementById(`cra-inc-${symbol}`);
  if (!skipCb || !inclCb) return;
  if (skipCb.checked) inclCb.checked = false;
  _craUpdatePool();
}

function _craUpdatePool() {
  if (!_craProposal) return;
  const sources = _craProposal.sources || [];
  let pool = 0;
  for (const s of sources) {
    if (s.blocked_by_policy || s.priority === "DEFER") continue;
    const inclCb = document.getElementById(`cra-inc-${s.symbol}`);
    if (inclCb && inclCb.checked) pool += (s.estimated_proceeds || 0);
  }
  // Update pool display in column 1
  const poolValEls = document.querySelectorAll(".cra-pool-val");
  if (poolValEls.length > 0) poolValEls[0].textContent = _craFmt(pool);

  // Update rotation map column pool summary
  const poolSummaryEl = document.getElementById("cra-rotation-pool-val");
  if (poolSummaryEl) poolSummaryEl.textContent = _craFmt(pool);
}

// ── Column 2: Rotation Map ────────────────────────────────────────────────────

function _craBuildRotationMapCol(p) {
  const pool = p.total_capital_pool || 0;
  const deployments = p.deployments || [];

  const poolSummaryHtml = `<div class="cra-pool-summary">
    <div style="font-size:0.7rem;color:var(--muted);margin-bottom:2px">Capital Pool → Deployment Queue</div>
    <div class="cra-pool-summary-val" id="cra-rotation-pool-val">${_craFmt(pool)}</div>
    <div style="font-size:0.7rem;color:var(--muted);margin-top:2px">
      ${deployments.length} target${deployments.length !== 1 ? "s" : ""} · CW-DAS rank order preserved
    </div>
  </div>`;

  const arrowHtml = `<div class="cra-rotation-arrow">↓</div>`;

  let targetsHtml = "";
  if (deployments.length === 0) {
    targetsHtml = `<div class="cra-no-targets">No deployment targets allocated. Capital pool may be below minimum lot size, or all queue candidates are at capacity.</div>`;
  } else {
    targetsHtml = deployments.map(t => _craBuildTargetCard(t)).join("");
  }

  // Remaining cash note
  const totalSuggested = deployments.reduce((s, t) => s + (t.suggested_amount || 0), 0);
  const remaining = pool - totalSuggested;
  const remainderHtml = remaining > 1
    ? `<div style="padding:8px 12px;font-size:0.74rem;color:var(--muted);border-top:1px solid var(--border);background:#fafafa;">
        Unallocated: ${_craFmt(remaining)}
       </div>`
    : "";

  return `<div>
    <div class="cra-col-header">Rotation Map — Proceeds → Targets</div>
    <div class="cra-col-body">
      ${poolSummaryHtml}
      ${arrowHtml}
      ${targetsHtml}
      ${remainderHtml}
    </div>
  </div>`;
}

function _craBuildTargetCard(t) {
  const tierShort = t.narrative_tier === "CORE_CONVICTION_LEADER" ? "CCL"
    : t.narrative_tier === "HIGH_CONVICTION_ANCHOR" ? "HCA"
    : (t.narrative_tier || "—").replace(/_/g, " ");
  const tierClass = `cra-tier-${tierShort}`;
  const rankClass = t.rank === 1 ? "cra-target-rank cra-target-rank-1" : "cra-target-rank";
  const dasScore = t.deployment_score != null
    ? parseFloat(t.deployment_score).toFixed(1)
    : "—";

  const curWt  = t.current_weight_pct  != null ? parseFloat(t.current_weight_pct).toFixed(2)  + "%" : "—";
  const projWt = t.projected_weight_pct != null ? parseFloat(t.projected_weight_pct).toFixed(2) + "%" : "—";

  return `<div class="cra-target-card">
    <div class="cra-target-row1">
      <span class="${rankClass}">#${t.rank}</span>
      <span class="cra-target-sym">${escHtml(t.symbol)}</span>
      <span class="${tierClass}">${tierShort}</span>
      <span class="cra-das-score">DAS ${dasScore}</span>
    </div>
    <div class="cra-target-row2">
      <span class="cra-target-amount">${_craFmt(t.suggested_amount)}</span>
      &nbsp;·&nbsp;
      <span>${curWt} <span class="cra-weight-arrow">→</span> ${projWt}</span>
      &nbsp;·&nbsp;
      <span style="font-size:0.7rem">${escHtml(t.allocation_node || "")}</span>
    </div>
    ${t.allocation_note ? `<div style="font-size:0.71rem;color:var(--muted);margin-top:2px">${escHtml(t.allocation_note)}</div>` : ""}
  </div>`;
}

// ── Column 3: Impact Summary ─────────────────────────────────────────────────

function _craBuildImpactCol(p) {
  const imp = p.impact || {};

  const fmtScore = v => v != null ? parseFloat(v).toFixed(4) : "—";
  const fmtPct   = v => v != null ? parseFloat(v).toFixed(2) + "%" : "—";

  const alignBefore = fmtScore(imp.alignment_score_before);
  const alignAfter  = fmtScore(imp.alignment_score_after);
  const alignDelta  = imp.alignment_delta != null ? parseFloat(imp.alignment_delta) : null;
  const alignDeltaStr = alignDelta != null
    ? (alignDelta >= 0 ? "+" : "") + alignDelta.toFixed(4)
    : "—";
  const alignDeltaCls = alignDelta == null ? "cra-delta-neutral"
    : alignDelta > 0 ? "cra-delta-pos" : alignDelta < 0 ? "cra-delta-neg" : "cra-delta-neutral";

  const concBefore = fmtPct(imp.concentration_before);
  const concAfter  = fmtPct(imp.concentration_after);
  const concDelta  = imp.concentration_delta != null ? parseFloat(imp.concentration_delta) : null;
  const concDeltaStr = concDelta != null
    ? (concDelta >= 0 ? "+" : "") + concDelta.toFixed(2) + "%"
    : "—";
  const concDeltaCls = concDelta == null ? "cra-delta-neutral"
    : concDelta < 0 ? "cra-delta-pos" : concDelta > 0 ? "cra-delta-neg" : "cra-delta-neutral";

  // Overweight nodes
  const owBefore  = (imp.overweight_nodes_before || []);
  const owAfter   = (imp.overweight_nodes_after  || []);
  const resolved  = owBefore.filter(n => !owAfter.includes(n));
  const remaining = owAfter;

  const owBeforeHtml = owBefore.length > 0
    ? owBefore.map(n => {
        const isResolved = !owAfter.includes(n);
        return `<div class="${isResolved ? "cra-node-resolved" : "cra-node-remaining"}">
          ${isResolved ? "✓" : "•"} ${escHtml(_craShortNode(n))}
        </div>`;
      }).join("")
    : `<div style="color:var(--muted);font-style:italic;font-size:0.78rem">None</div>`;

  const owAfterHtml = owAfter.length === 0
    ? `<div class="cra-node-resolved" style="font-weight:700">✓ All overweight nodes resolved</div>`
    : owAfter.map(n => `<div class="cra-node-remaining">• ${escHtml(_craShortNode(n))}</div>`).join("");

  const narrativeHtml = imp.impact_narrative
    ? `<div class="cra-narrative">${escHtml(imp.impact_narrative)}</div>`
    : "";

  return `<div>
    <div class="cra-col-header">Portfolio Impact — Estimate</div>
    <div class="cra-col-body">
      <div class="cra-impact-card">
        <div class="cra-estimate-banner">⚠ Estimate Only — Full Re-Analysis Required for Precision</div>
        <span class="cra-impact-section-lbl">Alignment Score</span>
        <div class="cra-impact-row">
          <span class="cra-impact-lbl">Before</span>
          <span class="cra-impact-vals">${alignBefore}</span>
        </div>
        <div class="cra-impact-row">
          <span class="cra-impact-lbl">After (est.)</span>
          <span class="cra-impact-vals">${alignAfter}</span>
        </div>
        <div class="cra-impact-row">
          <span class="cra-impact-lbl">Delta</span>
          <span class="cra-impact-vals ${alignDeltaCls}">${alignDeltaStr}</span>
        </div>
      </div>
      <div class="cra-impact-card">
        <span class="cra-impact-section-lbl">Concentration (top-5 weight)</span>
        <div class="cra-impact-row">
          <span class="cra-impact-lbl">Before</span>
          <span class="cra-impact-vals">${concBefore}</span>
        </div>
        <div class="cra-impact-row">
          <span class="cra-impact-lbl">After (est.)</span>
          <span class="cra-impact-vals">${concAfter}</span>
        </div>
        <div class="cra-impact-row">
          <span class="cra-impact-lbl">Delta</span>
          <span class="cra-impact-vals ${concDeltaCls}">${concDeltaStr}</span>
        </div>
      </div>
      <div class="cra-impact-card">
        <span class="cra-impact-section-lbl">Overweight Nodes — Before</span>
        <div class="cra-nodes-list">${owBeforeHtml}</div>
      </div>
      <div class="cra-impact-card">
        <span class="cra-impact-section-lbl">Overweight Nodes — After Rotation</span>
        <div class="cra-nodes-list">${owAfterHtml}</div>
      </div>
    </div>
    ${narrativeHtml}
  </div>`;
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function _craFmt(v) {
  const n = parseFloat(v || 0);
  if (isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return "$" + (n / 1_000_000).toFixed(2) + "M";
  if (Math.abs(n) >= 1_000)     return "$" + (n / 1_000).toFixed(1) + "K";
  return "$" + n.toFixed(0);
}

function _craShortNode(node) {
  // EQUITIES.US.LARGE → US·LARGE
  return (node || "").replace(/^EQUITIES\./, "").replace(/\./g, "·");
}

// ── CII Methodology Panel ─────────────────────────────────────────────────────
function _openCIIModal() {
  const overlay = document.getElementById("ciiModalOverlay");
  if (overlay) {
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }
}

function _closeCIIModal(evt) {
  // Close on overlay click (backdrop) or explicit call; don't close on modal content click
  if (evt && evt.target !== document.getElementById("ciiModalOverlay")) return;
  const overlay = document.getElementById("ciiModalOverlay");
  if (overlay) {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }
}

// Keyboard close (Escape key)
document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") _closeCIIModal();
});

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
