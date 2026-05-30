# Security vs ETF Decision Framework

**Phase 7.3 — Architecture Design**
**Document type:** Decision framework specification
**Based on:** Phase 7.2 live audit data + portfolio holdings as of 2026-05-30

---

## 1. The Core Question

When the allocation engine identifies an underweight node, it must decide:

**Option A — Individual Security**
> Add to (or initiate) a position in a specific security that lives in the
> target node, scored by composite/ESS/replay/STI, with known concentration impact.

**Option B — Broad ETF**
> Buy an index-tracking ETF mapped to the target node in the vehicle registry,
> providing diversified exposure at the cost of off-target leakage.

The current architecture defaults unconditionally to Option B.
This framework defines when each is correct.

---

## 2. Evaluation Dimensions

For any candidate (security or ETF) being considered for a target node, the
engine must evaluate seven dimensions:

### D1 — Node Coverage Precision
*What fraction of the candidate's effective exposure actually lands in the
target node, without leaking into already-overweight nodes?*

- **Pure direct security** in target node: 100% precision
- **ETF with leakage**: precision = (target_node_weight / total_weight)
- **Penalty**: Off-target weight landing in an overweight node is subtracted
  from coverage score using the node's current drift severity as a multiplier.

```
Node Coverage Score (NCS) = target_node_coverage_pct
                           − Σ(overweight_leakage_pct × severity_weight)

Where severity_weight:  HIGH = 1.0, MODERATE = 0.6, LOW = 0.2
```

**Example — VOO vs VRT for US Large:**

| Candidate | Target Coverage | OW Leakage (Hyper Mega, MODERATE) | NCS |
|-----------|----------------|-----------------------------------|-----|
| VOO | 15% | 30% × 0.6 = 18% penalty | −3% |
| VRT | 100% | 0% | 100% |

### D2 — Conviction Quality
*What is the engine's confidence in this candidate's future return quality?*

For individual securities:
```
Conviction Score = (composite_score / 5.0) × 30        # 0–30
                 + (1 if ESS == BULLISH else 0) × 10    # 0–10
                 + (1 if replay_supported else 0) × 10  # 0–10
                 + STI_tier_bonus                        # see below
                 = 0–60

STI tier bonus:
  CCL = 10, HCA = 7, TGC = 3, WTC = 0
```

For ETFs: Conviction Score = 0 (no composite signal, no ESS, no replay tier).

### D3 — Concentration Impact
*Does adding this candidate worsen concentration risk?*

```
Concentration Delta = (candidate_pct_of_portfolio + current_node_weight)
                    − max_node_threshold

Negative = reducing overconcentration (good)
Positive = adding to overconcentration (penalize)
```

For direct securities already owned, this is position-level concentration.
For ETFs, it is aggregate node-level concentration.

### D4 — Overlap Penalty
*Does this candidate duplicate exposure already well-represented in the portfolio?*

For individual securities:
- Check thematic_overlap_clusters from STI profiles
- Check overlap_peers list
- Penalize if trim_priority_score > 50 (implies redundancy risk)

For ETFs:
- Overlap = fraction of top-10 ETF holdings already in portfolio
- Example: VOO top-10 overlap with this portfolio ≈ 30% (NVDA, MSFT, AMZN, etc.)

### D5 — Mandate Alignment
*Does the mandate permit this candidate as an action?*

Under CONCENTRATED_ALPHA:
- Individual high-conviction securities: always mandate-compatible
- Broad ETFs in underweight nodes: immediately labeled INTENTIONAL_UNDERWEIGHT
  → mandate_urgency = INFORMATIONAL → effectively suppressed

If the mandate suppresses the action, Option B (ETF) has zero effective impact.

### D6 — Suitability (existing engine signal)
*What does the current vehicle suitability framework compute?*

Retained as-is. A LOW suitability score (<25/100) is a hard negative signal for
any ETF recommendation. No HIGH-suitability vehicle currently exists for US Large
under the Concentrated Alpha mandate.

