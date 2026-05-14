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
    ctx.beginPath();
    filtered.forEach((point, idx) => {
      const t = parseIsoDate(point.date).getTime();
      const x = xScale(t);
      const y = yScale(point.metric);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
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
    industry: document.getElementById("industrySelect").value,
    timeframe: document.getElementById("timeframeSelect").value,
    topN: String(Number(document.getElementById("topNInput").value || 20)),
  };
}

function pickReplayRow(filters) {
  const rows = state.replayInputs.filter((row) => {
    return (
      String(row.filter_geography || "").toUpperCase() === filters.geography &&
      String(row.filter_market_cap_bucket || "").toUpperCase() === filters.marketCap &&
      String(row.filter_industry || "").toUpperCase() === filters.industry &&
      String(row.top_n || "") === filters.topN
    );
  });

  if (!rows.length) return null;
  return rows.sort((a, b) => String(b.replay_id).localeCompare(String(a.replay_id)))[0];
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

async function render() {
  const renderId = ++state.renderEpoch;
  const isStale = () => renderId !== state.renderEpoch;

  const filters = getSelectedFilters();
  const replay = pickReplayRow(filters);
  const availability = pickAvailabilityRow(filters);
  const replayMatrixRow = pickReplayMatrixRow(filters);

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

  const replayId = String(replayMatrixRow.replay_id || replay?.replay_id || "");
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
  // Phase F: extract replay_mode from replay_inputs row
  const replayInputRow = state.replayInputs.find((r) => String(r.replay_id || "") === replayId);
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
    : "[HISTORICAL]";

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

  setStatus(`${modeLabel} Line render with ${seriesRows.length} points for replay ${replayId}. ${statusSummary}`);
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

    if (state.replayInputs.length > 0) {
      const first = state.replayInputs[0];
      document.getElementById("geographySelect").value = String(first.filter_geography || "US").toUpperCase();
      document.getElementById("marketCapSelect").value = String(first.filter_market_cap_bucket || "LARGE").toUpperCase();
      document.getElementById("industrySelect").value = String(first.filter_industry || "ALL").toUpperCase();
      document.getElementById("topNInput").value = Number(first.top_n || 20);
    }

    ["geographySelect", "marketCapSelect", "industrySelect", "timeframeSelect", "topNInput"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
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
