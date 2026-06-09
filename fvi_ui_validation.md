# FVI UI Validation

Repository: security-intelligence-hub  
Date: 2026-06-09

## UI Surfaces Confirmed

### PAP Cat3 (Allocation Reduction) Table

New column "FVI" shows:
- FVI tier badge (color-coded: ELITE=green, HIGH=blue, MEDIUM=orange, LOW=red)
- Peer group name in badge title attribute (tooltip)
- Retain advisory indicator: "↑ Retain preferred" (green) or "↓ Reduction candidate" (red)
- Advisory text in detail row

Example row for DODFX:
```
Symbol: DODFX
FVI: [HIGH] Foreign Large Value · ↑ Retain preferred
```

Example row for FIGFX (if present):
```
Symbol: FIGFX
FVI: [MEDIUM] Foreign Large Growth · ↓ Reduction candidate
```

Example row for VOO (index ETF in reduction candidate):
```
Symbol: VOO
FVI: [ELITE] US Large Blend ETF · ↑ Retain preferred
```

### PAP Cat4 (Funding Sources) Table

New column "FVI" shows:
- FVI tier badge only (no detail text in this view — keeps the table compact)
- Tooltip shows peer group on hover

### Symbols Without FVI Data

For symbols not in the FVI registry (individual equities: TSLA, MU, VRT, etc.), the FVI column renders empty — no badge, no label. This is correct graceful degradation.

### CSS Classes

| Tier | Class | Color |
|---|---|---|
| ELITE | fvi-ELITE | Green (#1a7c4f) |
| HIGH | fvi-HIGH | Blue (#1a5c8a) |
| MEDIUM | fvi-MEDIUM | Orange (#e07300) |
| LOW | fvi-LOW | Red (#c0392b) |
| WEAK | fvi-WEAK | Gray (#666) |

### Numerical Scores

Per Step 6 requirement: numerical scores are NOT shown by default in the PAP table. The FVI tier badge (ELITE/HIGH/MEDIUM/LOW) is the primary display. This prevents over-precision on advisory estimates.

Scores are available in the `fvi_data` field of the analysis result for any future expanded detail view.
