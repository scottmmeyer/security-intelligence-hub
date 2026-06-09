# PRA-IMPL-05 Final Recommendation

Repository: security-intelligence-hub  
Date: 2026-06-09  
Issue: PRA-IMPL-05 (#28) — FVI Advisory Overlay for Allocation Reduction

---

## Q1 — Is PRA-IMPL-05 Ready for Implementation?

**Yes, with a Phase 1 scope constraint.**

Phase 1 is implementation-ready:
- Peer group assignments are defined for all 15 portfolio fund vehicles
- FVI scoring model is specified
- Advisory-only integration design is documented
- Card schema (PRA-IMPL-01/02/03) is complete — FVI labels can be rendered immediately

**Single remaining prerequisite:** Create the peer group configuration file (`config/fvi_peer_groups.yaml`) with Phase 1 advisory estimates for the 15 held fund vehicles. This is a configuration task, not an architecture task.

Phase 2 (live provider data integration) requires separate data source evaluation and is explicitly out of scope for the current implementation issue.

---

## Q2 — Is DODFX a Retain, Monitor, or Replace Candidate?

**RETAIN.**

- FVI Tier: HIGH (estimated ~75/100)
- Peer ranking: top 25–35th percentile in Foreign Large Value
- Manager quality: above average (Dodge & Cox team-based, long tenure)
- Expense ratio: competitive for active international (~0.63%)
- Load: Class I shares have no front-end load; no switching cost friction
- Tax: unrealized gain ~$2,352 (~19%); minor drag on any sale
- Policy: SELL_LAST is independently correct and consistent with FVI HIGH tier

Combined FVI + Policy advisory: "DODFX is a quality vehicle. Retain as preferred International Large Value implementation. Reduce other International sources first in any sleeve reduction scenario."

---

## Q3 — Which Current Portfolio Funds Score Highest Under FVI?

**Estimated top FVI performers (ELITE tier):**

| Rank | Symbol | FVI Tier | Score | Why |
|---|---|---|---|---|
| 1 | FXAIX | ELITE | ~88 | Zero expense ratio, perfect tracking |
| 2 | VOO | ELITE | ~90 | Near-zero expense, deepest liquidity S&P 500 ETF |
| 3 | VB | ELITE | ~85 | Near-lowest cost US Small Blend |
| 4 | VO | ELITE | ~85 | Near-lowest cost US Mid Blend |
| 5 | BND | ELITE | ~82 | Benchmark US bond ETF, minimal cost |
| 6 | VEA | ELITE | ~82 | Lowest cost developed market ETF |
| 7 | VWO | ELITE | ~80 | Benchmark EM ETF, competitive cost |
| 8 | BNDX | ELITE | ~80 | Lowest cost hedged international bond |

Nearly all index ETFs in the portfolio score ELITE. This is expected: index ETFs in mature categories (S&P 500, small cap, bond) are typically near-optimal vehicles.

---

## Q4 — Which Current Portfolio Funds Score Lowest Under FVI?

**Estimated lowest FVI performers:**

| Rank | Symbol | FVI Tier | Score | Why |
|---|---|---|---|---|
| Lowest | FSOL | LOW | ~38 | Very new Solana ETF, limited track record, high vol |
| 2nd lowest | XRP | MEDIUM | ~45 | Recent product, limited issuer track record |
| 3rd lowest | FCPGX | MEDIUM | ~52 | Active small cap growth has historically underperformed |
| 4th lowest | FMCSX | MEDIUM | ~55 | Active mid cap has mixed long-term record |

**Note:** FSOL and XRP have small positions (0.02% each) and are in the DIGITAL.OTHER category. Their low FVI scores reflect category risk and instrument maturity, not necessarily issuer quality. For these instruments, FVI is less actionable than for traditional equity funds.

FCPGX and FMCSX are both small active Fidelity funds with small portfolio weights. Under FVI, these would be noted as lower-quality vehicles relative to passive alternatives (SCHA for small growth, SCHM for mid blend), but their small size limits the decision impact.

---

## Q5 — What Should Be Implemented First After PRA-IMPL-05 Assessment?

Recommended implementation sequence:

### Immediate Next: Create `config/fvi_peer_groups.yaml`

This is the only blocking prerequisite for PRA-IMPL-05 Phase 1. It contains the peer group assignments and Phase 1 advisory FVI estimates for all 15 portfolio fund vehicles. It is a configuration file with no code dependency.

### Then: PRA-IMPL-05 Phase 1 Implementation

1. Load `fvi_peer_groups.yaml` in the runner's additive annotation pass
2. Attach FVI advisory data to recommendation card drilldowns for relevant fund symbols
3. Update `_computePortfolioActions()` Cat 3 rendering to show FVI tier alongside reduction candidates
4. Update Funding Sources display with FVI advisory labels
5. No change to existing scoring, policy, or recommendation generation

### After Phase 1: Validate and Decide on Phase 2

Phase 2 (live Morningstar/Lipper data) should be designed only after Phase 1 advisory labels are validated through operator use. The manual config approach is sufficient for Phase 1 and removes the external data dependency risk.

---

## Summary

| Item | Decision |
|---|---|
| Implementation ready | Yes (Phase 1) |
| Blocking prerequisite | Create config/fvi_peer_groups.yaml |
| DODFX disposition | RETAIN |
| Highest FVI vehicles | VOO, FXAIX, VB, VO (all ELITE, index ETFs) |
| Lowest FVI vehicles | FSOL, XRP, FCPGX, FMCSX |
| Phase 2 (live data) | Defer until Phase 1 validated |
| No code changes | CW-DAS, ESS, STI, CRA, PAP, conviction scores all unchanged |
