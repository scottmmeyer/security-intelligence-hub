# Analyst Target Implementation Specification
## CII-005 Phase Assessment — June 5, 2026

---

## 1. Scope

This specification describes what would be implemented when analyst target
enrichment moves from assessment to execution. It is **not an implementation
instruction** — it is a design contract for future work.

---

## 2. Prerequisite: ISSUE-08 (analyst_count fix)

This specification assumes ISSUE-08 has been implemented first or is implemented
concurrently. ISSUE-08 adds `numberOfAnalystOpinions` to the fetch pipeline.
Without ISSUE-08, analyst_count will be null and the "N analysts" display falls
back to a dash.

Dependency is SOFT: the target display can ship without analyst_count and
gracefully degrade to `$X | +Y%` until ISSUE-08 lands.

---

## 3. Backend Changes

### 3.1 `fetch_yahoo_supplemental.py`

No changes needed for price_target, upside_pct, or current_price — these are
already fetched and stored.

**Required for ISSUE-08 (separate issue):**
```python
result["analyst_count"] = int(info.get("numberOfAnalystOpinions") or 0) or None
```

Add `"analyst_count"` to `_OUTPUT_HEADERS` list.

### 3.2 `load_analyst_consensus()` — `src/portfolio/analyst_consensus.py`

No changes needed. `analyst_count` is already in the `AnalystConsensus` model.
The load function sets it to `None` because the field is absent from the CSV.
After ISSUE-08 lands, change `analyst_count=None` to `analyst_count=_int("analyst_count")`.

### 3.3 `_build_consensus_payload()` — `src/portfolio/runner.py`

`analyst_count` is already emitted in the payload (always null today). No
changes needed. After ISSUE-08, the value will flow automatically.

### 3.4 `AnalystConsensus` model — `src/portfolio/models.py`

No changes needed.

---

## 4. UI Changes — Deployment Queue Signal Profile

### 4.1 New HTML block: Analyst Target Intelligence

To be inserted in `_dqRenderTableRows()` / `_dqWhySIHLikesItHtml()` area,
**after** the existing signal grid and **before** the CW-DAS breakdown grid.

```javascript
function _dqAnalystTargetHtml(ac) {
  if (!ac || (ac.price_target == null && ac.abr == null)) return "";

  const targetStr = ac.price_target != null
    ? `$${parseFloat(ac.price_target).toFixed(2)}`
    : "—";
  const upsideVal = ac.upside_pct != null ? parseFloat(ac.upside_pct) : null;
  const upsideStr = upsideVal != null
    ? `<span class="dq-ati-upside ${upsideVal >= 0 ? 'positive' : 'negative'}">
         ${upsideVal >= 0 ? "+" : ""}${upsideVal.toFixed(1)}%
       </span>`
    : "—";
  const countStr = ac.analyst_count != null ? `${ac.analyst_count} analysts` : "";
  const dateStr  = ac.refresh_date ? ac.refresh_date : "—";

  return `<div class="dq-analyst-target-block">
    <div class="dq-ati-header">Analyst Target Intelligence</div>
    <div class="dq-ati-row">
      <span class="dq-ati-item"><span class="dq-ati-lbl">Target</span> ${targetStr}</span>
      <span class="dq-ati-item"><span class="dq-ati-lbl">Upside</span> ${upsideStr}</span>
      ${countStr ? `<span class="dq-ati-item"><span class="dq-ati-lbl">Coverage</span> ${countStr}</span>` : ""}
      <span class="dq-ati-item dq-ati-date"><span class="dq-ati-lbl">Sourced</span> ${dateStr}</span>
    </div>
    <div class="dq-ati-advisory">⚠ Guidance only — analyst targets are opinions, not price forecasts. Do not use as trade triggers.</div>
  </div>`;
}
```

### 4.2 Placement in row expansion

Insert `_dqAnalystTargetHtml(ac2)` inside the expanded breakdown row after the
`_signalAgreementPanelHtml()` call and before the `dq-breakdown-header`
(CW-DAS Score Breakdown).

### 4.3 Recommendation card (`_consensusPanelHtml`)

The recommendation card already shows price_target, upside_pct, and current_price.
After ISSUE-08: add analyst_count display to this panel. No structural change needed.

---

## 5. CSS Classes Required

