const DATA_PATHS = {
  replaySeries: "/data/current/replay_performance_series.csv",
  replayInputs: "/data/current/replay_inputs.csv",
  replayAvailability: "/data/current/replay_availability.csv",
  replayMatrix: "/data/current/replay_matrix.csv",
  analyticalUniverse: "/data/current/analytical_universe.csv",
  benchmarkRegistry: "/config/benchmark_category_registry.yaml",
  vehicleRegistry: "/config/investable_vehicle_registry.yaml",
  snapshotMetadata: "/data/current/current_snapshot_metadata.json",
};

const SERIES_LABELS = {
  BENCHMARK: "Benchmark",
  INVESTABLE_VEHICLE: "ETF/Fund",
  FULL_UNIVERSE: "Full Universe",
  TOP_N_STRATEGY: "Top 20 Strategy",
};

const SERIES_COLORS = {
  BENCHMARK: "#1d3557",
  INVESTABLE_VEHICLE: "#2a9d8f",
  FULL_UNIVERSE: "#8d5a97",
  TOP_N_STRATEGY: "#e76f51",
};

const REQUIRED_EMPTY_MESSAGE =
  "Replay contracts exist, but no performance points are available for this filter window.";

const EXPECTED_SERIES_TYPES = [
  "BENCHMARK",
  "INVESTABLE_VEHICLE",
  "FULL_UNIVERSE",
  "TOP_N_STRATEGY",
];

const state = {
  replayInputs: [],
  replaySeries: [],
  replaySeriesLoad: { status: "AVAILABLE", message: "" },
  replayInputsLoad: { status: "AVAILABLE", message: "" },
  replayAvailabilityLoad: { status: "AVAILABLE", message: "" },
  replayMatrixLoad: { status: "AVAILABLE", message: "" },
  replayAvailability: [],
  replayMatrix: [],
  analyticalUniverse: [],
  benchmarkRegistryText: "",
  vehicleRegistryText: "",
  snapshotMetadata: null,
  renderEpoch: 0,
};

function parseCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === "," && !inQuotes) {
      out.push(current);
      current = "";
      continue;
    }
    current += ch;
  }
  out.push(current);
  return out;
}

function parseCsv(text) {
  const rows = text
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.length > 0);

  if (!rows.length) return [];
  const headers = parseCsvLine(rows[0]);
  return rows.slice(1).map((line) => {
    const values = parseCsvLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    return row;
  });
}

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: HTTP ${response.status}`);
  }
  return response.text();
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: HTTP ${response.status}`);
  }
  return response.json();
}

async function fetchTextStatus(path) {
  try {
    const text = await fetchText(path);
    return { status: "AVAILABLE", text, message: "" };
  } catch (error) {
    const msg = String(error && error.message ? error.message : error || "");
    if (msg.includes("HTTP 404")) {
      return {
        status: "UNAVAILABLE",
        text: "",
        message: `${path} is missing (HTTP 404). Historical replay panels are unavailable, but current-state panels remain available.`,
      };
    }
    return {
      status: "ERROR",
      text: "",
      message: `Replay performance series could not be loaded: ${msg}`,
    };
  }
}

function countRegistryEntries(yamlText, keyName) {
  const regex = new RegExp(`^\\s*-\\s*${keyName}:`, "gm");
  const matches = yamlText.match(regex);
  return matches ? matches.length : 0;
}

function lookupRegistryEntry(yamlText, idKey, idValue) {
  if (!yamlText || !idValue) return null;
  const blocks = yamlText.split(/\n(?=\s{2}-\s)/);
  for (const block of blocks) {
    const idMatch = block.match(new RegExp(`\\b${idKey}:\\s*(\\S+)`));
    if (idMatch && idMatch[1].trim() === idValue.trim()) {
      const nameMatch = block.match(/\bname:\s*(.+)/);
      const symbolMatch = block.match(/\bsymbol(?:_or_index)?:\s*(\S+)/);
      return {
        name: nameMatch ? nameMatch[1].trim() : null,
        symbol: symbolMatch ? symbolMatch[1].trim() : null,
      };
    }
  }
  return null;
}

function updateActiveLegend(replayMatrixRow) {
  const benchmarkEl = document.getElementById("legendBenchmarkId");
  const vehicleEl = document.getElementById("legendVehicleId");
  if (!benchmarkEl || !vehicleEl) return;
  if (!replayMatrixRow) {
    benchmarkEl.textContent = "—";
    vehicleEl.textContent = "—";
    return;
  }
  const bm = lookupRegistryEntry(state.benchmarkRegistryText, "benchmark_id", replayMatrixRow.benchmark_id || "");
  benchmarkEl.textContent = bm
    ? `${bm.symbol}\u2002\u00b7\u2002${bm.name}`
    : replayMatrixRow.benchmark_id || "—";
  const vh = lookupRegistryEntry(state.vehicleRegistryText, "vehicle_id", replayMatrixRow.vehicle_id || "");
  vehicleEl.textContent = vh
    ? `${vh.symbol}\u2002\u00b7\u2002${vh.name}`
    : replayMatrixRow.vehicle_id || "—";
}

function setStatus(message, isEmpty = false) {
  const box = document.getElementById("statusBox");
  box.textContent = message;
  box.classList.toggle("empty", isEmpty);
}

function lineMetricValue(row) {
  const cumulative = Number(row.cumulative_return);
  if (!Number.isNaN(cumulative)) return cumulative;
  const value = Number(row.value);
  return Number.isNaN(value) ? NaN : value;
}

function parseBoolText(value) {
  const raw = String(value || "").trim().toLowerCase();
  return raw === "true" || raw === "1" || raw === "yes";
}

function pointMetricValue(row) {
  const value = Number(row.value);
  return Number.isNaN(value) ? NaN : value;
}

function parseIsoDate(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function drawPlaceholder(ctx, width, height, message) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#d9ceb8";
  ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

  ctx.fillStyle = "#5a5347";
  ctx.font = "600 15px Avenir Next, Segoe UI, sans-serif";
  ctx.fillText("No Renderable Performance Lines", 24, 40);

  ctx.font = "14px Avenir Next, Segoe UI, sans-serif";
  const lines = message.match(/.{1,86}(\s|$)/g) || [message];
  lines.forEach((line, idx) => {
    ctx.fillText(line.trim(), 24, 74 + idx * 22);
  });
}

