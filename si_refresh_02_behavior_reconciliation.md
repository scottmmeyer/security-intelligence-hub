# SI-REFRESH-02 Behavior Reconciliation

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

## Core Question

Does Yahoo's `eps_growth_5yr = 0% coverage` produce FRESH or FRESH_PARTIAL under the current implementation?

## Definitive Answer: **FRESH**

### Evidence

1. `eps_growth_5yr` is classified as a supplemental field, not a primary field.
2. `degraded_fields` only includes primary fields with 0% coverage.
3. Yahoo primary fields today: price_target (98.1%), analyst_count (98.1%), current_price (99.9%) — all above 0%.
4. `degraded_fields = []` → no FRESH_PARTIAL trigger.
5. `coverage_pct = 99.9%` → above 95% threshold → no FRESH_PARTIAL trigger.
6. `badge_state = FRESH`

### What IS shown for Yahoo

The `zero_coverage_fields` list includes `eps_growth_5yr`. In `_renderSignalPills()`, this triggers the advisory path:

```javascript
} else if (info.zero_coverage_fields && info.zero_coverage_fields.length > 0) {
    const fields = info.zero_coverage_fields.join(", ");
    degradedHtml = `<span class="pill-degraded-advisory">0% today: ${fields}</span>`;
}
```

So the operator sees: Yahoo · 2026-06-09 · (fresh) · 696/697 rows · 99.9% · [advisory: 0% today: eps_growth_5yr]

The badge dot is **green** (FRESH), not orange (FRESH_PARTIAL).

## Comparison Against Original Certification

The certification document (si_refresh_02_certification.md) at Q2 states:

> "badge_state: FRESH (eps_growth_5yr is non-primary — does not trigger FRESH_PARTIAL)"

**This is correct.** The certification accurately describes the behavior.

However, the same certification also says:

> "The operator can now see the gap. Before SI-REFRESH-02, it was completely invisible."

**This is also correct.** The advisory tag makes the gap visible. The badge remains FRESH per design.

## Badge State Matrix — Actual vs Documented

| Condition | Documented Behavior | Actual Behavior | Match |
|---|---|---|---|
| coverage ≥ 95% + no primary degraded | FRESH | FRESH | ✓ |
| coverage < 95% | FRESH_PARTIAL | FRESH_PARTIAL | ✓ |
| primary field at 0% | FRESH_PARTIAL | FRESH_PARTIAL | ✓ |
| non-primary field at 0% (eps_growth_5yr) | FRESH + advisory | FRESH + advisory | ✓ |
| no today rows | STALE | STALE | ✓ |
| _running=True | badge shows REFRESHING | **badge still shows FRESH/STALE** | ✗ (known gap) |

## Discrepancy Identified

The REFRESHING badge state is documented as a recognized open item. The `_running` flag is handled separately in the UI (disabling the button and showing a message), but `badge_state` never takes the value "REFRESHING" because `_signal_status()` does not set it. This is consistent with the certification which lists it in the "Remaining refresh trust issues" table as OPEN.
