# Asset-Class-First Architecture

## Design Decision

The SIH Allocation Intelligence system organizes its hierarchy with **asset class as the primary (Level 1) dimension**. This is a deliberate break from geography-first or factor-first approaches.

---

## Why Asset Class First?

### 1. Risk budget starts at the asset class level

The most consequential portfolio decision is how to split capital between asset classes: equities, fixed income, digital assets, commodities, and cash. These decisions dominate long-term risk/return outcomes and are where governance guardrails (policy ceilings, cash floors) apply.

### 2. Governance and regulation are asset-class-scoped

Investment policy statements, regulatory constraints (e.g., maximum digital assets exposure), and fiduciary ceilings are naturally expressed at the asset class level. Placing asset class at Level 1 makes policy enforcement straightforward.

### 3. Replay evidence is heterogeneous across asset classes

The SIH replay system generates rich equity analytics. Fixed income, digital assets, and commodities have different data characteristics:
- Equities → HIGH sophistication: full replay pipeline
- Fixed Income → LOW sophistication: macro/duration methodology
- Digital/Commodities/Cash → NONE: pure methodology baseline

An asset-class-first hierarchy naturally partitions this heterogeneity.

### 4. Institutional convention

Institutional portfolio construction universally begins with asset class determination (strategic asset allocation), then sub-allocates within each class by geography, market cap, and style.

---

## Hierarchy Structure

```
Level 1 — Asset Class          (EQUITIES, FIXED_INCOME, DIGITAL, COMMODITIES, CASH)
Level 2 — Geography / Sub-type (US, INTERNATIONAL, EMERGING_MARKETS for equities; 
                                 BITCOIN, ETHEREUM, OTHER for digital; etc.)
Level 3 — Market Cap           (MEGA, LARGE, MID, SMALL, MICRO — equity only)
Level 4 — Mega Subtier         (HYPER_MEGA, ULTRA_MEGA, EXTENDED_MEGA — US equity only)
```

### Key Scheme: Dot-Notation

```
EQUITIES
EQUITIES.US
EQUITIES.US.MEGA
EQUITIES.US.MEGA.HYPER_MEGA
FIXED_INCOME
FIXED_INCOME.US
DIGITAL
DIGITAL.BITCOIN
COMMODITIES.GOLD
```

---

## Propagation Formula

`target_pct_of_total` for any node is the product of `target_pct_of_parent` across its full ancestry chain:

```
target_pct_of_total(EQUITIES.US.MEGA.HYPER_MEGA)
  = EQUITIES(70%) × US(72%) × MEGA(45%) × HYPER_MEGA(35%)
  = 0.70 × 0.72 × 0.45 × 0.35
  = 7.938%
```

This means changes to parent nodes automatically cascade to all descendants via the `_recompute_pct_of_total` step in the recalculation engine.

---

## Sum Invariant

For every parent node P with children C₁, C₂, ..., Cₙ:

```
∑ target_pct_of_parent(Cᵢ) = 100.0 ±0.01
```

Enforced by `validate_hierarchy_sums`. When evidence drives a change to one sibling, the recalculation engine proportionally renormalizes the remaining siblings.

---

## Node Metadata

Each node in `config/allocation_dimensions.yaml` carries:

| Field | Purpose |
|-------|---------|
| `key` | Dot-notation unique identifier |
| `label` | Human-readable display name |
| `parent_key` | Null for Level 1 nodes |
| `dimension_type` | ASSET_CLASS / GEOGRAPHY / MARKET_CAP / MEGA_SUBTIER / ASSET_SUBTYPE |
| `allocation_category_type` | EQUITY / FIXED_INCOME / DIGITAL / COMMODITY / CASH |
| `hierarchy_level` | 1–4 |
| `children` | Ordered list of child keys |
| `replay_filter_mapping` | Maps to `replay_inputs.csv` filter columns |
| `replay_sophistication` | HIGH / LOW / NONE |

---

## Comparison to Alternative Approaches

| Approach | Disadvantage for SIH |
|----------|----------------------|
| Geography-first | No clean governance boundary for asset class ceilings |
| Factor-first | Factor data not consistently available across asset classes |
| Sector-first | Sectors don't naturally span asset classes (equity-biased) |
| **Asset-class-first** | ✓ Natural policy boundary, ✓ heterogeneous replay handling, ✓ institutional convention |
