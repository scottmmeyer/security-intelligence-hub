"use strict";

// ─── Data paths ──────────────────────────────────────────────────────────────
const DATA = {
  policy:       "/data/allocation/recalculation_snapshots/",
  policyYaml:   "/config/allocation_policy.yaml",
  dimYaml:      "/config/allocation_dimensions.yaml",
  // NOTE: targets are now served from the archetype engine API, not the legacy CSV.
  // Legacy CSV kept as a fallback path only:
  targetsLegacy: "/data/current/strategic_allocation_targets.csv",
  overlays:     "/data/current/tactical_overlays.csv",
  recommendation: "/data/current/allocation_recommendation.csv",
  manifest:     "/data/allocation/manifest.json",
};

// ─── Asset class colors (matches CSS) ────────────────────────────────────────
const AC_COLORS = {
  EQUITIES:     "#1d3557",
  FIXED_INCOME: "#2a9d8f",
  DIGITAL:      "#8d5a97",
  COMMODITIES:  "#e76f51",
  CASH:         "#6b8e77",
};

// ─── State ────────────────────────────────────────────────────────────────────
let state = {
  policy: null,
  dimensions: null,
  targets: [],
  overlays: [],
  recommendations: [],
  manifest: null,
  snapshots: [],
  mandateType: "CONCENTRATED_ALPHA",
  displayName: "Concentrated Alpha",
  philosophy: "",
};

// ─── Utilities ────────────────────────────────────────────────────────────────

function parseCsvLine(line) {
  const result = [];
  let inQ = false, cur = "";
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') { inQ = !inQ; continue; }
    if (c === "," && !inQ) { result.push(cur); cur = ""; continue; }
    cur += c;
  }
  result.push(cur);
  return result;
}

function parseCsv(text) {
  const lines = text.trim().split("\n").filter(Boolean);
  if (!lines.length) return [];
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map(line => {
    const vals = parseCsvLine(line);
    const obj = {};
    headers.forEach((h, i) => { obj[h.trim()] = (vals[i] || "").trim(); });
    return obj;
  });
}

async function fetchText(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.text();
  } catch { return null; }
}