```css
/* Analyst Target Intelligence block */
.dq-analyst-target-block {
  background: #f9f7f2;
  border: 1px solid #e8e0d0;
  border-radius: 8px;
  padding: 10px 14px;
  margin: 10px 0;
}
.dq-ati-header {
  font-size: 0.70rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 6px;
}
.dq-ati-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 0.85rem;
}
.dq-ati-item { display: flex; flex-direction: column; gap: 1px; }
.dq-ati-lbl { font-size: 0.62rem; color: var(--muted); text-transform: uppercase; }
.dq-ati-upside.positive { color: var(--green); font-weight: 700; }
.dq-ati-upside.negative { color: var(--sev-high); font-weight: 700; }
.dq-ati-date { opacity: 0.75; }
.dq-ati-advisory {
  font-size: 0.70rem;
  color: var(--muted);
  font-style: italic;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid #e0d8cc;
}
```

---

## 6. UI Placement Summary

| Surface | What changes |
|---------|-------------|
| DQ Signal Profile (row expand) | ADD: `dq-analyst-target-block` after signal agreement panel |
| Recommendation card expansion | ADD: analyst_count after ISSUE-08 (minor field addition to `_consensusPanelHtml`) |
| Recommendation card — consensus panel | No structural change needed |
| DQ ABR `dq-sig-card` | Consider renaming label from "Yahoo ABR" to "ABR Consensus" for clarity (cosmetic, no functional impact) |

---

## 7. Fields to Display

| Field | Display label | Format | Notes |
|---|---|---|---|
| `price_target` | Target | `$X.XX` | Mean consensus target |
| `upside_pct` | Upside | `+X.X%` or `−X.X%` (color-coded) | Computed from target / current_price |
| `analyst_count` | Coverage | `N analysts` | ISSUE-08 required |
| `refresh_date` | Sourced | `YYYY-MM-DD` | Show always — freshness context |

---

## 8. Fields NOT to Display

| Field | Rationale |
|---|---|
| `targetHighPrice` | Invites anchoring to best-case; not actionable |
| `targetLowPrice` | Risk framing not aligned with SIH's actionability focus |
| `targetMedianPrice` | Low marginal value over mean; adds complexity without operator benefit |
| `averageAnalystRating` text | Redundant with `consensus_label` derivation already shown |
| Raw yfinance field names | Never expose API field names to operators |

---

## 9. Governance Notes

1. **No scoring influence.** All analyst target fields are display-only. The CW-DAS score, composite score, fundamental modifier, and replay gate are not modified by this implementation.

2. **Version impact.** If implemented: `app.js` v23 → v24, `index.html` v23 → v24.

3. **ISSUE-08 dependency.** Analyst count is always null until ISSUE-08 ships. The block degrades gracefully — count row is hidden if null, not shown as "—".

4. **Governance advisory is mandatory.** The `⚠ Guidance only` text is not optional styling — it is a required governance element for any surface that displays analyst price targets.

5. **ABR coverage gap.** ABR is only available for 65.4% of symbols. For names without ABR, the analyst target block should still show price_target and upside if available — ABR is a separate data point.

6. **No impact on CRA.** The Capital Rotation Advisor reads from `deployment_queue.json` and `security_overlays.csv`. Neither will change. No CRA changes are needed.

---

## 10. Version Impact Assessment

| Component | Change | Version impact |
|---|---|---|
| `fetch_yahoo_supplemental.py` | Add `analyst_count` field (ISSUE-08) | Minor — additive column |
| `load_analyst_consensus()` | Wire `analyst_count` from CSV (ISSUE-08) | Minor |
| `app.js` | Add `_dqAnalystTargetHtml()` function, insert in row expansion | v23 → v24 |
| `index.html` | Add `.dq-analyst-target-block` CSS | v23 → v24 |
| `src/portfolio/models.py` | No changes | No version impact |
| `src/portfolio/runner.py` | No changes | No version impact |
| `src/portfolio/deployment_queue.py` | No changes | No version impact |
| CW-DAS | No changes | CW-DAS 1.1 unchanged |
| CII | Strengthened (Layer 1 transparency) | CII v1.1 label unchanged |

---

## 11. GitHub Issue Recommendation

**One new issue warranted:**

```
Title: ISSUE-10: Add Analyst Target Intelligence block to DQ Signal Profile
Labels: enhancement, ux, signal-transparency, ready
Size: XS (1–2 hrs)
Depends on: ISSUE-08 (analyst_count fix)
```

**ISSUE-08 (analyst_count bug, GitHub #15) should be implemented first or concurrently.**

The display change (ISSUE-10) is independent of ISSUE-08 in that it can ship without analyst_count and gracefully degrade. However, the full value of the feature requires analyst_count, so sequencing ISSUE-08 → ISSUE-10 is recommended.
