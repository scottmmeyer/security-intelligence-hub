# ISSUE-12D — Algorithm Specification: Dislocation Outcome Review Engine

**Date:** 2026-06-15

---

## 1. Module: `src/pis/dislocation_outcome_review.py`

**Public API:**
```python
def pis_dor_summary(repo_root: Path | str = ".") -> dict
def pis_dor_cohorts(repo_root: Path | str = ".") -> dict
def pis_dor_recommendations(repo_root: Path | str = ".") -> dict
```

---

## 2. Data Models

```python
# UCF label → actionable direction
UCF_DIRECTION = {
    "CORE_CONVICTION_LEADER":  "BUY",
    "HIGH_CONVICTION_ANCHOR":  "BUY",
    "DEPLOYMENT_CANDIDATE":    "BUY",
    "TACTICAL_GROWTH":         "BUY",
    "MAINTAIN":                "",
    "TRIM_WATCH":              "REDUCE",
}

# UCF labels eligible as DIL recommendations
DIL_ELIGIBLE_LABELS = frozenset({
    "CORE_CONVICTION_LEADER",
    "HIGH_CONVICTION_ANCHOR",
    "DEPLOYMENT_CANDIDATE",
    "TRIM_WATCH",
})

@dataclass(frozen=True)
class DORRecord:
    record_id: str                    # DOR-{snapshot_date}-{symbol}
    snapshot_date: str                # YYYY-MM-DD
    symbol: str
    ucf_label: str                    # UCF label (cohort key)
    ucf_score: float
    ucf_rank: int
    recommended_direction: str        # BUY | REDUCE | ""
    signal_direction: str             # BULLISH | NEUTRAL | BEARISH
    composite_score: float
    replay_supported: bool
    replay_percentile: float
    cw_das_score: float
    conflict_flags: tuple[str, ...]   # advisory conflict badges
    action_status: str                # from action_attribution: FOLLOWED | IGNORED | etc.
    action_confidence: str
    outcome: str                      # WINNER | NEUTRAL | LOSER | UNKNOWN
    directional_return_pct: float     # from attribution_records
    excess_return_pct: float          # alpha vs benchmark
    observation_window_days: int      # days from recommendation to outcome
    governance_flags: tuple[str, ...] # advisory governance notes

@dataclass(frozen=True)
class CohortSummary:
    ucf_label: str
    direction: str                    # BUY | REDUCE | ""
    total_count: int
    followed_count: int
    ignored_count: int
    follow_rate_pct: float
    winner_count: int
    loser_count: int
    neutral_count: int
    win_rate_pct: float               # winners / (winners + losers) among followed
    avg_alpha_pct: float              # mean excess_return_pct for followed records
    avg_return_pct: float             # mean directional_return_pct for followed records
    missed_winner_count: int          # IGNORED records with positive outcome
```

---

## 3. Step 1 — Load UCF Verdict History

```python
def _load_ucf_history(repo_root: Path) -> list[dict]:
    """Return one record per (snapshot_date, symbol) for all UCF verdicts."""
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return []

    # Canonical date selection: latest PAR per snapshot_date
    by_date: dict[str, tuple[str, Path]] = {}
    for par_path in par_dir.iterdir():
        if not par_path.is_dir(): continue
        meta_file = par_path / "run_metadata.json"
        ucf_file = par_path / "ucf_verdicts.json"
        if not meta_file.exists() or not ucf_file.exists(): continue
        meta = json.loads(meta_file.read_text())
        snap_date = str(meta.get("snapshot_date", ""))[:10]
        created_at = str(meta.get("created_at_utc", ""))
        if len(snap_date) == 10:
            try: date.fromisoformat(snap_date)
            except ValueError: continue
            if snap_date not in by_date or created_at > by_date[snap_date][0]:
                by_date[snap_date] = (created_at, ucf_file)

    records = []
    for snap_date in sorted(by_date):
        _, ucf_file = by_date[snap_date]
        ucf_data = json.loads(ucf_file.read_text())
        for v in ucf_data.get("verdicts", []):
            symbol = str(v.get("symbol", "")).strip().upper()
            if not symbol: continue
            src = v.get("source_signals") or {}
            records.append({
                "snapshot_date": snap_date,
                "symbol": symbol,
                "ucf_label": str(v.get("ucf_label", "")),
                "ucf_score": float(src.get("cw_das_score") or v.get("ucf_score") or 0.0),
                "ucf_rank": int(v.get("ucf_rank") or 0),
                "signal_direction": str(src.get("signal_direction") or ""),
                "composite_score": float(src.get("composite_score") or 0.0),
                "replay_supported": bool(src.get("replay_supported")),
                "replay_percentile": float(src.get("replay_percentile") or 0.0),
                "cw_das_score": float(src.get("cw_das_score") or 0.0),
                "conflict_flags": list(v.get("conflict_flags") or []),
            })
    return records
```