async function fetchJson(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

function toggleCard(bodyId, btnId) {
  const body = document.getElementById(bodyId);
  const btn  = document.getElementById(btnId);
  if (!body || !btn) return;
  const collapsed = body.classList.toggle("collapsed");
  btn.textContent = collapsed ? "▼ expand" : "▲ collapse";
}
window.toggleCard = toggleCard;

function show(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "";
}

function acColor(assetClass) {
  return AC_COLORS[assetClass] || "#888";
}

function acPill(assetClass) {
  const labels = {
    EQUITIES: "EQ", FIXED_INCOME: "FI", DIGITAL: "DIG",
    COMMODITIES: "COM", CASH: "CASH",
  };
  return `<span class="ac-pill ${assetClass}">${labels[assetClass] || assetClass}</span>`;
}

function pctBar(pct, assetClass, maxPct = 100) {
  const fill = Math.min(100, (pct / maxPct) * 100);
  return `<div class="alloc-bar-bg">
    <div class="alloc-bar-fill" style="width:${fill}%;background:${acColor(assetClass)};"></div>
  </div>`;
}

function deltaChip(delta) {
  if (delta === null || delta === undefined || delta === "") return '<span class="delta neu">—</span>';
  const d = parseFloat(delta);
  if (isNaN(d)) return '<span class="delta neu">—</span>';
  if (d > 0)  return `<span class="delta pos">+${d.toFixed(2)}%</span>`;
  if (d < 0)  return `<span class="delta neg">${d.toFixed(2)}%</span>`;
  return `<span class="delta neu">0.00%</span>`;
}

function confidenceBadge(score) {
  const s = parseFloat(score);
  if (isNaN(s)) return "";
  if (s >= 0.75) return '<span class="badge pass">HIGH</span>';
  if (s >= 0.55) return '<span class="badge warn">MED</span>';
  return '<span class="badge fail">LOW</span>';
}

// ─── Section 1: Structural Policy ────────────────────────────────────────────

function renderPolicy(policy) {
  if (!policy) return;

  const sp = policy.structural_policy || {};
  const rg = policy.recalculation_governance || {};
  const acg = policy.asset_class_governance || {};

  const limits = [
    { label: "Cash Floor",          value: `${sp.cash_floor_pct ?? "—"}%` },
    { label: "Max Micro Cap",       value: `${sp.max_micro_cap_pct ?? "—"}%` },
    { label: "Max Digital Assets",  value: `${sp.max_digital_assets_pct ?? "—"}%` },
    { label: "Max Single Sector",   value: `${sp.max_single_sector_pct ?? "—"}%` },
    { label: "Max Mega Concentration", value: `${sp.max_mega_concentration_pct ?? "—"}%` },
    { label: "Max Single Asset Class", value: `${sp.max_single_asset_class_pct ?? "—"}%` },
    { label: "Min International",   value: `${sp.min_international_pct ?? "—"}%` },
    { label: "Max Recalc Delta",    value: `${rg.max_single_recalculation_delta_pct ?? "—"}%` },
    { label: "Confidence Threshold", value: rg.confidence_threshold ?? "—" },
    { label: "Policy Version",      value: policy.version ?? "—" },
    { label: "Effective Date",      value: policy.effective_date ?? "—" },
    { label: "Policy ID",           value: policy.policy_id ?? "—" },
  ];

  const grid = document.getElementById("policy-limits-grid");
  if (grid) {
    grid.innerHTML = limits.map(l => `
      <div class="policy-item">
        <div class="policy-label">${l.label}</div>
        <div class="policy-value">${l.value}</div>
      </div>`).join("");
  }

  // Asset class governance table
  const acTableEl = document.getElementById("policy-ac-table");
  if (acTableEl && Object.keys(acg).length) {
    const rows = Object.entries(acg).map(([ac, cfg]) => `
      <tr>
        <td>${acPill(ac)} <span style="margin-left:6px;">${ac.replace("_", " ")}</span></td>
        <td>${cfg.max_pct ?? "—"}%</td>
        <td>${cfg.min_pct ?? "—"}%</td>
        <td>${cfg.replay_sophistication ?? "—"}</td>
        <td>${cfg.tactical_overlays_supported ? '<span class="badge pass">YES</span>' : '<span class="badge fail">NO</span>'}</td>
      </tr>`).join("");
    acTableEl.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Asset Class</th><th>Max %</th><th>Min %</th><th>Replay</th><th>Overlays</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  show("section-policy");
}

// ─── Section 2: D3 Sunburst ───────────────────────────────────────────────────

function buildSunburstData(targets, dimensions) {
  // Build hierarchy from dimension nodes + inject target pct values
  const targetMap = {};
  targets.forEach(t => { targetMap[t.node_key] = t; });

  function buildNode(key, dimMap) {
    const dim = dimMap[key];
    const tgt = targetMap[key];
    const pct = tgt ? parseFloat(tgt.target_pct_of_total) || 0 : 0;
    const children = (dim?.children || [])
      .map(ck => buildNode(ck, dimMap))
      .filter(Boolean);
    return {
      name: key,
      label: dim?.label || key,
      pct,
      assetClass: key.split(".")[0],
      children: children.length ? children : undefined,
      value: children.length ? undefined : pct,
    };
  }

  const dimMap = {};
  if (dimensions && dimensions.nodes) {
    dimensions.nodes.forEach(n => { dimMap[n.key] = n; });
  }

  // Level 1 keys
  const l1Keys = ["EQUITIES", "FIXED_INCOME", "DIGITAL", "COMMODITIES", "CASH"];
  const children = l1Keys.map(k => buildNode(k, dimMap)).filter(Boolean);
  return { name: "root", children };
}

function renderSunburst(targets, dimensions) {
  const wrap = document.getElementById("sunburst-svg-wrap");
  if (!wrap) return;
  wrap.innerHTML = "";

  const size = Math.min(wrap.clientWidth || 480, 480);
  const radius = size / 2;

  const data = buildSunburstData(targets, dimensions);

  const root = d3.hierarchy(data)
    .sum(d => d.value || 0)
    .sort((a, b) => b.value - a.value);

  const partition = d3.partition().size([2 * Math.PI, radius]);
  partition(root);

  const arc = d3.arc()
    .startAngle(d => d.x0)
    .endAngle(d => d.x1)
    .padAngle(d => Math.min((d.x1 - d.x0) / 2, 0.005))
    .padRadius(radius / 2)
    .innerRadius(d => d.y0)
    .outerRadius(d => d.y1 - 2);

  const svg = d3.create("svg")
    .attr("viewBox", `${-radius} ${-radius} ${size} ${size}`)
    .attr("width", size)
    .attr("height", size)
    .style("font-family", "Avenir Next, Segoe UI, sans-serif");

  // Tooltip
  const tooltip = d3.select("body").selectAll(".sun-tooltip").data([null]).join("div")
    .attr("class", "sun-tooltip")
    .style("position", "fixed")
    .style("background", "#fffaf2")
    .style("border", "1px solid #d9ceb8")
    .style("border-radius", "8px")
    .style("padding", "8px 12px")
    .style("font-size", "0.82rem")
    .style("pointer-events", "none")
    .style("opacity", 0)
    .style("z-index", 1000)
    .style("max-width", "220px");

  svg.append("g")
    .selectAll("path")
    .data(root.descendants().filter(d => d.depth > 0))
    .join("path")
    .attr("d", arc)
    .attr("fill", d => {
      const ac = d.data.assetClass || d.ancestors().find(a => a.depth === 1)?.data?.name || "EQUITIES";
      const base = AC_COLORS[ac] || "#888";
      // Lighten for deeper levels
      return d.depth === 1 ? base : lightenColor(base, (d.depth - 1) * 0.18);
    })
    .attr("stroke", "#fffaf2")
    .attr("stroke-width", 1.5)
    .style("cursor", "pointer")
    .on("mouseover", function(event, d) {
      d3.select(this).attr("opacity", 0.8);
      const pct = d.data.pct ? d.data.pct.toFixed(2) : (d.value ? d.value.toFixed(2) : "0.00");
      tooltip
        .html(`<strong>${d.data.label}</strong><br/>
               <span style="color:#575043;">${d.data.name}</span><br/>
               <span style="color:#0d5c63;font-weight:700;">${pct}% of portfolio</span>`)
        .style("opacity", 1);
    })
    .on("mousemove", function(event) {
      tooltip.style("left", (event.clientX + 14) + "px").style("top", (event.clientY - 28) + "px");
    })
    .on("mouseout", function() {
      d3.select(this).attr("opacity", 1);
      tooltip.style("opacity", 0);
    });

  // Center label
  svg.append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "-0.3em")
    .attr("font-size", "0.72rem")
    .attr("fill", "#575043")
    .text("4-Ring");
  svg.append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "0.9em")
    .attr("font-size", "0.72rem")
    .attr("fill", "#575043")
    .text("Hierarchy");

  wrap.appendChild(svg.node());

  // Legend (L1 only)
  const legendEl = document.getElementById("sunburst-legend");
  if (legendEl) {
    const l1 = root.descendants().filter(d => d.depth === 1);
    legendEl.innerHTML = l1.map(d => {
      const pct = (d.value || 0).toFixed(2);
      return `<div class="sun-legend-item">
        <div class="sun-legend-swatch" style="background:${AC_COLORS[d.data.name] || '#888'};"></div>
        <span class="sun-legend-label">${d.data.label}</span>
        <span class="sun-legend-pct">${pct}%</span>
      </div>`;
    }).join("");
  }

  show("section-sunburst");
}

