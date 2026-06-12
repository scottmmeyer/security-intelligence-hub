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
      <span class="fbt-subtitle">Out-of-sample validation — scores were locked on the selection date before the measurement period began</span>
    </div>
    <div class="fbt-body">
      <div class="fbt-block">
        <div class="fbt-label">Score &amp; Selection Date</div>
        <div class="fbt-value">${scoreDate}</div>
      </div>
      <div class="fbt-block">
        <div class="fbt-label">Measurement Window</div>
        <div class="fbt-value">${startDate} → ${endDate}</div>
      </div>
      <div class="fbt-block">
        <div class="fbt-label">Universe</div>
        <div class="fbt-value">${geography} ${marketCap}</div>
      </div>
      <div class="fbt-block">
        <div class="fbt-label">Stocks Selected</div>
        <div class="fbt-value">${symbols.length} (Top ${topN})</div>
      </div>
      ${returnBlock}
    </div>
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
  `;
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

  if (!availability) {
    const message = "Replay availability governance mismatch: no availability row exists for selected category.";
    setStatus(message, true);
    drawGovernedPlaceholder(message);
    replayMetaNode.textContent = JSON.stringify(
      { selected_filters: filters, message },
      null,
      2,
    );
    return;
  }

  const replayStatus = String(availability.replay_status || "NOT_GENERATED").toUpperCase();
  const missingDependencies = String(availability.missing_dependencies || "").trim();
  const replayGenerated = parseBoolText(availability.replay_generated);

  if (!replayGenerated || ["NOT_GENERATED", "MISSING_MAPPING", "MISSING_MARKET_DATA", "BLOCKED"].includes(replayStatus)) {
    const message = [
      `Replay unavailable for ${filters.geography} ${filters.marketCap} ${filters.industry}.`,
      `Status: ${replayStatus}.`,
      missingDependencies ? `Missing dependencies: ${missingDependencies}` : "Missing dependencies: none reported.",
    ].join(" ");
    setStatus(message, true);
    drawGovernedPlaceholder(message);
    replayMetaNode.textContent = JSON.stringify(
      {
        selected_filters: filters,
        availability,
        replay_matrix_row: replayMatrixRow || "not generated",
      },
      null,
      2,
    );
    return;
  }

  if (!replayMatrixRow) {
    const message = "Replay/UI mismatch: availability indicates generated replay but replay_matrix has no matching row.";
    setStatus(message, true);
    drawGovernedPlaceholder(message);
    replayMetaNode.textContent = JSON.stringify(
      { selected_filters: filters, availability, message },
      null,
      2,
    );
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
    ? "[FORWARD SIM]"
    : replayMode === "CURRENT_RECOMMENDATION"
    ? "[CURRENT]"
    : "[FORWARD BACKTEST]";

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

  // Phase H: update freshness panel
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

  const hasSeries = seriesRows.length > 0;
  if (!hasSeries) {
    const message = [
      "Replay generated but performance series rows are empty for selected category.",
      missingDependencies ? `Missing dependencies: ${missingDependencies}` : "",
    ].join(" ").trim();
    setStatus(message, true);
    drawGovernedPlaceholder(message);
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

  setStatus(`${modeLabel} Line render with ${seriesRows.length} points for replay ${replayId}. ${statusSummary}${subtierNote}`);
  drawSeriesChart(seriesRows);
}

async function initialize() {
  try {
    const [seriesText, inputsText, availabilityText, matrixText, universeText, benchmarkYaml, vehicleYaml, snapshotMetaText] = await Promise.all([
      fetchText(DATA_PATHS.replaySeries),
      fetchText(DATA_PATHS.replayInputs),
      fetchText(DATA_PATHS.replayAvailability).catch(() => ""),
      fetchText(DATA_PATHS.replayMatrix).catch(() => ""),
      fetchText(DATA_PATHS.analyticalUniverse),
      fetchText(DATA_PATHS.benchmarkRegistry),
      fetchText(DATA_PATHS.vehicleRegistry),
      fetchText(DATA_PATHS.snapshotMetadata).catch(() => ""),
    ]);

    state.replaySeries = parseCsv(seriesText);
    state.replayInputs = parseCsv(inputsText);
    state.replayAvailability = parseCsv(availabilityText);
    state.replayMatrix = parseCsv(matrixText);
    state.analyticalUniverse = parseCsv(universeText);
    state.benchmarkRegistryText = benchmarkYaml;
    state.vehicleRegistryText = vehicleYaml;
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

    await render();
  } catch (error) {
    setStatus(`Failed to load UI data inputs: ${error.message}`, true);
    drawSeriesChart([], error.message);
    document.getElementById("replayMeta").textContent = JSON.stringify(
      { error: String(error.message || error) },
      null,
      2,
    );
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

function loadSignalStatus() {
  fetch("/api/signal-status", { cache: "no-store" })
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(data => {
      _renderSignalPills(data);
      if (data._running) {
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
    });
}

function _renderSignalPills(data) {
  const el = document.getElementById("signalStatusPills");
  if (!el) return;
  const providers = ["ess", "zacks", "danelfin", "yahoo"];
  const labels    = { ess: "ESS", zacks: "Zacks", danelfin: "Danelfin", yahoo: "Yahoo" };
  el.innerHTML = providers.filter(k => k in data).map(key => {
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

    // Coverage detail line (SI-REFRESH-02)
    let coverageHtml = "";
    if (info.attempted_count != null) {
      const covPct = info.coverage_pct != null ? info.coverage_pct.toFixed(1) : "—";
      coverageHtml = `<span class="pill-coverage">${info.with_data_count}/${info.attempted_count} rows · ${covPct}%</span>`;
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
      warningHtml = `<span class="pill-degraded">ESS coverage warning: ${info.coverage_warning_count} holdings absent${examples ? ` · ${examples}` : ""}</span>`;
    }

    const extraLines = [coverageHtml, degradedHtml, warningHtml].filter(Boolean).join(" ");

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
  }).join("");
}

function triggerSignalRefresh() {
  const btn = document.getElementById("signalRefreshBtn");
  const msg = document.getElementById("signalRefreshMsg");
  if (!btn || !msg) return;
  // Disable immediately to prevent double-click while the POST is in-flight
  btn.disabled = true;
  btn.textContent = "Starting…";

  fetch("/api/signal-refresh", { method: "POST", cache: "no-store" })
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
      msg.textContent = "Refresh started (smart mode \u2014 mandatory holdings included). Danelfin: ~60\u201390 min, Yahoo: ~15 min. Runs in background, you can continue using the UI.";
      _startRefreshPoll();
    })
    .catch(() => {
      btn.disabled = false;
      btn.textContent = "Refresh Stale";
      msg.style.display = "";
      msg.textContent = "Could not start refresh \u2014 is the server running with API support?";
    });
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
          const msg = document.getElementById("signalRefreshMsg");
          if (btn) { btn.disabled = false; btn.textContent = "Refresh Stale"; }
          if (msg) { msg.textContent = "Refresh complete. Signal dates updated."; }
          loadSignalStatus();
        }
      })
      .catch(() => {});
  }, 5000);
}
