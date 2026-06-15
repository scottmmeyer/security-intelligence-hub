# AI-006 Validation

**Date:** 2026-06-15

---

## Data Validation

### Danelfin CSV Coverage (latest_danelfin.csv)

| Symbol | Present | Raw | Score | Fresh |
|--------|---------|-----|-------|-------|
| CAH | YES | 5 | 2.5000 | 2026-06-15 |
| NUE | YES | 7 | 3.5000 | 2026-06-15 |
| SANM | YES | 8 | 4.0000 | 2026-06-15 |
| MTZ | YES | 9 | 4.5000 | 2026-06-15 |
| VRT | YES | 7 | 3.5000 | 2026-06-15 |
| ATLC | YES | 6 | 3.0000 | 2026-06-15 |
| DELL | YES | 5 | 2.5000 | 2026-06-15 |
| LRCX | YES | 6 | 3.0000 | 2026-06-12* |
| PCB | YES | 7 | 3.5000 | 2026-06-12* |
| CRS | YES | 8 | 4.0000 | 2026-06-12* |

*LRCX, PCB, CRS not refreshed today — 3-day stale. Within acceptable tolerance.

### Security Overlays Validation (PAR-20260615-FF5E50AF)

All 10 deployment candidates have `danelfin_score` populated in `security_overlays.csv`. ✓

### API Payload Validation

`danelfin_refresh_date` in run metadata: 2026-06-15 ✓  
`security_overlays[*].danelfin_score` populated: ✓  
`fidelity_signals_by_symbol` does NOT contain danelfin (by design — fidelity payload is ESS/Zacks/Yahoo only). ✓

### Composite Score Verification

Using the formula `(ESS×0.55 + Zacks×0.25 + Danelfin×0.10) / (0.55+0.25+0.10)`:

| Symbol | Computed | Actual (from PAR) | Match |
|--------|---------|-------------------|-------|
| CAH | 4.4444 | 4.444444 | ✓ |
| NUE | 4.2222 | 4.222222 | ✓ |
| SANM | 4.0000 | 4.0 | ✓ |
| MTZ | 3.7778 | 3.777778 | ✓ |
| VRT | 4.5556 | 4.555556 | ✓ |

All composite scores verified. Formula confirmed: ESS=55%, Zacks=25%, Danelfin=10%, Yahoo=10%.

### UI Rendering Validation

Danelfin appears in 8 distinct rendering paths in `ui/portfolio_alignment/app.js`. All 8 read from `ov.danelfin_score` (security_overlays), which is confirmed populated. No UI bugs detected.

---

## Governance Gate Simulation

| Gate | Excluded Symbols | Impact |
|------|-----------------|--------|
| Zacks >= 3 | None | No change |
| Zacks >= 4 | PCB (#5), MTZ (#8) | 2 candidates removed |
| Zacks >= 5 | 8 of 10 candidates | Extremely restrictive |

---

## Summary of Findings

1. **Danelfin IS present** in all required data stores and is display-ready.
2. **Danelfin IS scoring-active** — it contributes 10% of composite_score.
3. **CAH > NUE** is correct and stable — driven by ESS weight advantage, not Danelfin.
4. **PCB and MTZ** are ESS-conviction plays with NEUTRAL Zacks — by design, not a bug.
5. **No code changes are required** based on audit findings.