---

## 4. Step 2 — Load Action Attribution for DIL

```python
def _load_dil_action_attribution(repo_root: Path) -> dict[tuple[str, str], dict]:
    """Return {(symbol, recommendation_date): action_attribution_record} for DIL source."""
    cache_path = repo_root / "data" / "history" / "pis" / "action_attribution" / "attribution_cache.json"
    if not cache_path.exists():
        return {}
    cache = json.loads(cache_path.read_text())
    index: dict[tuple[str, str], dict] = {}
    for r in cache.get("records", []):
        if r.get("recommendation_source") != "DIL":
            continue
        sym = str(r.get("symbol", "")).upper()
        rec_date = str(r.get("recommendation_date", ""))[:10]
        key = (sym, rec_date)
        # Keep highest-status record if multiple exist
        if key not in index or _STATUS_RANK.get(r.get("action_status",""), 0) > _STATUS_RANK.get(index[key].get("action_status",""), 0):
            index[key] = r
    return index
```

---

## 5. Step 3 — Load Attribution Outcomes

```python
def _load_attribution_outcomes(repo_root: Path) -> dict[str, dict]:
    """Return {symbol: attribution_record} from attribution_records.csv."""
    path = repo_root / "data" / "history" / "pis" / "attribution" / "attribution_records.csv"
    rows = _read_csv(path)
    index: dict[str, dict] = {}
    for r in rows:
        sym = str(r.get("symbol", "")).upper()
        if sym:
            index[sym] = r  # last-write wins; most recent attribution per symbol
    return index
```

---

## 6. Step 4 — Load Benchmark Alpha

```python
def _load_benchmark_alpha(repo_root: Path) -> dict[str, float]:
    """Return {symbol: excess_return_pct} from benchmark attribution records."""
    path = repo_root / "data" / "history" / "pis" / "benchmark_attribution" / "recommendation_benchmark_records.csv"
    rows = _read_csv(path)
    alpha: dict[str, float] = {}
    for r in rows:
        sym = str(r.get("symbol", "")).upper()
        raw = r.get("recommendation_excess_return_pct", "")
        try:
            val = float(raw) if raw else None
        except (TypeError, ValueError):
            val = None
        if sym and val is not None:
            alpha[sym] = val
    return alpha
```

---

## 7. Step 5 — Build DOR Records

