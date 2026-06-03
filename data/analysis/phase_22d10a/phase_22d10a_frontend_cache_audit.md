# Phase 22D.10A — Frontend Cache Audit
**Date:** 2026-06-03  
**Scope:** ui/portfolio_alignment/index.html, ui/portfolio_alignment/app.js  
**Question:** Could browser cache serve stale JS after a deployment?

---

## 1. Fingerprinting Assessment

### Observed Mechanism
`ui/portfolio_alignment/index.html`, line 1523:
```html
<script src="app.js?v=4"></script>
```

`ui/outcome_visualization/index.html`, line 698:
```html
<script src="app.js?v=9"></script>
```

### Classification: MANUAL VERSION QUERY STRING

| Property | Value |
|---|---|
| Fingerprinting method | Manual `?v=N` query parameter |
| Is content-hash based? | **NO** |
| Is auto-incremented on build? | **NO** |
| Is incremented on every deploy? | **NO — requires human action** |
| Would stale JS be served if version not incremented? | **YES** |

---

## 2. Server-Side Cache Headers

The server (`scripts/run_outcome_ui.py`) extends `http.server.SimpleHTTPRequestHandler` with no override of `end_headers()` or `send_header()` for static file responses.

**`SimpleHTTPRequestHandler` default behavior:**
- Sends `Last-Modified` header based on file mtime
- Sends `Content-Type` inferred from extension
- Does **NOT** send `Cache-Control: no-cache`
- Does **NOT** send `ETag`
- Does **NOT** disable browser caching

**Result:** Browser will cache `app.js` using HTTP/1.1 heuristic caching (typically based on `Last-Modified` + `Expires` heuristics). On repeat page loads without a hard refresh, the browser **may** serve the cached prior version.

---

## 3. Cache Busting Scenarios

| Scenario | Stale JS Served? | Reason |
|---|---|---|
| Hard refresh (Cmd+Shift+R) | NO | Browser bypasses cache |
| Normal page reload (Cmd+R) | MAYBE | Depends on browser cache freshness |
| First load after server restart | Unlikely | Cache invalidated by new connection |
| Load in existing tab after deploy | **YES** | Browser serves cached `app.js?v=4` |
| Load in new tab, same session | **YES** | Browser L1 cache hit on `app.js?v=4` |
| `?v=N` not incremented after deploy | **YES** | Same URL, browser uses cached copy |

---

## 4. Phase 22D.10 Deploy Event

Phase 22D.10 modified `app.js` (settlement disclosure) but did **not** increment the version string. The version remained `?v=4` before and after the changes.

**Implication:** Any browser tab that had previously loaded the portfolio alignment UI and was not hard-refreshed may have been served the pre-22D.10 version of `app.js`, showing:
- No settlement disclosure banner
- `deployable_mv` (raw) displayed instead of `adjusted_deployable_mv`
- No "Adj. Deployable Cash" label in the summary strip

This is consistent with the observation that "Settlement disclosure appeared" only **after application restart**. The restart terminated the server; the browser reconnected to a fresh server, likely triggering a full reload of all assets.

---

## 5. Root Cause Determination

The browser cache served stale JS because:
1. `app.js?v=4` version was not incremented after the Phase 22D.10 edit
2. No `Cache-Control: no-cache` header is sent for static assets
3. Browser heuristic caching kept the pre-22D.10 `app.js` in memory

The server restart caused the browser to perform a full reload, which fetched the updated `app.js` from disk.

---

## 6. Risk Classification

| Risk | Severity | Notes |
|---|---|---|
| Future deploy shows stale UI logic | **MEDIUM** | Cash amounts shown may be incorrect |
| Backend logic already correct | N/A | Python changes take effect immediately after restart |
| Python API returning wrong data | LOW | Python modules loaded once at startup |

---

## 7. Recommended Mitigations (Not Implemented — Advisory)

1. **Increment `?v=N` after every app.js edit** (minimum viable fix)
2. Add `Cache-Control: no-store` header for all `/ui/` static assets in `run_outcome_ui.py` (prevents caching entirely — appropriate for dev server)
3. Long-term: adopt content-hash fingerprinting via a build tool

---

## 8. Verdict

**Was restart required because of stale browser cache? YES.**

The browser was serving a cached copy of `app.js?v=4` from before the Phase 22D.10 changes. The server restart triggered a fresh fetch, loading the updated code.

The restart was not required to activate the **backend** changes (Python logic was correct before the restart); it was required to force the **browser** to reload updated JavaScript.

**FINDING: OPERATIONALLY ACCEPTABLE** for a single-operator local dev server. The risk is understood and manageable via hard refresh or version string increment.