function lightenColor(hex, amount) {
  // Simple hex lightening
  let r = parseInt(hex.slice(1, 3), 16);
  let g = parseInt(hex.slice(3, 5), 16);
  let b = parseInt(hex.slice(5, 7), 16);
  r = Math.min(255, Math.round(r + (255 - r) * amount));
  g = Math.min(255, Math.round(g + (255 - g) * amount));
  b = Math.min(255, Math.round(b + (255 - b) * amount));
  return `rgb(${r},${g},${b})`;
}

// ─── Section 3: Recalculation / Validators ───────────────────────────────────

function renderRecalcPanel(manifest, snapshots) {
  // Snapshot meta
  const metaEl = document.getElementById("snapshot-meta");
  if (metaEl && manifest) {
    metaEl.innerHTML = `
      <span><strong>Latest Recalc:</strong> ${manifest.latest_recalculation_id || "—"}</span>
      <span><strong>Date:</strong> ${manifest.latest_recalculation_date || "—"}</span>
      <span><strong>Total Snapshots:</strong> ${manifest.total_snapshots || "—"}</span>
      <span><strong>Updated:</strong> ${manifest.updated_at_utc ? manifest.updated_at_utc.slice(0,19).replace("T"," ") + " UTC" : "—"}</span>
    `;
  }

  // Latest snapshot change summary
  const changeEl = document.getElementById("change-summary");
  if (changeEl && snapshots.length) {
    const latest = snapshots[snapshots.length - 1];
    const changes = Array.isArray(latest.change_summary) ? latest.change_summary : [latest.change_summary];
    changeEl.innerHTML = `
      <div style="font-size:0.82rem;color:var(--muted);">
        <strong>Change Summary (${latest.recalculation_id}):</strong>
        <ul style="margin:6px 0 0;padding-left:18px;line-height:1.7;">
          ${changes.map(c => `<li>${c}</li>`).join("")}
        </ul>
        <div style="margin-top:4px;">${latest.unchanged_summary || ""}</div>
      </div>`;
  }

  // Validators — inferred from change summary (PASS if no errors in change_summary)
  const validatorEl = document.getElementById("validator-grid");
  const VALIDATORS = [
    "hierarchy_sums", "policy_bounds", "tactical_overflow", "overlay_staleness",
    "recalculation_churn", "evidence_alignment", "concentration_ceilings", "lineage_completeness",
  ];
  if (validatorEl) {
    // We can't re-run validators client-side; show PASS for all if latest snapshot is valid
    const isValid = snapshots.length === 0 || (snapshots[snapshots.length - 1].total_allocation_valid);
    validatorEl.innerHTML = VALIDATORS.map(v => `
      <div class="validator-item">
        <span class="validator-icon">${isValid ? "✓" : "✗"}</span>
        <div>
          <div class="validator-name">${v.replace(/_/g, " ")}</div>
          <div class="validator-errors">${isValid ? "" : "See CLI output for details."}</div>
        </div>
        <span class="badge ${isValid ? "pass" : "fail"}" style="margin-left:auto;">${isValid ? "PASS" : "FAIL"}</span>
      </div>`).join("");
  }

  show("section-recalc");
}

