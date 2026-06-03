# Replay History Coverage Report — Phase 7.5S-A
**Date:** 2026-06-01  
**Symbols:** VRT, ARW, CIEN, CAH, ATLC, PRG  
**Source:** `data/current/replay_inputs.csv` + `data/current/replay_performance_series.csv`

---

## Coverage Overview

| Symbol | Total Replays | Earliest Start | Latest End | Total Trading Days (all replays) | replay_supported |
|--------|--------------|---------------|------------|----------------------------------|-----------------|
| VRT | 2 | 2025-05-14 | 2026-05-26 | 252 (HIST) + 4 (CURR) = 256 | **True** |
| ARW | 2 | 2025-05-14 | 2026-05-26 | 252 (HIST) + 4 (CURR) = 256 | **True** |
| CIEN | 1 | 2025-05-14 | 2026-05-14 | 252 | **True** |
| CAH | 1 | 2025-05-14 | 2026-05-14 | 252 | **True** |
| ATLC | 1 | 2025-05-14 | 2026-05-14 | 252 | **True** |
| PRG | 0 | — | — | 0 | **False** |

---

## Detailed Coverage Per Replay

---

### VRT — Replay 1 (Historical)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2025-05-14-TO-2026-05-14-US-LARGE-INDUSTRIALS-TOP20-RUN-WP05D-20260515-INDUS1-US-LARGE-INDUSTRIALS` |
| Mode | HISTORICAL_VALIDATION |
| Basket scope | US LARGE-cap INDUSTRIALS, Top-20 by composite score |
| Composite snapshot date | 2025-05-14 |
| Replay start | 2025-05-14 |
| Replay end | 2026-05-14 |
| Coverage window | 366 calendar days (1 year) |
| Trading days observed | **252** |
| Earliest series date | 2025-05-14 |
| Latest series date | 2026-05-14 |
| TOP_N_STRATEGY final cumulative return | **+66.7%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, INVESTABLE_VEHICLE, TOP_N_STRATEGY |
| Governs replay_supported? | No — bypassed by ALL replay (symbol_tier takes precedence) |

### VRT — Replay 2 (Current Recommendation)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2026-05-20-TO-2026-05-26-US-LARGE-ALL-TOP20-WP05D-20260526-ALL2-US-LARGE-ALL` |
| Mode | CURRENT_RECOMMENDATION |
| Basket scope | US LARGE-cap ALL industries, Top-20 by composite score |
| Composite snapshot date | 2026-05-20 |
| Replay start | 2026-05-20 |
| Replay end | 2026-05-26 |
| Coverage window | 6 calendar days |
| Trading days observed | **4** |
| Earliest series date | 2026-05-20 |
| Latest series date | 2026-05-26 |
| TOP_N_STRATEGY cumulative return (through 2026-05-26) | **+4.7%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, INVESTABLE_VEHICLE, TOP_N_STRATEGY |
| Governs replay_supported? | **Yes** — this is the active governing replay via symbol_tier |

---

### ARW — Replay 1 (Historical)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-TECHNOLOGY-TOP20-RUN-WP05D-20260515-TECH1-US-SMALL-TECHNOLOGY` |
| Mode | HISTORICAL_VALIDATION |
| Basket scope | US SMALL-cap TECHNOLOGY, Top-20 by composite score |
| Composite snapshot date | 2025-05-14 |
| Replay start | 2025-05-14 |
| Replay end | 2026-05-14 |
| Coverage window | 366 calendar days (1 year) |
| Trading days observed | **252** |
| Earliest series date | 2025-05-14 |
| Latest series date | 2026-05-14 |
| TOP_N_STRATEGY final cumulative return | **+45.3%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, INVESTABLE_VEHICLE, TOP_N_STRATEGY |
| Governs replay_supported? | No — bypassed by ALL replay |

### ARW — Replay 2 (Current Recommendation)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2026-05-20-TO-2026-05-26-US-SMALL-ALL-TOP20-WP05D-20260526-ALL2-US-SMALL-ALL` |
| Mode | CURRENT_RECOMMENDATION |
| Basket scope | US SMALL-cap ALL industries, Top-20 by composite score |
| Composite snapshot date | 2026-05-20 |
| Replay start | 2026-05-20 |
| Replay end | 2026-05-26 |
| Coverage window | 6 calendar days |
| Trading days observed | **4** |
| Earliest series date | 2026-05-20 |
| Latest series date | 2026-05-26 |
| TOP_N_STRATEGY cumulative return (through 2026-05-26) | **+4.0%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, INVESTABLE_VEHICLE, TOP_N_STRATEGY |
| Governs replay_supported? | **Yes** — active governing replay via symbol_tier |

---

### CIEN — Replay 1 (Historical)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-TECHNOLOGY-TOP20-RUN-WP05D-20260515-TECH1-US-MID-TECHNOLOGY` |
| Mode | HISTORICAL_VALIDATION |
| Basket scope | US MID-cap TECHNOLOGY, Top-20 by composite score |
| Composite snapshot date | 2025-05-14 |
| Replay start | 2025-05-14 |
| Replay end | 2026-05-14 |
| Coverage window | 366 calendar days (1 year) |
| Trading days observed | **252** |
| Earliest series date | 2025-05-14 |
| Latest series date | 2026-05-14 |
| TOP_N_STRATEGY final cumulative return | **+124.6%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, TOP_N_STRATEGY (894 total rows) |
| Governs replay_supported? | **Yes** — sole governing replay via industry_replay_evidence |