```python
def _build_dor_records(repo_root: Path) -> list[DORRecord]:
    ucf_history = _load_ucf_history(repo_root)
    dil_attribution = _load_dil_action_attribution(repo_root)
    attribution_outcomes = _load_attribution_outcomes(repo_root)
    benchmark_alpha = _load_benchmark_alpha(repo_root)

    records = []
    for entry in ucf_history:
        symbol = entry["symbol"]
        snap_date = entry["snapshot_date"]
        ucf_label = entry["ucf_label"]

        # Only DIL-eligible labels (actionable direction)
        if ucf_label not in DIL_ELIGIBLE_LABELS:
            continue

        direction = UCF_DIRECTION.get(ucf_label, "")

        # Action attribution lookup: (symbol, snap_date)
        attr = dil_attribution.get((symbol, snap_date), {})
        action_status = attr.get("action_status", "IGNORED")
        action_conf = attr.get("action_confidence", "NONE")

        # Performance outcome
        perf = attribution_outcomes.get(symbol, {})
        outcome = perf.get("outcome", "UNKNOWN")
        directional_return = float(perf.get("directional_return_pct") or 0.0)
        excess_return = benchmark_alpha.get(symbol, 0.0)

        # Governance flags
        gov_flags = []
        if action_status == "IGNORED" and outcome == "WINNER":
            gov_flags.append("MISSED_WINNER")
        if entry["conflict_flags"]:
            gov_flags.append("SIGNAL_CONFLICT")
        if action_status == "FOLLOWED" and outcome == "LOSER":
            gov_flags.append("FOLLOWED_LOSER")

        records.append(DORRecord(
            record_id=f"DOR-{snap_date}-{symbol}",
            snapshot_date=snap_date,
            symbol=symbol,
            ucf_label=ucf_label,
            ucf_score=entry["ucf_score"],
            ucf_rank=entry["ucf_rank"],
            recommended_direction=direction,
            signal_direction=entry["signal_direction"],
            composite_score=entry["composite_score"],
            replay_supported=entry["replay_supported"],
            replay_percentile=entry["replay_percentile"],
            cw_das_score=entry["cw_das_score"],
            conflict_flags=tuple(entry["conflict_flags"]),
            action_status=action_status,
            action_confidence=action_conf,
            outcome=outcome,
            directional_return_pct=directional_return,
            excess_return_pct=excess_return,
            observation_window_days=int(attr.get("response_days") or 0),
            governance_flags=tuple(gov_flags),
        ))
    return records
```

---

## 8. Step 6 — Cohort Analysis

```python
def _build_cohorts(records: list[DORRecord]) -> list[CohortSummary]:
    by_label: dict[str, list[DORRecord]] = defaultdict(list)
    for r in records:
        by_label[r.ucf_label].append(r)

    summaries = []
    for label in sorted(by_label, key=lambda l: _UCF_LABEL_RANK.get(l, 99)):
        recs = by_label[label]
        total = len(recs)
        followed = [r for r in recs if r.action_status in ("FOLLOWED", "PARTIALLY_FOLLOWED")]
        ignored = [r for r in recs if r.action_status == "IGNORED"]

        winners = sum(1 for r in followed if r.outcome == "WINNER")
        losers = sum(1 for r in followed if r.outcome == "LOSER")
        neutral = sum(1 for r in followed if r.outcome == "NEUTRAL")
        win_rate = round(winners / (winners + losers) * 100, 1) if (winners + losers) > 0 else 0.0

        followed_returns = [r.directional_return_pct for r in followed if r.directional_return_pct != 0.0]
        followed_alpha = [r.excess_return_pct for r in followed if r.excess_return_pct != 0.0]
        avg_return = round(mean(followed_returns), 2) if followed_returns else 0.0
        avg_alpha = round(mean(followed_alpha), 2) if followed_alpha else 0.0

        missed_winners = sum(1 for r in ignored if r.outcome == "WINNER")

        summaries.append(CohortSummary(
            ucf_label=label,
            direction=UCF_DIRECTION.get(label, ""),
            total_count=total,
            followed_count=len(followed),
            ignored_count=len(ignored),
            follow_rate_pct=round(len(followed) / total * 100, 1) if total else 0.0,
            winner_count=winners,
            loser_count=losers,
            neutral_count=neutral,
            win_rate_pct=win_rate,
            avg_alpha_pct=avg_alpha,
            avg_return_pct=avg_return,
            missed_winner_count=missed_winners,
        ))
    return summaries
```

---

## 9. Step 7 — Governance Observations