### D7 — Deployment Efficiency
*Given the deployable cash (~$9,424), what is the minimum effective position size?*

For ETFs: $9,424 of VOO = ~0.018% of SPX exposure in US Large node
For direct securities: $9,424 of VRT = +$9,424 into a 3.60% position
  → incremental exposure concentrated in highest-PIS candidate in target node

---

## 3. Decision Rules

### Rule 1 — Node Coverage Precision Gate
```
IF Node Coverage Score (D1) < 10% for the ETF candidate:
  → ETF is DISQUALIFIED for this node repair action
  → Fall through to individual security path
```

**Applies to:** VOO for US Large (NCS = −3%). VOO is disqualified as a US Large
repair vehicle.

### Rule 2 — Conviction Availability Gate
```
IF any existing portfolio holding satisfies ALL of:
  - lives directly in the target node
  - Conviction Score (D2) ≥ 40
  - Concentration Impact (D3) ≤ 0 (not worsening)
  - Overlap Penalty (D4) < 30
THEN:
  → Individual Security path is PREFERRED
  → ETF path is SECONDARY fallback only
```

**Applies to:** VRT and DELL for US Large.
VRT: conviction=76.7, in US Large, no concentration worsening, overlap=0.
DELL: conviction=73.6, in US Large.
→ Individual security path is preferred. ETF path is fallback.

### Rule 3 — Mandate Suppression Bypass
```
IF mandate_urgency = INFORMATIONAL for ETF recommendation:
  AND individual security alternative exists with conviction ≥ 40:
  → ETF recommendation is SUPPRESSED entirely
  → Individual security rec is surfaced as CONVICTION_DEPLOYMENT type
```

This resolves the PMI-engine contradiction. Rather than emitting a contradictory
MODERATE/INFORMATIONAL pair, the engine surfaces a coherent conviction recommendation.

### Rule 4 — Cross-Node Conflict Gate
```
FOR each Build candidate (ETF or security):
  Compute net_node_delta for all nodes with current MODERATE+ drift

  IF any net_node_delta for an OW node > +0.5%:
    → Tag candidate as CONFLICT_RISK
    → Require higher conviction threshold (D2 ≥ 55) to proceed
    → If threshold not met: SUPPRESS or downgrade to INFORMATIONAL
```

**Applies to:** VOO causes +~0.15% HYPER_MEGA worsening per 1% deployed.
At $9,424 (2.0% of portfolio), net impact ≈ +0.30% HYPER_MEGA — borderline.
With LOW conviction (D2=0): SUPPRESS.

### Rule 5 — Portfolio-Level Net Improvement Gate
```
FOR each candidate c in consideration set:
  net_improvement = Conviction Score (D2)
                  + Node Coverage Score (D1 × 10)
                  − Concentration Penalty (D3 × 15)
                  − Overlap Penalty (D4 × 5)

SELECT candidate with highest net_improvement.
SUPPRESS candidate if net_improvement < THRESHOLD (suggest: 25).
```

---

## 4. Security vs ETF Comparison Matrix (Current Portfolio)

### Target Node: EQUITIES.US.LARGE (Drift = −7.34%)

| Candidate | D1 NCS | D2 Conviction | D3 Conc | D4 Overlap | D5 Mandate | D6 Suitability | Net |
|-----------|--------|---------------|---------|------------|------------|----------------|-----|
| VRT | 100% | 76.7 | None | 0% | Compatible | N/A (security) | ✅ Strong |
| DELL | 100% | 73.6 | None | 0% | Compatible | N/A (security) | ✅ Strong |
| LRCX | 100% | 73.6 | None | 0% | Compatible | N/A (security) | ✅ Strong |
| PLTR | 100% | 31.0 | Low | 0% | Compatible | N/A (security) | ⚠ Weak (TGC, no replay) |
| VOO | −3% | 0 | Moderate | 30% | INTENTIONAL → INFO | LOW (15/100) | ❌ Disqualified |
| IVV | −3% | 0 | Moderate | 30% | INTENTIONAL → INFO | LOW (15/100) | ❌ Disqualified |
| SPY | −3% | 0 | Moderate | 30% | INTENTIONAL → INFO | LOW (15/100) | ❌ Disqualified |

