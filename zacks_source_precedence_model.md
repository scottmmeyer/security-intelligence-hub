# Zacks Source Precedence Model

**Date:** 2026-06-10

---

## Required Precedence

### Tier 1: Direct Zacks Fetch (Authoritative)

**Source:** `data/signals/zacks/latest_zacks.csv`  
**Fetched by:** `src/scoring/fetch_zacks_scores.py` via scraper  
**Conditions for use:** Symbol has a row with `sourced_date` within acceptable freshness window (e.g., ≤ 7 days)  
**Display label:** `Zacks Direct [YYYY-MM-DD]`  
**Badge state:** FRESH (if today), STALE (if older)

### Tier 2: Fidelity ESS Embedded Zacks (Fallback)

**Source:** `ess_zacks_rating` in base universe (extracted from Fidelity ESS `"Zacks Investment Research"` column)  
**Conditions for use:** Only when Tier 1 is absent or stale  
**Display label:** `Zacks (Fidelity ESS fallback) [source date unknown]` or `Zacks (Fidelity, {ess_date})`  
**Badge state:** Must NOT produce FRESH. Correct state: FALLBACK or STALE_WITH_FALLBACK  
**Scale note:** Fidelity ESS Zacks is on 1–5 scale (1=Sell, 5=Buy) — inverted from direct Zacks. Current conversion `6.0 - ess_zacks_raw` is correct.

### Tier 3: No Data / Last Resort

**Condition:** Neither Tier 1 nor Tier 2 available  
**Score used:** 3.0 (NEUTRAL) per current fallback  
**Display label:** `Zacks (unavailable) — neutral assumed`  
**Badge state:** NO_DATA

---

## Current vs Correct Behavior

### Composite Score (analytical_universe)

| Scenario | Current | Correct |
|---|---|---|
| Direct Zacks available | Uses direct — ✓ | Uses direct |
| Direct missing, ESS Zacks available | Uses ESS fallback — ✓ (silently) | Uses ESS fallback — with provenance tag |
| Neither available | Uses 3.0 neutral — ✓ | Same |

**Gap:** No provenance tag stored. When ESS fallback is used, `zacks_rating` in analytical_universe is empty and `composite_score` reflects the fallback silently. A companion field `zacks_source` should be added: `"DIRECT"`, `"FIDELITY_ESS_FALLBACK"`, or `"DEFAULT_NEUTRAL"`.

### Freshness Badge

| Scenario | Current | Correct |
|---|---|---|
| Direct Zacks fetched today | FRESH ✓ | FRESH |
| Direct Zacks from yesterday | STALE ✓ | STALE |
| Fidelity ESS Zacks only | Badge unaffected (reads latest_zacks.csv) ✓ | Same — Fidelity ESS must not produce FRESH badge |

**Verdict:** Badge logic is CORRECT. Fidelity ESS Zacks cannot produce a FRESH badge.

### Per-Symbol Date Display (DIL / Evidence List)

| Scenario | Current | Correct |
|---|---|---|
| Direct Zacks fetched today | Shows today's date — ✓ | Show per-symbol `sourced_date` from latest_zacks.csv |
| Direct Zacks fetched 3 weeks ago | Shows today's max date — ✗ | Show per-symbol `sourced_date` (e.g., 2026-05-21) |
| Fidelity ESS fallback used | Shows `latest_zacks.csv` max date — ✗ | Show "Fidelity ESS fallback, date unknown" |

**Gap:** DIL evidence labels should use per-symbol Zacks `sourced_date` from the overlay, not the global max date from `signal_source_metadata`.

### Badge FRESH vs FRESH with Coverage

| Scenario | Current | Correct |
|---|---|---|
| 5% of symbols fetched today, 95% from weeks ago | STALE (max date not today) — ✓ | Same |
| 100% fetched today but coverage < 95% rows | FRESH_PARTIAL ✓ | Same |
| Any symbol fetched today → max date = today | Could flip to FRESH with low actual coverage | Per-symbol staleness matters more than max date |

---

## Required Fields to Add for Full Source Governance

| Location | Current | Required Addition |
|---|---|---|
| `analytical_universe.csv` | `zacks_rating` (numeric, no source) | `zacks_source` enum: DIRECT / FIDELITY_ESS_FALLBACK / DEFAULT_NEUTRAL |
| `analytical_universe.csv` | No per-symbol date | `zacks_sourced_date` (from `latest_zacks.csv` row for this symbol) |
| Security overlay | `zacks_rating` (no source) | `zacks_source` |
| DIL evidence list | `[Zacks, max_date]` | `[Zacks Direct, {per-symbol date}]` or `[Fidelity ESS fallback, date unknown]` |
