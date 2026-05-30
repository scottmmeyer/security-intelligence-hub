"""Validators for dynamic analytical market-cap subtier contracts.

All validator functions return a list of error strings — an empty list means
the contract is satisfied.  Raise ValueError only for unrecoverable structural
problems (malformed policy config); use return-list pattern for dataset checks.
"""

from __future__ import annotations

from typing import Any, Dict, List

_MEGA_SUBTIER_LABELS = {"HYPER_MEGA", "ULTRA_MEGA", "EXTENDED_MEGA"}
_FIDELITY_BUCKETS = {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}
_REQUIRED_POLICY_KEYS = {
    "policy_id",
    "methodology_type",
    "partitioning_strategy",
    "ranking_basis",
    "tie_break_rule",
    "partition_rules",
}


def validate_subtier_policy_config(policy: Dict[str, Any]) -> List[str]:
    """Validate that a loaded policy dict satisfies structural contracts.

    Returns a list of error messages; empty list = valid.
    """
    errors: List[str] = []

    if not isinstance(policy, dict):
        return ["Policy config must be a dict."]

    missing = _REQUIRED_POLICY_KEYS - policy.keys()
    if missing:
        errors.append(f"Policy missing required key(s): {sorted(missing)}")

    methodology = str(policy.get("methodology_type", ""))
    if methodology not in {"DYNAMIC_RANK_BASED"}:
        errors.append(
            f"Unsupported methodology_type '{methodology}'. Expected DYNAMIC_RANK_BASED."
        )

    strategy = str(policy.get("partitioning_strategy", ""))
    if strategy not in {"MEGA_ONLY", "ALL_BUCKETS"}:
        errors.append(
            f"Unsupported partitioning_strategy '{strategy}'. "
            "Expected MEGA_ONLY or ALL_BUCKETS."
        )

    rules = policy.get("partition_rules")
    if not isinstance(rules, list) or len(rules) == 0:
        errors.append("partition_rules must be a non-empty list.")

    policy_id = str(policy.get("policy_id", "")).strip()
    if not policy_id:
        errors.append("policy_id must be a non-empty string.")

    return errors


def validate_mega_subtier_coverage(rows: List[Dict[str, Any]]) -> List[str]:
    """All rows with market_cap_bucket=MEGA must have a non-empty MEGA subtier.

    Returns a list of error messages; empty list = valid.
    """
    errors: List[str] = []
    for row in rows:
        bucket = str(row.get("market_cap_bucket", "")).strip().upper()
        if bucket != "MEGA":
            continue
        subtier = str(row.get("analytical_market_cap_subtier", "")).strip().upper()
        if subtier not in _MEGA_SUBTIER_LABELS:
            sym = row.get("symbol", "<unknown>")
            errors.append(
                f"MEGA symbol '{sym}' has invalid analytical_market_cap_subtier='{subtier}'. "
                f"Expected one of {sorted(_MEGA_SUBTIER_LABELS)}."
            )
    return errors


def validate_no_invalid_fidelity_subtier_combo(rows: List[Dict[str, Any]]) -> List[str]:
    """Non-MEGA rows must NOT carry HYPER_MEGA, ULTRA_MEGA, or EXTENDED_MEGA subtiers.

    Returns a list of error messages; empty list = valid.
    """
    errors: List[str] = []
    for row in rows:
        bucket = str(row.get("market_cap_bucket", "")).strip().upper()
        if bucket == "MEGA":
            continue
        subtier = str(row.get("analytical_market_cap_subtier", "")).strip().upper()
        if subtier in _MEGA_SUBTIER_LABELS:
            sym = row.get("symbol", "<unknown>")
            errors.append(
                f"Non-MEGA symbol '{sym}' (bucket={bucket}) has MEGA subtier "
                f"'{subtier}' — invalid Fidelity/subtier combination."
            )
    return errors


def validate_subtier_partitioning_completeness(rows: List[Dict[str, Any]]) -> List[str]:
    """Every row must have a non-empty analytical_market_cap_subtier.

    Returns a list of error messages; empty list = valid.
    """
    errors: List[str] = []
    for row in rows:
        subtier = str(row.get("analytical_market_cap_subtier", "")).strip()
        if not subtier:
            sym = row.get("symbol", "<unknown>")
            errors.append(
                f"Symbol '{sym}' has a missing (empty) analytical_market_cap_subtier."
            )
    return errors


def validate_no_duplicate_rank_assignment(rows: List[Dict[str, Any]]) -> List[str]:
    """Each symbol must appear exactly once within the MEGA cohort subtier assignment.

    Duplicates in the input list indicate a deduplication failure upstream.
    Returns a list of error messages; empty list = valid.
    """
    errors: List[str] = []
    seen: Dict[str, str] = {}  # symbol → subtier
    for row in rows:
        bucket = str(row.get("market_cap_bucket", "")).strip().upper()
        if bucket != "MEGA":
            continue
        sym = str(row.get("symbol", "")).strip().upper()
        subtier = str(row.get("analytical_market_cap_subtier", "")).strip().upper()
        if sym in seen:
            errors.append(
                f"Duplicate MEGA rank assignment for symbol '{sym}': "
                f"first saw '{seen[sym]}', now saw '{subtier}'."
            )
        else:
            seen[sym] = subtier
    return errors