### Target Node: EQUITIES.US.MEGA.EXTENDED_MEGA (Drift = −4.15%)

| Candidate | D1 NCS | D2 Conviction | D3 Conc | D4 Overlap | D5 Mandate | D6 Suitability | Net |
|-----------|--------|---------------|---------|------------|------------|----------------|-----|
| (No existing holding in node) | — | — | — | — | — | — | No direct option |
| VTI | 25% net | 0 | Moderate | 14% | INTENTIONAL → INFO | MEDIUM (34/100) | ⚠ Weak |
| SCHB | 25% net | 0 | Moderate | 14% | INTENTIONAL → INFO | MEDIUM (34/100) | ⚠ Weak |

**Note:** No existing portfolio holding is classified as EXTENDED_MEGA.
For this node, ETF is the only vehicle option. However, the mandate layer
suppresses the action anyway. Correct outcome: INFORMATIONAL, no deployment.

---

## 5. Decision Tree

```
When allocation engine detects underweight node (MODERATE+ severity):
│
├── Step 1: Does mandate suppress this action?
│     INTENTIONAL_UNDERWEIGHT / INFORMATIONAL → SKIP to End
│     (No conviction path needed — mandate has already decided)
│
├── Step 2: Are there existing portfolio holdings in the target node
│   with Conviction Score ≥ 40?
│     YES → Evaluate Individual Security Path (Section 3 Rules 1–5)
│     NO  → Evaluate ETF Path
│
├── Individual Security Path:
│   ├── Rank candidates by PIS (net_improvement score)
│   ├── Apply Rule 4 (cross-node conflict check)
│   ├── IF top candidate passes all gates:
│   │     → Surface as CONVICTION_DEPLOYMENT recommendation
│   └── IF no candidate passes:
│         → Surface as INFORMATIONAL (no high-conviction action available)
│
└── ETF Path:
    ├── Apply Rule 1 (NCS ≥ 10% gate)
    ├── Apply Rule 4 (cross-node conflict check)
    ├── Apply Rule 6 (suitability ≥ MEDIUM required)
    ├── IF ETF passes all gates:
    │     → Surface as ALLOCATION_REPAIR recommendation
    └── IF ETF fails any gate:
          → Surface as INFORMATIONAL with conflict explanation
```

---

## 6. ETF Use Cases (When ETF Is Correct)

ETF recommendations are appropriate when:

1. **No high-conviction direct security exists in the target node** (D2 < 40 for all candidates)
2. **The target node has no existing representation** in the portfolio and no
   single-security approach provides adequate diversification
3. **Mandate is not CONCENTRATED_ALPHA** (Balanced/Growth mandates — target
   adherence is a higher priority, ETF efficiency is valuable)
4. **NCS ≥ 25%** for the ETF vehicle (off-target leakage is acceptable and
   does not worsen existing overweights)
5. **Suitability ≥ MEDIUM** (HIGH preferred)

**Example where ETF is correct:**
Portfolio with BALANCED mandate, no international exposure, and no high-conviction
international securities → VEU or VXUS as ALLOCATION_REPAIR is appropriate.

---

## 7. Summary Decision Rules Reference

| Rule | Name | Gate Condition | Action if Failed |
|------|------|---------------|-----------------|
| R1 | NCS Gate | NCS < 10% | Disqualify ETF |
| R2 | Conviction Availability | High-conviction security exists in node | Prefer security over ETF |
| R3 | Mandate Suppression Bypass | Mandate = INFORMATIONAL + alt available | Suppress ETF, surface security |
| R4 | Cross-Node Conflict | OW node worsened > +0.5% | Require higher conviction threshold |
| R5 | Net Improvement Minimum | net_improvement < 25 | Suppress recommendation |
| R6 | Suitability Floor | suitability < MEDIUM | Suppress ETF recommendation |