```python
def _generate_observations(records: list[DORRecord], cohorts: list[CohortSummary]) -> list[str]:
    obs = []

    # High-conviction missed winners
    ccl_missed = [r for r in records if r.ucf_label == "CORE_CONVICTION_LEADER"
                  and r.action_status == "IGNORED" and r.outcome == "WINNER"]
    if ccl_missed:
        obs.append(
            f"{len(ccl_missed)} CORE_CONVICTION_LEADER recommendations were ignored "
            "and later showed positive outcomes. Governance review recommended."
        )

    # Best-performing cohort
    followed_cohorts = [c for c in cohorts if c.followed_count > 0 and c.win_rate_pct > 0]
    if followed_cohorts:
        best = max(followed_cohorts, key=lambda c: c.win_rate_pct)
        obs.append(
            f"{best.ucf_label} cohort shows the highest win rate at {best.win_rate_pct:.0f}% "
            f"({best.winner_count} winners from {best.followed_count} followed recommendations)."
        )

    # Alpha comparison: followed vs ignored
    followed_recs = [r for r in records if r.action_status in ("FOLLOWED","PARTIALLY_FOLLOWED")]
    ignored_recs_with_outcome = [r for r in records if r.action_status == "IGNORED" and r.outcome != "UNKNOWN"]
    if followed_recs and ignored_recs_with_outcome:
        avg_follow_alpha = mean(r.excess_return_pct for r in followed_recs if r.excess_return_pct != 0)
        avg_ignore_outcome = mean(r.excess_return_pct for r in ignored_recs_with_outcome if r.excess_return_pct != 0)
        if avg_ignore_outcome > avg_follow_alpha:
            obs.append(
                "Ignored DIL recommendations showed higher average alpha than followed recommendations "
                "in the current observation window. This is a governance review finding — no automatic adjustment implied."
            )

    # Signal conflict governance
    conflict_recs = [r for r in records if "SIGNAL_CONFLICT" in r.governance_flags]
    if conflict_recs:
        conflict_followed = [r for r in conflict_recs if r.action_status in ("FOLLOWED","PARTIALLY_FOLLOWED")]
        if conflict_followed:
            obs.append(
                f"{len(conflict_followed)} DIL recommendations with signal conflicts were followed. "
                f"Win rate: {sum(1 for r in conflict_followed if r.outcome=='WINNER') / len(conflict_followed) * 100:.0f}%."
            )

    # Total coverage note
    obs.append(
        f"DIL outcome review covers {len(records)} recommendation-date pairs across "
        f"{len(set(r.snapshot_date for r in records))} canonical dates."
    )

    return obs[:6]
```

---

## 10. API Payload Contracts

### GET /api/pis/dor/summary

```json
{
  "generated_at": "ISO timestamp",
  "total_dil_records": 456,
  "followed_count": 5,
  "ignored_count": 451,
  "winner_count": 5,
  "loser_count": 0,
  "neutral_count": 0,
  "unknown_count": 451,
  "follow_rate_pct": 1.1,
  "win_rate_pct": 100.0,
  "avg_alpha_pct": 12.3,
  "missed_winner_count": 0,
  "dates_covered": 19,
  "observations": ["..."],
  "governance_flags": ["..."]
}
```

### GET /api/pis/dor/cohorts

```json
{
  "generated_at": "ISO timestamp",
  "cohorts": [
    {
      "ucf_label": "CORE_CONVICTION_LEADER",
      "direction": "BUY",
      "total_count": 19,
      "followed_count": 1,
      "ignored_count": 18,
      "follow_rate_pct": 5.3,
      "winner_count": 1,
      "loser_count": 0,
      "win_rate_pct": 100.0,
      "avg_alpha_pct": 17.4,
      "missed_winner_count": 0
    }
  ]
}
```

### GET /api/pis/dor/recommendations

```json
{
  "generated_at": "ISO timestamp",
  "total": 456,
  "records": [
    {
      "record_id": "DOR-2026-06-01-VRT",
      "snapshot_date": "2026-06-01",
      "symbol": "VRT",
      "ucf_label": "CORE_CONVICTION_LEADER",
      "recommended_direction": "BUY",
      "action_status": "FOLLOWED",
      "outcome": "WINNER",
      "excess_return_pct": 17.4,
      "governance_flags": []
    }
  ]
}
```

---

## 11. Edge Cases

| Case | Handling |
|------|---------|
| No UCF verdicts | Empty payload, no exception |
| UCF label not in DIL_ELIGIBLE_LABELS | Record excluded from DOR (MAINTAIN/TACTICAL_GROWTH are advisory only) |
| No action attribution cache | All records get action_status="IGNORED" |
| No attribution outcome | outcome="UNKNOWN" |
| No benchmark records | excess_return_pct=0.0 |
| Only UNKNOWN outcomes | win_rate=0.0, governance observations note coverage gap |
| Single date of history | valid; observations note limited window |
