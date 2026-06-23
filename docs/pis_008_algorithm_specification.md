# PIS-008 — Algorithm Specification: Action Attribution Engine

**Date:** 2026-06-15

---

## 1. Module Entry Point

**File:** `src/pis/action_attribution.py`

**Public API:**
```python
def pis_action_attribution_summary(repo_root: Path | str = ".") -> dict
def pis_action_attribution_recommendations(repo_root: Path | str = ".") -> dict
def pis_action_attribution_sources(repo_root: Path | str = ".") -> dict
```

---

## 2. Data Models

```python
@dataclass(frozen=True)
class ActionAttributionRecord:
    attribution_id: str           # AA-{recommendation_id}-{symbol}
    recommendation_id: str
    recommendation_source: str    # PAP | CRA | DIL | DEPLOYMENT_QUEUE | REDUCTION_QUEUE | OTHER
    recommendation_date: str      # YYYY-MM-DD
    symbol: str
    recommended_direction: str    # BUY | REDUCE | ""
    action_status: str            # FOLLOWED | PARTIALLY_FOLLOWED | OPPOSED | IGNORED | EXPIRED
    action_confidence: str        # HIGH | MEDIUM | LOW | NONE
    observed_change_type: str     # NEW_POSITION | INCREASED | REDUCED | EXITED_POSITION | "" (none)
    observed_date: str            # YYYY-MM-DD | ""
    response_days: Optional[int]  # calendar days from recommendation to observed action
    delta_quantity: float         # actual change quantity (0 if IGNORED)
    delta_market_value: float     # actual change MV (0 if IGNORED)
    outcome: str                  # WINNER | NEUTRAL | LOSER | UNKNOWN (from attribution records)
    lineage_confidence: str       # original lineage confidence level
    created_at: str

@dataclass(frozen=True)
class SourceScorecard:
    source: str
    total_recommendations: int
    followed_count: int
    partially_followed_count: int
    ignored_count: int
    opposed_count: int
    expired_count: int
    follow_rate_pct: float        # (followed + partially) / total * 100
    ignore_rate_pct: float
    oppose_rate_pct: float
    avg_response_days: Optional[float]
    winner_count: int             # followed recs that became WINNER
    loser_count: int
    win_rate_pct: float           # winners / (winners + losers) among followed recs
```

---

## 3. Step 1 — Load Lineage Records

```
lineage_path = {repo_root}/data/history/pis/lineage/lineage_records.csv
rows = read_csv(lineage_path)

For each row:
    lineage_id       = row["lineage_id"]
    snapshot_id      = row["snapshot_id"]
    change_id        = row["change_id"]
    symbol           = row["symbol"].upper()
    change_type      = row["change_type"]
    rec_id           = row["matched_recommendation_id"]  # may be empty
    rec_source       = row["recommendation_source"]      # may be empty
    rec_date         = row["recommendation_date"]        # may be empty
    confidence       = row["confidence"]                 # NONE | LOW | MEDIUM | HIGH
    days_between     = int(row["days_between"]) if present else None
```

---

## 4. Step 2 — Load Change Records

```
changes_path = {repo_root}/data/history/pis/changes/change_records.csv
rows = read_csv(changes_path)

Build index: change_id → {symbol, change_type, snapshot_date, delta_quantity, delta_market_value}
```

---

## 5. Step 3 — Load Recommendation Candidates

Call the existing `build_recommendation_candidates()` from `recommendation_lineage.py`:

```python
from src.pis.recommendation_lineage import build_recommendation_candidates
candidates = build_recommendation_candidates(
    analysis_runs_root=repo_root / "data/portfolio_ingestion/analysis_runs"
)
```

This returns:
```
[{
    recommendation_id: str,
    source: str,
    recommendation_date: str,
    symbol: str,
    direction: str (BUY | REDUCE | ""),
    matched_recommendation: str,
    theme_symbols: [str],
}]
```

Build index: (symbol, recommendation_id) → direction, source, date

---

## 6. Step 4 — Load Existing Attribution Outcomes

```
attribution_path = {repo_root}/data/history/pis/attribution/attribution_records.csv
rows = read_csv(attribution_path)

Build index: change_id → outcome (WINNER | NEUTRAL | LOSER)
```

---

## 7. Step 5 — Classify Action Status

For each lineage record:

### Algorithm

