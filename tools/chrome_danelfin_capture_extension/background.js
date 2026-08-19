const LOCAL_CAPTURE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture";
const LOCAL_QUEUE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/queue";
const LOCAL_DIAGNOSTIC_QUEUE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-queue";
const LOCAL_DIAGNOSTIC_PENDING_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-queue/pending";
const LOCAL_DIAGNOSTIC_CLAIM_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-queue/claim";
const LOCAL_DIAGNOSTIC_STATUS_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/diagnostic-status";
const LOCAL_PRODUCTION_PENDING_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/production-queue/pending";
const LOCAL_PRODUCTION_CLAIM_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/production-queue/claim";
const LOCAL_PRODUCTION_STATUS_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture/production-status";
const AUTO_POLL_ALARM = "sih-danelfin-auto-poll";
const AUTO_POLL_MINUTES = 1;

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

async function loadCaptureQueue(diagnosticSymbol = "", diagnosticRunId = "", queueMode = "auto") {
  const mode = String(queueMode || "auto").trim().toLowerCase();
  let endpoint = LOCAL_QUEUE_ENDPOINT;
  if (mode === "diagnostic") {
    const params = new URLSearchParams();
    if (diagnosticRunId) {
      params.set("id", diagnosticRunId);
    }
    if (diagnosticSymbol) {
      params.set("symbol", diagnosticSymbol);
    }
    endpoint = params.toString()
      ? `${LOCAL_DIAGNOSTIC_PENDING_ENDPOINT}?${params.toString()}`
      : LOCAL_DIAGNOSTIC_PENDING_ENDPOINT;
  } else if (mode === "production") {
    const params = new URLSearchParams();
    if (diagnosticRunId) {
      params.set("id", diagnosticRunId);
    }
    endpoint = params.toString()
      ? `${LOCAL_PRODUCTION_PENDING_ENDPOINT}?${params.toString()}`
      : LOCAL_PRODUCTION_PENDING_ENDPOINT;
  } else if (diagnosticSymbol || diagnosticRunId) {
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

async function claimCaptureRun(runIdHint, workerId, queueMode = "diagnostic") {
  const runId = String(runIdHint || "").trim();
  if (!runId) {
    return [];
  }

  const mode = String(queueMode || "diagnostic").trim().toLowerCase();
  const endpoint = mode === "production" ? LOCAL_PRODUCTION_CLAIM_ENDPOINT : LOCAL_DIAGNOSTIC_CLAIM_ENDPOINT;
  const claimPayload = mode === "production"
    ? { run_id: runId, worker_id: String(workerId || "").trim() || "extension-worker" }
    : { diagnostic_run_id: runId, worker_id: String(workerId || "").trim() || "extension-worker" };

  const resp = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(claimPayload)
  });

  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(`claim failed: ${resp.status} ${JSON.stringify(body)}`);
  }
  if (!body || body.status !== "ok" || !Array.isArray(body.jobs)) {
    throw new Error(`claim payload invalid: ${JSON.stringify(body)}`);
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
    payload.run_id = String(diagnosticRunId);
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

async function postRunEvent(runId, event, payload = {}, queueMode = "diagnostic") {
  if (!runId) {
    return;
  }
  const mode = String(queueMode || "diagnostic").trim().toLowerCase();
  const endpoint = mode === "production" ? LOCAL_PRODUCTION_STATUS_ENDPOINT : LOCAL_DIAGNOSTIC_STATUS_ENDPOINT;
  const body = {
    run_id: String(runId),
    diagnostic_run_id: String(runId),
    event: String(event),
    ...payload
  };
  await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).catch(() => {});
}

function hasSameDayConflict(body) {
  const skipped = Array.isArray(body && body.skipped) ? body.skipped : [];
  return skipped.some((entry) => String((entry && entry.reason) || "") === "conflicts_with_existing_same_day_value");
}

function ensureAutoPollAlarm() {
  chrome.alarms.get(AUTO_POLL_ALARM, (existing) => {
    if (existing) {
      return;
    }
    chrome.alarms.create(AUTO_POLL_ALARM, {
      delayInMinutes: AUTO_POLL_MINUTES,
      periodInMinutes: AUTO_POLL_MINUTES
    });
  });
}

