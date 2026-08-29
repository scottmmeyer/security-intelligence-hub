function esc(v) {
  return String(v == null ? "" : v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function num(v, digits = 2) {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(digits) : "-";
}

function pct(v, digits = 2) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "-";
  const fixed = v.toFixed(digits);
  return (v > 0 ? "+" : "") + fixed + "%";
}

function by(path, fallback = null) {
  return (row) => {
    let cur = row;
    for (const key of path) {
      cur = cur && typeof cur === "object" ? cur[key] : undefined;
    }
    return cur == null ? fallback : cur;
  };
}

function tableHtml(headers, rows) {
  const head = headers.map((h) => `<th>${esc(h)}</th>`).join("");
  const body = rows
    .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

async function fetchJson(url, timeoutMs = 120000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

let _payload = null;

function activeRows() {
  if (!_payload || !Array.isArray(_payload.industries)) return [];
  const term = String(document.getElementById("industryFilter")?.value || "").trim().toUpperCase();
  const sector = String(document.getElementById("sectorFilter")?.value || "").trim().toUpperCase();
  return _payload.industries.filter((row) => {
    const industry = String(row.industry || "").toUpperCase();
    const rowSector = String(row.sector || "").toUpperCase();
    if (term && !industry.includes(term)) return false;
    if (sector && rowSector !== sector) return false;
    return true;
  });
}

function sortRows(rows, mode) {
  const sorted = [...rows];
  const dislocatedKey = by(["returns", "return_3m_pct"], null);
  const recoveryKey = by(["breadth", "above_50dma_share_change_20d_pp"], null);
  const leaderKey = by(["returns", "return_3m_vs_market_pct"], null);

  function cmpNumeric(a, b, keyFn, desc) {
    const av = keyFn(a);
    const bv = keyFn(b);
    const aNum = typeof av === "number" && Number.isFinite(av);
    const bNum = typeof bv === "number" && Number.isFinite(bv);
    if (!aNum && !bNum) return 0;
    if (!aNum) return 1;
    if (!bNum) return -1;
    return desc ? bv - av : av - bv;
  }

  if (mode === "improving") {
    sorted.sort((a, b) => cmpNumeric(a, b, recoveryKey, true));
  } else if (mode === "leadership") {
    sorted.sort((a, b) => cmpNumeric(a, b, leaderKey, true));
  } else {
    sorted.sort((a, b) => cmpNumeric(a, b, dislocatedKey, false));
  }
  return sorted;
}

function renderSummary(payload) {
  const coverage = payload.coverage_summary || {};
  const root = document.getElementById("summary");
  root.innerHTML = [
    ["As-of Industries", coverage.industry_count],
    ["Industries With Parent History", coverage.industries_with_parent_history],
    ["Holdings Covered", coverage.holding_count],
    ["Mean Member History Coverage", pct(coverage.mean_member_history_coverage_pct)],
  ]
    .map(
      ([label, value]) =>
        `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(String(value ?? "-"))}</div></div>`,
    )
    .join("");

  const asOf = document.getElementById("asOf");
  asOf.textContent = `As-of date: ${payload.as_of_date || "-"}. Reporting-only: ${payload.reporting_only ? "YES" : "NO"}.`;
}

function renderMostDislocated(rows) {
  const top = rows.slice(0, 10);
  const data = top.map((row) => [
    esc(row.industry || "-"),
    esc(row.sector || "-"),
    pct(row.returns?.return_3m_pct),
    pct(row.returns?.return_3m_vs_market_pct),
    pct(row.drawdown?.from_available_history_high_pct),
    `${row.history_coverage?.members_with_history || 0}/${row.member_count || 0}`,
  ]);
  document.getElementById("mostDislocated").innerHTML = tableHtml(
    ["Industry", "Sector", "3M Return", "3M vs Market", "Drawdown from High", "History Coverage"],
    data,
  );
}

function renderImprovingInternals(rows) {
  const top = rows.slice(0, 10);
  const data = top.map((row) => [
    esc(row.industry || "-"),
    esc(row.sector || "-"),
    pct(row.breadth?.above_50dma?.share_pct),
    pct(row.breadth?.above_50dma_share_change_20d_pp),
    pct(row.breadth?.above_200dma?.share_pct),
    pct(row.breadth?.positive_1m?.share_pct),
  ]);
  document.getElementById("improvingInternals").innerHTML = tableHtml(
    ["Industry", "Sector", "Above 50DMA", "50DMA Breadth Delta (20d)", "Above 200DMA", "Positive 1M"],
    data,
  );
}

function renderCurrentLeadership(rows) {
  const top = rows.slice(0, 10);
  const data = top.map((row) => [
    esc(row.industry || "-"),
    esc(row.sector || "-"),
    esc(row.momentum_context?.relative_strength_level || "UNAVAILABLE"),
    esc(row.momentum_context?.relative_momentum_change || "UNAVAILABLE"),
    pct(row.returns?.return_3m_vs_market_pct),
    pct(row.returns?.return_6m_vs_market_pct),
  ]);
  document.getElementById("currentLeadership").innerHTML = tableHtml(
    ["Industry", "Sector", "Relative Level", "Relative Change", "3M vs Market", "6M vs Market"],
    data,
  );
}

function render() {
  const rows = activeRows();
  const mode = String(document.getElementById("sortMode")?.value || "dislocated");
  const ordered = sortRows(rows, mode);
  renderMostDislocated(ordered);
  renderImprovingInternals(ordered);
  renderCurrentLeadership(ordered);
}

function initControls(payload) {
  const sectors = new Set();
  for (const row of payload.industries || []) {
    const sector = String(row.sector || "").trim();
    if (sector) sectors.add(sector);
  }
  const sectorFilter = document.getElementById("sectorFilter");
  for (const sector of [...sectors].sort()) {
    const opt = document.createElement("option");
    opt.value = sector;
    opt.textContent = sector;
    sectorFilter.appendChild(opt);
  }

  const rerender = () => render();
  document.getElementById("industryFilter").addEventListener("input", rerender);
  document.getElementById("sectorFilter").addEventListener("change", rerender);
  document.getElementById("sortMode").addEventListener("change", rerender);
}

async function main() {
  try {
    const payload = await fetchJson("/api/pis/dri/industry-map", 180000);
    _payload = payload;
    renderSummary(payload);
    initControls(payload);
    render();
  } catch (err) {
    const message = `DRI industry map unavailable: ${esc(err?.message || err)}`;
    for (const id of ["summary", "mostDislocated", "improvingInternals", "currentLeadership", "asOf"]) {
      const el = document.getElementById(id);
      if (el) el.innerHTML = `<span class="muted">${message}</span>`;
    }
  }
}

main();
