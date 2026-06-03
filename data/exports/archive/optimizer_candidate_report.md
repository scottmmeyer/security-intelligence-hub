# Optimizer Candidate Report

**Generated:** 2026-05-30T15:53:23Z
**Mandate:** Concentrated Alpha
**Portfolio:** 472,220 | 81 holdings | Date: 2026-05-30
**Run ID:** PAR-20260530-7B861236

**Cross-rec conflicts detected:** T1=6 | T2=1 | T3=6

### Conflict Summary
- **T1** [🔴]: Build EQUITIES.US.LARGE using VOO worsens existing overweight at EQUITIES.INTERNATIONAL.LARGE    `severity=HIGH | vehicle=VOO`
- **T1** [🔴]: Build EQUITIES.US.LARGE using IVV worsens existing overweight at EQUITIES.INTERNATIONAL.LARGE    `severity=HIGH | vehicle=IVV`
- **T1** [🔴]: Build EQUITIES.US.LARGE using SPY worsens existing overweight at EQUITIES.INTERNATIONAL.LARGE    `severity=HIGH | vehicle=SPY`
- **T1** [🔴]: Build EQUITIES.US.MEGA.EXTENDED_MEGA using VTI worsens existing overweight at EQUITIES.INTERNATIONAL.LARGE    `severity=HIGH | vehicle=VTI`
- **T1** [🔴]: Build EQUITIES.US.MEGA.EXTENDED_MEGA using SCHB worsens existing overweight at EQUITIES.INTERNATIONAL.LARGE    `severity=HIGH | vehicle=SCHB`
- **T1** [🔴]: Build EQUITIES.US.MEGA.EXTENDED_MEGA using VOO worsens existing overweight at EQUITIES.INTERNATIONAL.LARGE    `severity=HIGH | vehicle=VOO`
- **T2** [🟡]: Vehicle VOO appears in both 'EQUITIES.US.LARGE' and 'EQUITIES.US.MEGA.EXTENDED_MEGA' Build recs    `severity=LOW | vehicle=VOO`
- **T3** [🔴]: Rec 'EQUITIES.US.LARGE' has engine severity=MODERATE but mandate urgency=INFORMATIONAL — contradictory output    `severity=HIGH | vehicle=None`
- **T3** [🔴]: Rec 'EQUITIES.INTERNATIONAL.LARGE' has engine severity=MODERATE but mandate urgency=INFORMATIONAL — contradictory output    `severity=HIGH | vehicle=None`
- **T3** [🔴]: Rec 'EQUITIES.US.MEGA.EXTENDED_MEGA' has engine severity=MODERATE but mandate urgency=INFORMATIONAL — contradictory output    `severity=HIGH | vehicle=None`
- **T3** [🔴]: Rec 'EQUITIES.US.MEGA.HYPER_MEGA' has engine severity=MODERATE but mandate urgency=INFORMATIONAL — contradictory output    `severity=HIGH | vehicle=None`
- **T3** [🔴]: Rec 'EQUITIES.US.LARGE' has engine severity=MODERATE but mandate urgency=INFORMATIONAL — contradictory output    `severity=HIGH | vehicle=None`
- **T3** [🔴]: Rec 'EQUITIES.INTERNATIONAL' has engine severity=MODERATE but mandate urgency=INFORMATIONAL — contradictory output    `severity=HIGH | vehicle=None`

---

## Strategic portfolio assessment: strategically sound with optimization opportunities
**Rec ID:** `REC-C89EEF6E`  **Type:** PORTFOLIO_CONSTRUCTION_NARRATIVE  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## Build EQUITIES.US.LARGE allocation (-7.3% drift)
**Rec ID:** `REC-04ADB715`  **Type:** INCREASE_UNDERWEIGHT  **Node:** `EQUITIES.US.LARGE`  **Severity:** MODERATE  **Mandate urgency:** INFORMATIONAL  **Mandate label:** INTENTIONAL_UNDERWEIGHT
**Optimizer decision:** `MANDATE_BLOCKED`
**Conflicts:** T1:VOO | T1:IVV | T1:SPY | T2:VOO | T3:None