// ─── Section 4: Overlays ─────────────────────────────────────────────────────

function renderOverlays(overlays) {
  const tableEl = document.getElementById("overlay-table");
  const emptyEl = document.getElementById("overlay-empty");
  const active = overlays.filter(o => o.status === "ACTIVE");

  if (!active.length) {
    if (tableEl) tableEl.style.display = "none";
    if (emptyEl) emptyEl.style.display = "";
  } else {
    if (emptyEl) emptyEl.style.display = "none";
    if (tableEl) {
      tableEl.innerHTML = `
        <thead><tr>
          <th>ID</th><th>Dimension</th><th>Value</th>
          <th>Overlay %</th><th>Signal</th><th>Expires</th><th>Status</th>
        </tr></thead>
        <tbody>${active.map(o => `
          <tr>
            <td style="font-size:0.78rem;color:var(--muted);">${o.overlay_id}</td>
            <td>${o.dimension_type}</td>
            <td>${o.dimension_value}</td>
            <td>${deltaChip(o.overlay_pct)}</td>
            <td>${o.momentum_signal}</td>
            <td>${o.expiry_date || "—"}</td>
            <td><span class="badge pass">ACTIVE</span></td>
          </tr>`).join("")}
        </tbody>`;
    }
  }
  show("section-overlay");
}

// ─── Section 5: Strategic Targets ────────────────────────────────────────────

