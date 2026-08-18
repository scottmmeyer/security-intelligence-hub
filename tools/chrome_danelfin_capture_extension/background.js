const LOCAL_CAPTURE_ENDPOINT = "http://127.0.0.1:8765/api/danelfin/browser-capture";
const CAPTURE_QUEUE = [
  ["MU", "VRT"],
  ["FHI", "DELL"],
  ["CVE", "AEIS"],
  ["CAH", "TSM"],
  ["ATLC", "TSLA"]
];

const PAGE_LOAD_TIMEOUT_MS = 30000;
const MESSAGE_RETRY_COUNT = 6;
const MESSAGE_RETRY_DELAY_MS = 500;
const QUEUE_DELAY_MS = 1200;

let queueRunning = false;

function pairUrl(left, right) {
  return `https://danelfin.com/stocks/${String(left).toLowerCase()}-vs-${String(right).toLowerCase()}`;
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

async function postCapture(observations, dryRun) {
  const payload = {
    dry_run: Boolean(dryRun),
    acquisition_method: "BROWSER_CAPTURE_DANELFIN_UI",
    operator_source: "PAIR_PAGE",
    observations
  };

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
  let processedPairs = 0;
  let stopReason = "completed";

  try {
    for (const pair of CAPTURE_QUEUE) {
      const left = String(pair[0] || "").trim().toUpperCase();
      const right = String(pair[1] || "").trim().toUpperCase();
      if (!left || !right) {
        throw new Error(`invalid queue pair: ${JSON.stringify(pair)}`);
      }

      const created = await chrome.tabs.create({
        url: pairUrl(left, right),
        active: false
      });

      if (!created || typeof created.id !== "number") {
        throw new Error(`failed to create tab for pair ${left}/${right}`);
      }

      try {
        const loadedTab = await waitForTabComplete(created.id);
        const tabUrl = String((loadedTab && loadedTab.url) || "");
        if (!tabUrl.startsWith("https://danelfin.com/") && !tabUrl.startsWith("https://www.danelfin.com/")) {
          throw new Error(`temporary tab loaded unexpected URL: ${tabUrl || "(empty)"}`);
        }

        const response = await requestCapture(created.id, [left, right]);
        if (response.capture.challenge) {
          stopReason = `provider challenge detected for ${left}/${right}`;
          throw new Error(stopReason);
        }

        const ingestBody = await postCapture(response.capture.observations, false);
        if (hasSameDayConflict(ingestBody)) {
          stopReason = `same-day conflict for ${left}/${right}`;
          throw new Error(stopReason);
        }

        processedPairs += 1;
      } finally {
        await chrome.tabs.remove(created.id).catch(() => {});
      }

      await sleep(QUEUE_DELAY_MS);
    }
  } catch (err) {
    if (stopReason === "completed") {
      stopReason = String(err && err.message ? err.message : err);
    }
    console.error("Danelfin background capture queue failed", err);
  } finally {
    queueRunning = false;
    const elapsedMs = Date.now() - runStartedAt;
    console.info("Danelfin background capture queue finished", {
      processedPairs,
      totalPairs: CAPTURE_QUEUE.length,
      elapsedMs,
      stopReason
    });
  }
});
