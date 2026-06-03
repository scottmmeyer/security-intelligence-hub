# Fidelity Analyst Alignment Report — Phase 7.5K

**Date:** 2026-05-31  
**Reference Run:** PAR-20260529-BAF83F16  
**Data Sources:**  
- `data/current/signal_snapshot.csv` (ESS via Fidelity, snapshot 2026-05-26)  
- `data/signals/yahoo/2026-05-29_yahoo_supplemental.csv` (Yahoo ABR)  
- `data/signals/zacks/latest_zacks.csv` (Zacks normalised score, 2026-05-29)  
**Scope:** Transparency audit only. No scoring changes. No ranking changes.

---

## Fidelity Data Inventory

| Field | Source | Column in System | Notes |
|-------|--------|:----------------:|-------|
| `ess_text` | `signal_snapshot.csv` | `starmine_ess_text` | VERY_BULLISH → VERY_BEARISH |
| `ess_numeric` | `signal_snapshot.csv` | `starmine_ess_numeric` | 1.0–5.0 normalised scale |
| `fidelity_rating` | Derived | — | ESS text → STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL |
| `fidelity_direction` | Derived | — | BULLISH / NEUTRAL / BEARISH |
| `refresh_date` | `signal_snapshot.csv` | `snapshot_date` | 2026-05-26 for current snapshot |
| `coverage_domain` | `signal_snapshot.csv` | `coverage_domain` | STARMINE_COVERED / NON_STARMINE_ANALYST |

**Total symbols with Fidelity ESS coverage:** 2,481 (STARMINE_COVERED or text-mapped)  
**Coverage for top 20 deployment candidates:** 20/20 (100%)

### ESS-to-Rating Scale

| ESS Text | Fidelity Rating | Direction |
|:--------:|:---------------:|:---------:|
| VERY_BULLISH | STRONG_BUY | BULLISH |
| BULLISH | BUY | BULLISH |
| NEUTRAL | HOLD | NEUTRAL |
| BEARISH | SELL | BEARISH |
| VERY_BEARISH | STRONG_SELL | BEARISH |

---

## Three-Signal Consensus Matrix

The consensus matrix evaluates agreement across three independent signals:

| Signal | Source | Scale | Direction Mapping |
|--------|--------|-------|-------------------|
| **ESS (Fidelity)** | `signal_snapshot.csv` | 5-text labels | VERY_BULLISH/BULLISH → BULLISH; NEUTRAL → NEUTRAL; BEARISH/VERY_BEARISH → BEARISH |
| **Yahoo ABR** | `yahoo_supplemental.csv` | ABR 1.0–5.0 | STRONG_BUY/BUY/MODERATE_BUY → BULLISH; HOLD → NEUTRAL; SELL → BEARISH |
| **Zacks** | `latest_zacks.csv` | 1–5 normalised | ≥4.0 → BULLISH; 3.0–3.9 → NEUTRAL; <3.0 → BEARISH |

### Matrix Classifications

| Classification | Meaning |
|:--------------:|---------|
| FULL_ALIGNMENT_BULLISH | All available signals point bullish |
| FULL_ALIGNMENT_BEARISH | All available signals point bearish |
| PARTIAL_ALIGNMENT | Majority (2 of available) agree |
| MAJOR_DIVERGENCE | Available signals strongly disagree |
| INSUFFICIENT_DATA | Fewer than 2 signals available |

---

## Top 20 Consensus Alignment Table