function drawSeriesChart(seriesRows) {
  const canvas = document.getElementById("seriesCanvas");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  if (!seriesRows.length) {
    drawPlaceholder(ctx, width, height, REQUIRED_EMPTY_MESSAGE);
    return;
  }

  const grouped = {};
  seriesRows.forEach((row) => {
    const type = row.series_type;
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push({ date: row.date, metric: lineMetricValue(row) });
  });

  Object.values(grouped).forEach((points) => {
    points.sort((a, b) => new Date(a.date) - new Date(b.date));
  });

  // Detect if TOP_N_STRATEGY and FULL_UNIVERSE have the same final value (lines would coincide)
  const fuPts = grouped["FULL_UNIVERSE"] || [];
  const topnPts = grouped["TOP_N_STRATEGY"] || [];
  const topNMatchesFU = fuPts.length > 0 && topnPts.length > 0 &&
    Math.abs(
      (fuPts[fuPts.length - 1].metric || 0) - (topnPts[topnPts.length - 1].metric || 0)
    ) < 0.0001;

  const allPoints = Object.values(grouped).flat().filter((p) => Number.isFinite(p.metric));
  if (!allPoints.length) {
    drawPlaceholder(ctx, width, height, REQUIRED_EMPTY_MESSAGE);
    return;
  }

  const dates = allPoints
    .map((p) => parseIsoDate(p.date))
    .filter((d) => d !== null)
    .map((d) => d.getTime());
  const minDate = Math.min(...dates);
  const maxDate = Math.max(...dates);

  const values = allPoints.map((p) => p.metric);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valuePad = (maxValue - minValue || 1) * 0.1;

  const bounds = {
    left: 72,
    top: 20,
    right: width - 20,
    bottom: height - 50,
  };

  const xScale = (t) => {
    if (maxDate === minDate) return (bounds.left + bounds.right) / 2;
    return bounds.left + ((t - minDate) / (maxDate - minDate)) * (bounds.right - bounds.left);
  };
  const yScale = (v) => {
    const lo = minValue - valuePad;
    const hi = maxValue + valuePad;
    if (hi === lo) return (bounds.top + bounds.bottom) / 2;
    return bounds.bottom - ((v - lo) / (hi - lo)) * (bounds.bottom - bounds.top);
  };

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#d9ceb8";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

  ctx.strokeStyle = "#bbb29f";
  ctx.beginPath();
  ctx.moveTo(bounds.left, bounds.top);
  ctx.lineTo(bounds.left, bounds.bottom);
  ctx.lineTo(bounds.right, bounds.bottom);
  ctx.stroke();

  const yTicks = 5;
  for (let i = 0; i <= yTicks; i += 1) {
    const ratio = i / yTicks;
    const y = bounds.bottom - ratio * (bounds.bottom - bounds.top);
    const value = (minValue - valuePad) + ratio * ((maxValue + valuePad) - (minValue - valuePad));

    ctx.strokeStyle = "#f0eadf";
    ctx.beginPath();
    ctx.moveTo(bounds.left, y);
    ctx.lineTo(bounds.right, y);
    ctx.stroke();

    ctx.fillStyle = "#665d50";
    ctx.font = "12px Avenir Next, Segoe UI, sans-serif";
    ctx.fillText(value.toFixed(2), 12, y + 4);
  }

  const xTickCount = 4;
  for (let i = 0; i <= xTickCount; i += 1) {
    const ratio = i / xTickCount;
    const t = minDate + ratio * (maxDate - minDate);
    const x = xScale(t);
    const d = new Date(t);
    const label = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;

    ctx.strokeStyle = "#f0eadf";
    ctx.beginPath();
    ctx.moveTo(x, bounds.top);
    ctx.lineTo(x, bounds.bottom);
    ctx.stroke();

    ctx.fillStyle = "#665d50";
    ctx.font = "12px Avenir Next, Segoe UI, sans-serif";
    ctx.fillText(label, Math.max(4, x - 35), bounds.bottom + 22);
  }

  Object.entries(grouped).forEach(([type, points]) => {
    const filtered = points.filter((p) => Number.isFinite(p.metric) && parseIsoDate(p.date));
    if (!filtered.length) return;

    ctx.strokeStyle = SERIES_COLORS[type] || "#333";
    ctx.lineWidth = 2.4;
    // When TOP_N_STRATEGY coincides with FULL_UNIVERSE, draw it dashed so both remain visible
    if (type === "TOP_N_STRATEGY" && topNMatchesFU) {
      ctx.setLineDash([10, 5]);
    } else {
      ctx.setLineDash([]);
    }
    ctx.beginPath();
    filtered.forEach((point, idx) => {
      const t = parseIsoDate(point.date).getTime();
      const x = xScale(t);
      const y = yScale(point.metric);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  });
}

function drawPointInTimeChart(seriesRows) {
  const canvas = document.getElementById("seriesCanvas");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  const grouped = {};
  seriesRows.forEach((row) => {
    const type = row.series_type;
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(row);
  });

  const points = Object.entries(grouped)
    .map(([type, rows]) => {
      const latest = rows.sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")))[rows.length - 1];
      return {
        type,
        value: pointMetricValue(latest),
      };
    })
    .filter((item) => Number.isFinite(item.value));

  if (!points.length) {
    drawPlaceholder(ctx, width, height, REQUIRED_EMPTY_MESSAGE);
    return;
  }

  const bounds = {
    left: 72,
    top: 20,
    right: width - 20,
    bottom: height - 50,
  };

  const maxValue = Math.max(...points.map((item) => item.value));
  const paddedMax = maxValue <= 0 ? 1 : maxValue * 1.1;
  const barWidth = (bounds.right - bounds.left) / Math.max(points.length * 1.8, 1);

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#d9ceb8";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, width - 1, height - 1);

  ctx.strokeStyle = "#bbb29f";
  ctx.beginPath();
  ctx.moveTo(bounds.left, bounds.top);
  ctx.lineTo(bounds.left, bounds.bottom);
  ctx.lineTo(bounds.right, bounds.bottom);
  ctx.stroke();

  ctx.fillStyle = "#5a5347";
  ctx.font = "600 14px Avenir Next, Segoe UI, sans-serif";
  ctx.fillText("Point-in-time mode: single timestamp available", bounds.left, 16);

  points.forEach((item, index) => {
    const x = bounds.left + (index + 0.5) * ((bounds.right - bounds.left) / points.length);
    const barHeight = (item.value / paddedMax) * (bounds.bottom - bounds.top);
    const y = bounds.bottom - barHeight;

    ctx.fillStyle = SERIES_COLORS[item.type] || "#333";
    ctx.fillRect(x - barWidth / 2, y, barWidth, barHeight);

    ctx.fillStyle = "#665d50";
    ctx.font = "12px Avenir Next, Segoe UI, sans-serif";
    ctx.fillText((SERIES_LABELS[item.type] || item.type).slice(0, 16), x - barWidth, bounds.bottom + 18);
    ctx.fillText(item.value.toFixed(2), x - barWidth / 2, y - 6);
  });
}

function computeSeriesStatuses(seriesRows) {
  return computeSeriesStatusesWithAvailability(seriesRows, null);
}

function computeSeriesStatusesWithAvailability(seriesRows, availabilityRow) {
  const grouped = {};
  seriesRows.forEach((row) => {
    const type = String(row.series_type || "");
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(row);
  });

  const benchmarkAllowed = availabilityRow ? parseBoolText(availabilityRow.benchmark_available) : true;
  const vehicleAllowed = availabilityRow ? parseBoolText(availabilityRow.vehicle_available) : true;
  const stockAllowed = availabilityRow ? parseBoolText(availabilityRow.stock_replay_available) : false;
  const topNAllowed = availabilityRow ? parseBoolText(availabilityRow.top_n_available) : false;

  const typeAllowed = {
    BENCHMARK: benchmarkAllowed,
    INVESTABLE_VEHICLE: vehicleAllowed,
    FULL_UNIVERSE: stockAllowed,
    TOP_N_STRATEGY: topNAllowed,
  };

  return EXPECTED_SERIES_TYPES.map((type) => {
    const points = grouped[type] || [];
    if (!typeAllowed[type]) {
      return `${SERIES_LABELS[type]}: unavailable`;
    }
    if (points.length === 0) {
      return `${SERIES_LABELS[type]}: pending`;
    }
    if (points.length === 1) {
      return `${SERIES_LABELS[type]}: insufficient_history`;
    }
    return `${SERIES_LABELS[type]}: initialized`;
  });
}

function getSelectedFilters() {
  return {
    geography: document.getElementById("geographySelect").value,
    marketCap: document.getElementById("marketCapSelect").value,
    subtier: document.getElementById("subtierSelect") ? document.getElementById("subtierSelect").value : "",
    industry: document.getElementById("industrySelect").value,
    timeframe: document.getElementById("timeframeSelect").value,
    topN: String(Number(document.getElementById("topNInput").value || 20)),
  };
}

function pickReplayRow(filters) {
  const baseMatch = (row) =>
    String(row.filter_geography || "").toUpperCase() === filters.geography &&
    String(row.filter_market_cap_bucket || "").toUpperCase() === filters.marketCap &&
    String(row.filter_industry || "").toUpperCase() === filters.industry &&
    String(row.top_n || "") === filters.topN;

  const hasStocks = (row) => {
    const syms = String(row.selected_symbols || "").trim();
    return syms !== "" && syms !== "|";
  };

  const latest = (rows) =>
    rows.length ? rows.sort((a, b) => String(b.replay_id).localeCompare(String(a.replay_id)))[0] : null;

  // When a subtier is selected, prefer subtier-specific replays if they have stocks.
  // Fall back to full-bucket base when the subtier basket is empty for this geo.
  if (filters.subtier) {
    const subtierRows = state.replayInputs.filter(
      (row) => baseMatch(row) && String(row.filter_analytical_subtier || "").toUpperCase() === filters.subtier.toUpperCase() && hasStocks(row)
    );
    if (subtierRows.length) return latest(subtierRows);
  }

  // Full-bucket / ALL selected (or subtier yielded empty basket): only match base rows
  const rows = state.replayInputs.filter(
    (row) => baseMatch(row) && String(row.filter_analytical_subtier || "") === ""
  );
  return latest(rows);
}

function pickAvailabilityRow(filters) {
  const rows = state.replayAvailability.filter((row) => {
    return (
      String(row.geography || "").toUpperCase() === filters.geography &&
      String(row.market_cap_bucket || "").toUpperCase() === filters.marketCap &&
      String(row.industry || "").toUpperCase() === filters.industry
    );
  });
  return rows.length ? rows[0] : null;
}

function pickReplayMatrixRow(filters) {
  const rows = state.replayMatrix.filter((row) => {
    return (
      String(row.geography || "").toUpperCase() === filters.geography &&
      String(row.market_cap_bucket || "").toUpperCase() === filters.marketCap &&
      String(row.industry || "").toUpperCase() === filters.industry
    );
  });
  return rows.length ? rows[0] : null;
}

function availabilitySummaryLines() {
  const rows = [...state.replayAvailability].sort((a, b) => {
    const geo = String(a.geography || "").localeCompare(String(b.geography || ""));
    if (geo !== 0) return geo;
    return String(a.market_cap_bucket || "").localeCompare(String(b.market_cap_bucket || ""));
  });
  return rows.map((row) => {
    const benchmark = parseBoolText(row.benchmark_available) ? "AVAILABLE" : "PENDING";
    const vehicle = parseBoolText(row.vehicle_available) ? "AVAILABLE" : "PENDING";
    const stockReplay = parseBoolText(row.stock_replay_available) ? "AVAILABLE" : "NOT_GENERATED";
    const status = String(row.replay_status || "UNKNOWN");
    return `${row.geography} ${row.market_cap_bucket}: benchmark=${benchmark}, ETF/fund=${vehicle}, stock replay=${stockReplay}, status=${status}`;
  });
}

function drawGovernedPlaceholder(message) {
  const canvas = document.getElementById("seriesCanvas");
  const ctx = canvas.getContext("2d");
  drawPlaceholder(ctx, canvas.width, canvas.height, message);
}

function _renderReplayUnavailableState(reason, details) {
  const payload = details || {};
  const replayMetaNode = document.getElementById("replayMeta");
  const stockCoverageNode = document.getElementById("stockCoverageMeta");
  const returnComparisonNode = document.getElementById("returnComparisonTable");
  const explainerNode = document.getElementById("forwardBacktestExplainer");

  const message = payload.message || "Replay context unavailable for the selected view.";
  setStatus(message, true);
  drawGovernedPlaceholder(message);

  if (replayMetaNode) {
    replayMetaNode.textContent = JSON.stringify(
      {
        replay_panel_status: reason,
        ...payload,
      },
      null,
      2,
    );
  }
  if (stockCoverageNode) {
    stockCoverageNode.textContent = "Stock coverage unavailable: replay evidence summary is unavailable for the selected replay context.";
  }
  if (returnComparisonNode) {
    returnComparisonNode.innerHTML = "<p>Return comparison unavailable — replay evidence summary not available.</p>";
  }
  if (explainerNode) {
    explainerNode.style.display = "none";
  }
}

function _renderDecisionReadiness(payload) {
  const summaryEl = document.getElementById("decisionReadinessSummary");
  const pillsEl = document.getElementById("decisionReadinessPills");
  if (!summaryEl || !pillsEl) return;

  const readiness = payload && payload.decision_readiness ? payload.decision_readiness : null;
  if (!readiness) {
    summaryEl.textContent = "Decision readiness unavailable.";
    pillsEl.innerHTML = '<span class="refresh-insight-pill">No readiness payload available.</span>';
    return;
  }

  const classification = String(readiness.classification || "UNKNOWN");
  const pct = Number(readiness.core_fresh_pct);
  const stale = Number(readiness.stale_or_missing || 0);
  summaryEl.textContent = `Classification: ${classification} · Core freshness: ${Number.isFinite(pct) ? pct.toFixed(1) : "0.0"}% · Stale/missing: ${stale}`;
  pillsEl.innerHTML = [
    `<span class="refresh-insight-pill"><span class="universe-tag">Status</span>${_ovEscHtml(classification)}</span>`,
    `<span class="refresh-insight-pill"><span class="universe-tag">Freshness</span>${Number.isFinite(pct) ? pct.toFixed(1) : "0.0"}%</span>`,
    `<span class="refresh-insight-pill"><span class="universe-tag">Stale/Missing</span>${stale}</span>`,
  ].join("");
}

function _renderCandidateReadiness(payload) {
  const grid = document.getElementById("candidateReadinessGrid");
  if (!grid) return;
  const readiness = payload && payload.readiness ? payload.readiness : null;
  if (!readiness || typeof readiness !== "object") {
    grid.innerHTML = '<div class="candidate-metric-card">Candidate readiness unavailable.</div>';
    return;
  }

  const keys = ["research_universe", "cw_das", "ucf", "recommendations", "cra"];
  grid.innerHTML = keys.map((key) => {
    const metric = readiness[key] || {};
    const status = String(metric.status || "UNKNOWN");
    const fresh = Number(metric.core_fresh || 0);
    const total = Number(metric.total || 0);
    const pct = Number(metric.core_fresh_pct || 0);
    return `<div class="candidate-metric-card">
      <div class="candidate-metric-label">${_ovEscHtml(key.replaceAll("_", " ").toUpperCase())}</div>
      <div class="candidate-metric-value">${_ovEscHtml(status)}</div>
      <div class="candidate-metric-sub">Fresh: ${fresh}/${total} · ${Number.isFinite(pct) ? pct.toFixed(1) : "0.0"}%</div>
    </div>`;
  }).join("");
}

function _renderRecommendationFreshness(payload) {
  const filterEl = document.getElementById("recommendationFreshnessFilters");
  const bodyEl = document.getElementById("recommendationFreshnessBody");
  if (!filterEl || !bodyEl) return;

  const rows = Array.isArray(payload && payload.rows) ? payload.rows : [];
  const freshCount = rows.filter((row) => String(row.freshness || "").toUpperCase() === "FRESH").length;
  const staleCount = rows.length - freshCount;

  filterEl.innerHTML = [
    `<span class="refresh-insight-pill"><span class="universe-tag">Rows</span>${rows.length}</span>`,
    `<span class="refresh-insight-pill"><span class="universe-tag">Fresh</span>${freshCount}</span>`,
    `<span class="refresh-insight-pill"><span class="universe-tag">Stale</span>${staleCount}</span>`,
  ].join("");

  if (!rows.length) {
    bodyEl.innerHTML = '<tr><td colspan="7" style="color: var(--muted);">No recommendation freshness rows available.</td></tr>';
    return;
  }

  const providerCell = (cell) => {
    const source = cell && typeof cell === "object" ? cell : {};
    const stateText = String(source.state || "missing").toUpperCase();
    const stateLabel = {
      FRESH: "FRESH",
      STALE: "STALE",
      MISSING: "HOLDING ABSENT",
      NO_STARMINE_SCORE: "NO STARMINE ESS SCORE",
    }[stateText] || stateText;
    const dateText = String(source.date || "NA");
    return `${_ovEscHtml(stateLabel)} (${_ovEscHtml(dateText)})`;
  };

  bodyEl.innerHTML = rows.slice(0, 200).map((row) => `
    <tr>
      <td>${_ovEscHtml(String(row.symbol || "—"))}</td>
      <td>${providerCell(row.zacks)}</td>
      <td>${providerCell(row.danelfin)}</td>
      <td>${providerCell(row.yahoo)}</td>
      <td>${providerCell(row.ess)}</td>
      <td>${providerCell(row.fmp)}</td>
      <td>${_ovEscHtml(String(row.freshness || "UNKNOWN"))}</td>
    </tr>
  `).join("");
}

function _renderRefreshTransparencyUnavailable(message) {
  const summaryEl = document.getElementById("decisionReadinessSummary");
  const pillsEl = document.getElementById("decisionReadinessPills");
  const gridEl = document.getElementById("candidateReadinessGrid");
  const filterEl = document.getElementById("recommendationFreshnessFilters");
  const bodyEl = document.getElementById("recommendationFreshnessBody");

  if (summaryEl) summaryEl.textContent = message;
  if (pillsEl) pillsEl.innerHTML = `<span class="refresh-insight-pill">${_ovEscHtml(message)}</span>`;
  if (gridEl) gridEl.innerHTML = `<div class="candidate-metric-card">${_ovEscHtml(message)}</div>`;
  if (filterEl) filterEl.innerHTML = "";
  if (bodyEl) bodyEl.innerHTML = `<tr><td colspan="7" style="color: var(--muted);">${_ovEscHtml(message)}</td></tr>`;
}

function loadRefreshTransparencyPanels() {
  fetch("/api/refresh-transparency", { cache: "no-store" })
    .then((r) => r.ok ? r.json() : Promise.reject(r.status))
    .then((payload) => {
      _renderDecisionReadiness(payload);
      _renderCandidateReadiness(payload);
      _renderRecommendationFreshness(payload);
    })
    .catch(() => {
      _renderRefreshTransparencyUnavailable("Refresh transparency unavailable.");
    });
}

async function tryLoadReplayMetadata(replayId) {
  if (!replayId) return null;
  // Phase A: history is now snapshot_date-partitioned; try new path, fall back to legacy.
  const legacyPath = `/data/history/replays/replay_id=${replayId}/replay_metadata.json`;
  // We don't know snapshot_date from replayId alone, so try legacy first then rely on
  // replay_metadata_path from the matrix row (passed separately via state.replayMatrix).
  const matrixRow = state.replayMatrix.find((r) => String(r.replay_id || "") === replayId);
  const metadataPath = matrixRow && matrixRow.replay_metadata_path
    ? matrixRow.replay_metadata_path.replace(/^\/?(.*)/,  "/" + "$1")
    : legacyPath;
  try {
    const text = await fetchText(metadataPath);
    return JSON.parse(text);
  } catch (err) {
    // Fallback to legacy path if partitioned path fails
    if (metadataPath !== legacyPath) {
      try {
        const text = await fetchText(legacyPath);
        return JSON.parse(text);
      } catch {
        return null;
      }
    }
    return null;
  }
}

async function tryLoadEvidenceSummary(matrixRow) {
  if (!matrixRow) return null;
  const rawPath = matrixRow.replay_evidence_summary_path;
  if (!rawPath) return null;
  const path = rawPath.replace(/^\/?(.*)/,  "/" + "$1");
  try {
    const text = await fetchText(path);
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function renderForwardBacktestExplainer(replayInputRow, evidenceSummary) {
  const el = document.getElementById("forwardBacktestExplainer");
  if (!el) return;
  if (!replayInputRow) {
    el.style.display = "none";
    return;
  }

  const scoreDate = replayInputRow.composite_score_snapshot_date || replayInputRow.start_date || "—";
  const startDate = replayInputRow.start_date || "—";
  const endDate = replayInputRow.end_date || "—";
  const topN = replayInputRow.top_n || "20";
  const symbols = String(replayInputRow.selected_symbols || "").split("|").filter(Boolean);
  const marketCap = replayInputRow.filter_market_cap_bucket || "—";
  const geography = replayInputRow.filter_geography || "—";
  const portfolioDate =
    (state.snapshotMetadata && state.snapshotMetadata.snapshot_date)
    || (state.snapshotMetadata && String(state.snapshotMetadata.generated_at_utc || "").slice(0, 10))
    || new Date().toISOString().slice(0, 10);

  const parseIsoDateOnly = (s) => {
    const t = String(s || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(t)) return null;
    const d = new Date(`${t}T00:00:00Z`);
    return Number.isNaN(d.getTime()) ? null : d;
  };

  const portfolioDateObj = parseIsoDateOnly(portfolioDate);
  const measurementEndObj = parseIsoDateOnly(endDate);
  const replayAgeDays = (portfolioDateObj && measurementEndObj)
    ? Math.max(0, Math.round((portfolioDateObj.getTime() - measurementEndObj.getTime()) / (24 * 60 * 60 * 1000)))
    : null;

  let replayFreshnessLabel = "Unknown replay age";
  if (replayAgeDays !== null && replayAgeDays <= 14) replayFreshnessLabel = "Recent replay";
  else if (replayAgeDays !== null && replayAgeDays <= 45) replayFreshnessLabel = "Historical replay";
  else if (replayAgeDays !== null) replayFreshnessLabel = "Older replay";

  const showOlderWarning = replayAgeDays !== null && replayAgeDays > 30;
  const replayPurpose = "historical_validation";

  const fmt = (v) => (v === null || v === undefined || isNaN(Number(v))) ? "—" : (Number(v) * 100).toFixed(2) + "%";
  const finalTopN = evidenceSummary?.top_n_strategy_final_return;
  const finalBM = evidenceSummary?.benchmark_final_return;
  const delta = evidenceSummary?.strategy_vs_benchmark_delta;
  const deltaNum = Number(delta);
  const deltaSign = !isNaN(deltaNum) && deltaNum >= 0 ? "+" : "";
  const returnClass = !isNaN(deltaNum) ? (deltaNum >= 0 ? "positive" : "negative") : "";

  const returnBlock = (finalTopN !== null && finalTopN !== undefined)
    ? `<div class="fbt-block">
        <div class="fbt-label">Top-N Strategy Return</div>
        <div class="fbt-value ${returnClass}">${fmt(finalTopN)}<span style="font-size:0.82rem;font-weight:400;"> (${deltaSign}${fmt(delta)} vs Benchmark ${fmt(finalBM)})</span></div>
       </div>`
    : "";

  el.style.display = "block";
  el.innerHTML = `
    <div class="fbt-header">
      <span class="fbt-badge">Forward Backtest</span>
      <span class="fbt-subtitle">Historical replay validation — not today\'s portfolio state</span>
    </div>
    <div class="fbt-purpose">
      This panel tests whether historical SIH scores predicted future returns. It uses the selected score date and measurement window shown below.
      It does not represent today\'s portfolio performance or current recommendation freshness.
    </div>
    <div class="fbt-body">
      <div class="fbt-block">
        <div class="fbt-label">Historical score date</div>
        <div class="fbt-value">${scoreDate}</div>
      </div>
      <div class="fbt-block">
        <div class="fbt-label">Historical measurement window</div>
        <div class="fbt-value">${startDate} → ${endDate}</div>
      </div>
      <div class="fbt-block">
        <div class="fbt-label">Replay universe</div>
        <div class="fbt-value">${geography} ${marketCap}</div>
      </div>
      <div class="fbt-block">
        <div class="fbt-label">Historical selected basket</div>
        <div class="fbt-value">${symbols.length} (Top ${topN})</div>
      </div>
      ${returnBlock}
    </div>

    <div class="fbt-freshness">
      <div><strong>Replay age:</strong> ${replayAgeDays === null ? "Unknown" : `${replayAgeDays} days after measurement end`}</div>
      <div><strong>Portfolio date:</strong> ${portfolioDate || "—"}</div>
      <div><strong>Measurement ended:</strong> ${endDate || "—"}</div>
      <div><strong>Replay freshness:</strong> ${replayFreshnessLabel}</div>
    </div>

    ${showOlderWarning ? `<div class="fbt-warning">This replay window is historical and may be older than the current portfolio analysis. Use it to evaluate model behavior, not to make today\'s trade decision.</div>` : ""}

    <div class="fbt-stocks">
      <div class="fbt-label">Top ${topN} stocks scored on ${scoreDate} — held for the full period, no changes:</div>
      <div class="fbt-symbols">${symbols.map((s) => `<span class="fbt-symbol">${s}</span>`).join("")}</div>
    </div>
    <div class="fbt-explanation">
      These ${symbols.length} stocks were selected based exclusively on composite scores calculated on <strong>${scoreDate}</strong>.
      No information from after that date was used. Performance was then tracked forward from <strong>${startDate}</strong> to <strong>${endDate}</strong>
      using actual market prices, equally weighted, with no rebalancing.
      If the Top-N Strategy line is above the Benchmark and ETF/Fund lines, it means the scoring system
      successfully identified future outperformers — a true out-of-sample forward test.
      If it is below, the model did not add predictive value for this tier over this period.
    </div>
    <div class="fbt-guidance">
      Use Portfolio Alignment, Security-Level Intelligence, and Capital Deployment Queue for today\'s portfolio state.
      Use this Forward Backtest to evaluate whether past scores showed predictive value.
    </div>
  `;

  // Additive replay UX contract details for debugging; no calculation behavior changes.
  const replayMetaNode = document.getElementById("replayMeta");
  if (replayMetaNode) {
    try {
      const existing = JSON.parse(replayMetaNode.textContent || "{}");
      replayMetaNode.textContent = JSON.stringify(
        {
          ...existing,
          replay_purpose: replayPurpose,
          is_current_portfolio_state: false,
          selection_date_label: "Historical score date",
          measurement_window_label: "Historical measurement window",
          portfolio_date: portfolioDate,
          measurement_end_date: endDate,
          replay_age_days: replayAgeDays,
          replay_freshness_label: replayFreshnessLabel,
          replay_freshness_warning: showOlderWarning
            ? "This replay window is historical and may be older than the current portfolio analysis."
            : "",
        },
        null,
        2,
      );
    } catch {
      // no-op; meta view is diagnostic only
    }
  }
}

function renderStockCoveragePanel(evidenceSummary) {
  const panel = document.getElementById("stockCoverageMeta");
  if (!panel) return;
  if (!evidenceSummary) {
    panel.textContent = "Stock coverage data not available.";
    return;
  }
  const rawSelected = Array.isArray(evidenceSummary.selected_symbols) ? evidenceSummary.selected_symbols : [];
  const uniqueSelected = [...new Set(rawSelected)];
  const selected = uniqueSelected.join(", ") || "None";
  const dupCount = rawSelected.length - uniqueSelected.length;
  const missing = Array.isArray(evidenceSummary.missing_price_symbols) && evidenceSummary.missing_price_symbols.length
    ? evidenceSummary.missing_price_symbols.join(", ")
    : "None";
  const partial = Array.isArray(evidenceSummary.partial_price_symbols) && evidenceSummary.partial_price_symbols.length
    ? evidenceSummary.partial_price_symbols.join(", ")
    : "None";
  const universeSize = evidenceSummary.full_universe_symbol_count ?? null;
  const topN = evidenceSummary.top_n ?? null;
  const overlapNote = universeSize !== null && topN !== null && universeSize <= topN
    ? `\n⚠ Universe (${universeSize}) ≤ Top-N (${topN}): all universe stocks selected — Top-N Strategy = Full Universe; chart lines coincide`
    : "";
  const dupNote = dupCount > 0 ? ` (${dupCount} duplicate${dupCount > 1 ? "s" : ""} removed)` : "";
  panel.textContent = [
    `Coverage Status : ${evidenceSummary.coverage_status || "—"}`,
    `Full-Universe : ${evidenceSummary.full_universe_coverage_status || "—"}`,
    `Top-N : ${evidenceSummary.top_n_coverage_status || "—"}`,
    `Universe Size  : ${universeSize ?? "—"}`,
    `Top N          : ${topN ?? "—"}`,
    `Selected       : ${selected}${dupNote}`,
    `Missing Prices : ${missing}`,
    `Partial Prices : ${partial}`,
  ].join("\n") + overlapNote;
}

function renderReturnComparisonTable(evidenceSummary) {
  const container = document.getElementById("returnComparisonTable");
  if (!container) return;
  if (!evidenceSummary) {
    container.innerHTML = "<p>Return comparison unavailable — evidence summary not found.</p>";
    return;
  }
  const fmt = (v) => (v === null || v === undefined) ? "—" : (Number(v) * 100).toFixed(2) + "%";
  const rows = [
    ["Benchmark", fmt(evidenceSummary.benchmark_final_return), "—"],
    ["ETF / Fund (Vehicle)", fmt(evidenceSummary.investable_vehicle_final_return), "—"],
    ["Full Universe (Equal Weight)", fmt(evidenceSummary.full_universe_final_return), "—"],
    [
      `Top-N Strategy (N=${evidenceSummary.top_n ?? "?"})`,
      fmt(evidenceSummary.top_n_strategy_final_return),
      fmt(evidenceSummary.strategy_vs_benchmark_delta) + " vs Benchmark"
        + (evidenceSummary.strategy_vs_vehicle_delta != null
          ? " / " + fmt(evidenceSummary.strategy_vs_vehicle_delta) + " vs Vehicle"
          : ""),
    ],
  ];
  const thead = `<thead><tr><th>Series</th><th>Cumulative Return</th><th>Delta</th></tr></thead>`;
  const tbody = "<tbody>" + rows.map(([name, ret, delta]) =>
    `<tr><td>${name}</td><td>${ret}</td><td>${delta}</td></tr>`
  ).join("") + "</tbody>";
  container.innerHTML = `<table class="return-comparison">${thead}${tbody}</table>`;
}

async function render() {
  const renderId = ++state.renderEpoch;
  const isStale = () => renderId !== state.renderEpoch;

  const filters = getSelectedFilters();
  const replay = pickReplayRow(filters);
  const availability = pickAvailabilityRow(filters);
  const replayMatrixRow = pickReplayMatrixRow(filters);

  updateActiveLegend(replayMatrixRow);

  const replayMetaNode = document.getElementById("replayMeta");
  const registryMetaNode = document.getElementById("registryMeta");
  const availabilityMetaNode = document.getElementById("availabilityMeta");

  const registrySummary = {
    benchmark_definitions: countRegistryEntries(state.benchmarkRegistryText, "benchmark_id"),
    investable_vehicles: countRegistryEntries(state.vehicleRegistryText, "vehicle_id"),
    analytical_universe_rows: state.analyticalUniverse.length,
    replay_inputs_rows: state.replayInputs.length,
    replay_series_rows: state.replaySeries.length,
    replay_availability_rows: state.replayAvailability.length,
    replay_matrix_rows: state.replayMatrix.length,
  };
  registryMetaNode.textContent = JSON.stringify(registrySummary, null, 2);
  availabilityMetaNode.textContent = [
    "Replay Availability Summary",
    "",
    ...availabilitySummaryLines(),
  ].join("\n");

  const freshnessMeta = document.getElementById("snapshotFreshnessMeta");
  if (freshnessMeta) {
    const meta = state.snapshotMetadata;
    freshnessMeta.textContent = meta
      ? JSON.stringify(
          {
            snapshot_date: meta.snapshot_date,
            generated_at_utc: meta.generated_at_utc,
            freshness_status: meta.freshness_status,
            run_id: meta.run_id,
          },
          null,
          2,
        )
      : "current_snapshot_metadata.json not found";
  }

  if (state.replaySeriesLoad.status !== "AVAILABLE") {
    _renderReplayUnavailableState(state.replaySeriesLoad.status, {
      selected_filters: filters,
      replay_series_path: DATA_PATHS.replaySeries,
      message: state.replaySeriesLoad.message,
    });
    return;
  }

  if (state.replayInputsLoad.status !== "AVAILABLE") {
    _renderReplayUnavailableState(state.replayInputsLoad.status, {
      selected_filters: filters,
      replay_inputs_path: DATA_PATHS.replayInputs,
      message: state.replayInputsLoad.message,
    });
    return;
  }

  if (state.replayAvailabilityLoad.status !== "AVAILABLE") {
    _renderReplayUnavailableState(state.replayAvailabilityLoad.status, {
      selected_filters: filters,
      replay_availability_path: DATA_PATHS.replayAvailability,
      message: state.replayAvailabilityLoad.message,
    });
    return;
  }

  if (state.replayMatrixLoad.status !== "AVAILABLE") {
    _renderReplayUnavailableState(state.replayMatrixLoad.status, {
      selected_filters: filters,
      replay_matrix_path: DATA_PATHS.replayMatrix,
      message: state.replayMatrixLoad.message,
    });
    return;
  }

  if (!availability) {
    _renderReplayUnavailableState("UNAVAILABLE", {
      selected_filters: filters,
      message: "Replay availability governance mismatch: no availability row exists for selected category.",
    });
    return;
  }

  const replayStatus = String(availability.replay_status || "NOT_GENERATED").toUpperCase();
  const missingDependencies = String(availability.missing_dependencies || "").trim();
  const replayGenerated = parseBoolText(availability.replay_generated);

  if (!replayGenerated || ["NOT_GENERATED", "MISSING_MAPPING", "MISSING_MARKET_DATA", "BLOCKED"].includes(replayStatus)) {
    _renderReplayUnavailableState("UNAVAILABLE", {
      selected_filters: filters,
      availability,
      replay_matrix_row: replayMatrixRow || "not generated",
      message: [
        `Replay unavailable for ${filters.geography} ${filters.marketCap} ${filters.industry}.`,
        `Status: ${replayStatus}.`,
        missingDependencies ? `Missing dependencies: ${missingDependencies}` : "Missing dependencies: none reported.",
      ].join(" "),
    });
    return;
  }

  if (!replayMatrixRow) {
    _renderReplayUnavailableState("ERROR", {
      selected_filters: filters,
      availability,
      message: "Replay/UI mismatch: availability indicates generated replay but replay_matrix has no matching row.",
    });
    return;
  }

  const replayId = String(replay?.replay_id || replayMatrixRow.replay_id || "");
  console.log("[render] filters:", JSON.stringify(filters), "replayId:", replayId);
  const seriesRows = state.replaySeries
    .filter((row) => String(row.replay_id || "") === replayId)
    .sort((a, b) => {
      const type = String(a.series_type || "").localeCompare(String(b.series_type || ""));
      if (type !== 0) return type;
      return String(a.date || "").localeCompare(String(b.date || ""));
    });

  const replayMetadata = await tryLoadReplayMetadata(replayId);
  if (isStale()) {
    return;
  }

  // Phase H (WP-05D): load replay_evidence_summary.json from partition dir.
  // Wrapped defensively: evidence summary failures must never block chart rendering.
  let evidenceSummary = null;
  try {
    evidenceSummary = await tryLoadEvidenceSummary(replayMatrixRow);
    if (isStale()) {
      return;
    }
  } catch {
    // ignore — evidence summary is enhancement-only
  }
  try { renderStockCoveragePanel(evidenceSummary); } catch { /* non-fatal */ }
  try { renderReturnComparisonTable(evidenceSummary); } catch { /* non-fatal */ }
  // Phase F: extract replay_mode from replay_inputs row
  const replayInputRow = state.replayInputs.find((r) => String(r.replay_id || "") === replayId);
  try { renderForwardBacktestExplainer(replayInputRow, evidenceSummary); } catch { /* non-fatal */ }
  const replayMode = String(
    (replayInputRow && replayInputRow.replay_mode) ||
    (replayMetadata && replayMetadata.replay_mode) ||
    "HISTORICAL_VALIDATION"
  );

  // Phase F: display replay_mode badge in status
  const modeLabel = replayMode === "FORWARD_SIMULATION"
    ? "[SELECTED REPLAY]"
    : replayMode === "CURRENT_RECOMMENDATION"
    ? "[SELECTED REPLAY]"
    : "[FORWARD BACKTEST HISTORICAL]";

  replayMetaNode.textContent = JSON.stringify(
    {
      selected_filters: filters,
      replay_mode: replayMode,
      replay_row: replay || "replay_inputs row not found",
      availability,
      replay_matrix_row: replayMatrixRow,
      replay_metadata: replayMetadata || "not found in history partition",
    },
    null,
    2,
  );

  const hasSeries = seriesRows.length > 0;
  if (!hasSeries) {
    _renderReplayUnavailableState("UNAVAILABLE", {
      selected_filters: filters,
      replay_id: replayId,
      message: [
        "Replay generated but performance series rows are empty for selected category.",
        missingDependencies ? `Missing dependencies: ${missingDependencies}` : "",
      ].join(" ").trim(),
    });
    return;
  }

  const statusSummary = computeSeriesStatusesWithAvailability(seriesRows, availability).join(" | ");
  const uniqueDates = new Set(seriesRows.map((row) => String(row.date || ""))).size;
  if (uniqueDates <= 1) {
    setStatus(`Point-in-time render for replay ${replayId}. ${statusSummary}`);
    drawPointInTimeChart(seriesRows);
    return;
  }

  const subtierNote = filters.subtier && replay && String(replay.filter_analytical_subtier || "") === ""
    ? ` [${filters.subtier} subtier: no dedicated replay built — showing ${filters.geography} ${filters.marketCap} full-bucket results]`
    : "";

  setStatus(`${modeLabel} Selected replay artifact render with ${seriesRows.length} points for replay ${replayId}. ${statusSummary}${subtierNote}`);
  drawSeriesChart(seriesRows);
}

async function initialize() {
  try {
    const [
      seriesResult,
      inputsResult,
      availabilityResult,
      matrixResult,
      universeResult,
      benchmarkResult,
      vehicleResult,
      snapshotMetaText,
    ] = await Promise.all([
      fetchTextStatus(DATA_PATHS.replaySeries),
      fetchTextStatus(DATA_PATHS.replayInputs),
      fetchTextStatus(DATA_PATHS.replayAvailability),
      fetchTextStatus(DATA_PATHS.replayMatrix),
      fetchTextStatus(DATA_PATHS.analyticalUniverse),
      fetchTextStatus(DATA_PATHS.benchmarkRegistry),
      fetchTextStatus(DATA_PATHS.vehicleRegistry),
      fetchText(DATA_PATHS.snapshotMetadata).catch(() => ""),
    ]);

    state.replaySeriesLoad = {
      status: seriesResult.status,
      message: seriesResult.message,
    };
    state.replayInputsLoad = {
      status: inputsResult.status,
      message: inputsResult.message,
    };
    state.replayAvailabilityLoad = {
      status: availabilityResult.status,
      message: availabilityResult.message,
    };
    state.replayMatrixLoad = {
      status: matrixResult.status,
      message: matrixResult.message,
    };
    state.replaySeries = parseCsv(seriesResult.text || "");
    state.replayInputs = parseCsv(inputsResult.text || "");
    state.replayAvailability = parseCsv(availabilityResult.text || "");
    state.replayMatrix = parseCsv(matrixResult.text || "");
    state.analyticalUniverse = parseCsv(universeResult.text || "");
    state.benchmarkRegistryText = benchmarkResult.text || "";
    state.vehicleRegistryText = vehicleResult.text || "";
    state.snapshotMetadata = snapshotMetaText ? (() => { try { return JSON.parse(snapshotMetaText); } catch { return null; } })() : null;

    // Dynamically populate industry dropdown from available replay data
    const industryEl = document.getElementById("industrySelect");
    if (industryEl && state.replayInputs.length > 0) {
      const rawIndustries = [...new Set(
        state.replayInputs.map(r => String(r.filter_industry || "ALL").toUpperCase())
      )].sort();
      const industries = rawIndustries.includes("ALL")
        ? ["ALL", ...rawIndustries.filter(i => i !== "ALL")]
        : ["ALL", ...rawIndustries];
      industryEl.innerHTML = industries
        .map(ind => `<option value="${ind}">${ind}</option>`)
        .join("");
    }

    if (state.replayInputs.length > 0) {
      const first = state.replayInputs[0];
      document.getElementById("geographySelect").value = String(first.filter_geography || "US").toUpperCase();
      document.getElementById("marketCapSelect").value = String(first.filter_market_cap_bucket || "LARGE").toUpperCase();
      document.getElementById("industrySelect").value = "ALL";
      document.getElementById("topNInput").value = Number(first.top_n || 20);
    }

    // Subtier auto-sync: selecting a subtier drives the market cap bucket to the
    // correct parent bucket so the chart always has valid replay data to display.
    const SUBTIER_TO_BUCKET = {
      HYPER_MEGA: "MEGA",
      ULTRA_MEGA: "MEGA",
      EXTENDED_MEGA: "MEGA",
      LARGE: "LARGE",
      MID: "MID",
      SMALL: "SMALL",
      MICRO: "MICRO",
    };
    const subtierEl = document.getElementById("subtierSelect");
    const marketCapEl = document.getElementById("marketCapSelect");
    let preSyncMarketCap = null;
    if (subtierEl) {
      subtierEl.addEventListener("change", () => {
        const bucket = SUBTIER_TO_BUCKET[subtierEl.value.toUpperCase()];
        if (bucket && marketCapEl) {
          // Save the user's original market cap before overriding it
          if (preSyncMarketCap === null) preSyncMarketCap = marketCapEl.value;
          marketCapEl.value = bucket;
        } else if (!subtierEl.value && preSyncMarketCap !== null && marketCapEl) {
          // Restore the original market cap when going back to ALL
          marketCapEl.value = preSyncMarketCap;
          preSyncMarketCap = null;
        }
        render();
      });
    }

    ["geographySelect", "marketCapSelect", "industrySelect", "timeframeSelect", "topNInput"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("change", () => {
        // If the user manually changes market cap, forget the saved pre-sync value
        if (id === "marketCapSelect") preSyncMarketCap = null;
        render();
      });
    });

    loadRefreshTransparencyPanels();
    setTimeout(() => {
      loadLatestPortfolioActionPanel();
    }, 0);
    setTimeout(() => {
      const panel = document.getElementById("portfolioActionPanel");
      if (panel && String(panel.textContent || "").includes("Loading latest portfolio action plan...")) {
        loadLatestPortfolioActionPanel();
      }
    }, 1200);
    await render();
  } catch (error) {
    setStatus(`Failed to load UI data inputs: ${error.message}`, true);
    drawSeriesChart([], error.message);
    document.getElementById("replayMeta").textContent = JSON.stringify(
      { error: String(error.message || error) },
      null,
      2,
    );
    loadRefreshTransparencyPanels();
    setTimeout(() => {
      loadLatestPortfolioActionPanel();
    }, 0);
    setTimeout(() => {
      const panel = document.getElementById("portfolioActionPanel");
      if (panel && String(panel.textContent || "").includes("Loading latest portfolio action plan...")) {
        loadLatestPortfolioActionPanel();
      }
    }, 1200);
  }
}

initialize();

// ---------------------------------------------------------------------------
// Symbol Lookup
// ---------------------------------------------------------------------------

const SIGNAL_PATHS = {
  zacks:    "/data/signals/zacks/latest_zacks.csv",
  yahoo:    "/data/signals/yahoo/latest_yahoo_supplemental.csv",
  danelfin: "/data/signals/danelfin/latest_danelfin.csv",
  metadata: "/data/signals/security_metadata/latest_security_metadata.csv",
};

async function fetchSignalCsv(path) {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) return [];
    const text = await response.text();
    return parseCsv(text);
  } catch {
    return [];
  }
}

function essBadge(text) {
  const t = String(text || "").trim().toUpperCase();
  const cls = {
    VERY_BULLISH: "badge-very-bullish",
    BULLISH:      "badge-bullish",
    NEUTRAL:      "badge-neutral",
    BEARISH:      "badge-bearish",
    VERY_BEARISH: "badge-very-bearish",
  }[t] || "badge-unknown";
  const label = t || "n/a";
  return `<span class="lookup-badge ${cls}">${label}</span>`;
}

function fmtUpside(val) {
  const n = parseFloat(val);
  if (!isFinite(n)) return `<span class="lf-value na">n/a</span>`;
  const cls = n >= 0 ? "positive" : "negative";
  return `<span class="lf-value ${cls}">${n >= 0 ? "+" : ""}${n.toFixed(1)}%</span>`;
}

function fmtVal(val, prefix = "", suffix = "", decimals = 2) {
  const n = parseFloat(val);
  if (!isFinite(n)) return `<span class="lf-value na">n/a</span>`;
  return `<span class="lf-value">${prefix}${n.toFixed(decimals)}${suffix}</span>`;
}

function fmtText(val) {
  const s = String(val || "").trim();
  if (!s) return `<span class="lf-value na">n/a</span>`;
  return `<span class="lf-value">${s}</span>`;
}

function fieldHtml(label, valueHtml) {
  return `<div class="lookup-field"><div class="lf-label">${label}</div><div>${valueHtml}</div></div>`;
}

// ---------------------------------------------------------------------------
// Factor contribution helpers — Phase 8
// Mirrors analytical_universe_manager weight constants + scoring logic.
// ---------------------------------------------------------------------------
const _FACTOR_ESS_SCORE_MAP = {
  VERY_BULLISH: 5.0, BULLISH: 4.0, NEUTRAL: 3.0, BEARISH: 2.0, VERY_BEARISH: 1.0,
};
// v1 production weights
const _V1_FACTOR_WEIGHTS = { ess: 0.55, zacks: 0.25, danelfin: 0.10, yahoo: 0.10 };
// v2 experimental weights (must match composite_versioning.py)
const _V2_FACTOR_WEIGHTS = { ess: 0.50, zacks: 0.225, danelfin: 0.175, yahoo: 0.10 };

function _resolveZacksScore(zacksRaw) {
  const n = parseFloat(zacksRaw);
  if (isFinite(n) && n >= 1.0 && n <= 5.0) return n;
  const textMap = {
    "STRONG BUY": 5, "STRONG_BUY": 5, "OUTPERFORM": 4, "BUY": 4, "OVERWEIGHT": 4,
    "NEUTRAL": 3, "HOLD": 3, "MARKET PERFORM": 3, "MARKET_PERFORM": 3,
    "UNDERPERFORM": 2, "SELL": 2, "UNDERWEIGHT": 2,
    "STRONG SELL": 1, "STRONG_SELL": 1,
  };
  return textMap[String(zacksRaw || "").trim().toUpperCase()] || null;
}

/**
 * Compute per-factor attributions for a composite score.
 *
 * @param {string} essText     - ESS signal text
 * @param {string} zacksRaw    - Zacks rating (numeric string or text)
 * @param {string} yahooNorm   - Normalized Yahoo ABR string (or "" for v1)
 * @param {string} danelfinRaw - Danelfin numeric score string
 * @param {object} weights     - { ess, zacks, danelfin, yahoo }
 * @returns {Array<{name, rawDisplay, score, baseW, effW, contrib, available}>}
 */
function computeFactorAttribution(essText, zacksRaw, yahooNorm, danelfinRaw, weights) {
  const essUpper = String(essText || "").trim().toUpperCase();
  const essScore = _FACTOR_ESS_SCORE_MAP[essUpper];
  const essAvail = essScore !== undefined;

  const zScore = _resolveZacksScore(zacksRaw);
  const zAvail = zScore !== null;

  const yScore = parseFloat(yahooNorm);
  const yAvail = isFinite(yScore) && yScore > 0.0;

  const dScore = parseFloat(danelfinRaw);
  const dAvail = isFinite(dScore) && dScore > 0.0;

  const rawFactors = [
    { name: "ESS",       rawDisplay: essUpper || "—",         score: essScore ?? 0, w: weights.ess,      avail: essAvail },
    { name: "Zacks",     rawDisplay: zacksRaw || "—",          score: zScore  ?? 0, w: weights.zacks,    avail: zAvail   },
    { name: "Danelfin",  rawDisplay: danelfinRaw || "—",       score: dScore  ?? 0, w: weights.danelfin, avail: dAvail   },
    { name: "Yahoo ABR", rawDisplay: yahooNorm  || "—",        score: yScore  ?? 0, w: weights.yahoo,    avail: yAvail   },
  ];

  const totalW = rawFactors.filter(f => f.avail).reduce((s, f) => s + f.w, 0);
  if (totalW === 0) return null;

  return rawFactors.map(f => ({
    ...f,
    effW:   f.avail ? f.w / totalW : 0,
    contrib: f.avail ? f.score * f.w / totalW : 0,
  }));
}

/**
 * Render the factor attribution panel HTML.
 *
 * @param {Array} factors  - result of computeFactorAttribution (may be null)
 * @param {string} label   - section title (e.g. "Score Attribution — v1")
 * @param {string} version - "v1" | "v2"
 * @returns {string} HTML fragment
 */
function renderFactorAttributionHtml(factors, label, version) {
  if (!factors) return "";
  const maxContrib = 5.0; // max score × effW ≤ 5 (if only one signal)
  const rows = factors.map(f => {
    if (!f.avail) {
      return `
        <div class="fc-row fc-unavail">
          <span class="fc-factor">${f.name}</span>
          <span class="fc-raw">n/a</span>
          <div class="fc-bar-wrap"><div class="fc-bar-fill fc-na" style="width:0%"></div></div>
          <span class="fc-contrib-val fc-na">—</span>
        </div>`;
    }
    const pct = Math.round(100 * f.contrib / maxContrib);
    const barColor = version === "v2"
      ? (f.name === "Yahoo ABR" ? "#6b3fa0" : "#2a9d8f")
      : "#2a9d8f";
    const rawLabel = f.name === "Zacks"
      ? (isFinite(parseFloat(f.rawDisplay)) ? `Z${parseFloat(f.rawDisplay).toFixed(1)}` : f.rawDisplay)
      : f.name === "Danelfin"
      ? (isFinite(parseFloat(f.rawDisplay)) ? `${Math.round(parseFloat(f.rawDisplay) * 2)}/10` : f.rawDisplay)
      : f.name === "Yahoo ABR"
      ? (isFinite(parseFloat(f.rawDisplay)) ? `${parseFloat(f.rawDisplay).toFixed(2)} (norm)` : f.rawDisplay)
      : f.rawDisplay;
    return `
      <div class="fc-row">
        <span class="fc-factor">${f.name}</span>
        <span class="fc-raw" title="${f.rawDisplay}">${rawLabel}</span>
        <div class="fc-bar-wrap"><div class="fc-bar-fill" style="width:${pct}%;background:${barColor}"></div></div>
        <span class="fc-contrib-val">+${f.contrib.toFixed(2)}</span>
      </div>`;
  }).join("");

  return `
    <div class="factor-attribution">
      <div class="factor-attribution-title">${label}</div>
      ${rows}
    </div>`;
}

/**
 * Render the v1 vs v2 comparison row.
 */
function renderV2CompareHtml(v1Score, v2ScoreRaw, yahooNorm) {
  const v2 = parseFloat(v2ScoreRaw);
  if (!isFinite(v2) || !v2ScoreRaw) return "";
  const delta = v2 - parseFloat(v1Score);
  const sign  = delta >= 0 ? "+" : "";
  const cls   = Math.abs(delta) < 0.005 ? "neutral" : (delta > 0 ? "positive" : "negative");
  const abr   = parseFloat(yahooNorm);
  const abrLabel = isFinite(abr) && abr > 0
    ? ` · Yahoo ABR ${abr.toFixed(2)}`
    : " · Yahoo ABR n/a";
  return `
    <div class="v2-compare-row">
      <span class="v2-badge">v2 Experimental</span>
      <span class="v2-score">${v2.toFixed(4)}</span>
      <span class="v2-delta ${cls}">(${sign}${delta.toFixed(4)} vs v1${abrLabel})</span>
    </div>`;
}

async function lookupSymbol() {
  const input = document.getElementById("lookupInput");
  const resultDiv = document.getElementById("lookupResult");
  const sym = String(input.value || "").trim().toUpperCase();
  if (!sym) {
    resultDiv.innerHTML = "";
    return;
  }

  resultDiv.innerHTML = `<p class="lookup-not-found">Searching for <strong>${sym}</strong>…</p>`;

  const [zacksRows, yahooRows, danelfinRows, metaRows] = await Promise.all([
    fetchSignalCsv(SIGNAL_PATHS.zacks),
    fetchSignalCsv(SIGNAL_PATHS.yahoo),
    fetchSignalCsv(SIGNAL_PATHS.danelfin),
    fetchSignalCsv(SIGNAL_PATHS.metadata),
  ]);

  const auRow    = state.analyticalUniverse.find((r) => String(r.symbol || "").toUpperCase() === sym);
  const zRow     = zacksRows.find((r) => String(r.symbol || "").toUpperCase() === sym);
  const yRow     = yahooRows.find((r) => String(r.symbol || "").toUpperCase() === sym);
  const dRow     = danelfinRows.find((r) => String(r.symbol || "").toUpperCase() === sym);
  const mRow     = metaRows.find((r) => String(r.symbol || "").toUpperCase() === sym);

  if (!auRow && !zRow && !yRow && !dRow && !mRow) {
    resultDiv.innerHTML = `<p class="lookup-not-found">No data found for <strong>${sym}</strong>. It may not be in the current analytical universe or signal cache.</p>`;
    return;
  }

  // Derive fields
  const essText     = auRow ? auRow.ess_score_text : "";
  const compScore   = auRow ? auRow.composite_score : "";
  const mcap        = auRow ? auRow.market_cap_bucket : "";
  const subtier     = auRow ? (auRow.analytical_market_cap_subtier || "") : "";
  const sector      = mRow ? (mRow.sector || "") : (auRow ? (auRow.sector !== "ALL" ? auRow.sector : "") : "");
  const industry    = mRow ? (mRow.industry || "") : "";
  const country     = mRow ? (mRow.country || "") : "";
  const quoteType   = mRow ? (mRow.quote_type || "") : "";
  const zRankRaw    = zRow  ? zRow.zacks_rank : (auRow ? auRow.zacks_rating : "");
  const zScoreRaw   = zRow  ? zRow.score : "";
  const danScore    = dRow  ? dRow.danelfin_score : (auRow ? auRow.danelfin_score : "");
  const danRaw10    = danScore ? Math.round(parseFloat(danScore) * 2) : null;
  const curPx       = yRow  ? yRow.current_price : "";
  const tgtPx       = yRow  ? yRow.price_target : "";
  const upside      = yRow  ? yRow.upside_pct : "";
  const abr         = yRow  ? yRow.abr : "";
  const eps         = yRow  ? (yRow.eps_growth_5yr || yRow["eps_growth_5yr"] || "") : "";
  // Phase 8: governance + v2 experimental fields from universe row
  const compV2Raw   = auRow ? (auRow.composite_v2_yahoo || "") : "";
  const yahooNorm   = auRow ? (auRow.yahoo_abr_normalized || "") : "";

  // Zacks rank label
  const zRankNum = parseFloat(zRankRaw);
  const zRankLabel = isFinite(zRankNum)
    ? [`Strong Buy`, `Buy`, `Hold`, `Sell`, `Strong Sell`][Math.round(zRankNum) - 1] || String(zRankNum)
    : "n/a";
  const zRankHtml = isFinite(zRankNum)
    ? `<span class="lf-value">Z${Math.round(zRankNum)} — ${zRankLabel}</span>`
    : `<span class="lf-value na">n/a</span>`;

  const danHtml = danRaw10 !== null
    ? `<span class="lf-value">${danRaw10}/10</span>`
    : `<span class="lf-value na">n/a</span>`;

  const abrNum = parseFloat(abr);
  const abrLabel = isFinite(abrNum)
    ? [`Strong Buy`, `Buy`, `Hold`, `Sell`, `Strong Sell`][Math.round(abrNum) - 1] || abr
    : "";
  const abrHtml = isFinite(abrNum)
    ? `<span class="lf-value">${abrNum.toFixed(2)} — ${abrLabel}</span>`
    : `<span class="lf-value na">n/a</span>`;

  const fields = [
    fieldHtml("Symbol",       `<span class="lf-value" style="font-size:1.25rem">${sym}</span>`),
    fieldHtml("Market Cap",   fmtText(mcap || (auRow ? "WATCHLIST" : ""))),
    ...(subtier && subtier !== mcap ? [fieldHtml("Analytical Subtier", fmtText(subtier))] : []),
    ...(sector ? [fieldHtml("Sector", fmtText(sector))] : []),
    ...(industry ? [fieldHtml("Industry", fmtText(industry))] : []),
    ...(country ? [fieldHtml("Country", fmtText(country))] : []),
    ...(quoteType && quoteType !== "EQUITY" ? [fieldHtml("Type", fmtText(quoteType))] : []),
    fieldHtml("ESS Signal",   essText ? essBadge(essText) : `<span class="lf-value na">n/a</span>`),
    fieldHtml("Composite",    fmtVal(compScore, "", "", 4)),
    fieldHtml("Zacks Rank",   zRankHtml),
    fieldHtml("Danelfin AI",  danHtml),
    fieldHtml("Yahoo ABR",    abrHtml),
    fieldHtml("Current Px",   fmtVal(curPx, "$")),
    fieldHtml("Target Px",    fmtVal(tgtPx, "$")),
    fieldHtml("Upside",       fmtUpside(upside)),
    ...(eps ? [fieldHtml("5yr EPS Est", fmtVal(eps, "", "%", 1))] : []),
  ];

  const missingProviders = !zRow || !yRow || !dRow;

  const sources = [
    auRow ? "universe" : null,
    zRow  ? "zacks" : null,
    yRow  ? "yahoo" : null,
    dRow  ? "danelfin" : null,
    mRow  ? "metadata" : null,
  ].filter(Boolean).join(", ");

  const fetchBtnHtml = missingProviders
    ? `<div style="margin-top: 12px;">
        <button id="fetchLiveBtn" onclick="fetchLiveScores('${sym}')"
          style="padding:7px 18px;border-radius:9px;border:none;background:var(--accent-2);color:#fff;font-size:0.88rem;cursor:pointer;font-family:inherit;">
          Fetch Live Scores
        </button>
        <span id="fetchLiveStatus" style="margin-left:10px;font-size:0.82rem;color:var(--muted);"></span>
       </div>`
    : "";

  // Phase 8: factor attribution panels
  const v1Attribs  = computeFactorAttribution(essText, zRankRaw, "", danScore, _V1_FACTOR_WEIGHTS);
  const v1AttrHtml = renderFactorAttributionHtml(v1Attribs, "Score Attribution — v1 (Production)", "v1");

  let v2SectionHtml = "";
  if (compV2Raw) {
    if (yahooNorm) {
      // Full v2 attribution including Yahoo ABR factor
      const v2Attribs  = computeFactorAttribution(essText, zRankRaw, yahooNorm, danScore, _V2_FACTOR_WEIGHTS);
      v2SectionHtml = renderFactorAttributionHtml(v2Attribs, "Score Attribution — v2 Experimental (Yahoo ABR included)", "v2")
                    + renderV2CompareHtml(compScore, compV2Raw, yahooNorm);
    } else {
      // v2 computed but no ABR for this symbol — score comparison only
      v2SectionHtml = renderV2CompareHtml(compScore, compV2Raw, "");
    }
  }

  resultDiv.innerHTML = `
    <div class="lookup-card" id="lookupCard">${fields.join("")}</div>
    ${v1AttrHtml}
    ${v2SectionHtml}
    <p style="margin: 8px 0 0; font-size: 0.78rem; color: var(--muted);">Data sources: ${sources}</p>
    ${fetchBtnHtml}
  `;
}

// ---------------------------------------------------------------------------
// On-demand live score fetch
// ---------------------------------------------------------------------------

let _fetchPollTimer = null;

async function fetchLiveScores(sym) {
  const btn    = document.getElementById("fetchLiveBtn");
  const status = document.getElementById("fetchLiveStatus");
  if (!btn || !status) return;

  btn.disabled = true;
  btn.textContent = "Fetching\u2026";
  status.textContent = "Contacting Zacks, Danelfin & Yahoo (may take 5\u201315s)\u2026";

  try {
    const res = await fetch("/api/score-fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: sym }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
    btn.disabled = false;
    btn.textContent = "Retry";
    return;
  }

  // Poll until done
  clearInterval(_fetchPollTimer);
  _fetchPollTimer = setInterval(async () => {
    try {
      const r = await fetch(`/api/score-fetch/status?symbol=${encodeURIComponent(sym)}`, { cache: "no-store" });
      if (!r.ok) return;
      const data = await r.json();
      if (data.status === "done") {
        clearInterval(_fetchPollTimer);
        _applyLiveScores(sym, data);
      } else if (data.status === "error") {
        clearInterval(_fetchPollTimer);
        status.textContent = `Fetch error: ${data.error || "unknown"}`;
        btn.disabled = false;
        btn.textContent = "Retry";
      }
    } catch (_) {}
  }, 2000);
}

function _applyLiveScores(sym, data) {
  const btn    = document.getElementById("fetchLiveBtn");
  const status = document.getElementById("fetchLiveStatus");
  const card   = document.getElementById("lookupCard");
  if (btn)    { btn.disabled = false; btn.textContent = "Refresh Live Scores"; }
  if (status) { status.textContent = `Fetched at ${data.fetched_at ? data.fetched_at.substring(11, 19) + " UTC" : "just now"}`; }

  // Build a fresh overlay of provider fields
  const z = data.zacks    || {};
  const y = data.yahoo    || {};
  const d = data.danelfin || {};

  // Zacks
  const zRankNum = z.rank != null ? parseFloat(z.rank) : NaN;
  const zRankLabel = isFinite(zRankNum)
    ? [`Strong Buy`, `Buy`, `Hold`, `Sell`, `Strong Sell`][Math.round(zRankNum) - 1] || String(zRankNum)
    : "n/a";
  const zHtml = isFinite(zRankNum)
    ? `<span class="lf-value">Z${Math.round(zRankNum)} \u2014 ${zRankLabel}</span>`
    : `<span class="lf-value na">n/a</span>`;

  // Danelfin
  const dRaw = d.raw != null ? d.raw : null;
  const dHtml = dRaw !== null
    ? `<span class="lf-value">${dRaw}/10</span>`
    : `<span class="lf-value na">n/a</span>`;

  // Yahoo / ABR
  const abrNum = (y.abr != null) ? parseFloat(y.abr) : (z.abr != null ? parseFloat(z.abr) : NaN);
  const abrLabel = isFinite(abrNum)
    ? [`Strong Buy`, `Buy`, `Hold`, `Sell`, `Strong Sell`][Math.round(abrNum) - 1] || abrNum.toFixed(2)
    : "";
  const abrHtml = isFinite(abrNum)
    ? `<span class="lf-value">${abrNum.toFixed(2)} \u2014 ${abrLabel}</span>`
    : `<span class="lf-value na">n/a</span>`;

  const tgtPx    = y.price_target  ?? z.price_target  ?? null;
  const curPx    = y.current_price ?? null;
  const eps      = y.eps_growth_5yr ?? z.eps_growth ?? null;
  const upside   = (tgtPx != null && curPx != null && curPx > 0)
    ? ((tgtPx - curPx) / curPx * 100)
    : null;

  // Inject/replace provider fields in the card
  function _setOrAddField(id, label, valueHtml) {
    let el = document.getElementById(id);
    if (!el && card) {
      el = document.createElement("div");
      el.id = id;
      el.className = "lookup-field";
      card.appendChild(el);
    }
    if (el) el.innerHTML = `<div class="lf-label">${label}</div>${valueHtml}`;
  }

  _setOrAddField("lf-live-zacks",    "Zacks Rank (live)",   zHtml);
  _setOrAddField("lf-live-danelfin", "Danelfin AI (live)",  dHtml);
  _setOrAddField("lf-live-abr",      "Analyst Cons (live)", abrHtml);
  if (curPx != null) _setOrAddField("lf-live-curpx",  "Current Px (live)", fmtVal(curPx, "$"));
  if (tgtPx != null) _setOrAddField("lf-live-tgtpx",  "Target Px (live)",  fmtVal(tgtPx, "$"));
  if (upside != null) _setOrAddField("lf-live-upside", "Upside (live)",     fmtUpside(upside.toFixed(1)));
  if (eps    != null) _setOrAddField("lf-live-eps",    "5yr EPS Est (live)",fmtVal(eps, "", "%", 1));
}

// ---------------------------------------------------------------------------
// Signal Data Freshness
// ---------------------------------------------------------------------------

let _refreshPollTimer = null;
let _latestPortfolioRun = null;

function _ovEscHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function _ovFmtMoney(value, digits = 0) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function _ovFmtPct(value, digits = 1) {
  const pct = Number(value);
  if (!Number.isFinite(pct)) return "—";
  return `${pct.toFixed(digits)}%`;
}

function _ovLatestRun(rows) {
  if (!Array.isArray(rows) || !rows.length) return null;
  return [...rows].sort((left, right) => {
    const leftTs = Date.parse(left.created_at_utc || "") || 0;
    const rightTs = Date.parse(right.created_at_utc || "") || 0;
    return leftTs - rightTs;
  }).slice(-1)[0] || null;
}

function _ovAlignmentNode(alignment, key) {
  return (alignment || []).find((row) => String(row.node_key || "").toUpperCase() === key) || null;
}

function _ovDeployableCash(data) {
  const planCash = Number(data?.deployment_plan?.deployable_cash);
  if (Number.isFinite(planCash)) return planCash;
  const cashCtx = data?.deployment_queue?.cash_context || {};
  const adjusted = Number(cashCtx.adjusted_deployable_mv);
  if (Number.isFinite(adjusted)) return adjusted;
  const deployable = Number(cashCtx.deployable_mv);
  return Number.isFinite(deployable) ? deployable : 0;
}

function _buildOutcomeHardAssetModel(data) {
  const alignment = data.alignment || [];
  const queue = (data.deployment_queue && Array.isArray(data.deployment_queue.queue)) ? data.deployment_queue.queue : [];
  const planRecs = (data.deployment_plan && Array.isArray(data.deployment_plan.recommendations)) ? data.deployment_plan.recommendations : [];
  const gate = data.hard_asset_priority_gate || {};
  const candidateQueue = data.hard_asset_candidate_queue || {};
  const commodities = _ovAlignmentNode(alignment, "COMMODITIES") || {};
  const gold = _ovAlignmentNode(alignment, "COMMODITIES.GOLD") || {};
  const energy = _ovAlignmentNode(alignment, "COMMODITIES.ENERGY") || {};
  const broad = _ovAlignmentNode(alignment, "COMMODITIES.BROAD_BASKET") || {};
  const totalValue = Number(data.total_market_value || data.snapshot?.total_market_value || data.deployment_queue?.total_market_value || 0);
  const deployableCash = _ovDeployableCash(data);
  const commodityGapPct = Math.max(0, Number(commodities.target_pct || 0) - Number(commodities.actual_pct || 0));
  const hardAssetFirst = (
    Number(commodities.target_pct || 0) > 0 &&
    commodityGapPct >= 1.0 &&
    deployableCash > 0 &&
    queue.length > 0
  );

  const sleeveNodes = Array.isArray(candidateQueue.sleeve_nodes) && candidateQueue.sleeve_nodes.length
    ? candidateQueue.sleeve_nodes
    : [
      {
        node_key: "COMMODITIES.GOLD",
        label: "Gold",
        actual_pct: Number(gold.actual_pct || 0),
        target_pct: Number(gold.target_pct || 0),
        gap_amount_full_portfolio: totalValue * (Math.max(0, Number(gold.target_pct || 0) - Number(gold.actual_pct || 0)) / 100),
        deployable_cash_fill_amount: deployableCash * 0.5,
        direct_completion_candidates: [{ symbol: "GLD" }, { symbol: "IAU" }, { symbol: "SGOL" }],
        equity_proxy_candidates: [{ symbol: "KGC" }],
        not_direct_filler_reason: "Not a direct COMMODITIES.GOLD filler",
      },
      {
        node_key: "COMMODITIES.ENERGY",
        label: "Energy",
        actual_pct: Number(energy.actual_pct || 0),
        target_pct: Number(energy.target_pct || 0),
        gap_amount_full_portfolio: totalValue * (Math.max(0, Number(energy.target_pct || 0) - Number(energy.actual_pct || 0)) / 100),
        deployable_cash_fill_amount: deployableCash * 0.35,
        direct_completion_candidates: [{ symbol: "USO" }, { symbol: "BNO" }, { symbol: "UNG" }],
        equity_proxy_candidates: [{ symbol: "XLE" }, { symbol: "PSX" }, { symbol: "CVE" }, { symbol: "DVN" }],
        not_direct_filler_reason: "Energy/materials equities are equity-adjacent proxies, not direct commodity fillers",
      },
      {
        node_key: "COMMODITIES.BROAD_BASKET",
        label: "Broad Basket",
        actual_pct: Number(broad.actual_pct || 0),
        target_pct: Number(broad.target_pct || 0),
        gap_amount_full_portfolio: totalValue * (Math.max(0, Number(broad.target_pct || 0) - Number(broad.actual_pct || 0)) / 100),
        deployable_cash_fill_amount: deployableCash * 0.15,
        direct_completion_candidates: [{ symbol: "DBC" }, { symbol: "PDBC" }, { symbol: "GSG" }],
        equity_proxy_candidates: [{ symbol: "NUE" }, { symbol: "STLD" }, { symbol: "CRS" }],
        not_direct_filler_reason: "Materials equities are equity-adjacent proxies, not direct commodity fillers",
      },
    ];

  const planBySymbol = {};
  planRecs.forEach((row) => {
    if (row && row.symbol) planBySymbol[String(row.symbol).toUpperCase()] = row;
  });

  return {
    hardAssetFirst,
    priorityBias: gate.priority_bias || (hardAssetFirst ? "HARD_ASSET_REVIEW_FIRST" : "EQUITY_QUEUE_AVAILABLE"),
    gateVerdict: gate.verdict || (hardAssetFirst ? "REVIEW_HARD_ASSETS_FIRST" : "EQUITY_QUEUE_AVAILABLE"),
    queue,
    planBySymbol,
    deployableCash,
    totalValue,
    sleeveNodes,
    summary: {
      commoditiesActualPct: Number(commodities.actual_pct || 0),
      commoditiesTargetPct: Number(commodities.target_pct || 0),
      goldActualPct: Number(gold.actual_pct || 0),
      goldTargetPct: Number(gold.target_pct || 0),
      energyActualPct: Number(energy.actual_pct || 0),
      energyTargetPct: Number(energy.target_pct || 0),
      broadActualPct: Number(broad.actual_pct || 0),
      broadTargetPct: Number(broad.target_pct || 0),
      commodityGapPct,
    },
  };
}

function _renderLatestPortfolioActionPanel(data) {
  const el = document.getElementById("portfolioActionPanel");
  if (!el) return;

  const model = _buildOutcomeHardAssetModel(data);
  const runId = data.run_id || "—";
  const snapshotDate = data.snapshot_date || data.run_metadata?.snapshot_date || "—";
  const holdings = Number(data.holding_count || 0);
  const summary = model.summary;
  const firstAction = model.hardAssetFirst
    ? `Review hard-asset sleeve: COMMODITIES are ${_ovFmtPct(summary.commoditiesActualPct)} vs ${_ovFmtPct(summary.commoditiesTargetPct)} target; use deployable cash before equity deployment unless target is waived.`
    : "Commodity sleeve is not the controlling cash-allocation constraint for this run.";

  const whatMatters = [
    firstAction,
    `Deployable cash available: ${_ovFmtMoney(model.deployableCash, 0)}.`,
    model.queue.length
      ? `Equity deployment queue remains available${model.hardAssetFirst ? " as fallback" : ""}: ${model.queue.slice(0, 3).map((row) => row.symbol).join(", ")}.`
      : "No equity deployment candidates are currently available.",
  ];

  const sleeveCards = model.sleeveNodes.map((node) => {
    const label = node.label || String(node.node_key || "").split(".").slice(-1)[0].replaceAll("_", " ");
    const direct = Array.isArray(node.direct_completion_candidates)
      ? node.direct_completion_candidates.map((row) => row.symbol).filter(Boolean)
      : [];
    const proxies = Array.isArray(node.equity_proxy_candidates)
      ? node.equity_proxy_candidates.map((row) => row.symbol).filter(Boolean)
      : [];
    const fullGap = node.gap_amount_full_portfolio ?? node.full_target_amount;

    return `<div style="border: 1px solid var(--border); border-radius: 10px; background: #fff; padding: 10px;">
      <div style="font-weight: 700; margin-bottom: 4px;">${_ovEscHtml(label)} Sleeve</div>
      <div style="font-size: 0.8rem; line-height: 1.45; color: var(--muted);">
        Actual vs target: <strong>${_ovFmtPct(node.actual_pct ?? 0)}</strong> vs <strong>${_ovFmtPct(node.target_pct ?? 0)}</strong><br>
        Suggested add: <strong>${_ovFmtMoney(node.deployable_cash_fill_amount, 0)}</strong><br>
        Full target gap: <strong>${_ovFmtMoney(fullGap, 0)}</strong><br>
        Direct hard-asset completion candidates: <strong>${_ovEscHtml(direct.join(" / ") || "—")}</strong><br>
        Equity-adjacent proxies: <strong>${_ovEscHtml(proxies.join(" / ") || "—")}</strong><br>
        ${_ovEscHtml(node.not_direct_filler_reason || "Display-only candidates; not trade instructions.")}
      </div>
    </div>`;
  }).join("");

  const queueRows = model.queue.slice(0, 10).map((row, index) => {
    const symbol = String(row.symbol || "").toUpperCase();
    const planRow = model.planBySymbol[symbol] || {};
    const amount = planRow.suggested_add ?? planRow.suggested_amount ?? planRow.suggested_deploy_amount ?? row.suggested_amount;
    return `<tr>
      <td style="padding: 6px 8px; border-top: 1px solid var(--border); font-family: monospace;">${index + 1}. ${_ovEscHtml(symbol)}</td>
      <td style="padding: 6px 8px; border-top: 1px solid var(--border); text-align: right;">${_ovFmtMoney(amount, 0)}</td>
    </tr>`;
  }).join("");

  const fallbackLabel = model.hardAssetFirst
    ? "Equity deployment fallback — review hard-asset sleeve first."
    : "Capital deployment queue remains available.";

  el.innerHTML = `<div style="display: grid; gap: 12px; color: var(--text);">
    <div style="border: 1px solid var(--border); border-radius: 12px; background: #fff7e8; padding: 12px;">
      <div style="font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 6px;">What matters right now</div>
      <div style="font-size: 0.82rem; color: var(--text); margin-bottom: 6px;">Run ${_ovEscHtml(runId)} · ${_ovEscHtml(snapshotDate)} · ${_ovEscHtml(String(holdings))} holdings · ${_ovFmtMoney(model.totalValue, 0)} portfolio value</div>
      <ol style="margin: 0; padding-left: 18px; line-height: 1.5;">
        ${whatMatters.map((item) => `<li>${_ovEscHtml(item)}</li>`).join("")}
      </ol>
    </div>

    <div style="border: 1px solid var(--border); border-radius: 12px; background: ${model.hardAssetFirst ? "#fff3e0" : "#fff"}; padding: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px;">Today’s Operator Action Plan</div>
      <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px;">
        <span style="padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); background: #fff; font-size: 0.73rem;">DISPLAY ONLY</span>
        <span style="padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); background: #fff; font-size: 0.73rem;">OPERATOR REVIEW REQUIRED</span>
        <span style="padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); background: #fff; font-size: 0.73rem;">NO CAPITAL DEPLOYMENT QUEUE CHANGES</span>
        <span style="padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); background: #fff; font-size: 0.73rem;">NO CRA CHANGES</span>
        <span style="padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); background: #fff; font-size: 0.73rem;">NO TRADE EXECUTION</span>
      </div>
      <div style="font-size: 0.88rem; font-weight: 700; color: ${model.hardAssetFirst ? "#8a4b08" : "var(--text)"};">${model.hardAssetFirst ? "Hard-Asset Sleeve Is Unfilled" : "Equity deployment queue is available."}</div>
      <div style="margin-top: 6px; line-height: 1.5;">
        Commodities are <strong>${_ovFmtPct(summary.commoditiesActualPct)}</strong> vs <strong>${_ovFmtPct(summary.commoditiesTargetPct)}</strong> target.<br>
        Before deploying cash to equities, review hard-asset sleeve completion.<br>
        Suggested cash-first sleeve fill: Gold <strong>${_ovFmtMoney(model.sleeveNodes[0]?.deployable_cash_fill_amount, 0)}</strong>, Energy <strong>${_ovFmtMoney(model.sleeveNodes[1]?.deployable_cash_fill_amount, 0)}</strong>, Broad Basket <strong>${_ovFmtMoney(model.sleeveNodes[2]?.deployable_cash_fill_amount, 0)}</strong>.
      </div>
    </div>

    <div style="border: 1px solid var(--border); border-radius: 12px; background: #fff; padding: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px;">Hard-Asset Priority Gate</div>
      <div style="line-height: 1.5;">
        Priority bias: <strong>${_ovEscHtml(String(model.priorityBias || "—"))}</strong><br>
        Gate verdict: <strong>${_ovEscHtml(String(model.gateVerdict || "—"))}</strong><br>
        Deployable cash: <strong>${_ovFmtMoney(model.deployableCash, 0)}</strong><br>
        Equity deployment candidates: <strong>${_ovEscHtml(String(model.queue.length))}</strong>
      </div>
    </div>

    <div style="border: 1px solid var(--border); border-radius: 12px; background: #fff; padding: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px;">Hard-Asset Sleeve Review</div>
      <div style="line-height: 1.5;">
        Commodities: <strong>${_ovFmtPct(summary.commoditiesActualPct)}</strong> vs <strong>${_ovFmtPct(summary.commoditiesTargetPct)}</strong><br>
        Gold: <strong>${_ovFmtPct(summary.goldActualPct)}</strong> vs <strong>${_ovFmtPct(summary.goldTargetPct)}</strong><br>
        Energy: <strong>${_ovFmtPct(summary.energyActualPct)}</strong> vs <strong>${_ovFmtPct(summary.energyTargetPct)}</strong><br>
        Broad Basket: <strong>${_ovFmtPct(summary.broadActualPct)}</strong> vs <strong>${_ovFmtPct(summary.broadTargetPct)}</strong>
      </div>
    </div>

    <div style="border: 1px solid var(--border); border-radius: 12px; background: #fff; padding: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px;">Hard-Asset Candidate Queue</div>
      <div style="font-size: 0.82rem; line-height: 1.5; margin-bottom: 8px;">
        Direct commodity completion candidate examples: <strong>GLD / IAU / SGOL</strong>, <strong>USO / BNO / UNG</strong>, <strong>DBC / PDBC / GSG</strong>.<br>
        KGC, XLE, PSX, CVE, DVN, NUE, STLD, and CRS are equity-adjacent proxies, not direct commodity fillers.
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
        ${sleeveCards}
      </div>
    </div>

    <div style="border: 1px solid var(--border); border-radius: 12px; background: #fff; padding: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 8px;">Sleeve Fit Drilldown</div>
      <div style="font-size: 0.82rem; line-height: 1.55; color: var(--muted);">
        Direct hard-asset completion candidates are display-only and sized for operator review. KGC remains proxy-only and is not treated as a direct COMMODITIES.GOLD filler.
      </div>
    </div>

    <div style="border: 1px solid var(--border); border-radius: 12px; background: #fff; padding: 14px;">
      <div style="font-size: 0.95rem; font-weight: 700; margin-bottom: 4px;">Capital Deployment Queue</div>
      <div style="font-size: 0.82rem; color: ${model.hardAssetFirst ? "#8a4b08" : "var(--muted)"}; margin-bottom: 10px;">${_ovEscHtml(fallbackLabel)}</div>
      <table style="width: 100%; border-collapse: collapse; font-size: 0.84rem; background: #fff;">
        <thead>
          <tr>
            <th style="text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border);">Symbol</th>
            <th style="text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border);">Suggested Amount</th>
          </tr>
        </thead>
        <tbody>
          ${queueRows || '<tr><td colspan="2" style="padding: 8px; color: var(--muted);">No deployment candidates available.</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>`;
}

async function loadLatestPortfolioActionPanel(attempt = 0) {
  const el = document.getElementById("portfolioActionPanel");
  if (!el) {
    if (attempt < 20) {
      setTimeout(() => {
        loadLatestPortfolioActionPanel(attempt + 1);
      }, 100);
    }
    return;
  }
  try {
    const runsResp = await fetch("/api/portfolio/runs", { cache: "no-store" });
    if (!runsResp.ok) throw new Error(`HTTP ${runsResp.status}`);
    const runsBody = await runsResp.json();
    const latest = _ovLatestRun(runsBody.portfolios || []);
    if (!latest || !latest.run_id) {
      el.innerHTML = "No completed portfolio analysis runs available.";
      return;
    }

    const runId = String(latest.run_id);
    const runRoot = `/data/portfolio_ingestion/analysis_runs/${encodeURIComponent(runId)}`;
    const [deploymentPlan, deploymentQueue, alignmentCsv, runMetadata] = await Promise.all([
      fetchJson(`${runRoot}/deployment_plan.json`),
      fetchJson(`${runRoot}/deployment_queue.json`),
      fetchText(`${runRoot}/alignment.csv`),
      fetchJson(`${runRoot}/run_metadata.json`).catch(() => ({})),
    ]);

    const alignment = parseCsv(alignmentCsv || "");
    if (!alignment.length || !deploymentPlan || !deploymentQueue) {
      el.innerHTML = "Operator action plan unavailable - persisted operator artifacts are incomplete for the latest run.";
      return;
    }

    _latestPortfolioRun = {
      ...latest,
      run_id: runId,
      snapshot_date: latest.snapshot_date || runMetadata.snapshot_date || "",
      holding_count: latest.holding_count,
      total_market_value: latest.total_market_value,
      alignment,
      deployment_queue: deploymentQueue,
      deployment_plan: deploymentPlan,
      hard_asset_priority_gate: runMetadata.hard_asset_priority_gate || null,
      hard_asset_candidate_queue: runMetadata.hard_asset_candidate_queue || null,
      daily_operator_action_plan: runMetadata.daily_operator_action_plan || null,
      today_operator_action_plan: runMetadata.today_operator_action_plan || null,
    };
    _renderLatestPortfolioActionPanel(_latestPortfolioRun);
  } catch (error) {
    el.innerHTML = `Operator action plan unavailable - ${_ovEscHtml(error.message || "request failed")}`;
  }
}

function loadSignalStatus() {
  fetch("/api/signal-status", { cache: "no-store" })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => Promise.all([
      Promise.resolve(data),
      fetch("/api/signal-refresh/status", { cache: "no-store" })
        .then(r => r.ok ? r.json() : null)
        .catch(() => null),
    ]))
    .then(([data, runtime]) => {
      const refreshRunning = Boolean(runtime && runtime.running);
      const progress = (runtime && runtime.provider_progress) ? runtime.provider_progress : {};
      ["zacks", "danelfin", "yahoo"].forEach((provider) => {
        if (!data[provider] || !progress[provider]) return;
        const p = progress[provider];
        data[provider].refresh_progress = {
          active: refreshRunning,
          completed_count: p.completed_count,
          planned_total_count: p.planned_total_count,
          progress_pct: p.progress_pct,
          progress_label: p.progress_label,
          is_complete: p.is_complete,
        };
      });
      _renderSignalPills(data);
      _renderHoldingsCoverage(data.portfolio_holdings_coverage || null);
      _renderRefreshModeDefinition();
      loadRefreshRuntimeStatus();
      if (refreshRunning) {
        const btn = document.getElementById("signalRefreshBtn");
        const msg = document.getElementById("signalRefreshMsg");
        if (btn) { btn.disabled = true; btn.textContent = "Refreshing\u2026"; }
        if (msg) { msg.style.display = ""; msg.textContent = "Refresh in progress (smart mode \u2014 mandatory holdings included). Danelfin: ~60\u201390 min, Yahoo: ~15 min. Runs in background."; }
        _startRefreshPoll();
      }
    })
    .catch(() => {
      const el = document.getElementById("signalStatusPills");
      if (el) el.innerHTML = '<span style="color: var(--muted); font-size: 0.83rem;">Status unavailable \u2014 API not reachable</span>';
      const holdingsEl = document.getElementById("holdingsCoveragePills");
      const holdingsSummaryEl = document.getElementById("holdingsCoverageSummary");
      if (holdingsEl) holdingsEl.innerHTML = '<span style="color: var(--muted); font-size: 0.83rem;">Coverage unavailable \u2014 API not reachable</span>';
      if (holdingsSummaryEl) holdingsSummaryEl.textContent = 'Coverage unavailable.';
    });
}

function _selectedRefreshMode() {
  const modeSelect = document.getElementById("signalRefreshMode");
  return modeSelect ? String(modeSelect.value || "portfolio_signals") : "portfolio_signals";
}

function _refreshModeGuidance(mode) {
  if (mode === "stale_only") {
    return "Refreshes stale/missing provider coverage plus stale market-regime proxy symbols for lightweight maintenance.";
  }
  if (mode === "portfolio_signals") {
    return "Refreshes portfolio holdings plus mandatory provider dependencies and market-regime proxy symbols required for coverage and guardrail freshness.";
  }
  if (mode === "holdings_plus_buy_candidates") {
    return "Refreshes current portfolio holdings and top deployment/buy candidates, plus mandatory dependencies and market-regime proxies. Use this before making portfolio decisions without running the full universe refresh.";
  }
  if (mode === "rebuild_research_universe") {
    return "Refreshes the full research universe. Intended weekly or when rebuilding the candidate universe.";
  }
  if (mode === "prepare_portfolio_review") {
    return "Builds the portfolio review artifact bundle without forcing a full research-universe refresh.";
  }
  return "Select a refresh mode to view scope and guidance.";
}

function _renderRefreshModeDefinition() {
  const panel = document.getElementById("refreshModeDefinitionPanel");
  const nextIntent = document.getElementById("refreshNextIntentSummary");
  const mode = _selectedRefreshMode();
  const guidance = _refreshModeGuidance(mode);
  if (panel) {
    panel.innerHTML = `<div class="refresh-mode-purpose">${_ovEscHtml(guidance)}</div>`;
  }
  if (nextIntent) {
    nextIntent.textContent = `${_refreshModeLabel(mode)} — ${guidance}`;
  }
}

function _scopeFormulaFromSummary(summary, intent) {
  const s = summary || {};
  const holdings = Number(s.portfolio_holdings_count || 0);
  const buy = Number(s.buy_candidate_count || 0);
  const deps = Number(s.mandatory_dependency_count || 0);
  const proxies = Number(s.market_proxy_count || 0);
  const deduped = Number(s.deduped_symbol_count || 0);
  const full = Number(s.full_universe_count || 0);

  if (intent === "rebuild_research_universe") {
    return full > 0
      ? `Planned refresh scope: ~${full.toLocaleString("en-US")} research universe symbols`
      : "Planned refresh scope: full research universe";
  }
  if (intent === "holdings_plus_buy_candidates") {
    return `Planned refresh scope: ${holdings} holdings + ${buy} buy candidates + ${deps} required dependencies + ${proxies} market proxies = ${deduped} symbols`;
  }
  if (intent === "portfolio_signals") {
    return `Planned refresh scope: ${holdings} holdings + ${deps} required dependencies + ${proxies} market proxies = ${deduped} symbols`;
  }
  if (intent === "stale_only") {
    return `Planned refresh scope: stale provider rows + ${proxies} stale market proxies`;
  }
  return "Planned refresh scope: based on selected refresh intent";
}

function loadRefreshRuntimeStatus() {
  fetch("/api/signal-refresh/status", { cache: "no-store" })
    .then(r => r.ok ? r.json() : Promise.reject())
    .then(data => {
      const activeSummary = document.getElementById("refreshActiveStateSummary");
      const activeDetails = document.getElementById("refreshActiveStateDetails");
      const completionBanner = document.getElementById("refreshCompletionBanner");
      const intent = String(data.resolved_intent || _selectedRefreshMode() || "portfolio_signals");
      const scopeSummary = data.scope_summary || {};
      const scopeFormula = data.scope_formula || _scopeFormulaFromSummary(scopeSummary, intent);

      if (activeSummary) {
        activeSummary.textContent = data.running
          ? `Refreshing (${_refreshModeLabel(intent)})`
          : "No active refresh job.";
      }
      if (activeDetails) {
        activeDetails.innerHTML = `<span class="refresh-insight-pill">${_ovEscHtml(scopeFormula)}</span>`;
      }
      if (completionBanner) {
        if (data.running) {
          completionBanner.textContent = "";
          completionBanner.className = "completion-banner";
        } else if (data.last_report && data.last_exit_code === 0) {
          completionBanner.textContent = _scopeFormulaFromSummary(data.last_report.scope_summary || scopeSummary, intent);
          completionBanner.className = "completion-banner complete";
        } else {
          completionBanner.textContent = "";
          completionBanner.className = "completion-banner";
        }
      }
    })
    .catch(() => {
      _renderRefreshModeDefinition();
    });
}

function _renderSignalPills(data) {
  const el = document.getElementById("signalStatusPills");
  if (!el) return;
  const holdingsProviders = (data.portfolio_holdings_coverage && data.portfolio_holdings_coverage.providers) || {};
  const providers = ["ess", "zacks", "danelfin", "yahoo"];
  const labels = { ess: "ESS / LSEG", zacks: "Zacks", danelfin: "Danelfin", yahoo: "Yahoo" };
  const renderPill = (key) => {
    const info    = data[key];
    const label   = labels[key];
    const dateStr = info.sourced_date || "—";

    // SI-REFRESH-02: Use badge_state when available, fall back to stale boolean
    const badgeState = info.badge_state ||
      (!info.sourced_date ? "UNKNOWN" : info.stale ? "STALE" : "FRESH");

    const dotCls = {
      FRESH:         "dot-fresh",
      FRESH_PARTIAL: "dot-partial",
      STALE:         "dot-stale",
      REFRESHING:    "dot-refreshing",
      ERROR:         "dot-stale",
      UNKNOWN:       "dot-unknown",
    }[badgeState] || "dot-unknown";

    const stsCls = {
      FRESH:         "pill-status-fresh",
      FRESH_PARTIAL: "pill-status-partial",
      STALE:         "pill-status-stale",
      REFRESHING:    "pill-status-refreshing",
      ERROR:         "pill-status-stale",
      UNKNOWN:       "pill-status-unknown",
    }[badgeState] || "pill-status-unknown";

    const stsLbl = {
      FRESH:         "fresh",
      FRESH_PARTIAL: "fresh — partial",
      STALE:         "stale",
      REFRESHING:    "refreshing",
      ERROR:         "error",
      UNKNOWN:       "no data",
    }[badgeState] || "unknown";

    let refreshProgressHtml = "";
    const refreshProgress = info.refresh_progress && typeof info.refresh_progress === "object"
      ? info.refresh_progress
      : null;
    if (refreshProgress && refreshProgress.active) {
      const completed = Number(refreshProgress.completed_count || 0);
      const plannedRaw = refreshProgress.planned_total_count;
      const planned = (plannedRaw == null || plannedRaw === "") ? null : Number(plannedRaw);
      if (planned != null && Number.isFinite(planned) && planned >= 0) {
        const shownCompleted = Math.min(completed, planned);
        const progressPct = refreshProgress.progress_pct != null
          ? Number(refreshProgress.progress_pct)
          : (planned > 0 ? (shownCompleted / planned) * 100.0 : 100.0);
        const pctLabel = Number.isFinite(progressPct) ? progressPct.toFixed(1) : "0.0";
        refreshProgressHtml = `<span class="pill-coverage">Active refresh progress: ${shownCompleted}/${planned} rows · ${pctLabel}%</span>`;
      } else {
        refreshProgressHtml = `<span class="pill-coverage">Active refresh progress: ${completed} rows processed</span>`;
      }
    }

    // Coverage detail line (SI-REFRESH-02)
    let coverageHtml = "";
    if (info.attempted_count != null) {
      const covPct = info.coverage_pct != null ? info.coverage_pct.toFixed(1) : "—";
      coverageHtml = `<span class="pill-coverage">Provider today rows: ${info.with_data_count}/${info.attempted_count} · ${covPct}%</span>`;
    }

    let canonicalCoverageHtml = "";
    const holdingsInfo = holdingsProviders[key] || null;
    if (holdingsInfo && ["zacks", "danelfin", "yahoo"].includes(key)) {
      canonicalCoverageHtml = `<span class="pill-coverage">Current holdings: ${holdingsInfo.covered_within_threshold}/${holdingsInfo.applicable_holdings} within threshold · stale ${holdingsInfo.stale} · missing ${holdingsInfo.missing} · failed ${holdingsInfo.failed}</span>`;
    }

    // Degraded fields warning
    let degradedHtml = "";
    if (info.degraded_fields && info.degraded_fields.length > 0) {
      const fields = info.degraded_fields.join(", ");
      degradedHtml = `<span class="pill-degraded">⚠ 0% coverage: ${fields}</span>`;
    } else if (info.zero_coverage_fields && info.zero_coverage_fields.length > 0) {
      // Non-primary zero-coverage fields shown as advisory
      const fields = info.zero_coverage_fields.join(", ");
      degradedHtml = `<span class="pill-degraded-advisory">0% today: ${fields}</span>`;
    }

    let warningHtml = "";
    if (info.coverage_warning_count > 0) {
      const examples = (info.coverage_warning_examples || []).join(", ");
      warningHtml = `<span class="pill-degraded">ESS coverage warning: ${info.coverage_warning_count} holdings with ESS coverage gaps${examples ? ` · ${examples}` : ""}</span>`;
    }

    let holdingsHtml = "";
    if (holdingsInfo && holdingsInfo.status && holdingsInfo.status !== "COMPLIANT") {
      holdingsHtml = `<span class="pill-degraded">Holdings coverage: ${String(holdingsInfo.status).toLowerCase().replaceAll("_", " ")}</span>`;
    }

    const extraLines = [canonicalCoverageHtml, refreshProgressHtml, coverageHtml, degradedHtml, warningHtml, holdingsHtml].filter(Boolean).join(" ");

    return `<div class="signal-pill ${badgeState === 'FRESH_PARTIAL' ? 'signal-pill-partial' : ''}">
      <span class="dot ${dotCls}"></span>
      <div class="pill-body">
        <div class="pill-main-row">
          <span class="pill-label">${label}</span>
          <span class="pill-date">${dateStr}</span>
          <span class="${stsCls}">(${stsLbl})</span>
        </div>
        ${extraLines ? `<div class="pill-detail-row">${extraLines}</div>` : ""}
      </div>
    </div>`;
    };

  const automatedProviders = ["zacks", "danelfin", "yahoo"].filter((k) => k in data);
  const manualProviders = ["ess"].filter((k) => k in data);
  const sections = [];
  if (automatedProviders.length) {
    sections.push(
      `<div class="refresh-state-line"><strong>Automated Research Providers</strong></div>` +
      `<div class="signal-status-row">${automatedProviders.map(renderPill).join("")}</div>`
    );
  }
  if (manualProviders.length) {
    sections.push(
      `<div class="refresh-state-line" style="margin-top: 6px;"><strong>Manual Source Freshness</strong></div>` +
      `<div class="signal-status-row">${manualProviders.map(renderPill).join("")}</div>`
    );
  }
  el.innerHTML = sections.length ? sections.join("") : '<span style="color: var(--muted); font-size: 0.83rem;">No provider freshness data.</span>';
}

function _renderHoldingsCoverage(coverage) {
  const el = document.getElementById("holdingsCoveragePills");
  const summaryEl = document.getElementById("holdingsCoverageSummary");
  if (!el || !summaryEl) return;

  if (!coverage || !coverage.providers) {
    summaryEl.textContent = "Coverage unavailable.";
    el.innerHTML = '<span style="color: var(--muted); font-size: 0.83rem;">No holdings coverage data.</span>';
    return;
  }

  const runId = coverage.run_id || "—";
  const baseline = coverage.active_holdings_baseline != null ? coverage.active_holdings_baseline : "—";
  const threshold = coverage.threshold_days != null ? coverage.threshold_days : 2;
  const applicableTotals = Object.values(coverage.providers || {})
    .map((provider) => Number(provider && provider.applicable_holdings != null ? provider.applicable_holdings : 0))
    .filter((value) => Number.isFinite(value));
  const providerApplicable = applicableTotals.length ? Math.max(...applicableTotals) : 0;
  summaryEl.textContent = `Baseline: ${runId} · Active equity holdings: ${baseline} · Provider-applicable holdings: ${providerApplicable} · Threshold: ${threshold}d`;

  const providers = ["zacks", "danelfin", "yahoo"];
  const labels = { zacks: "Zacks", danelfin: "Danelfin", yahoo: "Yahoo" };
  el.innerHTML = providers.filter(key => coverage.providers[key]).map(key => {
    const info = coverage.providers[key];
    const status = info.status || "UNKNOWN";
    const dotCls = {
      COMPLIANT: "dot-fresh",
      DEGRADED: "dot-partial",
      NON_COMPLIANT: "dot-stale",
      UNKNOWN: "dot-unknown",
    }[status] || "dot-unknown";
    const stsCls = {
      COMPLIANT: "pill-status-fresh",
      DEGRADED: "pill-status-partial",
      NON_COMPLIANT: "pill-status-stale",
      UNKNOWN: "pill-status-unknown",
    }[status] || "pill-status-unknown";
    const statusLabel = String(status).toLowerCase().replaceAll("_", " ");

    const detail = [
      `Applicable: ${info.applicable_holdings}`,
      `Covered today: ${info.covered_today}`,
      `Within threshold: ${info.covered_within_threshold}`,
      `Stale: ${info.stale}`,
      `Missing: ${info.missing}`,
      `Not applicable: ${info.not_applicable}`,
      `Failed: ${info.failed}`,
    ].map(text => `<span class="pill-coverage">${text}</span>`).join(" ");

    return `<div class="signal-pill ${status === 'DEGRADED' ? 'signal-pill-partial' : ''}">
      <span class="dot ${dotCls}"></span>
      <div class="pill-body">
        <div class="pill-main-row">
          <span class="pill-label">${labels[key]}</span>
          <span class="${stsCls}">(${statusLabel})</span>
        </div>
        <div class="pill-detail-row">${detail}</div>
      </div>
    </div>`;
  }).join("");
}

function triggerSignalRefresh() {
  const btn = document.getElementById("signalRefreshBtn");
  const msg = document.getElementById("signalRefreshMsg");
  const modeSelect = document.getElementById("signalRefreshMode");
  const mode = modeSelect ? String(modeSelect.value || "portfolio_signals") : "portfolio_signals";
  if (!btn || !msg) return;

  if (mode === "rebuild_research_universe") {
    const ok = window.confirm("This will refresh approximately 2,473 research-universe symbols. Historical snapshots and trend history will be retained. Continue?");
    if (!ok) return;
  }

  // Disable immediately to prevent double-click while the POST is in-flight
  btn.disabled = true;
  btn.textContent = "Starting…";

  fetch("/api/signal-refresh", {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      intent: mode,
      requested_by: "operator",
      source: "outcome_visualization",
    }),
  })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      msg.style.display = "";
      if (data.started === false) {
        // Already running — keep button disabled and start polling
        btn.textContent = "Refreshing\u2026";
        msg.textContent = "Refresh already running in background.";
        _startRefreshPoll();
        return;
      }
      btn.disabled = true;
      btn.textContent = "Refreshing\u2026";
      const formula = data.scope_formula ? ` ${data.scope_formula}` : "";
      msg.textContent = `Refresh started (${_refreshModeLabel(mode)}). Running in background…${formula}`;
      _startRefreshPoll();
    })
    .catch(() => {
      btn.disabled = false;
      btn.textContent = _refreshModeLabel(mode);
      msg.style.display = "";
      msg.textContent = "Could not start refresh \u2014 is the server running with API support?";
    });
}