async function runCaptureWorker(trigger, diagnosticSymbol = "", diagnosticRunIdHint = "", queueMode = "auto") {
  if (queueRunning) {
    console.info("Danelfin capture worker already running; wake ignored", { trigger });
    return;
  }

  queueRunning = true;
  const runStartedAt = Date.now();
  let processedJobs = 0;
  let totalJobs = 0;
  let stopReason = "completed";
  let diagnosticRunId = "";
  let activeQueueMode = String(queueMode || "auto").trim().toLowerCase();

  try {
    let pendingQueue = [];
    if (activeQueueMode === "alarm_auto") {
      pendingQueue = await loadCaptureQueue("", "", "diagnostic");
      activeQueueMode = "diagnostic";
      if (!pendingQueue.length) {
        pendingQueue = await loadCaptureQueue("", "", "production");
        activeQueueMode = "production";
      }
    } else {
      pendingQueue = await loadCaptureQueue(diagnosticSymbol, diagnosticRunIdHint, activeQueueMode);
      if (activeQueueMode !== "diagnostic" && activeQueueMode !== "production") {
        activeQueueMode = (diagnosticSymbol || diagnosticRunIdHint) ? "diagnostic" : "production";
      }
    }

    totalJobs = pendingQueue.length;
    if (!pendingQueue.length) {
      console.info("Danelfin background capture queue is empty; nothing to do", { trigger });
      return;
    }

    const workerId = `${chrome.runtime.id}:${trigger}`;
    diagnosticRunId = String((pendingQueue[0] && (pendingQueue[0].diagnostic_run_id || pendingQueue[0].run_id)) || "").trim();
    const claimMode = activeQueueMode === "production" ? "production" : "diagnostic";
    let captureQueue = pendingQueue;
    if (diagnosticRunId) {
      captureQueue = await claimCaptureRun(diagnosticRunId, workerId, claimMode);
      if (!captureQueue.length) {
        console.info("Danelfin prepared job already claimed; skipping", { trigger, diagnosticRunId });
        return;
      }
    }

    if (diagnosticRunId) {
      await postRunEvent(diagnosticRunId, "worker_started", {
        trigger,
        worker_id: workerId,
      }, claimMode);
    }

    for (const job of captureQueue) {
      const kind = String(job && job.kind ? job.kind : "").trim().toLowerCase();
      const mode = String(job && job.mode ? job.mode : "").trim().toLowerCase();
      const symbols = Array.isArray(job && job.symbols) ? job.symbols.map((symbol) => String(symbol || "").trim().toUpperCase()).filter(Boolean) : [];
      const operatorSource = String(job && job.operator_source ? job.operator_source : (kind === "single" ? "STOCK_PAGE" : "PAIR_PAGE")).trim().toUpperCase();
      const dryRun = Boolean(job && job.dry_run);
      const runId = String(job && (job.diagnostic_run_id || job.run_id) ? (job.diagnostic_run_id || job.run_id) : "").trim();
      const url = String(job && job.url ? job.url : "").trim();
      if (kind !== "pair" && kind !== "single") {
        throw new Error(`invalid queue job kind: ${JSON.stringify(job)}`);
      }
      if (mode !== "diagnostic" && mode !== "production") {
        throw new Error(`invalid queue job mode: ${JSON.stringify(job)}`);
      }
      if (mode === "diagnostic" && dryRun !== true) {
        throw new Error(`diagnostic job must run in dry_run mode: ${JSON.stringify(job)}`);
      }
      if ((kind === "pair" && symbols.length !== 2) || (kind === "single" && symbols.length !== 1)) {
        throw new Error(`invalid queue job symbols: ${JSON.stringify(job)}`);
      }

      const left = symbols[0];
      const right = symbols[1];
      const jobUrl = url || (kind === "single" ? singleUrl(left) : pairUrl(left, right));
      if (mode === "production" && dryRun !== false) {
        throw new Error(`production job must run in non-dry mode: ${JSON.stringify(job)}`);
      }
      await postRunEvent(runId, "worker_claimed", { url: jobUrl, trigger, mode, dry_run: dryRun }, mode);
      await postRunEvent(runId, "navigation_started", { url: jobUrl, trigger }, mode);

      const [activeBefore] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      const created = await chrome.tabs.create({
        url: jobUrl,
        active: false
      });

      if (!created || typeof created.id !== "number") {
        throw new Error(`failed to create tab for pair ${left}/${right}`);
      }

      try {
        const loadedTab = await waitForTabComplete(created.id);
        const [activeAfter] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        await postRunEvent(runId, "navigation_completed", {
          url: String((loadedTab && loadedTab.url) || jobUrl),
          active_tab_before: activeBefore && typeof activeBefore.id === "number" ? activeBefore.id : null,
          active_tab_after: activeAfter && typeof activeAfter.id === "number" ? activeAfter.id : null,
          auto_tab_active: false,
        }, mode);
        const tabUrl = String((loadedTab && loadedTab.url) || "");
        if (!tabUrl.startsWith("https://danelfin.com/") && !tabUrl.startsWith("https://www.danelfin.com/")) {
          throw new Error(`temporary tab loaded unexpected URL: ${tabUrl || "(empty)"}`);
        }

        await postRunEvent(runId, "capture_started", { url: tabUrl, trigger }, mode);
        const response = await requestCapture(created.id, symbols);
        await postRunEvent(runId, "capture_completed", {
          url: tabUrl,
          raw_capture_present: Boolean(response && response.capture),
          parser_executed: true,
        }, mode);
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
    await postRunEvent(diagnosticRunId, "error", {
      error: String(err && err.message ? err.message : err),
      trigger,
    }, activeQueueMode === "production" ? "production" : "diagnostic");
    if (stopReason === "completed") {
      stopReason = String(err && err.message ? err.message : err);
    }
    console.error("Danelfin background capture queue failed", err);
  } finally {
    queueRunning = false;
    const elapsedMs = Date.now() - runStartedAt;
    console.info("Danelfin background capture queue finished", {
      trigger,
      processedJobs,
      totalJobs,
      elapsedMs,
      stopReason
    });
  }
}

chrome.action.onClicked.addListener(async () => {
  const [activeTab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  const activeUrl = activeTab && activeTab.url ? activeTab.url : "";
  const diagnosticSymbol = diagnosticSymbolFromUrl(activeUrl);
  const diagnosticRunIdHint = diagnosticRunIdFromUrl(activeUrl);
  await runCaptureWorker("manual_click", diagnosticSymbol, diagnosticRunIdHint, "auto");
});

chrome.runtime.onInstalled.addListener(() => {
  ensureAutoPollAlarm();
});

chrome.runtime.onStartup.addListener(() => {
  ensureAutoPollAlarm();
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (!alarm || alarm.name !== AUTO_POLL_ALARM) {
    return;
  }
  await runCaptureWorker("alarm_poll", "", "", "alarm_auto");
});

ensureAutoPollAlarm();