| Rank | Symbol | DAS | ESS | Fidelity Rating | Yahoo ABR | Zacks | Matrix | Flags |
|:----:|--------|:---:|:---:|:---------------:|:---------:|:-----:|:------:|-------|
| 1 | VRT | 95.53 | VERY_BULLISH | STRONG_BUY | STRONG_BUY | 4.0 (Buy) | ✅ FULL_BULLISH | — |
| 2 | ARW | 94.11 | VERY_BULLISH | STRONG_BUY | NO_CONSENSUS | 5.0 (Strong Buy) | ✅ FULL_BULLISH | NO_ABR |
| 3 | SNX | 93.51 | VERY_BULLISH | STRONG_BUY | BUY | 5.0 (Strong Buy) | ✅ FULL_BULLISH | — |
| 4 | ATLC | 93.48 | VERY_BULLISH | STRONG_BUY | NO_CONSENSUS | 5.0 (Strong Buy) | ✅ FULL_BULLISH | NO_ABR |
| 5 | PSX | 93.34 | VERY_BULLISH | STRONG_BUY | MODERATE_BUY | 5.0 (Strong Buy) | ✅ FULL_BULLISH | — |
| 6 | CBOE | 93.04 | VERY_BULLISH | STRONG_BUY | HOLD | 5.0 (Strong Buy) | ⚠️ PARTIAL | ESS+Zacks bullish; ABR neutral |
| 7 | AVT | 92.10 | VERY_BULLISH | STRONG_BUY | NO_CONSENSUS | 4.0 (Buy) | ✅ FULL_BULLISH | NO_ABR |
| 8 | LRCX | 91.73 | VERY_BULLISH | STRONG_BUY | BUY | 4.0 (Buy) | ✅ FULL_BULLISH | — |
| 9 | CAH | 91.59 | VERY_BULLISH | STRONG_BUY | STRONG_BUY | 4.0 (Buy) | ✅ FULL_BULLISH | — |
| 10 | DELL | 90.91 | VERY_BULLISH | STRONG_BUY | BUY | 4.0 (Buy) | ✅ FULL_BULLISH | STALE_TARGET |
| 11 | SANM | 90.78 | BULLISH | BUY | NO_CONSENSUS | 5.0 (Strong Buy) | ✅ FULL_BULLISH | NO_ABR |
| 12 | PCB | 90.74 | VERY_BULLISH | STRONG_BUY | NO_CONSENSUS | 3.0 (Hold) | ⚠️ PARTIAL | ESS bullish; Zacks neutral |
| 13 | CIEN | 90.11 | BULLISH | BUY | MODERATE_BUY | 5.0 (Strong Buy) | ✅ FULL_BULLISH | — |
| 14 | NUE | 89.62 | BULLISH | BUY | BUY | 5.0 (Strong Buy) | ✅ FULL_BULLISH | — |
| 15 | GFF | 88.50 | BULLISH | BUY | NO_CONSENSUS | 4.0 (Buy) | ✅ FULL_BULLISH | NO_ABR |
| 16 | ALNT | 88.46 | BULLISH | BUY | BUY | 3.0 (Hold) | ⚠️ PARTIAL | ESS+ABR bullish; Zacks neutral |
| 17 | MTZ | 88.35 | BULLISH | BUY | STRONG_BUY | 3.0 (Hold) | ⚠️ PARTIAL | ESS+ABR bullish; Zacks neutral |
| 18 | CRS | 88.20 | BULLISH | BUY | STRONG_BUY | 3.0 (Hold) | ⚠️ PARTIAL | ESS+ABR bullish; Zacks neutral |
| 19 | CMCO | 87.95 | BULLISH | BUY | NO_CONSENSUS | 3.0 (Hold) | ⚠️ PARTIAL | ESS bullish; Zacks neutral |
| 20 | ANGO | 87.88 | BULLISH | BUY | NO_CONSENSUS | 4.0 (Buy) | ✅ FULL_BULLISH | NO_ABR |

**Zacks normalised: 5.0 = Strong Buy (rank 1), 4.0 = Buy (rank 2), 3.0 = Hold (rank 3)**

---

## Distribution Summary

| Matrix Classification | Count | Symbols |
|:---------------------:|:-----:|---------|
| FULL_ALIGNMENT_BULLISH | 14 | VRT, ARW, SNX, ATLC, PSX, AVT, LRCX, CAH, DELL, SANM, CIEN, NUE, GFF, ANGO |
| PARTIAL_ALIGNMENT | 6 | CBOE, PCB, ALNT, MTZ, CRS, CMCO |
| MAJOR_DIVERGENCE | 0 | — |
| FULL_ALIGNMENT_BEARISH | 0 | — |

**The top 20 deployment candidates are overwhelmingly bullish (14/20 FULL_ALIGNMENT_BULLISH). No MAJOR_DIVERGENCE cases in top 20.**

### ABR Coverage
- 12/20 have Yahoo ABR data
- 8/20 have NO_ABR (micro/small-cap limited coverage)

### Partial Alignment Cases (Zacks Hold with ESS Bullish)
6 symbols show PARTIAL_ALIGNMENT because Zacks score = 3.0 (Hold/Neutral) while ESS and/or Yahoo ABR are bullish:

