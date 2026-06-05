# Company Snapshot FMP Compatibility Design — Phase 8.0B.X.2

## Objective
Ensure the Company Snapshot card layout is designed so future FMP fundamental metrics can be inserted beneath it without requiring structural refactoring.

## Target Future Layout (Phase 8.0B.1C+)

```
┌────────────────────────────────────────────────┐
│ COMPANY SNAPSHOT                               │
│ [AI INFRASTRUCTURE] [DATA CENTER]              │
│                                                │
│ Company      Vertiv Holdings Co                │
│ Headquarters Westerville, OH, USA              │
│ Sector       Industrials                       │
│ Industry     Electrical Equipment & Parts      │
│ What They Do Manufactures power, cooling, and  │
│              digital infrastructure systems... │
│ Why It Matters Benefits from AI data-center    │
│              buildout and grid modernization.  │
│ Country      United States                     │
│ Cap Tier     [LARGE]                           │
├────────────────────────────────────────────────┤
│ FUNDAMENTAL SNAPSHOT    (Phase 8.0B.1C)        │
│                                                │
│ EV/EBITDA   18.4x    ROE    32.1%             │
│ Rev Growth  +14.2%   ROIC   21.7%             │
│ Earn Surp   Beat (3/4 qtrs)                    │
├────────────────────────────────────────────────┤
│ SIGNAL PROFILE          (existing)             │
│                                                │
│ Composite     92        Zacks  1               │
│ ESS           Strong    Danelfin  9            │
├────────────────────────────────────────────────┤
│ CW-DAS BREAKDOWN        (existing)             │
└────────────────────────────────────────────────┘
```

## Spacing and Structural Requirements

### Company Snapshot Container

Current CSS:
```css
.dq-company-snapshot {
  margin-top: 12px;
  padding: 10px 14px;
  background: #f9f6f0;
  border: 1px solid var(--border);
  border-radius: 8px;
}
```

No structural changes needed. The container is already self-contained.

### Fundamental Snapshot (future)

Will be a sibling element rendered AFTER `.dq-company-snapshot` in the card expansion HTML:

```html
${_dqCompanySnapshotHtml(sym, _securityMetadata)}
${_dqFundamentalSnapshotHtml(sym, _fmpData)}   <!-- Phase 8.0B.1C -->
${_dqSignalProfileHtml(sym, overlays)}           <!-- existing -->
${_dqBreakdownHtml(sym, ...)}                    <!-- existing -->
```

**No refactoring required.** The insertion point is simply after the Company Snapshot block.

### CSS Addition Needed (Phase 8.0B.1C)

```css
.dq-fundamental-snapshot {
  margin-top: 8px;
  padding: 10px 14px;
  background: #f0f4f9;      /* slightly cooler tone than company snapshot */
  border: 1px solid var(--border);
  border-radius: 8px;
}
```

Color differentiation:
- Company Snapshot: warm background (`#f9f6f0`) — identity / context
- Fundamental Snapshot: cool background (`#f0f4f9`) — quantitative data
- Signal Profile: neutral (`var(--card-bg)`) — signal output

## FMP Field Mapping (Pre-design)

| Display Label | FMP Field | Phase |
|---------------|-----------|-------|
| EV/EBITDA | `evToEBITDATTM` | 8.0B.1C |
| ROE | `returnOnEquityTTM` | 8.0B.1C |
| ROIC | `returnOnInvestedCapitalTTM` | 8.0B.1C |
| Rev Growth | `growthRevenue` (income_growth) | 8.0B.1C |
| Earnings Surprise | Beat/Miss streak (earnings_surprises) | 8.0B.1C |

All FMP fields are already fetched in Phase 8.0B.1A.1 and stored in `data/signals/fmp/`.
The Phase 8.0B.1C work is purely display — reading existing FMP data into UI.

## Section Ordering Rationale

```
Company Snapshot → "Who is this company?"
Fundamental Snapshot → "How is the business performing?"
Signal Profile → "What do the signals say?"
CW-DAS Breakdown → "How does this factor into my allocation?"
```

This ordering follows the natural operator thought process: context → fundamentals → signals → action.

## No Changes Required Now

Phase 8.0B.X.2 does not need to modify the insertion order or wrapper structure.
The layout is already compatible. Future phases simply add sibling elements.

## Verdict: COMPATIBLE — No structural changes required
The current card expansion architecture accommodates future Fundamental Snapshot insertion as a drop-in sibling block.
