# UI Render Path Trace — SIGNAL-UX-01
**Date:** 2026-06-17  
**Scope:** Forensic trace only — no code changes made

---

## Overview

The Portfolio Alignment dashboard (`ui/portfolio_alignment/`) contains **three distinct signal display surfaces**. SIGNAL-UX-01 modifications were applied to two of them. The third — the Reduction Queue Intelligence Profile — was not patched and is the panel visible when a user opens PRIM's "▼ Profile" row.

---

## Surface 1: DQ Signal Profile Cards (Deployment Queue)
**Function:** `_dqRenderTableRows()`  
**File:** `ui/portfolio_alignment/app.js`, line 4919  
**Panel location:** Deployment Queue table → expandable breakdown row  
**Panel identifier:** `dq-bd-${i}` → grid of `.dq-sig-card` elements  

### Translation call sites (SIGNAL-UX-01 applied):
```js
// app.js line 4986–4987
const _tZacks    = typeof _sihZacksTranslate    !== "undefined" ? _sihZacksTranslate(zacks) : null;
const _tDanelfin = typeof _sihDanelfinTranslate !== "undefined" ? _sihDanelfinTranslate(danelfin) : null;
```

### Rendered HTML (translated):
```html
<!-- Danelfin card, app.js lines 5049–5053 -->
<div class="dq-sig-card">
  <div class="dq-sig-val">[_tDanelfin.nativeRating]</div>
  <div class="dq-sig-sublabel">[_tDanelfin.meaning · Normalized X.XX · DIRECTION]</div>
  <div class="dq-sig-lbl">Danelfin</div>
</div>

<!-- Zacks card, app.js lines 5054–5058 -->
<div class="dq-sig-card">
  <div class="dq-sig-val">[_tZacks.nativeRating]</div>
  <div class="dq-sig-sublabel">[_tZacks.meaning · Normalized X.XX · DIRECTION]</div>
  <div class="dq-sig-lbl">Zacks</div>
</div>
```

**Status: SIGNAL-UX-01 APPLIED ✅**

---

## Surface 2: Signal Agreement Panel
**Function:** `_computeSignalAgreement()` → `_signalAgreementPanelHtml()`  
**File:** `ui/portfolio_alignment/app.js`, line 2361  
**Panel location:** Embedded within DQ breakdown row AND Reduction Queue profile  
**Panel identifier:** `.sa-panel` — rendered via `_signalAgreementPanelHtml(ov, ac, fs)`  

### Translation call sites (SIGNAL-UX-01 applied):
```js
// app.js lines 2368–2371
const _tzR    = typeof _sihZacksTranslate    !== "undefined" ? _sihZacksTranslate(ov && ov.zacks_rating) : null;
const _tdR    = typeof _sihDanelfinTranslate !== "undefined" ? _sihDanelfinTranslate(ov && ov.danelfin_score) : null;
const _teR    = typeof _sihEssTranslate      !== "undefined" ? _sihEssTranslate(...) : null;
const _taR    = (ac && typeof _sihAnalystConsensusTranslate !== "undefined") ? _sihAnalystConsensusTranslate(...) : null;
```

### Rendered HTML (translated):
```js
// app.js lines 2385–2399 — signals[] array with native/sublabel built from translation
{
  name: "Zacks",
  native: _tzR ? `${_tzR.nativeRating} ${_tzR.meaning}` : fallback,
  sublabel: _tzR ? `Normalized ${_tzR.normalizedScore} / 5` : "",
  direction: zDir,
},
{
  name: "Danelfin",
  native: _tdR ? `${_tdR.nativeRating}` : fallback,
  sublabel: _tdR ? `${_tdR.meaning} · Normalized ${_tdR.normalizedScore}` : fallback,
  direction: danDir,
}
```

**Note:** `_signalAgreementPanelHtml` is called from within `renderReductionQueue`'s profile html at line ~5950:
```js
${_signalAgreementPanelHtml(ov, ac2, fs)}
```
This means the **Signal Agreement sub-panel** within the Reduction Queue profile IS translated. However, the **profileItem rows above it** (lines 5826–5827) are a separate, legacy block that is not.