function _refreshModeLabel(mode) {
  if (mode === "stale_only") return "Refresh Stale Only";
  if (mode === "holdings_plus_buy_candidates") return "Refresh Current Holdings + Buy Candidates";
  if (mode === "rebuild_research_universe") return "Refresh Full Research Universe";
  if (mode === "prepare_portfolio_review") return "Prepare Portfolio Review";
  return "Refresh Current Holdings Only";
}

function _startRefreshPoll() {
  if (_refreshPollTimer) clearInterval(_refreshPollTimer);
  _refreshPollTimer = setInterval(() => {
    fetch("/api/signal-refresh/status", { cache: "no-store" })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        if (!data.running) {
          clearInterval(_refreshPollTimer);
          _refreshPollTimer = null;
          const btn = document.getElementById("signalRefreshBtn");
          const modeSelect = document.getElementById("signalRefreshMode");
          const mode = modeSelect ? String(modeSelect.value || "portfolio_signals") : "portfolio_signals";
          const msg = document.getElementById("signalRefreshMsg");
          if (btn) { btn.disabled = false; btn.textContent = _refreshModeLabel(mode); }
          if (msg) {
            msg.textContent = _buildRefreshOutcomeMessage(data.last_report || null);
          }
          loadSignalStatus();
          loadRefreshRuntimeStatus();
        }
      })
      .catch(() => {});
  }, 5000);
}

