const LOCAL_CAPTURE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture";
const LOCAL_QUEUE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/queue";
const LOCAL_DIAGNOSTIC_QUEUE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-queue";
const LOCAL_DIAGNOSTIC_PENDING_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-queue/pending";
const LOCAL_DIAGNOSTIC_STATUS_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-status";

const PAGE_LOAD_TIMEOUT_MS = 30000;
const MESSAGE_RETRY_COUNT = 6;
const MESSAGE_RETRY_DELAY_MS = 500;
const QUEUE_DELAY_MS = 1200;

let queueRunning = false;

function pairUrl(left, right) {
  return `https://danelfin.com/stocks/${String(left).toLowerCase()}-vs-${String(right).toLowerCase()}`;
}

function singleUrl(symbol) {
  return `https://danelfin.com/stock/${String(symbol).toLowerCase()}`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function waitForTabComplete(tabId, timeoutMs = PAGE_LOAD_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;

    function cleanup() {
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onRemoved.removeListener(onRemoved);
      clearInterval(pollTimer);
    }

    function tryResolveFromTab(tab) {
      if (tab && tab.status === "complete") {
        cleanup();
        resolve(tab);
        return true;
      }
      return false;
    }

    function onRemoved(removedTabId) {
      if (removedTabId !== tabId) {
        return;
      }
      cleanup();
      reject(new Error("temporary tab was closed before completion"));
    }

    function onUpdated(updatedTabId, changeInfo, tab) {
      if (updatedTabId !== tabId) {
        return;
      }
      if (changeInfo.status === "complete") {
        tryResolveFromTab(tab);
      }
    }

    const pollTimer = setInterval(async () => {
      if (Date.now() >= deadline) {
        cleanup();
        reject(new Error("timed out waiting for temporary tab load"));
        return;
      }
      try {
        const tab = await chrome.tabs.get(tabId);
        tryResolveFromTab(tab);
      } catch (_err) {
        // Ignore transient get failures; onRemoved handler will catch hard close.
      }
    }, 300);

    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.onRemoved.addListener(onRemoved);
  });
}

async function requestCapture(tabId, expectedSymbols) {
  let lastErr = null;
  for (let attempt = 1; attempt <= MESSAGE_RETRY_COUNT; attempt += 1) {
    try {
      const response = await chrome.tabs.sendMessage(tabId, {
        type: "CAPTURE_DANELFIN",
        expectedSymbols
      });
      if (response && response.ok && response.capture) {
        return response;
      }
      const message = response && response.error ? response.error : "capture message failed";
      throw new Error(message);
    } catch (err) {
      lastErr = err;
      if (attempt < MESSAGE_RETRY_COUNT) {
        await sleep(MESSAGE_RETRY_DELAY_MS);
      }
    }
  }
  throw new Error(
    `content-script capture failed after ${MESSAGE_RETRY_COUNT} attempts: ${String(
      lastErr && lastErr.message ? lastErr.message : lastErr
    )}`
  );
}

function diagnosticSymbolFromUrl(urlValue) {
  const raw = String(urlValue || "").trim();
  if (!raw) {
    return "";
  }
  try {
    const parsed = new URL(raw);
    const value = String(parsed.searchParams.get("danelfin_diag_symbol") || "").trim().toUpperCase();
    if (/^[A-Z0-9./-]{1,12}$/.test(value)) {
      return value;
    }
  } catch (_err) {
    return "";
  }
  return "";
}

function diagnosticRunIdFromUrl(urlValue) {
  const raw = String(urlValue || "").trim();
  if (!raw) {
    return "";
  }
  try {
    const parsed = new URL(raw);
    const value = String(parsed.searchParams.get("danelfin_diag_run_id") || "").trim();
    if (value) {
      return value;
    }
  } catch (_err) {
    return "";
  }
  return "";
}

async function loadCaptureQueue(diagnosticSymbol = "", diagnosticRunId = "") {
  let endpoint = LOCAL_QUEUE_ENDPOINT;
  if (diagnosticSymbol || diagnosticRunId) {
    const params = new URLSearchParams();
    if (diagnosticRunId) {
      params.set("id", diagnosticRunId);
    }
    if (diagnosticSymbol) {
      params.set("symbol", diagnosticSymbol);
    }
    endpoint = `${LOCAL_DIAGNOSTIC_PENDING_ENDPOINT}?${params.toString()}`;
  }

  const resp = await fetch(endpoint, {
    method: "GET",
    headers: { "Accept": "application/json" }
  });

  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(`queue fetch failed: ${resp.status} ${JSON.stringify(body)}`);
  }

  if (!body || body.status !== "ok" || !Array.isArray(body.jobs)) {
    throw new Error(`queue payload invalid: ${JSON.stringify(body)}`);
  }

  return body.jobs;
}

async function postCapture(observations, dryRun, operatorSource, diagnosticRunId = null) {
  const payload = {
    dry_run: Boolean(dryRun),
    acquisition_method: "BROWSER_CAPTURE_DANELFIN_UI",
    operator_source: operatorSource,
    observations
  };
  if (diagnosticRunId) {
    payload.diagnostic_run_id = String(diagnosticRunId);
  }

  const resp = await fetch(LOCAL_CAPTURE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(`local ingest failed: ${resp.status} ${JSON.stringify(body)}`);
  }
  return body;
}

