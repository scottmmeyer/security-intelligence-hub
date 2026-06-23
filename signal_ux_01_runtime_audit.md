# SIGNAL-UX-01 Runtime Audit
**Date:** 2026-06-17  
**Scope:** Forensic evidence only — no code changes made  
**Status:** IMPLEMENTATION DEFECT IDENTIFIED

---

## Q1 — Running UI Build Timestamp and Deployed JS Bundle Version

**Evidence (server log, terminal 7108e21e):**
```
10:55:39 GET /ui/portfolio_alignment/ HTTP/1.1 → 200
10:55:39 GET /ui/signal_translation_registry.js?v=1 HTTP/1.1 → 200
10:55:39 GET /ui/portfolio_alignment/app.js?v=28 HTTP/1.1 → 200

10:56:42 GET /ui/portfolio_alignment/ HTTP/1.1 → 304
10:56:42 GET /ui/signal_translation_registry.js?v=1 HTTP/1.1 → 304
10:56:42 GET /ui/portfolio_alignment/app.js?v=28 HTTP/1.1 → 304
```

**File timestamps (filesystem):**
```
-rw-r--r--  448345  Jun 17 10:50  ui/portfolio_alignment/app.js
-rw-r--r--  204046  Jun 17 10:49  ui/portfolio_alignment/index.html
-rw-r--r--   13239  Jun 17 10:48  ui/signal_translation_registry.js
-rw-r--r--   51450  Jun 17 10:51  ui/ucf_operator_dashboard/index.html
```

**Conclusion:** All four files modified today (Jun 17, 10:48–10:51). Bundle version is `app.js?v=28`. Registry version is `?v=1`. First page load received HTTP 200 (fresh download), subsequent reload received HTTP 304 (browser cache hit on exact same content). The files currently being served are the files modified during SIGNAL-UX-01 implementation.

---

## Q2 — Verify `signal_translation_registry.js` Is Loaded by the Browser

**Evidence (index.html source, line 4045):**
```html
<script src="../signal_translation_registry.js?v=1"></script>
<script src="app.js?v=28"></script>
```

**Evidence (server log):**
```
GET /ui/signal_translation_registry.js?v=1 → 200 (initial load)
GET /ui/signal_translation_registry.js?v=1 → 304 (cached, subsequent reload)
```

**Conclusion:** Registry script IS included in `index.html` before `app.js` (correct load order). The server confirms it was fetched with HTTP 200. The `_sihZacksTranslate`, `_sihDanelfinTranslate`, `_sihEssTranslate`, and `_sihAnalystConsensusTranslate` functions are available globally when `app.js` executes.

---

## Q3 — Verify PRIM Detail Panel Rendering Path Calls Registry Functions

**Evidence (app.js grep, exact call sites):**
```
Line 2368: _sihZacksTranslate    — called in _computeSignalAgreement()
Line 2369: _sihDanelfinTranslate — called in _computeSignalAgreement()
Line 4986: _sihZacksTranslate    — called in _dqRenderTableRows()
Line 4987: _sihDanelfinTranslate — called in _dqRenderTableRows()
Line 5323: _sihZacksTranslate    — called in _buildInvestmentThesis() / DIL path
```

**Evidence (absence):**
SIGNAL-UX-01 modifications do NOT include any `_sihZacksTranslate` or `_sihDanelfinTranslate` call within `renderReductionQueue()` (lines 5618–5955). The `profileHtml` block at lines 5823–5858 uses only raw variable references with no translation guards.

**Conclusion:** The translation registry IS called in `_computeSignalAgreement` and `_dqRenderTableRows`, but **NOT in `renderReductionQueue`**. The PRIM "▼ Profile" panel (rendered by `renderReductionQueue`) never reaches any registry function.

---

## Q4 — Screenshot Panel: SIGNAL-UX-01 Path or Legacy Path?

**Evidence (panel identification):**

The user-visible panel showing "Zacks Rating: 1.0" and "Danelfin Score: 4.5000" is the **Reduction Queue Intelligence Profile** — the expandable "▼ Profile" section attached to each row in the Reduction Queue.

**Evidence (function and lines):**
- Function: `renderReductionQueue()`, declared at `app.js:5618`
- Variable assignment at `app.js:5735–5736`:
  ```js
  const zacks    = ov.zacks_rating  || fid.zacks_rating  || "";
  const danelfin = ov.danelfin_score || fid.danelfin_score || "";
  ```
- Render output at `app.js:5826–5827`:
  ```js
  ${profileItem("Zacks Rating", zacks || "—", "")}
  ${profileItem("Danelfin Score", danelfin || "—", "")}
  ```

**Evidence (PRIM symbol confirmed in portfolio):**  
Server log confirms PRIM is in the active portfolio symbol list:
```
GET /api/signal-conflicts?symbols=ARW,...,PRIM,...
```

**Conclusion:** The screenshot panel is a **legacy rendering path**. `renderReductionQueue` was not modified during SIGNAL-UX-01. SIGNAL-UX-01 modifications targeted `_computeSignalAgreement` (signal agreement panel, a sub-panel within the DQ breakdown row) and `_dqRenderTableRows` (DQ deployment queue cards). These are different UI surfaces from the Reduction Queue profile. The Reduction Queue is where PRIM appears as a sell candidate, and its profile panel was never patched.

---