| Symbol | Zacks score | ESS | Yahoo ABR | Interpretation |
|--------|:-----------:|:---:|:---------:|----------------|
| CBOE | 3.0* | VERY_BULLISH | HOLD | ESS and Zacks both bullish. ABR HOLD adds caution. *Zacks rank=1 → score=5.0** |
| PCB | 3.0 | VERY_BULLISH | NO_CONSENSUS | Zacks neutral (Hold); ESS strongly bullish. Small-cap limited coverage. |
| ALNT | 3.0 | BULLISH | BUY | Zacks neutral; ESS and ABR bullish. 2-of-3 → PARTIAL. |
| MTZ | 3.0 | BULLISH | STRONG_BUY | Zacks neutral; ESS and ABR bullish. 2-of-3 → PARTIAL. |
| CRS | 3.0 | BULLISH | STRONG_BUY | Zacks neutral; ESS and ABR bullish. 2-of-3 → PARTIAL. |
| CMCO | 3.0 | BULLISH | NO_CONSENSUS | Zacks neutral; ESS bullish. Only 2 signals available. |

---

## CBOE — Repeated Analyst Caution Signal

CBOE continues to show multi-source caution:
- **Phase 7.5J**: CONSENSUS_DIVERGENCE — ESS VERY_BULLISH vs Yahoo ABR HOLD (3.12)
- **Phase 7.5K**: PARTIAL_ALIGNMENT — ESS VERY_BULLISH + Zacks Strong Buy vs Yahoo ABR HOLD

CBOE's momentum-driven ESS and Zacks Strong Buy rating contrast with analyst consensus at HOLD. This is a consistent divergence between quantitative models (ESS, Zacks rank) and broker consensus (ABR). The platform surfaces this for operator awareness.

---

## AEIS — Case Study

### Background
AEIS was previously affected by the StarMine ESS overwrite bug (Phase 7.5G remediation). This case study confirms the platform now surfaces a coherent, complete multi-signal story.

### Signal State (as of 2026-05-31)

| Signal | Value | Interpretation |
|--------|-------|---------------|
| ESS (Fidelity) | BEARISH | StarMine rates AEIS bearish — Fidelity platform view |
| Fidelity Rating | SELL | ESS BEARISH → SELL in analyst language |
| Fidelity Direction | BEARISH | Directional indication: negative |
| Yahoo ABR | NO_CONSENSUS | AEIS not covered in current Yahoo supplemental feed |
| Zacks normalised | 5.0 (rank=1) | Zacks Strong Buy — strongest possible bullish rating |
| Danelfin | 4.0/5 (BULLISH) | Bullish quantitative model rating |

### Consensus Matrix for AEIS

| Signal | Direction | Source |
|--------|:---------:|--------|
| ESS (Fidelity) | BEARISH | `signal_snapshot.csv` — STARMINE_COVERED |
| Yahoo ABR | UNKNOWN | Not in Yahoo supplemental |
| Zacks | BULLISH | `latest_zacks.csv` — rank=1 (Strong Buy) |
| **Classification** | **MAJOR_DIVERGENCE** | ESS=BEARISH vs Zacks=BULLISH; only 2 signals available |

### Deployment Status
- **Deployment queue:** Not in queue (no deployment recommendation)
- **Overlay flag:** HOLD
- **Composite score:** 3.055556 (moderate)
- **Signal direction:** NEUTRAL (conflicting signals resolve to neutral)

### Coherence Assessment

| Check | Status |
|-------|:------:|
| ESS visible to operator | ✅ PASS |
| Fidelity Rating (SELL) visible to operator | ✅ PASS |
| Zacks conflict surfaced (SELL vs Strong Buy) | ✅ PASS |
| Consensus matrix shows MAJOR_DIVERGENCE | ✅ PASS |
| Deployment decision unchanged (HOLD) | ✅ PASS |
| No scoring impact from transparency layer | ✅ PASS |

**Platform verdict:** The AEIS story is now coherent and fully visible to the operator. The ESS/Fidelity signal (BEARISH/SELL) directly conflicts with the Zacks signal (Strong Buy). The operator can see this divergence clearly via the Analyst Signal Stack panel and MAJOR_DIVERGENCE classification. The platform's HOLD recommendation appropriately reflects the signal conflict.

---

## Governance Notes

1. **No scoring changes.** CW-DAS scores, composite scores, and RPS scores are unchanged.
2. **No ranking changes.** Deployment queue order is unaffected.
3. **No deployment logic changes.** `fidelity_signals_by_symbol` is a display-only payload.
4. **The Fidelity Analyst card is a transparency reformatting** of the ESS data already in the system, not a new data source.
5. **The consensus matrix is display-only.** It does not gate, score, or rank any security.
6. **Zacks score in matrix uses normalised 1–5 scale** from `latest_zacks.csv`, not raw Zacks rank.