async function postDiagnosticEvent(runId, event, payload = {}) {
  if (!runId) {
    return;
  }
  const body = {
    diagnostic_run_id: String(runId),
    event: String(event),
    ...payload
  };
  await fetch(LOCAL_DIAGNOSTIC_STATUS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).catch(() => {});
}

function hasSameDayConflict(body) {
  const skipped = Array.isArray(body && body.skipped) ? body.skipped : [];
  return skipped.some((entry) => String((entry && entry.reason) || "") === "conflicts_with_existing_same_day_value");
}

chrome.action.onClicked.addListener(async () => {
  if (queueRunning) {
    console.warn("Danelfin capture queue already running; ignoring duplicate click");
    return;
  }

  queueRunning = true;
  const runStartedAt = Date.now();
  let processedJobs = 0;
  let totalJobs = 0;
  let stopReason = "completed";
  let diagnosticRunId = "";

  try {
    const [activeTab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    const activeUrl = activeTab && activeTab.url ? activeTab.url : "";
    const diagnosticSymbol = diagnosticSymbolFromUrl(activeUrl);
    const diagnosticRunIdHint = diagnosticRunIdFromUrl(activeUrl);
    const captureQueue = await loadCaptureQueue(diagnosticSymbol, diagnosticRunIdHint);
    totalJobs = captureQueue.length;
    if (!captureQueue.length) {
      console.info("Danelfin background capture queue is empty; nothing to do");
      return;
    }
    diagnosticRunId = String((captureQueue[0] && captureQueue[0].diagnostic_run_id) || "").trim();
    await postDiagnosticEvent(diagnosticRunId, "worker_started");

    for (const job of captureQueue) {
      const kind = String(job && job.kind ? job.kind : "").trim().toLowerCase();
      const symbols = Array.isArray(job && job.symbols) ? job.symbols.map((symbol) => String(symbol || "").trim().toUpperCase()).filter(Boolean) : [];
      const operatorSource = String(job && job.operator_source ? job.operator_source : (kind === "single" ? "STOCK_PAGE" : "PAIR_PAGE")).trim().toUpperCase();
      const dryRun = Boolean(job && job.dry_run);
      const runId = String(job && job.diagnostic_run_id ? job.diagnostic_run_id : "").trim();
      const url = String(job && job.url ? job.url : "").trim();
      if (kind !== "pair" && kind !== "single") {
        throw new Error(`invalid queue job kind: ${JSON.stringify(job)}`);
      }
      if ((kind === "pair" && symbols.length !== 2) || (kind === "single" && symbols.length !== 1)) {
        throw new Error(`invalid queue job symbols: ${JSON.stringify(job)}`);
      }

      const left = symbols[0];
      const right = symbols[1];
      const jobUrl = url || (kind === "single" ? singleUrl(left) : pairUrl(left, right));
      await postDiagnosticEvent(runId, "worker_claimed", { url: jobUrl });
      await postDiagnosticEvent(runId, "navigation_started", { url: jobUrl });

      const created = await chrome.tabs.create({
        url: jobUrl,
        active: false
      });

      if (!created || typeof created.id !== "number") {
        throw new Error(`failed to create tab for pair ${left}/${right}`);
      }

      try {
        const loadedTab = await waitForTabComplete(created.id);
        await postDiagnosticEvent(runId, "navigation_completed", { url: String((loadedTab && loadedTab.url) || jobUrl) });
        const tabUrl = String((loadedTab && loadedTab.url) || "");
        if (!tabUrl.startsWith("https://danelfin.com/") && !tabUrl.startsWith("https://www.danelfin.com/")) {
          throw new Error(`temporary tab loaded unexpected URL: ${tabUrl || "(empty)"}`);
        }

        await postDiagnosticEvent(runId, "capture_started", { url: tabUrl });
        const response = await requestCapture(created.id, symbols);
        await postDiagnosticEvent(runId, "capture_completed", { url: tabUrl });
        if (response.capture.challenge) {
          stopReason = `provider challenge detected for ${symbols.join("/")}`;
          throw new Error(stopReason);
        }

        const ingestBody = await postCapture(response.capture.observations, dryRun, operatorSource, runId || null);
        if (hasSameDayConflict(ingestBody)) {
          stopReason = `same-day conflict for ${symbols.join("/")}`;
          throw new Error(stopReason);
        }

        processedJobs += 1;
      } finally {
        await chrome.tabs.remove(created.id).catch(() => {});
      }

      await sleep(QUEUE_DELAY_MS);
    }
  } catch (err) {
    await postDiagnosticEvent(diagnosticRunId, "error", { error: String(err && err.message ? err.message : err) });
    if (stopReason === "completed") {
      stopReason = String(err && err.message ? err.message : err);
    }
    console.error("Danelfin background capture queue failed", err);
  } finally {
    queueRunning = false;
    const elapsedMs = Date.now() - runStartedAt;
    console.info("Danelfin background capture queue finished", {
      processedJobs,
      totalJobs,
      elapsedMs,
      stopReason
    });
  }
});