## Q5 — Does Translated Text Exist but Hidden by CSS?

**Evidence (HTML generation analysis):**

`renderReductionQueue` at lines 5826–5827 generates:
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

No translation wrapper, no `nt-*` class, no hidden sibling element is generated. The `_sihZacksTranslate` / `_sihDanelfinTranslate` functions are never invoked in this code path, so no translated markup is emitted at all.

**Conclusion:** No CSS visibility issue. No translated text is generated for this panel. The HTML produced by `renderReductionQueue` for the `profileItem` rows contains only the raw numeric values. There is nothing to unhide.

---

## Q6 — Is a Frontend Rebuild/Restart Required?

**Evidence:** This project uses static JS files served directly by a Python HTTP server. There is no build step, bundler, or compilation stage. Files on disk are served directly.

**Conclusion:** No rebuild is required in the traditional sense. However, a **browser hard refresh** (Cmd+Shift+R on macOS) may be needed to bypass the HTTP 304 cache after any code change. The server itself requires no restart for static file changes.

---

## Q7 — Cache-Busting / Versioning Problem?

**Evidence (server log):**
```
First load:    GET /ui/portfolio_alignment/app.js?v=28 → 200 (fresh)
Subsequent:    GET /ui/portfolio_alignment/app.js?v=28 → 304 (browser cache hit)
```

**Conclusion:** The `?v=28` query parameter is the cache-busting mechanism. HTTP 304 responses confirm the browser is serving the same file that was downloaded on the first 200 request — this is correct behavior, not a malfunction. The 304 cache hit is on the files that were modified during SIGNAL-UX-01. The version string is **not** the problem. The cache is serving the correct, updated files. The defect is in the source code, not in caching or versioning.

---

## Q8 — Exact File and Function Currently Rendering Legacy Values

| Field | Value |
|-------|-------|
| **File** | `ui/portfolio_alignment/app.js` |
| **Function** | `renderReductionQueue` |
| **Function declaration** | Line 5618 |
| **Raw variable assignment — Zacks** | Line 5735: `const zacks = ov.zacks_rating \|\| fid.zacks_rating \|\| "";` |
| **Raw variable assignment — Danelfin** | Line 5736: `const danelfin = ov.danelfin_score \|\| fid.danelfin_score \|\| "";` |
| **Render call — Zacks Rating** | Line 5826: `${profileItem("Zacks Rating", zacks \|\| "—", "")}` |
| **Render call — Danelfin Score** | Line 5827: `${profileItem("Danelfin Score", danelfin \|\| "—", "")}` |
| **Panel label** | `profileItem()` helper — outputs label + raw value only |
| **Translation guard** | Absent — no `_sihZacksTranslate` / `_sihDanelfinTranslate` call |
| **PRIM symbol confirmed** | Server log `signal-conflicts?symbols=...,PRIM,...` |

For a PRIM position with `zacks_rating = 1.0` and `danelfin_score = 4.5000`, the rendered output is:
```
Zacks Rating    : 1.0
Danelfin Score  : 4.5000
```

---

## Q9 — Minimal Deployment Action Required to Activate

**Not implementing — evidence only, per Q10 directive.**

The minimal corrective action requires patching `renderReductionQueue` in `ui/portfolio_alignment/app.js` at lines 5735–5736 (variable setup) and 5826–5827 (render calls) to follow the same pattern already established in `_dqRenderTableRows` at lines 4986–4987 and 5044–5063:

1. Add translation calls after line 5736, analogous to lines 4986–4987:
   ```js
   const _tZacks    = typeof _sihZacksTranslate    !== "undefined" ? _sihZacksTranslate(zacks) : null;
   const _tDanelfin = typeof _sihDanelfinTranslate !== "undefined" ? _sihDanelfinTranslate(danelfin) : null;
   ```
2. Replace `profileItem("Zacks Rating", zacks || "—", "")` at line 5826 with translated display  
3. Replace `profileItem("Danelfin Score", danelfin || "—", "")` at line 5827 with translated display  
4. Hard-refresh browser (Cmd+Shift+R) after the file is saved

No server restart, no rebuild, no version bump strictly required (though bumping `?v=28` → `?v=29` in `index.html` ensures existing browser caches are invalidated).

---

## Q10 — Confirmation: No Code Modified

**CONFIRMED.** This document contains forensic evidence only. No source files were modified during this audit. All line references are read-only observations from `grep_search` and `read_file` tool calls against the files as currently written on disk.

---

## Summary

The SIGNAL-UX-01 implementation is partially complete. The translation registry (`signal_translation_registry.js`) is correctly loaded, syntactically valid, and served by the server. Translation calls are correctly applied in two out of the three relevant code paths:

| Code Path | Function | Translation Applied |
|-----------|----------|---------------------|
| DQ Signal Profile (deployment queue breakdown) | `_dqRenderTableRows` | ✅ YES (lines 4986–4987, 5044–5063) |
| Signal Agreement Panel | `_computeSignalAgreement` | ✅ YES (lines 2368–2369) |
| **Reduction Queue Intelligence Profile** | **`renderReductionQueue`** | **❌ NO (lines 5826–5827)** |

The user's PRIM position is in the **Reduction Queue**, not the Deployment Queue. The profile panel they are expanding is rendered by `renderReductionQueue`, which was never modified as part of SIGNAL-UX-01.
