function esc(v) {
  return String(v == null ? "" : v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function badge(v) {
  return `<span class="badge">${esc(v || "UNAVAILABLE")}</span>`;
}

function num(v, digits = 2) {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(digits) : "—";
}

function pct(v) {
  return typeof v === "number" && Number.isFinite(v) ? `${v.toFixed(2)}%` : "—";
}

function relativeLevelFromHorizons(relativeHorizons) {
  if (!relativeHorizons || typeof relativeHorizons !== "object") {
    return "UNAVAILABLE";
  }
  let value = null;
  for (const horizon of ["3M", "1M", "1W"]) {
    const candidate = relativeHorizons[horizon]?.relative_return_pct;
    if (typeof candidate === "number" && Number.isFinite(candidate)) {
      value = candidate;
      break;
    }
  }
  if (value == null) {
    return "UNAVAILABLE";
  }
  if (value >= 3.0) return "HIGH";
  if (value >= 1.0) return "MEDIUM";
  if (value <= -3.0) return "LOW";
  if (value <= -1.0) return "WEAK";
  return "NEUTRAL";
}

function renderExecutive(summary) {
  const root = document.getElementById("executive");
  const holdings = summary?.portfolio_momentum_map?.holdings || [];
  const sectors = summary?.sector_rotation || [];
  const industries = summary?.industry_rotation || [];
  const marketState = summary?.market_momentum?.market_absolute_momentum?.state || "UNAVAILABLE";
  const coverage = summary?.coverage || {};
  const hierarchy = coverage?.hierarchy_availability || {};
  const securityCounts = coverage?.security_counts || {};
  const sectorParentCounts = coverage?.sector_parent_counts || {};
  const industryParentCounts = coverage?.industry_parent_counts || {};

  const applicableSecurityCount = Number(securityCounts?.applicable || 0);
  const fullHistorySecurityCount = Number(securityCounts?.present || 0);
  const anyHistorySecurityCount = Number(securityCounts?.present || 0) + Number(securityCounts?.partial || 0);

  const fullHistorySecurityCoverage =
    typeof coverage?.full_history_security_coverage_pct === "number"
      ? coverage.full_history_security_coverage_pct
      : coverage.security_history_coverage_pct;
  const fullHistoryWeightCoverage = coverage?.full_history_portfolio_weight_coverage_pct;
  const anyHistoryWeightCoverage = coverage?.any_history_portfolio_weight_coverage_pct;

  const sectorParentRequired = Number(sectorParentCounts?.required || 0);
  const sectorParentAvailable = Number(sectorParentCounts?.available || 0);
  const industryParentRequired = Number(industryParentCounts?.required || 0);
  const industryParentAvailable = Number(industryParentCounts?.available || 0);
  const industryParentTotal = Number(industryParentCounts?.total || industryParentRequired);
  const industryParentNotApplicable = Number(industryParentCounts?.not_applicable || 0);

  root.innerHTML = `
    <div class="kv-grid">
      <div class="kpi"><div class="kpi-label">Snapshot Date</div><div class="kpi-value">${esc(summary?.snapshot_date || "—")}</div></div>
      <div class="kpi"><div class="kpi-label">Market State</div><div class="kpi-value">${esc(marketState)}</div></div>
      <div class="kpi"><div class="kpi-label">Holdings Covered</div><div class="kpi-value">${holdings.length}</div></div>
      <div class="kpi"><div class="kpi-label">Sectors</div><div class="kpi-value">${sectors.length}</div></div>
      <div class="kpi"><div class="kpi-label">Industries</div><div class="kpi-value">${industries.length}</div></div>
      <div class="kpi"><div class="kpi-label">Generated (UTC)</div><div class="kpi-value mono">${esc(summary?.generated_at_utc || "—")}</div></div>
      <div class="kpi"><div class="kpi-label">Full History Security Coverage</div><div class="kpi-value">${pct(fullHistorySecurityCoverage)}</div><div class="kpi-sub">${fullHistorySecurityCount}/${applicableSecurityCount} applicable holdings</div></div>
      <div class="kpi"><div class="kpi-label">Any History Security Coverage</div><div class="kpi-value">${pct(coverage.any_history_security_coverage_pct)}</div><div class="kpi-sub">${anyHistorySecurityCount}/${applicableSecurityCount} applicable holdings</div></div>
      <div class="kpi"><div class="kpi-label">Full History Weight Coverage</div><div class="kpi-value">${pct(fullHistoryWeightCoverage)}</div><div class="kpi-sub">weight of applicable holdings</div></div>
      <div class="kpi"><div class="kpi-label">Any History Weight Coverage</div><div class="kpi-value">${pct(anyHistoryWeightCoverage)}</div><div class="kpi-sub">weight of applicable holdings</div></div>
      <div class="kpi"><div class="kpi-label">Sector Parent Coverage</div><div class="kpi-value">${pct(coverage.sector_parent_coverage_pct)}</div><div class="kpi-sub">${sectorParentAvailable}/${sectorParentRequired} sector groups requiring a parent</div></div>
      <div class="kpi"><div class="kpi-label">Industry Parent Coverage</div><div class="kpi-value">${pct(coverage.industry_parent_coverage_pct)}</div><div class="kpi-sub">${industryParentAvailable}/${industryParentRequired} applicable industry groups (total=${industryParentTotal}, not applicable=${industryParentNotApplicable})</div></div>
      <div class="kpi"><div class="kpi-label">Fully Evaluated Weight</div><div class="kpi-value">${pct(coverage.portfolio_momentum_evaluable_weight_pct)}</div><div class="kpi-sub">weight where Security State is FULLY_EVALUATED</div></div>
      <div class="kpi"><div class="kpi-label">Coverage State</div><div class="kpi-value">${esc(coverage.portfolio_coverage_state || "UNAVAILABLE")}</div><div class="kpi-sub">derived from fully evaluated portfolio weight</div></div>
    </div>
    <div class="coverage-compact">
      <div class="kpi-label">Hierarchy Coverage (denominator: applicable holdings)</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Layer</th><th>Security Count %</th><th>Portfolio Weight %</th></tr></thead>
          <tbody>
            <tr><td>Market Relative</td><td>${pct(hierarchy.market_relative_evaluable_security_pct)}</td><td>${pct(hierarchy.market_relative_evaluable_weight_pct)}</td></tr>
            <tr><td>Sector Relative</td><td>${pct(hierarchy.sector_relative_evaluable_security_pct)}</td><td>${pct(hierarchy.sector_relative_evaluable_weight_pct)}</td></tr>
            <tr><td>Industry Relative</td><td>${pct(hierarchy.industry_relative_evaluable_security_pct)}</td><td>${pct(hierarchy.industry_relative_evaluable_weight_pct)}</td></tr>
            <tr><td>Full Hierarchy (Absolute + Market + Sector + Industry)</td><td>${pct(hierarchy.full_hierarchy_security_pct)}</td><td>${pct(hierarchy.full_hierarchy_weight_pct)}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <p class="muted" style="margin-top:10px;">Momentum is explanatory only and does not create buy/sell/add/trim actions.</p>
  `;
}

function renderMarket(summary) {
  const root = document.getElementById("market");
  const market = summary?.market_momentum?.market_absolute_momentum || {};
  const h = market.horizons || {};
  const rows = ["1W", "1M", "3M", "6M", "12M"].map((k) => {
    const d = h[k] || {};
    return `<tr><td>${k}</td><td>${esc(d.state || "UNAVAILABLE")}</td><td>${pct(d.return_pct)}</td><td>${esc(d.confidence || "UNAVAILABLE")}</td><td>${esc(d.as_of_date || "—")}</td></tr>`;
  }).join("");
  root.innerHTML = `
    <div style="margin-bottom:8px;">State: ${badge(market.state)}</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Horizon</th><th>State</th><th>Return</th><th>Confidence</th><th>As Of</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderMu(summary) {
  const root = document.getElementById("mu");
  const mu = summary?.security_drilldown?.mu || {};
  const q = mu.questions || {};
  root.innerHTML = `
    <div class="mono">Symbol: ${esc(mu.symbol || "MU")}</div>
    <table>
      <tbody>
        <tr><td>Absolute Rising</td><td>${esc(q.is_absolute_rising || "UNAVAILABLE")}</td></tr>
        <tr><td>vs Market</td><td>${esc(q.vs_market || "UNAVAILABLE")}</td></tr>
        <tr><td>vs Sector</td><td>${esc(q.vs_sector || "UNAVAILABLE")}</td></tr>
        <tr><td>vs Industry</td><td>${esc(q.vs_industry || "UNAVAILABLE")}</td></tr>
        <tr><td>Leadership Change</td><td>${esc(q.leadership_change || "UNAVAILABLE")}</td></tr>
        <tr><td>Semiconductor Fundamentals</td><td>${esc(q.semiconductor_fundamentals || "UNAVAILABLE")}</td></tr>
        <tr><td>MU Fundamentals</td><td>${esc(q.mu_fundamentals || "UNAVAILABLE")}</td></tr>
        <tr><td>Extension</td><td>${esc(q.extension || "UNAVAILABLE")}</td></tr>
      </tbody>
    </table>
    <p class="muted" style="margin-top:8px;">Absolute Rising is based on MU 1M absolute return sign (YES if 1M return &gt; 0, NO if evaluated and &le; 0, UNAVAILABLE only when 1M return is unavailable).</p>
    ${mu.data_gap ? `<p class="muted" style="margin-top:8px;">${esc(mu.data_gap)}</p>` : ""}
  `;
}

function renderSectorTable(summary) {
  const root = document.getElementById("sectors");
  const sectors = summary?.sector_rotation || [];
  const rows = sectors.map((s) => `
    <tr>
      <td>${esc(s.sector)}</td>
      <td>${esc(s.classification)}</td>
      <td>${esc(s.relative_to_market?.level || "UNAVAILABLE")}</td>
      <td>${esc(s.relative_to_market?.change || "UNAVAILABLE")}</td>
      <td>${esc(s.breadth?.state || "UNAVAILABLE")}</td>
      <td>${num(s.breadth?.positive_short_share, 3)}</td>
      <td>${num(s.breadth?.outperform_parent_share, 3)}</td>
    </tr>
  `).join("");
  root.innerHTML = `
    <table>
      <thead><tr><th>Sector</th><th>Class</th><th>Rel Level</th><th>Rel Change</th><th>Breadth</th><th>Pos Short %</th><th>Outperform %</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="7" class="muted">No sector rows available.</td></tr>`}</tbody>
    </table>
  `;
}

function renderIndustryTable(summary) {
  const root = document.getElementById("industries");
  const industries = summary?.industry_rotation || [];
  const rows = industries.map((s) => `
    <tr>
      <td>${esc(s.industry)}</td>
      <td>${esc(s.sector)}</td>
      <td>${esc(s.classification)}</td>
      <td>${esc(s.relative_to_market?.level || "UNAVAILABLE")}</td>
      <td>${esc(s.relative_to_market?.change || "UNAVAILABLE")}</td>
      <td>${esc(s.relative_to_sector?.level || "UNAVAILABLE")}</td>
    </tr>
  `).join("");
  root.innerHTML = `
    <table>
      <thead><tr><th>Industry</th><th>Sector</th><th>Class</th><th>Rel vs Market</th><th>Change</th><th>Rel vs Sector</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="6" class="muted">No industry rows available.</td></tr>`}</tbody>
    </table>
  `;
}

function renderPortfolio(summary) {
  const root = document.getElementById("portfolio");
  const rowsData = summary?.portfolio_momentum_map?.holdings || [];
  const rows = rowsData.map((r) => `
    <tr>
      <td>${esc(r.symbol)}</td>
      <td>${num(r.portfolio_weight, 3)}</td>
      <td>${esc(r.sector)}</td>
      <td>${esc(r.industry)}</td>
      <td>
        ${esc(r.security_state)}
        <div class="layer-summary mono muted">
          ABS:${esc(r.absolute_security_momentum?.state || "UNAVAILABLE")}
          | MKT:${esc(r.relative_strength_level || "UNAVAILABLE")}
          | SEC:${esc(relativeLevelFromHorizons(r.security_vs_sector))}
          | IND:${esc(relativeLevelFromHorizons(r.security_vs_industry))}
        </div>
      </td>
      <td>${esc(r.relative_strength_level)}</td>
      <td>${esc(r.relative_momentum_change)}</td>
      <td>${esc(r.fundamental_momentum?.state || "UNAVAILABLE")}</td>
      <td>${esc(r.confirmation_state)}</td>
      <td>${esc(r.extension_state)}</td>
      <td>${esc(r.change_detection?.change_7d || "UNAVAILABLE")}</td>
      <td>${esc(r.change_detection?.change_30d || "UNAVAILABLE")}</td>
    </tr>
  `).join("");
  root.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Symbol</th><th>Wt%</th><th>Sector</th><th>Industry</th><th>Security State</th><th>Rel Level</th><th>Rel Change</th><th>Fundamental</th><th>Confirmation</th><th>Extension</th><th>7D</th><th>30D</th>
        </tr>
      </thead>
      <tbody>${rows || `<tr><td colspan="12" class="muted">No holdings available.</td></tr>`}</tbody>
    </table>
  `;
}

function renderMethodology(methodology) {
  const root = document.getElementById("methodology");
  if (!methodology) {
    root.textContent = "Unavailable";
    return;
  }
  const matters = (methodology.when_momentum_matters || []).map((x) => `<li>${esc(x)}</li>`).join("");
  const ignore = (methodology.when_to_ignore_momentum || []).map((x) => `<li>${esc(x)}</li>`).join("");
  root.innerHTML = `
    <p><strong>${esc(methodology.governance_statement || "Momentum alone is insufficient for an investment recommendation.")}</strong></p>
    <p><strong>When Momentum Matters</strong></p>
    <ul>${matters}</ul>
    <p><strong>When Momentum Should Be Ignored</strong></p>
    <ul>${ignore}</ul>
    <p><strong>Preferred State:</strong> ${esc(methodology.confirmation_logic?.preferred_state || "—")}</p>
    <p><strong>Caution State:</strong> ${esc(methodology.confirmation_logic?.caution_state || "—")}</p>
    <p><strong>Potential Early State:</strong> ${esc(methodology.confirmation_logic?.potential_early_state || "—")}</p>
    <p><strong>Risk State:</strong> ${esc(methodology.confirmation_logic?.risk_state || "—")}</p>
  `;
}

async function main() {
  try {
    const [summaryRes, methodRes] = await Promise.all([
      fetch("/api/pis/momentum/summary"),
      fetch("/api/pis/momentum/methodology"),
    ]);
    const summary = await summaryRes.json();
    const methodology = await methodRes.json();
    renderExecutive(summary);
    renderMarket(summary);
    renderMu(summary);
    renderSectorTable(summary);
    renderIndustryTable(summary);
    renderPortfolio(summary);
    renderMethodology(methodology);
  } catch (err) {
    const ids = ["executive", "market", "mu", "sectors", "industries", "portfolio", "methodology"];
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) {
        el.innerHTML = `<span class="muted">Failed to load momentum reporting payload: ${esc(err?.message || err)}</span>`;
      }
    }
  }
}

main();
