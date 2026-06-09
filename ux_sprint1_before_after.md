# UX Sprint 1 — Before / After Comparison

## UX-PA-01: KPI Strip Label

| | Before | After |
|---|---|---|
| KPI label for allocation score | "Legacy Alignment" | "Allocation Alignment" |
| Behavioral change | None | None |

---

## UX-PA-03: Page Section Order

### Before
1. Recommendations + Replay Alignment (row)
2. Security-Level Intelligence Overlay
3. Capital Rotation Advisor (hidden unless loaded)
4. Portfolio Action Pipeline (hidden unless loaded)

### After
1. Recommendations + Replay Alignment (row)
2. **Capital Rotation Advisor** (moved up)
3. **Portfolio Action Pipeline** (moved up)
4. Security-Level Intelligence Overlay (moved to bottom)

**Why**: CRA and PAP are actionable panels. Security Overlay is analytical/informational. Actionable content should appear before supporting analytical context.

---

## UX-PA-04: Multi-Dim Score Cards

### Before
```
[72]
Allocation Alignment
Moderate
░░░░░░░░░░████
```

### After
```
[72]
Allocation Alignment
Moderate
░░░░░░░░░░████
↓ View
```
Each card now has a "↓ View" scroll-to link targeting its logical page section.

---

## UX-PA-06: Blocked Rec Explainability

### Before
```
🔒 Operator Protected — not executable
[Full recommendation text…]
```

### After
```
🔒 Operator Protected — not executable
To unblock: remove DO_NOT_SELL policy on FBTC.
[Full recommendation text…]
```
```
⏸ Sell Last — deferred
To prioritize: remove SELL_LAST policy on FBTC.
```

---

## UX-PA-07: Deployable Cash Summary Card

### Before
```
$14,320
Deployable Cash
```

### After
```
$14,320
Deployable Cash
Excess above 3% mandate floor ⓘ
```
Hover tooltip: "Excess above 3% mandate floor. Full cash: $18,400. Floor reserve: $4,080. Deployable: $14,320."