function _buildRefreshOutcomeMessage(report) {
  if (!report || !report.providers) {
    return "Refresh completed.";
  }

  const providers = ["zacks", "danelfin", "yahoo"];
  const labels = { zacks: "Zacks", danelfin: "Danelfin", yahoo: "Yahoo" };
  const rows = [];
  let totalSubmitted = 0;
  let totalRefreshed = 0;
  let totalFailed = 0;
  let totalCoverageGain = 0;

  providers.forEach((provider) => {
    const info = report.providers[provider];
    if (!info) return;
    const submitted = Number(info.submitted || 0);
    const refreshed = Number(info.refreshed || 0);
    const failed = Number(info.failed || 0);
    const before = info.coverage_before || {};
    const after = info.coverage_after || {};
    const beforeCovered = Number(before.covered_today || 0);
    const afterCovered = Number(after.covered_today || 0);
    const applicable = Number(after.applicable_holdings || before.applicable_holdings || 0);

    totalSubmitted += submitted;
    totalRefreshed += refreshed;
    totalFailed += failed;
    totalCoverageGain += Math.max(afterCovered - beforeCovered, 0);

    rows.push(
      `${labels[provider]}: submitted ${submitted}, refreshed ${refreshed}, failed ${failed}, coverage ${beforeCovered}/${applicable} -> ${afterCovered}/${applicable}`
    );
  });

  if (totalSubmitted === 0) {
    return "Refresh completed. No refresh required; holdings coverage already compliant or no stale/missing applicable holdings targeted.";
  }

  const head = `Refresh completed. ${totalRefreshed} holdings refreshed${totalFailed ? `, ${totalFailed} failures` : ""}${totalCoverageGain ? `, coverage +${totalCoverageGain}` : ""}.`;
  return `${head} ${rows.join(" | ")}`;
}