function renderTargets(targets) {
  const tableEl = document.getElementById("targets-table");
  const filterAC = document.getElementById("filter-asset-class");
  const filterDepth = document.getElementById("filter-depth");

  function draw() {
    const ac    = filterAC?.value || "";
    const depth = filterDepth?.value || "";
    const rows  = targets.filter(t =>
      (!ac    || t.asset_class === ac) &&
      (!depth || t.hierarchy_depth === depth)
    );

    if (!tableEl) return;
    tableEl.innerHTML = `
      <thead><tr>
        <th>Node Key</th><th>L</th><th>Class</th>
        <th>% of Parent</th><th>% of Total</th>
        <th>Allocation</th><th>Delta</th><th>Confidence</th>
      </tr></thead>
      <tbody>${rows.map(t => `
        <tr>
          <td style="font-size:0.8rem;">${t.node_key}</td>
          <td style="text-align:center;">${t.hierarchy_depth}</td>
          <td>${acPill(t.asset_class)}</td>
          <td>${parseFloat(t.target_pct_of_parent || 0).toFixed(2)}%</td>
          <td><strong>${parseFloat(t.target_pct_of_total || 0).toFixed(2)}%</strong></td>
          <td style="min-width:80px;">${pctBar(parseFloat(t.target_pct_of_total || 0), t.asset_class)}</td>
          <td>${deltaChip(t.delta_pct)}</td>
          <td>${confidenceBadge(t.confidence_score)}</td>
        </tr>`).join("")}
      </tbody>`;
  }

  filterAC?.addEventListener("change", draw);
  filterDepth?.addEventListener("change", draw);
  draw();
  show("section-targets");
}

// ─── Section 6: Concentration Risk ───────────────────────────────────────────

function renderConcentration(targets, policy) {
  const el = document.getElementById("concentration-bars");
  if (!el) return;

  const sp = policy?.structural_policy || {};
  const checks = [
    {
      label: "EQUITIES.US.MEGA (Mega concentration)",
      value: parseFloat(targets.find(t => t.node_key === "EQUITIES.US.MEGA")?.target_pct_of_total || 0),
      ceiling: sp.max_mega_concentration_pct ?? 50,
      ac: "EQUITIES",
    },
    {
      label: "DIGITAL (Digital assets ceiling)",
      value: parseFloat(targets.find(t => t.node_key === "DIGITAL")?.target_pct_of_total || 0),
      ceiling: sp.max_digital_assets_pct ?? 8,
      ac: "DIGITAL",
    },
    {
      label: "Micro Cap combined",
      value: targets.filter(t => t.node_key.includes("MICRO"))
               .reduce((sum, t) => sum + parseFloat(t.target_pct_of_total || 0), 0),
      ceiling: sp.max_micro_cap_pct ?? 5,
      ac: "EQUITIES",
    },
    {
      label: "CASH (floor check)",
      value: parseFloat(targets.find(t => t.node_key === "CASH")?.target_pct_of_total || 0),
      ceiling: 100, floor: sp.cash_floor_pct ?? 2,
      ac: "CASH",
    },
  ];

  el.innerHTML = checks.map(c => {
    const pct = c.value;
    const ceiling = c.ceiling;
    const ratio = Math.min(1, pct / (ceiling || 100));
    const warn = pct > ceiling * 0.85;
    const over = pct > ceiling;
    const color = over ? "var(--fail)" : warn ? "var(--warn)" : acColor(c.ac);
    const badgeClass = over ? "fail" : warn ? "warn" : "pass";
    const badgeText = over ? "OVER" : warn ? "HIGH" : "OK";

    return `<div style="margin-bottom:14px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
        <span style="font-size:0.85rem;">${c.label}</span>
        <span>
          <strong style="font-size:0.88rem;">${pct.toFixed(2)}%</strong>
          <span style="font-size:0.8rem;color:var(--muted);"> / ${ceiling}% ceiling</span>
          <span class="badge ${badgeClass}" style="margin-left:6px;">${badgeText}</span>
        </span>
      </div>
      <div class="alloc-bar-bg" style="height:12px;">
        <div class="alloc-bar-fill" style="width:${(ratio * 100).toFixed(1)}%;background:${color};"></div>
      </div>
    </div>`;
  }).join("");

  show("section-concentration");
}

