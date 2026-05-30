#!/usr/bin/env python3
"""Classification integrity audit: validate benchmark assignments, geography, and eligibility flags.

Runs all classification validators (V01-V11) against the current analytical universe.
Writes findings to data/classification_audit/ as JSON + text summary.

Exit codes:
    0 — clean (or only WARNING-level findings)
    1 — one or more EXCEPTION-level findings detected

Usage:
    PYTHONPATH=. .venv/bin/python scripts/run_classification_audit.py
    PYTHONPATH=. .venv/bin/python scripts/run_classification_audit.py --universe data/current/analytical_universe.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.models.analytical_models import AnalyticalUniverseRow
from src.classification.classification_validators import (
    ClassificationFinding,
    FindingLevel,
    validate_universe_classifications,
)

_DEFAULT_UNIVERSE = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
_AUDIT_OUTPUT_DIR = _REPO_ROOT / "data" / "classification_audit"


def _load_universe_rows(path: Path) -> list[AnalyticalUniverseRow]:
    """Load AnalyticalUniverseRow objects from analytical_universe.csv."""
    rows: list[AnalyticalUniverseRow] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            # Bool fields stored as strings in CSV
            def _to_bool(val: str, default: bool = True) -> bool:
                v = str(val or "").strip().lower()
                if v in ("false", "0", "no"):
                    return False
                if v in ("true", "1", "yes"):
                    return True
                return default

            def _to_float(val: str, default: float = 0.0) -> float:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            rows.append(AnalyticalUniverseRow(
                security_id=raw.get("security_id", ""),
                symbol=raw.get("symbol", ""),
                security_type=raw.get("security_type", "UNKNOWN"),
                snapshot_date=raw.get("snapshot_date", ""),
                run_id=raw.get("run_id", ""),
                market_cap_bucket=raw.get("market_cap_bucket", ""),
                geography=raw.get("geography", ""),
                country=raw.get("country", ""),
                industry=raw.get("industry", ""),
                sector=raw.get("sector", ""),
                composite_score=_to_float(raw.get("composite_score", ""), 0.0),
                ess_score_text=raw.get("ess_score_text", ""),
                zacks_rating=raw.get("zacks_rating", ""),
                yahoo_score=raw.get("yahoo_score", ""),
                danelfin_score=raw.get("danelfin_score", ""),
                benchmark_id=raw.get("benchmark_id", ""),
                investable_vehicle_id=raw.get("investable_vehicle_id", ""),
                price_at_snapshot=raw.get("price_at_snapshot", ""),
                provider_lineage=raw.get("provider_lineage", ""),
                analytical_market_cap_subtier=raw.get("analytical_market_cap_subtier", ""),
                classification_policy_id=raw.get("classification_policy_id", ""),
                classification_snapshot_date=raw.get("classification_snapshot_date", ""),
                replay_eligible=_to_bool(raw.get("replay_eligible", ""), True),
                scoring_eligible=_to_bool(raw.get("scoring_eligible", ""), True),
                allocation_eligible=_to_bool(raw.get("allocation_eligible", ""), True),
                benchmark_confidence=raw.get("benchmark_confidence", ""),
                sector_benchmark_id=raw.get("sector_benchmark_id", ""),
                classification_method=raw.get("classification_method", ""),
            ))
    return rows


def _write_audit_report(
    findings: list[ClassificationFinding],
    universe_path: Path,
    output_dir: Path,
) -> dict:
    """Write JSON + text reports to output_dir. Returns summary dict."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    exception_findings = [f for f in findings if f.level == FindingLevel.EXCEPTION]
    warning_findings = [f for f in findings if f.level == FindingLevel.WARNING]

    summary = {
        "audit_timestamp_utc": ts,
        "universe_path": str(universe_path),
        "total_findings": len(findings),
        "exception_count": len(exception_findings),
        "warning_count": len(warning_findings),
        "status": "FAIL" if exception_findings else "PASS",
    }

    findings_dicts = [
        {
            "validator_id": f.validator_id,
            "level": f.level.value,
            "symbol": f.symbol,
            "security_type": f.security_type,
            "geography": f.geography,
            "benchmark_id": f.benchmark_id,
            "message": f.message,
        }
        for f in findings
    ]

    report = {"summary": summary, "findings": findings_dicts}
    json_path = output_dir / f"classification_audit_{ts}.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    text_path = output_dir / f"classification_audit_{ts}.txt"
    with text_path.open("w", encoding="utf-8") as fh:
        fh.write(f"Classification Integrity Audit — {ts}\n")
        fh.write(f"Universe: {universe_path}\n")
        fh.write(f"Status: {summary['status']}\n")
        fh.write(f"Findings: {len(findings)} total ({len(exception_findings)} EXCEPTION, {len(warning_findings)} WARNING)\n")
        fh.write("\n")
        for f in sorted(findings, key=lambda x: (x.level.value, x.validator_id, x.symbol)):
            fh.write(f"[{f.level.value}] {f.validator_id} | {f.symbol} | {f.message}\n")

    # Also write latest symlink for easy access
    latest_path = output_dir / "latest_audit.json"
    with latest_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run classification integrity audit.")
    parser.add_argument(
        "--universe",
        type=Path,
        default=_DEFAULT_UNIVERSE,
        help="Path to analytical_universe.csv",
    )
    args = parser.parse_args()

    universe_path = Path(args.universe)
    if not universe_path.exists():
        print(f"[AUDIT] ERROR: Universe file not found: {universe_path}", file=sys.stderr)
        return 1

    print(f"[AUDIT] Loading universe from {universe_path.name}...")
    rows = _load_universe_rows(universe_path)
    print(f"[AUDIT] Loaded {len(rows)} rows.")

    print("[AUDIT] Running classification validators...")
    findings = validate_universe_classifications(rows)

    summary = _write_audit_report(findings, universe_path, _AUDIT_OUTPUT_DIR)
    print(f"[AUDIT] Status: {summary['status']}")
    print(f"[AUDIT] Findings: {summary['total_findings']} total "
          f"({summary['exception_count']} EXCEPTION, {summary['warning_count']} WARNING)")
    print(f"[AUDIT] Reports written to {_AUDIT_OUTPUT_DIR}/")

    exceptions = [f for f in findings if f.level == FindingLevel.EXCEPTION]
    warnings = [f for f in findings if f.level == FindingLevel.WARNING]

    if warnings:
        print(f"\n--- WARNINGS ({len(warnings)}) ---")
        for f in warnings:
            print(f"  [{f.validator_id}] {f.symbol}: {f.message}")

    if exceptions:
        print(f"\n--- EXCEPTIONS ({len(exceptions)}) ---")
        for f in exceptions:
            print(f"  [{f.validator_id}] {f.symbol}: {f.message}")
        print(f"\n[AUDIT] FAIL — {len(exceptions)} exception(s) require remediation.")
        return 1

    print("\n[AUDIT] PASS — no exceptions detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
