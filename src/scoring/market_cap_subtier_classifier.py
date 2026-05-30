"""Dynamic analytical market-cap subtier classification.

Computes ``analytical_market_cap_subtier`` for every row in the analytical
universe at snapshot-generation time.  The resulting assignment is frozen and
becomes immutable historical analytical truth — it must never be recomputed
against already-persisted partitions.

Algorithm (DYNAMIC_MEGA_THIRDS_V1):
  1. Collect all Fidelity-MEGA rows; sort by market_cap_raw_usd DESC, then
     symbol ASC for deterministic tie-breaking.
  2. Partition into thirds:
       base = N // 3
       rem  = N % 3
       hyper_count    = base + (1 if rem > 0 else 0)   # top third, rounded up
       ultra_count    = base + (1 if rem > 1 else 0)   # middle third
       extended_count = N - hyper_count - ultra_count  # bottom third
  3. Assign HYPER_MEGA / ULTRA_MEGA / EXTENDED_MEGA accordingly.
  4. Non-MEGA rows: analytical_market_cap_subtier = market_cap_bucket (passthrough).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_POLICY_PATH = _REPO_ROOT / "config" / "market_cap_subtier_policy.yaml"

_REQUIRED_POLICY_KEYS = {
    "policy_id",
    "methodology_type",
    "partitioning_strategy",
    "ranking_basis",
    "tie_break_rule",
    "partition_rules",
}

_VALID_METHODOLOGY_TYPES = {"DYNAMIC_RANK_BASED"}
_VALID_PARTITIONING_STRATEGIES = {"MEGA_ONLY", "ALL_BUCKETS"}

_SUBTIER_LABELS = ("HYPER_MEGA", "ULTRA_MEGA", "EXTENDED_MEGA")


def load_subtier_policy(
    path: str | Path = _DEFAULT_POLICY_PATH,
) -> Dict[str, Any]:
    """Load and validate the subtier policy YAML.

    Raises ValueError if any required key is missing or a field holds an
    unsupported value.
    """
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("market_cap_subtier_policy.yaml root must be a mapping.")

    missing = _REQUIRED_POLICY_KEYS - payload.keys()
    if missing:
        raise ValueError(
            f"market_cap_subtier_policy.yaml is missing required key(s): {sorted(missing)}"
        )

    methodology = str(payload.get("methodology_type", ""))
    if methodology not in _VALID_METHODOLOGY_TYPES:
        raise ValueError(
            f"Unsupported methodology_type '{methodology}'. "
            f"Valid values: {sorted(_VALID_METHODOLOGY_TYPES)}"
        )

    strategy = str(payload.get("partitioning_strategy", ""))
    if strategy not in _VALID_PARTITIONING_STRATEGIES:
        raise ValueError(
            f"Unsupported partitioning_strategy '{strategy}'. "
            f"Valid values: {sorted(_VALID_PARTITIONING_STRATEGIES)}"
        )

    rules = payload.get("partition_rules")
    if not isinstance(rules, list) or len(rules) == 0:
        raise ValueError("market_cap_subtier_policy.yaml 'partition_rules' must be a non-empty list.")

    return payload


def _compute_mega_thirds(n: int) -> tuple[int, int, int]:
    """Return (hyper_count, ultra_count, extended_count) for a MEGA cohort of size n.

    Remainder is distributed top-down (hyper first, then ultra) to avoid
    bottom-tier inflation and ensure the assignment is fully deterministic.

    Edge cases:
      n=0 → (0, 0, 0)
      n=1 → (1, 0, 0)
      n=2 → (1, 1, 0)
      n=3 → (1, 1, 1)
      n=4 → (2, 1, 1)
      n=5 → (2, 2, 1)
    """
    if n <= 0:
        return (0, 0, 0)
    base = n // 3
    rem = n % 3
    hyper_count = base + (1 if rem > 0 else 0)
    ultra_count = base + (1 if rem > 1 else 0)
    extended_count = n - hyper_count - ultra_count
    return (hyper_count, ultra_count, extended_count)


def classify_analytical_subtiers(
    rows: List[Dict[str, Any]],
    policy: Dict[str, Any],
    snapshot_date: str,
) -> List[Dict[str, Any]]:
    """Inject analytical_market_cap_subtier, classification_policy_id, and
    classification_snapshot_date into every row dict (in-place copy).

    ``rows`` must be plain dicts that include at minimum the keys:
      - ``symbol``
      - ``market_cap_bucket``
      - ``market_cap_raw_usd``  (used for MEGA ranking; may be empty for non-MEGA)

    Returns a new list of dicts — original dicts are NOT mutated.
    """
    policy_id = str(policy["policy_id"])

    # --- separate MEGA from non-MEGA ---
    mega_dicts: List[Dict[str, Any]] = []
    non_mega_dicts: List[Dict[str, Any]] = []

    for row in rows:
        bucket = str(row.get("market_cap_bucket", "")).strip().upper()
        if bucket == "MEGA":
            mega_dicts.append(row)
        else:
            non_mega_dicts.append(row)

    # --- rank MEGA cohort deterministically ---
    def _sort_key(d: Dict[str, Any]) -> tuple[int, str]:
        raw = d.get("market_cap_raw_usd", 0)
        try:
            cap = int(raw) if raw not in ("", None) else 0
        except (ValueError, TypeError):
            cap = 0
        sym = str(d.get("symbol", "")).strip().upper()
        # Sort descending by cap (negate), ascending by symbol for tie-break
        return (-cap, sym)

    sorted_mega = sorted(mega_dicts, key=_sort_key)

    hyper_n, ultra_n, _ = _compute_mega_thirds(len(sorted_mega))

    enriched: List[Dict[str, Any]] = []

    for i, row in enumerate(sorted_mega):
        if i < hyper_n:
            subtier = "HYPER_MEGA"
        elif i < hyper_n + ultra_n:
            subtier = "ULTRA_MEGA"
        else:
            subtier = "EXTENDED_MEGA"

        enriched.append({
            **row,
            "analytical_market_cap_subtier": subtier,
            "classification_policy_id": policy_id,
            "classification_snapshot_date": snapshot_date,
        })

    for row in non_mega_dicts:
        bucket = str(row.get("market_cap_bucket", "")).strip().upper()
        enriched.append({
            **row,
            "analytical_market_cap_subtier": bucket,  # passthrough
            "classification_policy_id": policy_id,
            "classification_snapshot_date": snapshot_date,
        })

    return enriched