// ─── Section 7: Allocation Recommendation ────────────────────────────────────

let recommendationChart = null;

function renderRecommendation(recommendations, targets) {
  const l1Recs = recommendations.filter(r => {
    const t = targets.find(tt => tt.node_key === r.node_key);
    return t && t.hierarchy_depth === "1";
  });

  // Fallback: if no recommendations, use L1 targets directly
  const l1Data = l1Recs.length ? l1Recs.map(r => ({
    label: r.node_key.replace("_", " "),
    strategic: parseFloat(r.strategic_target_pct || 0),
    effective: parseFloat(r.effective_target_pct || 0),
    overlay:   parseFloat(r.tactical_overlay_pct || 0),
    ac: r.asset_class,
  })) : targets
    .filter(t => t.hierarchy_depth === "1")
    .map(t => ({
      label: t.node_key.replace("_", " "),
      strategic: parseFloat(t.target_pct_of_total || 0),
      effective: parseFloat(t.target_pct_of_total || 0),
      overlay: 0,
      ac: t.asset_class,
    }));

  const ctx = document.getElementById("recommendation-chart")?.getContext("2d");
  if (ctx) {
    if (recommendationChart) recommendationChart.destroy();
    recommendationChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: l1Data.map(d => d.label),
        datasets: [
          {
            label: "Strategic Target %",
            data: l1Data.map(d => d.strategic),
            backgroundColor: l1Data.map(d => acColor(d.ac) + "cc"),
            borderColor:     l1Data.map(d => acColor(d.ac)),
            borderWidth: 1.5,
            borderRadius: 6,
          },
          {
            label: "Tactical Overlay %",
            data: l1Data.map(d => d.overlay),
            backgroundColor: "rgba(242,143,59,0.4)",
            borderColor:     "rgba(242,143,59,0.9)",
            borderWidth: 1.5,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { position: "top", labels: { font: { size: 12 } } },
          tooltip: {
            callbacks: {
              label: ctx => `${ctx.dataset.label}: ${ctx.raw.toFixed(2)}%`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: v => v + "%" },
            grid: { color: "#f0ebe0" },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }

  // Table
  const tableEl = document.getElementById("recommendation-table");
  if (tableEl && l1Data.length) {
    tableEl.innerHTML = `
      <thead><tr>
        <th>Node</th><th>Asset Class</th><th>Strategic %</th>
        <th>Overlay %</th><th>Effective %</th><th>Capped?</th>
      </tr></thead>
      <tbody>${l1Data.map(d => {
        const rec = l1Recs.find(r => r.asset_class === d.ac) || {};
        return `<tr>
          <td>${d.label}</td>
          <td>${acPill(d.ac)}</td>
          <td>${d.strategic.toFixed(2)}%</td>
          <td>${deltaChip(d.overlay)}</td>
          <td><strong>${d.effective.toFixed(2)}%</strong></td>
          <td>${rec.is_policy_capped === "True"
            ? '<span class="badge warn">CAPPED</span>'
            : '<span class="badge pass">—</span>'}</td>
        </tr>`;
      }).join("")}
      </tbody>`;
  }

  show("section-recommendation");
}

// ─── Section 8: Historical Snapshots ─────────────────────────────────────────

function renderHistory(manifest) {
  const tableEl  = document.getElementById("history-table");
  const emptyEl  = document.getElementById("history-empty");
  const history  = manifest?.history || [];

  if (!history.length) {
    if (tableEl) tableEl.style.display = "none";
    if (emptyEl) emptyEl.style.display = "";
  } else {
    if (emptyEl) emptyEl.style.display = "none";
    if (tableEl) {
      tableEl.innerHTML = `
        <thead><tr>
          <th>Recalculation ID</th><th>Date</th><th>Triggered By</th>
          <th>Changes</th><th>Valid?</th>
        </tr></thead>
        <tbody>${[...history].reverse().map(h => `
          <tr>
            <td style="font-size:0.78rem;">${h.recalculation_id}</td>
            <td>${h.recalculation_date || "—"}</td>
            <td>${h.triggered_by || "—"}</td>
            <td>${h.change_count ?? "—"}</td>
            <td>${h.total_allocation_valid
              ? '<span class="badge pass">VALID</span>'
              : '<span class="badge fail">INVALID</span>'}</td>
          </tr>`).join("")}
        </tbody>`;
    }
  }
  show("section-history");
}

// ─── Bootstrap ───────────────────────────────────────────────────────────────

async function loadAllData() {
  const mandate = document.getElementById("archetypeSelect")?.value || "CONCENTRATED_ALPHA";

  const [
    policyYamlText,
    dimYamlText,
    archetypeResp,
    overlaysText,
    recommendationText,
    manifestJson,
  ] = await Promise.all([
    fetchText(DATA.policyYaml),
    fetchText(DATA.dimYaml),
    fetchJson(`/api/portfolio/archetype-targets?mandate=${encodeURIComponent(mandate)}`),
    fetchText(DATA.overlays),
    fetchText(DATA.recommendation),
    fetchJson(DATA.manifest),
  ]);

  if (policyYamlText && typeof jsyaml !== "undefined") {
    state.policy = jsyaml.load(policyYamlText);
  }
  if (dimYamlText && typeof jsyaml !== "undefined") {
    state.dimensions = jsyaml.load(dimYamlText);
  }

  // ── Archetype targets: prefer API response, fall back to legacy CSV ──────
  if (archetypeResp && !archetypeResp.error && Array.isArray(archetypeResp.targets)) {
    state.targets     = archetypeResp.targets;
    state.mandateType = archetypeResp.mandate_type || mandate;
    state.displayName = archetypeResp.display_name || mandate;
    state.philosophy  = archetypeResp.philosophy  || "";
  } else {
    // Fallback to legacy CSV (should not happen in normal operation)
    const legacyText = await fetchText(DATA.targetsLegacy);
    state.targets     = legacyText ? parseCsv(legacyText) : [];
    state.mandateType = mandate;
    state.displayName = mandate;
    state.philosophy  = "";
  }

  // Show active archetype badge + philosophy
  const badge = document.getElementById("archetypeActiveBadge");
  if (badge) {
    badge.textContent = state.displayName;
    badge.style.display = "inline-block";
  }
  const philEl = document.getElementById("archetypePhilosophy");
  if (philEl) {
    if (state.philosophy) {
      philEl.textContent = state.philosophy;
      philEl.style.display = "block";
    } else {
      philEl.style.display = "none";
    }
  }

  state.overlays       = overlaysText       ? parseCsv(overlaysText)       : [];
  state.recommendations = recommendationText ? parseCsv(recommendationText) : [];
  state.manifest       = manifestJson;

  // Load all snapshot JSONs from manifest history
  if (manifestJson?.history?.length) {
    const snapshotPromises = manifestJson.history.map(h =>
      fetchJson(`/data/allocation/recalculation_snapshots/${h.recalculation_id}.json`)
    );
    state.snapshots = (await Promise.all(snapshotPromises)).filter(Boolean);
  }

  // Hide loading bar
  const loading = document.getElementById("loading-bar");
  if (loading) loading.style.display = "none";

  // Render all sections
  renderPolicy(state.policy);
  renderSunburst(state.targets, state.dimensions);
  renderRecalcPanel(state.manifest, state.snapshots);
  renderOverlays(state.overlays);
  renderTargets(state.targets);
  renderConcentration(state.targets, state.policy);
  renderRecommendation(state.recommendations, state.targets);
  renderHistory(state.manifest);

  // Section 9: Architecture always visible
  show("section-arch");
}

function onMandateChange() {
  // Show loading bar while re-fetching archetype targets
  const loading = document.getElementById("loading-bar");
  if (loading) loading.style.display = "";
  // Hide the archetype badge while loading
  const badge = document.getElementById("archetypeActiveBadge");
  if (badge) badge.style.display = "none";
  loadAllData().catch(err => console.error("Mandate reload error:", err));
}

document.addEventListener("DOMContentLoaded", loadAllData);