| Candidate | Type | Target Node | PIS | Mandate Status | ETF Gate | NCS | Suit | Composite | Replay | STI Tier | Trim | Helps/Node | Conflict Flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **DELL** | SECURITY | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | NA | 100.0% | NA | 4.500 | ✓ | HIGH_CONVICTION_ANCHOR | 0.1 | EQUITIES.US.LARGE |  |
| **LRCX** | SECURITY | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | NA | 100.0% | NA | 4.500 | ✓ | HIGH_CONVICTION_ANCHOR | 0.1 | EQUITIES.US.LARGE |  |
| **PLTR** | SECURITY | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | NA | 100.0% | NA | 3.286 |  | TACTICAL_GROWTH_CANDIDATE | 3.4 | EQUITIES.US.LARGE |  |
| **VRT** | SECURITY | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | NA | 100.0% | NA | 4.556 | ✓ | CORE_CONVICTION_LEADER | 0.3 | EQUITIES.US.LARGE |  |
| **VOO** | ETF | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True] | 0.0% | LOW | — |  | NA | 0.0 | EQUITIES.US.LARGE | OVERWEIGHT_NODE_WORSENED⚠ worsens OW |
| **IVV** | ETF | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True] | 0.0% | LOW | — |  | NA | 0.0 | EQUITIES.US.LARGE | OVERWEIGHT_NODE_WORSENED⚠ worsens OW |
| **SPY** | ETF | `EQUITIES.US.LARGE` | **0.0** | MANDATE_BLOCKED | FAIL [suitability=LOW; NCS=0.0%<10.0%; worsens_overweight=True] | 0.0% | LOW | — |  | NA | 0.0 | EQUITIES.US.LARGE | OVERWEIGHT_NODE_WORSENED⚠ worsens OW |

---

## Reduce EQUITIES.INTERNATIONAL.LARGE allocation (+4.2% drift)
**Rec ID:** `REC-3F564454`  **Type:** REDUCE_OVERWEIGHT  **Node:** `EQUITIES.INTERNATIONAL.LARGE`  **Severity:** MODERATE  **Mandate urgency:** INFORMATIONAL  **Mandate label:** INTENTIONAL_OVERWEIGHT
**Optimizer decision:** `REDUCE_COHERENT`
**Conflicts:** T1:VOO | T1:IVV | T1:SPY | T1:VTI | T1:SCHB | T1:VOO | T3:None

_No candidates evaluated for this recommendation type._

---

## Build EQUITIES.US.MEGA.EXTENDED_MEGA allocation (-4.1% drift)
**Rec ID:** `REC-18337245`  **Type:** INCREASE_UNDERWEIGHT  **Node:** `EQUITIES.US.MEGA.EXTENDED_MEGA`  **Severity:** MODERATE  **Mandate urgency:** INFORMATIONAL  **Mandate label:** INTENTIONAL_UNDERWEIGHT
**Optimizer decision:** `MANDATE_BLOCKED`
**Conflicts:** T1:VTI | T1:SCHB | T1:VOO | T2:VOO | T3:None

| Candidate | Type | Target Node | PIS | Mandate Status | ETF Gate | NCS | Suit | Composite | Replay | STI Tier | Trim | Helps/Node | Conflict Flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **VTI** | ETF | `EQUITIES.US.MEGA.EXTENDED_MEGA` | **0.0** | MANDATE_BLOCKED | FAIL [worsens_overweight=True] | 16.6% | MEDIUM | — |  | NA | 0.0 | EQUITIES.US.MEGA.EXTENDED_MEGA | OVERWEIGHT_NODE_WORSENED⚠ worsens OW |
| **SCHB** | ETF | `EQUITIES.US.MEGA.EXTENDED_MEGA` | **0.0** | MANDATE_BLOCKED | FAIL [worsens_overweight=True] | 16.6% | MEDIUM | — |  | NA | 0.0 | EQUITIES.US.MEGA.EXTENDED_MEGA | OVERWEIGHT_NODE_WORSENED⚠ worsens OW |
| **VOO** | ETF | `EQUITIES.US.MEGA.EXTENDED_MEGA` | **0.0** | MANDATE_BLOCKED | FAIL [suitability=LOW; NCS=7.0%<10.0%; worsens_overweight=True] | 7.0% | LOW | — |  | NA | 0.0 | EQUITIES.US.MEGA.EXTENDED_MEGA | OVERWEIGHT_NODE_WORSENED⚠ worsens OW |

---

## Reduce EQUITIES.US.MEGA.HYPER_MEGA allocation (+3.7% drift)
**Rec ID:** `REC-4E732B66`  **Type:** REDUCE_OVERWEIGHT  **Node:** `EQUITIES.US.MEGA.HYPER_MEGA`  **Severity:** MODERATE  **Mandate urgency:** INFORMATIONAL  **Mandate label:** INTENTIONAL_OVERWEIGHT
**Optimizer decision:** `REDUCE_COHERENT`
**Conflicts:** T3:None

