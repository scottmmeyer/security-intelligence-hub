"""Security type policy: maps raw security_type strings to canonical class + eligibility flags.

Loads config/security_type_policy.yaml and provides:
  - get_type_info(raw_security_type) -> SecurityTypeInfo
  - is_replay_eligible(raw_security_type) -> bool
  - is_scoring_eligible(raw_security_type) -> bool
  - is_allocation_eligible(raw_security_type) -> bool
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_POLICY_PATH = _REPO_ROOT / "config" / "security_type_policy.yaml"

# Canonical class names as constants for safe comparison
CANONICAL_EQUITY = "EQUITY"
CANONICAL_ETF = "ETF"
CANONICAL_MUTUAL_FUND = "MUTUAL_FUND"
CANONICAL_BOND = "BOND"
CANONICAL_DIGITAL_ASSET = "DIGITAL_ASSET"
CANONICAL_UNKNOWN = "UNKNOWN"

KNOWN_CANONICAL_CLASSES = {
    CANONICAL_EQUITY,
    CANONICAL_ETF,
    CANONICAL_MUTUAL_FUND,
    CANONICAL_BOND,
    CANONICAL_DIGITAL_ASSET,
    CANONICAL_UNKNOWN,
}


@dataclass(frozen=True)
class SecurityTypeInfo:
    """Resolved canonical classification + eligibility flags for a security type."""

    raw_security_type: str
    canonical_class: str
    replay_eligible: bool
    scoring_eligible: bool
    allocation_eligible: bool
    resolved_from_mapping: bool
    """True if matched via type_mappings; False if defaulted to UNKNOWN class."""


class SecurityTypePolicy:
    """Loaded security type policy providing fast type lookups."""

    def __init__(self, policy_data: dict) -> None:
        self._class_eligibility: Dict[str, Dict[str, bool]] = {}
        self._type_map: Dict[str, str] = {}  # normalized raw → canonical_class

        for cls_name, flags in policy_data.get("canonical_classes", {}).items():
            self._class_eligibility[cls_name] = {
                "replay_eligible": bool(flags.get("replay_eligible", True)),
                "scoring_eligible": bool(flags.get("scoring_eligible", True)),
                "allocation_eligible": bool(flags.get("allocation_eligible", True)),
            }

        for entry in policy_data.get("type_mappings", []):
            raw = str(entry.get("raw", "")).strip()
            canonical = str(entry.get("canonical_class", "")).strip()
            if raw and canonical:
                self._type_map[raw.lower()] = canonical

    def get_type_info(self, raw_security_type: str) -> SecurityTypeInfo:
        """Return SecurityTypeInfo for the given raw security_type string.

        Matching is case-insensitive exact lookup first. Unrecognized strings
        fall back to CANONICAL_UNKNOWN with conservative (True) eligibility.
        """
        normalized = str(raw_security_type or "").strip().lower()
        canonical = self._type_map.get(normalized)
        resolved = canonical is not None

        if not resolved:
            canonical = CANONICAL_UNKNOWN

        flags = self._class_eligibility.get(canonical, {
            "replay_eligible": True,
            "scoring_eligible": True,
            "allocation_eligible": True,
        })

        return SecurityTypeInfo(
            raw_security_type=str(raw_security_type or "").strip(),
            canonical_class=canonical,
            replay_eligible=flags["replay_eligible"],
            scoring_eligible=flags["scoring_eligible"],
            allocation_eligible=flags["allocation_eligible"],
            resolved_from_mapping=resolved,
        )

    def is_replay_eligible(self, raw_security_type: str) -> bool:
        return self.get_type_info(raw_security_type).replay_eligible

    def is_scoring_eligible(self, raw_security_type: str) -> bool:
        return self.get_type_info(raw_security_type).scoring_eligible

    def is_allocation_eligible(self, raw_security_type: str) -> bool:
        return self.get_type_info(raw_security_type).allocation_eligible


def load_security_type_policy(
    path: Path | str = _DEFAULT_POLICY_PATH,
) -> SecurityTypePolicy:
    """Load and return a SecurityTypePolicy from the given YAML path."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Security type policy not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return SecurityTypePolicy(data)