```python
def classify_action_status(
    confidence: str,
    change_type: str,
    recommended_direction: str,
    days_between: Optional[int],
    delta_quantity: float,
) -> tuple[str, str]:
    """Returns (action_status, action_confidence)"""

    # IGNORED: lineage confidence is NONE — no recommendation matched this change
    # or no change matched the recommendation
    if confidence == "NONE":
        return "IGNORED", "HIGH"  # confident it was ignored

    # From this point, a match exists. Evaluate direction alignment.
    change_direction = _change_to_direction(change_type)
    # BUY if change_type in {NEW_POSITION, INCREASED}
    # REDUCE if change_type in {EXITED_POSITION, REDUCED}
    # "" if UNCHANGED

    if not recommended_direction:
        # No direction in recommendation — cannot classify alignment
        return "FOLLOWED", "LOW"  # benefit of the doubt

    if not change_direction:
        return "IGNORED", "MEDIUM"

    # Direction mismatch = OPPOSED
    if change_direction != recommended_direction:
        return "OPPOSED", confidence  # original lineage confidence

    # Direction matches — is it partial?
    # Use threshold: if delta_quantity > 0 but position size suggests partial execution
    # NOTE: we do not have "suggested quantity" from recommendations, so we classify
    # all direction-matched changes as FOLLOWED with a LOW partial flag when delta is small.
    # Partial threshold: if delta_market_value < $500 (minimum lot), treat as partial.
    PARTIAL_MV_THRESHOLD = 500.0
    if abs(delta_market_value) < PARTIAL_MV_THRESHOLD and confidence == "LOW":
        return "PARTIALLY_FOLLOWED", "LOW"

    # Check for expiry
    MAX_ATTRIBUTION_WINDOW_DAYS = 30
    if days_between is not None and days_between > MAX_ATTRIBUTION_WINDOW_DAYS:
        return "EXPIRED", "MEDIUM"

    return "FOLLOWED", confidence
```

### Direction Map

```python
def _change_to_direction(change_type: str) -> str:
    if change_type in {"NEW_POSITION", "INCREASED"}:
        return "BUY"
    if change_type in {"EXITED_POSITION", "REDUCED"}:
        return "REDUCE"
    return ""
```

---

## 8. Step 6 — Handle Unmatched Recommendations (IGNORED)

For every recommendation candidate that has NO matching lineage record at all — i.e., the symbol from the recommendation never appeared in change_records for any period — classify as IGNORED.

Algorithm:
```
all_rec_candidates = build_recommendation_candidates(...)
matched_rec_ids = {lin.matched_recommendation_id for lin in lineage_records if lin.matched_recommendation_id}

for candidate in all_rec_candidates:
    if candidate.recommendation_id not in matched_rec_ids:
        # Check if this symbol had ANY change in the attribution window
        changes_for_symbol = changes_index.get(candidate.symbol, [])
        relevant_window_changes = [
            c for c in changes_for_symbol
            if 0 <= days_delta(c.snapshot_date, candidate.recommendation_date) <= 30
        ]
        if not relevant_window_changes:
            emit ActionAttributionRecord(action_status="IGNORED", ...)
        else:
            # Symbol changed but not matched to this rec — IGNORED with lower confidence
            emit ActionAttributionRecord(action_status="IGNORED", action_confidence="MEDIUM", ...)
```

---

## 9. Step 7 — Source Scorecard Computation

```python
def compute_source_scorecard(records: list[ActionAttributionRecord]) -> list[SourceScorecard]:
    by_source: dict[str, list[ActionAttributionRecord]] = defaultdict(list)
    for r in records:
        by_source[r.recommendation_source].append(r)

    scorecards = []
    for source, recs in by_source.items():
        total = len(recs)
        followed = sum(1 for r in recs if r.action_status == "FOLLOWED")
        partial  = sum(1 for r in recs if r.action_status == "PARTIALLY_FOLLOWED")
        ignored  = sum(1 for r in recs if r.action_status == "IGNORED")
        opposed  = sum(1 for r in recs if r.action_status == "OPPOSED")
        expired  = sum(1 for r in recs if r.action_status == "EXPIRED")

        responded = [r for r in recs if r.response_days is not None]
        avg_days = mean(r.response_days for r in responded) if responded else None

        followed_recs = [r for r in recs if r.action_status in {"FOLLOWED", "PARTIALLY_FOLLOWED"}]
        winners = sum(1 for r in followed_recs if r.outcome == "WINNER")
        losers  = sum(1 for r in followed_recs if r.outcome == "LOSER")
        win_rate = (winners / (winners + losers) * 100) if (winners + losers) > 0 else 0.0

        scorecards.append(SourceScorecard(
            source=source,
            total_recommendations=total,
            followed_count=followed,
            partially_followed_count=partial,
            ignored_count=ignored,
            opposed_count=opposed,
            expired_count=expired,
            follow_rate_pct=round((followed + partial) / total * 100, 1) if total else 0.0,
            ignore_rate_pct=round(ignored / total * 100, 1) if total else 0.0,
            oppose_rate_pct=round(opposed / total * 100, 1) if total else 0.0,
            avg_response_days=round(avg_days, 1) if avg_days is not None else None,
            winner_count=winners,
            loser_count=losers,
            win_rate_pct=round(win_rate, 1),
        ))

    return sorted(scorecards, key=lambda s: s.total_recommendations, reverse=True)
```