---

### CAH — Replay 1 (Historical)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2025-05-14-TO-2026-05-14-US-MID-HEALTHCARE-TOP20-RUN-WP05D-20260515-HEALTH1-US-MID-HEALTHCARE` |
| Mode | HISTORICAL_VALIDATION |
| Basket scope | US MID-cap HEALTHCARE, Top-20 by composite score |
| Composite snapshot date | 2025-05-14 |
| Replay start | 2025-05-14 |
| Replay end | 2026-05-14 |
| Coverage window | 366 calendar days (1 year) |
| Trading days observed | **252** |
| Earliest series date | 2025-05-14 |
| Latest series date | 2026-05-14 |
| TOP_N_STRATEGY final cumulative return | **+15.0%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, INVESTABLE_VEHICLE, TOP_N_STRATEGY (1008 total rows) |
| Governs replay_supported? | **Yes** — sole governing replay via industry_replay_evidence |

---

### ATLC — Replay 1 (Historical)

| Attribute | Value |
|-----------|-------|
| replay_id | `REPLAY-2025-05-14-TO-2026-05-14-US-MICRO-FINANCIAL_SERVICES-TOP20-RUN-WP05D-20260515-FIN1-US-MICRO-FINANCIAL_SERVICES` |
| Mode | HISTORICAL_VALIDATION |
| Basket scope | US MICRO-cap FINANCIAL SERVICES, Top-20 by composite score |
| Composite snapshot date | 2025-05-14 |
| Replay start | 2025-05-14 |
| Replay end | 2026-05-14 |
| Coverage window | 366 calendar days (1 year) |
| Trading days observed | **252** |
| Earliest series date | 2025-05-14 |
| Latest series date | 2026-05-14 |
| TOP_N_STRATEGY final cumulative return | **+13.8%** |
| Series types present | BENCHMARK, FULL_UNIVERSE, INVESTABLE_VEHICLE, TOP_N_STRATEGY (1008 total rows) |
| Governs replay_supported? | **Yes** — sole governing replay via industry_replay_evidence |

---

### PRG — No Replay Coverage

| Attribute | Value |
|-----------|-------|
| Symbol classification | US MICRO-cap INDUSTRIALS |
| Composite score (current) | 4.722 (VERY_BULLISH) |
| US-MICRO-INDUSTRIALS replay exists? | Yes (HISTORICAL_VALIDATION, snapshot 2025-05-14) |
| US-MICRO-ALL replay exists? | Yes (CURRENT_RECOMMENDATION, snapshot 2026-05-20) |
| PRG in top-20 at 2025-05-14 snapshot? | **No** |
| PRG in top-20 at 2026-05-20 snapshot? | **No** |
| Replay coverage window | None |
| Trading days observed | 0 |
| replay_supported | **False** |

PRG was evaluated for both available replays but did not place in the top-20 composite scorers for US MICRO-cap stocks at either snapshot date. The replay infrastructure is in place; PRG simply did not rank highly enough at the relevant dates.

---

## Coverage Window Comparison

```
Symbol  Start        End          Window      Mode(s)                 Basket Return
──────  ──────────   ──────────   ─────────   ──────────────────────  ─────────────
VRT     2025-05-14   2026-05-14   252 days    HISTORICAL              +66.7% (INDUS)
VRT     2026-05-20   2026-05-26   4 days      CURRENT_REC ← active    +4.7%  (ALL)
ARW     2025-05-14   2026-05-14   252 days    HISTORICAL              +45.3% (TECH)
ARW     2026-05-20   2026-05-26   4 days      CURRENT_REC ← active    +4.0%  (ALL)
CIEN    2025-05-14   2026-05-14   252 days    HISTORICAL ← active     +124.6% (TECH)
CAH     2025-05-14   2026-05-14   252 days    HISTORICAL ← active     +15.0% (HLTH)
ATLC    2025-05-14   2026-05-14   252 days    HISTORICAL ← active     +13.8% (FIN)
PRG     —            —            0 days      NONE                    —
```

**Note:** "Basket return" is the TOP_N_STRATEGY cumulative return for the entire basket, not the individual symbol's return. Individual symbol returns are not tracked in the performance series — only basket-level performance is.

---

## Structural Asymmetry Note

VRT and ARW have a critical asymmetry: their `replay_supported=True` is governed by 4-day CURRENT_RECOMMENDATION replays (2026-05-20 to 2026-05-26), even though 252-day HISTORICAL_VALIDATION replays also exist for their industry tiers. The historical replays are present in the data but bypassed by the ALL-industry routing logic.

CIEN, CAH, and ATLC have no CURRENT_RECOMMENDATION coverage — their support is based entirely on the 252-day historical window ending 2026-05-14.
