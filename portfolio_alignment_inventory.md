# Portfolio Alignment Page — Complete Section Inventory

Repository: security-intelligence-hub  
Audit Date: 2026-06-09  
Reference PAR: PAR-20260609-42A90186

## Page Sections in Visual Order

### 1. Upload Zone

**Type:** Action / Input  
**Content:** CSV upload drop zone; mandate selector (Concentrated Alpha, Balanced, etc.); "Analyze Portfolio" trigger  
**Data shown:** None until analysis completes  
**Operator action:** Trigger analysis by uploading portfolio CSV

---

### 2. KPI Strip (Run Summary)

**Type:** Dashboard KPIs  
**Content:** 6 cards

| Card | Value (live) | Type |
|---|---|---|
| Holdings | 81 | Diagnostic |
| Portfolio Value | $465K | Informational |
| Legacy Alignment | 41% | Ambiguous |
| Recommendations | 7 Actions / 3 Blocked / 25 Anchors / 1 Narrative / 1 Explain | Mixed |
| Concentration | DIVERSIFIED | Informational |
| Format | CSV source format | Diagnostic |

**Issues:** "Legacy Alignment 41%" carries the label "Legacy" — unclear to any operator what this means or whether it should be higher or lower.

---

### 3. Multi-Dimensional Scorecards

**Type:** Score summary  
**Content:** 4 gauge-style score cards

| Score | Value | Meaning |
|---|---|---|
| Allocation Alignment | ~41 | Distance from target allocations |
| Portfolio Quality | unknown | Concentration + signal quality |
| Implementation Quality | unknown | Vehicle suitability |
| Replay Alignment | 58 | Replay-supported coverage |

**Issues:** Four scores shown but only one (Allocation Alignment) is clearly actionable. The relationship between these scores and the recommendation list is not explained.

---

### 4. Portfolio Mandate Assessment Panel

**Type:** Informational / Context  
**Content:** Mandate type badge; intentional asymmetry state; conviction score; evidence signals  
**Current values:** Mandate = CONCENTRATED_ALPHA; Asymmetry = HIGH_CONVICTION_ASYMMETRY  
**Issues:** "Intentional Asymmetry" and "Conviction Score 87%" have no linked explanation of what would change if the score were lower.

---

### 5. Capital Deployment Queue

**Type:** Actionable decision surface  
**Content:** Ranked list of 32 deployment candidates; tier summaries (T1/T2/T3); cash context  
**Key metric:** Deployable = $21,711.59 (4.67% excess above 7% mandate floor)  
**Action:** Operator selects which symbols to deploy capital into  
**Issues:** Deployable cash ($21,711) is prominently shown but the page does not show why cash is elevated or whether that is good/bad.

---

### 6. Capital Deployment Plan (on demand)

**Type:** Actionable planning artifact  
**Content:** Tiered allocation recommendations based on deployable cash  
**Action:** Used to confirm allocation amounts before execution  

---

### 7. Dislocation Watchlist

**Type:** Diagnostic / Monitoring  
**Content:** Dislocation detections, tier classifications, evidence links  
**Issues:** Only visible when dislocation events exist; otherwise hidden. Operators may not know it exists.

---

### 8. Current vs Target Allocation Map

**Type:** Diagnostic alignment table  
**Content:** 40 allocation nodes; actual vs target percentages; drift in pp; severity; urgency  
**Issues:** 40 nodes of data. The most overweight (EQUITIES +4.86pp above max, INTL +6.1pp) are buried in a long table. No quick scan path.

---

### 9. Concentration Risk

**Type:** Diagnostic governance  
**Content:** HHI concentration score; top 1/5/10 holding percentages; concentration tier badge  
**Current:** DIVERSIFIED; top1=SBS ~3.83%  
**Issues:** Standalone panel with no recommended action — operator sees "DIVERSIFIED" and moves on without knowing if that's relative to the mandate target.

---

### 10. Prioritized Recommendations (Allocation & Portfolio Observations)

**Type:** Mixed — Actions + Intelligence  
**Content (34 total):**
- 7 ACTION cards (4 EXECUTABLE, 3 BLOCKED/DEFERRED)
- 2 OBSERVATION cards (STRATEGIC_RETAIN_SIGNAL)
- 4 NARRATIVE cards (3 retain + 1 portfolio assessment)
- 21 EXPLAINABILITY cards (20 conviction + 1 replay context)

**Lane structure (PRA-IMPL-03):**
- Actions lane (expanded)
- Blocked/Deferred lane (expanded)
- Conviction Anchors (collapsed, 25 items including Top 5 visible — PRA-IMPL-06)
- Portfolio Narrative (collapsed)
- Explainability (collapsed)

**Issues:** INCREASE_UNDERWEIGHT recs (Build US Large -6.2%) appear alongside REDUCE recs (Reduce INTL +6.1%) — operator may not understand that both can be simultaneously valid. BLOCKED recommendations appear but the note only says BLOCKED, not what would unblock them.

---

### 11. Replay Alignment & Geography

**Type:** Diagnostic / Evidence  
**Content:** Replay score (58.2/100); geographic breakdown; coverage/quality components  
**Issues:** 58/100 is hard to interpret without context. Is that good? The page shows components (coverage 30.5/60, quality 27.7/40) but doesn't explain what actions improve it.

---

### 12. Security-Level Intelligence Overlay

**Type:** Diagnostic table + drill-down  
**Content:** Per-holding signal dashboard — ESS, Zacks, Danelfin, composite, replay support, opportunity flag, conviction tier, execution state  
**Issues:** Enormous table. 81 holdings. No primary-task affordance. This is the deepest diagnostic layer but sits in the middle of the page. Operator must scroll past it to reach PAP.

---

### 13. Capital Rotation Advisor (CRA)

**Type:** Actionable proposal  
**Content:** Capital pool construction; rotation targets; funding sources; tax annotations; Include/Skip controls  
**Issues:** Auto-loads but if the server hasn't generated a proposal yet, shows empty/loading. No visual indicator that this is the most operationally significant section on the page.

---

### 14. Portfolio Action Pipeline (PAP)

**Type:** Actionable structured workflow  
**Content:** 5 categories:
- Cat 1: Signal Deterioration
- Cat 2: Strategic Exit
- Cat 3: Allocation Reduction (with FVI overlays — PRA-IMPL-05)
- Cat 4: Funding Sources (with FVI overlays)
- Cat 5: Policy-Suppressed Actions

**Issues:** This is arguably the most operationally useful section (direct execution guidance) but it appears at the very bottom of the page after 13 other sections.

---

## Additional Components

### Tax Position Panel (sidebar / collapsible)

**Content:** Tax bucket classifications; cost basis; unrealized gain/loss; LT threshold proximity  
**Issues:** Excellent advisory data but collapsed by default and located in the left sidebar — easy to miss.

### Operator Policy Panel (sidebar / collapsible)

**Content:** Active policies (DO_NOT_SELL: TSLA, SELL_LAST: DODFX); policy management interface  
**Issues:** Policy state is globally important (affects all recommendations) but displayed in a sidebar panel operator may not notice.
