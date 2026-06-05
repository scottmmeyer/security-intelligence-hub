# Phase 8.0B.0A — Cost / Benefit Analysis

**Date:** 2026-06-04  

---

## Implementation Cost

### API Cost

| Phase | FMP Plan Required | Monthly Cost |
|-------|-----------------|-------------|
| 8.0B.1A–B.5 (intake + display) | Starter | **$19/mo** |
| 8.0B.1C (scoring) | Starter | $19/mo |
| 8.0B.2 (dislocation framework) | Starter | $19/mo |
| Scale > 2,500 symbols | Ultimate | $99/mo |

**Near-term cost:** $19/month. Less than a single trade commission. Against the value of preventing one false sell signal on a good position, this is trivially justified.

### Development Effort

| Phase | Estimated Effort | Risk |
|-------|-----------------|------|
| 8.0B.1A — Signal Intake | **Low** — mirrors existing refresh_signals.py pattern | Low |
| 8.0B.1B — Analytical Universe join | **Low** — mirrors existing CSV join patterns | Low |
| 8.0B.1B.5 — Diagnostic Overlay (UI) | **Moderate** — new UI column in security overlay table | Low |
| 8.0B.1C — CW-DAS Momentum | **Moderate** — scoring formula change with governance review | Medium |
| 8.0B.2 — Dislocation Framework | **Moderate** — new CRA logic + classification | Medium |

**Total estimated effort through 8.0B.1B.5 (highest ROI phases):** 3–5 sessions

---

## Intelligence Improvement Assessment

### CW-DAS Improvement

| Current CW-DAS Weakness | FMP Fix | Estimated Score Impact |
|------------------------|---------|----------------------|
| Momentum (10pts) uses only ESS direction — lags earnings by 1–2 weeks | Replace with earnings momentum (beat rate + revision direction) | +8–10 pts for persistent beaters; −8–10 pts for consistent missers |
| No fundamental quality gate | FCF yield and gross margin context | Re-orders 10–15% of queue candidates |
| Replay + conviction tier — no forward validation | Earnings beat history = forward conviction signal | CCL/HCA tier promoted/demoted for 5–10% of candidates |

**Expected outcome:** CW-DAS rank order improves meaningfully for ~20% of candidates. The highest-ranked candidates under current CW-DAS (VRT, DELL, ARW) would generally be confirmed or further elevated by FMP data. Low-conviction candidates with deteriorating fundamentals would be correctly depressed.

---

### CRA Improvement

| Current CRA Weakness | FMP Fix | Expected Outcome |
|---------------------|---------|-----------------|
| False sell signals on temporarily dislocated stocks | Thesis integrity check (earnings beat + growth stable) | Prevents 1–3 false sell signals per rotation proposal |
| No source quality differentiation | FMP quality metrics on sell candidates | Distinguishes "sell because deteriorating" vs "sell because overweight but strong" |
| TAX_AWARE_EXIT without quality context | FCF yield + margins confirm business quality | Prevents harvesting a temporarily down but fundamentally strong position |

**Expected outcome:** CRA proposal quality improves materially. The most damaging failure mode (selling AVGO/DELL on a dip) is prevented. Operator trust increases.

---

### Conviction Scoring Improvement

| Current Weakness | FMP Fix |
|-----------------|---------|
| CCL/HCA tier based on replay + composite — backward-looking | Earnings beat history = forward-validated conviction |
| No distinction between "strong signal" and "strong business" | Revenue acceleration + margin quality = business strength |

**Expected outcome:** The top 10 conviction holdings more reliably reflect businesses with both strong analyst signals AND strong fundamentals.

---

### Dislocation Framework

| Current State | After FMP |
|--------------|----------|
| Cannot identify "cheap on pullback" scenarios | AVGO −15% with 31% revenue growth = DISLOCATION HIGH |
| CRA surfaces false sell signals on dislocations | CRA surfaces WATCH_DISLOCATION; no capital pool entry |
| No framework for "stocks on sale" | Full dislocation scoring framework |

**This is the highest-value new capability FMP enables.** No existing portfolio intelligence tool in the operator's workflow (as observed) can systematically classify dislocations.

---

## ROI Ranking

| Investment | Cost | Benefit |
|-----------|------|---------|
| Upgrade to Starter + Phase 8.0B.1A | $19/mo + ~1 session | Signal pipeline established; data flowing |
| Phase 8.0B.1B + 1B.5 | 2–3 sessions | Visibility + operator trust checkpoint |
| Phase 8.0B.1C (CW-DAS) | 2–3 sessions | 20% of rankings improve; false positives reduced |
| Phase 8.0B.2 (Dislocation) | 2–3 sessions | New highest-value capability unlocked |

**Total ROI:** $19/month buys a fundamental intelligence layer that prevents false sell signals, identifies buying opportunities after pullbacks, and adds earnings-validated conviction. This is unambiguously the highest ROI infrastructure investment available to SIH at this scale.

---

## Highest ROI Sequence (Recommended)

1. **Upgrade FMP key to Starter** — immediate prerequisite, $19/mo
2. **Phase 8.0B.1A** — signal intake (fastest path to data flow)
3. **Phase 8.0B.1B** — analytical universe extension (data visible)
4. **Phase 8.0B.1B.5** — diagnostic overlay (trust checkpoint)
5. **Phase 8.0B.1C** — CW-DAS scoring integration (highest score impact)
6. **Phase 8.0B.2** — dislocation framework (new capability)