**Status: SIGNAL-UX-01 APPLIED ✅ (but only the signal agreement sub-panel, not the profileItem rows)**

---

## Surface 3: Reduction Queue Intelligence Profile (▼ Profile)
**Function:** `renderReductionQueue()`  
**File:** `ui/portfolio_alignment/app.js`, line 5618  
**Panel location:** Reduction Queue table → "▼ Profile" expandable row → `rq-profile-grid`  
**Panel identifier:** `rq-profile-${idx}` — rendered via `profileItem()` helper  

### Variable assignment (raw, no translation):
```js
// app.js lines 5735–5736
const zacks    = ov.zacks_rating  || fid.zacks_rating  || "";
const danelfin = ov.danelfin_score || fid.danelfin_score || "";
```

### No translation calls exist in this function scope.

### Rendered HTML (legacy — UNTRANSLATED):
```js
// app.js lines 5826–5827
${profileItem("Zacks Rating",   zacks    || "—", "")}
${profileItem("Danelfin Score", danelfin || "—", "")}
```

Where `profileItem` expands to:
```html
<div class="rq-profile-row-item">
  <span class="rq-profile-lbl">Zacks Rating</span>
  <span class="rq-profile-val ">1.0</span>
</div>
<div class="rq-profile-row-item">
  <span class="rq-profile-lbl">Danelfin Score</span>
  <span class="rq-profile-val ">4.5000</span>
</div>
```

**Status: SIGNAL-UX-01 NOT APPLIED ❌ — THIS IS THE PANEL THE USER IS VIEWING**

---

## PRIM Symbol Position in Portfolio

Server log confirms PRIM is an active portfolio symbol and appears in Reduction Queue context:
```
GET /api/signal-conflicts?symbols=...,PRIM,...  → 200
POST /api/portfolio/analyze                     → 200
```

PRIM is a **sell candidate in the Reduction Queue**, not a buy candidate in the Deployment Queue. Its profile panel is rendered exclusively by `renderReductionQueue`, which was never patched.

---

## Call Chain for User-Visible PRIM Panel

```
POST /api/portfolio/analyze  →  _analysisResult populated
         │
         ▼
renderReductionQueue(sources, totalPool, fviData, overlayBySymbol, ucfBySymbol, fidBySymbol)
  │  [app.js:5618]
  │
  ├── for each source s in top10
  │     ├── zacks    = ov.zacks_rating || fid.zacks_rating || ""   [line 5735]
  │     ├── danelfin = ov.danelfin_score || fid.danelfin_score || "" [line 5736]
  │     │   ← NO _sihZacksTranslate / _sihDanelfinTranslate call here
  │     │
  │     └── profileHtml = `...
  │           ${profileItem("Zacks Rating", zacks || "—", "")}      [line 5826]
  │           ${profileItem("Danelfin Score", danelfin || "—", "")} [line 5827]
  │         ...`
  │
  └── DOM output → <span class="rq-profile-val ">1.0</span>
                   <span class="rq-profile-val ">4.5000</span>
```

---

## Comparison: Modified Path vs. Unmodified Path

| Attribute | `_dqRenderTableRows` (MODIFIED) | `renderReductionQueue` (UNMODIFIED) |
|-----------|--------------------------------|--------------------------------------|
| Panel label | DQ Signal Profile | RQ Intelligence Profile |
| Panel CSS class | `.dq-sig-card` | `.rq-profile-row-item` |
| Translation calls | ✅ Lines 4986–4987 | ❌ None |
| Zacks display | `#5 Strong Sell · Normalized 1.0` | `1.0` |
| Danelfin display | `AI=9 · Very Bullish · Normalized 4.5` | `4.5000` |
| Registry guard | `typeof _sihZacksTranslate !== "undefined"` | Absent |
| PRIM appears here? | ❌ (PRIM is a sell candidate, not in DQ) | ✅ YES |

---

## Root Cause Statement

The SIGNAL-UX-01 implementation applied translation to the **Deployment Queue** signal profile panel but did not apply the same pattern to the **Reduction Queue** intelligence profile panel. PRIM surfaces exclusively in the Reduction Queue (as a sell candidate). The user's screenshot shows the Reduction Queue profile, which was never modified.