_No candidates evaluated for this recommendation type._

---

## Replay-supported opportunity in EQUITIES.US.LARGE (underweight -7.3%)
**Rec ID:** `REC-ED31D83F`  **Type:** IMPROVE_REPLAY_ALIGNMENT  **Node:** `EQUITIES.US.LARGE`  **Severity:** MODERATE  **Mandate urgency:** INFORMATIONAL  **Mandate label:** INTENTIONAL_UNDERWEIGHT
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## Reduce EQUITIES.INTERNATIONAL allocation (+6.8% drift)
**Rec ID:** `REC-FDAE7FA1`  **Type:** REDUCE_OVERWEIGHT  **Node:** `EQUITIES.INTERNATIONAL`  **Severity:** MODERATE  **Mandate urgency:** INFORMATIONAL  **Mandate label:** INTENTIONAL_OVERWEIGHT
**Optimizer decision:** `REDUCE_COHERENT`
**Conflicts:** T3:None

_No candidates evaluated for this recommendation type._

---

## SANM: High Conviction Retain
**Rec ID:** `REC-4059BC0C`  **Type:** STRATEGIC_RETAIN_SIGNAL  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## PSX: High Conviction Retain
**Rec ID:** `REC-741657EB`  **Type:** STRATEGIC_RETAIN_SIGNAL  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## MU: High Conviction Retain — retain signal
**Rec ID:** `REC-13599529`  **Type:** STRATEGIC_RETAIN_NARRATIVE  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## VRT: High Conviction Retain — retain signal
**Rec ID:** `REC-518A1615`  **Type:** STRATEGIC_RETAIN_NARRATIVE  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## CVE: High Conviction Retain — retain signal
**Rec ID:** `REC-B2B63DE6`  **Type:** STRATEGIC_RETAIN_NARRATIVE  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## Replay alignment: 22.9/100 (coverage=22.9/60, quality=0.0/40)
**Rec ID:** `REC-F2BE2EFF`  **Type:** REPLAY_ALIGNMENT_CONTEXT  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## CVE: High Conviction Retain | tier=CORE_CONVICTION_LEADER | composite=4.889
**Rec ID:** `REC-A0D758F6`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## ARW: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.889
**Rec ID:** `REC-8817AE14`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## SNX: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.778
**Rec ID:** `REC-E58FDD84`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## ATLC: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE | composite=4.778
**Rec ID:** `REC-E6F4D4E0`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## MU: High Conviction Retain | tier=CORE_CONVICTION_LEADER | composite=4.722
**Rec ID:** `REC-719353EA`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## PSX: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.722
**Rec ID:** `REC-C576FE87`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## ASML: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.722
**Rec ID:** `REC-6922E518`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## PRG: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE | composite=4.722
**Rec ID:** `REC-B032A6F3`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## AEIS: High Conviction Retain | tier=CORE_CONVICTION_LEADER | composite=4.714
**Rec ID:** `REC-CB196ED9`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## SANM: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.714
**Rec ID:** `REC-568F5E71`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## STNG: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.714
**Rec ID:** `REC-7251C57D`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## SIMO: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.571
**Rec ID:** `REC-A207F7FA`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## CIEN: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE | composite=4.571
**Rec ID:** `REC-4ABDD1D2`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## VRT: High Conviction Retain | tier=CORE_CONVICTION_LEADER | composite=4.556
**Rec ID:** `REC-F0418C7D`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## CAH: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE | composite=4.556
**Rec ID:** `REC-5D4EFC20`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## DELL: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.500
**Rec ID:** `REC-E2708405`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## LRCX: High Conviction Retain | tier=HIGH_CONVICTION_ANCHOR | composite=4.500
**Rec ID:** `REC-746044F2`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## AVT: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE | composite=4.500
**Rec ID:** `REC-A53382F0`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## TSM: High Conviction Retain | tier=CORE_CONVICTION_LEADER | composite=4.444
**Rec ID:** `REC-242C836F`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## NUE: Tactical Growth | tier=TACTICAL_GROWTH_CANDIDATE | composite=4.286
**Rec ID:** `REC-2A4E3FE0`  **Type:** CONVICTION_EXPLAINABILITY_CARD  **Node:** `None`  **Severity:** LOW  **Mandate urgency:** MODERATE  **Mandate label:** 
**Optimizer decision:** `NOT_APPLICABLE`

_No candidates evaluated for this recommendation type._

---

## Summary Statistics
- **MANDATE_BLOCKED**: 2 rec(s)
- **Mandate blocked**: 2 rec(s)