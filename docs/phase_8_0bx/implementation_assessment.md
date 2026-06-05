# Implementation Assessment

**Date:** 2026-06-04  
**Scope:** Display-only — no scoring, no CW-DAS, no ranking changes

---

## Implementation Plan

### Step 1: New API endpoint — `GET /api/security-metadata`

Add to `scripts/run_outcome_ui.py`:

```python
elif path == "/api/security-metadata":
    from src.scoring.fetch_security_metadata import load_latest_security_metadata
    metadata = load_latest_security_metadata()
    self._json_response(metadata)
```

Returns: `{symbol → {sector, industry, country, quote_type, sourced_date}}`  
Source: `data/signals/security_metadata/latest_security_metadata.csv` (already on disk)  
No new data fetching. No new files. One endpoint.

### Step 2: Frontend — load metadata once per analysis

In `app.js`, add a `_securityMetadata = {}` global and a fetch on analysis load:

```js
let _securityMetadata = {};

async function _loadSecurityMetadata() {
    try {
        const resp = await fetch("/api/security-metadata");
        if (resp.ok) _securityMetadata = await resp.json();
    } catch (_) { /* non-blocking */ }
}
```

Called from `renderResults()` alongside the existing analysis render (non-blocking, fire-and-forget).

### Step 3: Company Snapshot HTML function

```js
function _dqCompanySnapshotHtml(sym, holdingsLookup, metadataLookup) {
    const h = holdingsLookup[sym] || {};
    const m = metadataLookup[sym] || {};
    
    const rawName = h.description || sym;
    const name = _cleanCompanyName(rawName, sym);
    
    const sector   = m.sector   || h.sector   || "—";
    const industry = m.industry || h.industry || "—";
    const country  = m.country  || "—";
    const capTier  = h.market_cap_bucket || "—";
    
    return `<div class="dq-company-snapshot">
      <div class="dq-cs-header">Company Snapshot — ${escHtml(sym)}</div>
      <div class="dq-cs-name">${escHtml(name)}</div>
      <div class="dq-cs-grid">
        <div class="dq-cs-lbl">Sector</div>
        <div class="dq-cs-val">${escHtml(sector)}</div>
        <div class="dq-cs-lbl">Industry</div>
        <div class="dq-cs-val">${escHtml(industry)}</div>
        <div class="dq-cs-lbl">Country</div>
        <div class="dq-cs-val">${escHtml(country)}</div>
        <div class="dq-cs-lbl">Cap Tier</div>
        <div class="dq-cs-val">${escHtml(capTier)}</div>
      </div>
    </div>`;
}
```

### Step 4: CSS additions to `index.html`

```css
.dq-company-snapshot {
    margin-top: 12px;
    padding: 10px 14px;
    background: #faf8f4;
    border: 1px solid var(--border);
    border-radius: 8px;
}
.dq-cs-header {
    font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--muted); margin-bottom: 6px;
}
.dq-cs-name {
    font-size: 0.88rem; font-weight: 700;
    color: var(--fg); margin-bottom: 8px;
}
.dq-cs-grid {
    display: grid; grid-template-columns: 110px 1fr;
    gap: 3px 10px; font-size: 0.80rem;
}
.dq-cs-lbl { color: var(--muted); }
.dq-cs-val { color: var(--fg); font-weight: 500; }
```

### Step 5: Wire into existing card expansion

In `_dqRenderTableRows()`, after the `dq-breakdown-notes` div, add:

```js
${_dqCompanySnapshotHtml(sym, _holdingsBySymbol, _securityMetadata)}
```

Where `_holdingsBySymbol` is already built from `_ovSource`/holdings data.

---

## Complexity Assessment

| Component | Effort | Risk |
|-----------|--------|------|
| API endpoint | ~10 lines | Zero — reads existing file |
| `_loadSecurityMetadata()` | ~10 lines | Zero — non-blocking fetch |
| `_dqCompanySnapshotHtml()` | ~30 lines | Zero — display only |
| CSS | ~20 lines | Zero |
| Wire into card | ~3 lines | Low |

**Total estimated: 1 session, ~75 lines, no architectural changes.**

---

## Non-Negotiable Guardrails (confirmed)

- ❌ No CW-DAS score changes
- ❌ No rank changes  
- ❌ No recommendation changes
- ❌ No new data fetching (security_metadata already on disk)
- ✅ Display only
- ✅ Non-blocking (metadata load failure doesn't break anything)
- ✅ Graceful degradation: all fields fall back to "—" if missing