---

## 10. Step 8 — Missed Opportunities

Missed opportunities = IGNORED recommendations where the symbol later moved in the recommended direction AND showed a positive outcome.

```python
def find_missed_opportunities(records: list[ActionAttributionRecord]) -> list[dict]:
    missed = []
    for r in records:
        if r.action_status != "IGNORED":
            continue
        # Would have been a winner if followed
        if r.outcome in ("WINNER",) and r.recommended_direction:
            missed.append({...})
    return sorted(missed, key=lambda m: abs(m.get("delta_market_value", 0)), reverse=True)[:10]
```

---

## 11. API Payload Contracts

### GET /api/pis/action-attribution/summary

```json
{
  "generated_at": "ISO timestamp",
  "total_attribution_records": 53,
  "followed_count": 18,
  "partially_followed_count": 3,
  "ignored_count": 25,
  "opposed_count": 2,
  "expired_count": 5,
  "follow_rate_pct": 39.6,
  "ignore_rate_pct": 47.2,
  "oppose_rate_pct": 3.8,
  "avg_response_days": 4.2,
  "sources_covered": ["PAP", "CRA", "DIL", "DEPLOYMENT_QUEUE"],
  "dates_covered": 18,
  "observations": [
    "DEPLOYMENT_QUEUE has the highest follow rate at 78%.",
    "PAP recommendations are followed 25% of the time.",
    "2 recommendations were opposed — portfolio moved in the opposite direction."
  ]
}
```

### GET /api/pis/action-attribution/recommendations

```json
{
  "generated_at": "ISO timestamp",
  "records": [
    {
      "attribution_id": "AA-REC-A1ACC627-ARW",
      "recommendation_id": "REC-A1ACC627",
      "recommendation_source": "DEPLOYMENT_QUEUE",
      "recommendation_date": "2026-06-01",
      "symbol": "ARW",
      "recommended_direction": "BUY",
      "action_status": "FOLLOWED",
      "action_confidence": "MEDIUM",
      "observed_change_type": "INCREASED",
      "observed_date": "2026-06-08",
      "response_days": 7,
      "delta_quantity": 15.0,
      "delta_market_value": 2340.50,
      "outcome": "WINNER",
      "lineage_confidence": "MEDIUM"
    }
  ]
}
```

### GET /api/pis/action-attribution/sources

```json
{
  "generated_at": "ISO timestamp",
  "scorecards": [
    {
      "source": "DEPLOYMENT_QUEUE",
      "total_recommendations": 21,
      "followed_count": 16,
      "partially_followed_count": 2,
      "ignored_count": 3,
      "opposed_count": 0,
      "expired_count": 0,
      "follow_rate_pct": 85.7,
      "ignore_rate_pct": 14.3,
      "oppose_rate_pct": 0.0,
      "avg_response_days": 3.8,
      "winner_count": 9,
      "loser_count": 4,
      "win_rate_pct": 69.2
    }
  ]
}
```

---

## 12. Storage

```
data/history/pis/action_attribution/
    attribution_records.csv    ← per-recommendation action status
    source_scorecards.csv      ← source effectiveness summary
    attribution_cache.json     ← serialized summary payload (invalidated on any lineage or change update)
```

Cache invalidation follows same pattern as allocation drift: stale when any lineage or changes file is newer than cache.

---

## 13. Edge Cases

| Case | Handling |
|------|---------|
| Recommendation with no affected_symbols | No record generated (cannot attribute to symbol) |
| UNCHANGED change records | Excluded from all attribution (not an action) |
| Recommendation date after change date | days_between may be negative; treat as same-day (0) |
| Symbol in multiple recommendations same direction | All generate separate records; each evaluated independently |
| No lineage records at all | Summary returns all zeros |
| Attribution records missing (no attribution.csv) | outcome = "UNKNOWN" for all records |
| days_between > 30 | EXPIRED status |
| Empty direction from recommendation | action_status = FOLLOWED with LOW confidence (benefit of the doubt) |
