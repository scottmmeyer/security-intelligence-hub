#!/usr/bin/env python3
"""Materialize canonical macro/liquidity series artifacts for reporting-only UI use.

This script fetches authoritative observation CSVs from public FRED graph endpoints,
then writes deterministic local artifacts used by Portfolio Alignment's
Macro & Liquidity Context endpoint.

It is intentionally separate from request handling so UI rendering does not depend
on live network calls.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_PATH = REPO_ROOT / "data" / "current" / "macro_liquidity_series.csv"
HISTORY_ROOT = REPO_ROOT / "data" / "history" / "macro_liquidity"

HEADERS = [
    "series_id",
    "display_name",
    "source_provider",
    "source_agency",
    "units",
    "frequency",
    "expected_update_frequency",
    "observation_date",
    "value",
    "materialized_at_utc",
    "availability",
    "freshness_state",
    "age_days",
    "source_url",
    "series_url",
    "artifact_path",
    "provenance",
]


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    display_name: str
    source_agency: str
    units: str
    frequency: str
    expected_update_frequency: str

    @property
    def source_url(self) -> str:
        return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={self.series_id}"

    @property
    def series_url(self) -> str:
        return f"https://fred.stlouisfed.org/series/{self.series_id}"


SERIES_SPECS: list[SeriesSpec] = [
    SeriesSpec("DGS2", "US 2Y Treasury Constant Maturity", "Board of Governors of the Federal Reserve System", "Percent", "Business Daily", "business_daily"),
    SeriesSpec("DGS10", "US 10Y Treasury Constant Maturity", "Board of Governors of the Federal Reserve System", "Percent", "Business Daily", "business_daily"),
    SeriesSpec("DGS30", "US 30Y Treasury Constant Maturity", "Board of Governors of the Federal Reserve System", "Percent", "Business Daily", "business_daily"),
    SeriesSpec("BAMLC0A0CM", "ICE BofA US Corporate Index Option-Adjusted Spread", "ICE Data Indices, LLC", "Percent", "Business Daily", "business_daily"),
    SeriesSpec("BAMLH0A0HYM2", "ICE BofA US High Yield Index Option-Adjusted Spread", "ICE Data Indices, LLC", "Percent", "Business Daily", "business_daily"),
    SeriesSpec("VIXCLS", "CBOE Volatility Index: VIX", "Chicago Board Options Exchange", "Index", "Business Daily", "business_daily"),
    SeriesSpec("DCOILWTICO", "Crude Oil Prices: West Texas Intermediate (WTI)", "U.S. Energy Information Administration", "USD per Barrel", "Business Daily", "business_daily"),
    SeriesSpec("DCOILBRENTEU", "Crude Oil Prices: Brent - Europe", "U.S. Energy Information Administration", "USD per Barrel", "Business Daily", "business_daily"),
    SeriesSpec("WTREGEN", "Treasury General Account", "Board of Governors of the Federal Reserve System", "Millions of USD", "Weekly", "weekly"),
    SeriesSpec("WRESBAL", "Reserve Balances with Federal Reserve Banks", "Board of Governors of the Federal Reserve System", "Millions of USD", "Weekly", "weekly"),
    SeriesSpec("RRPONTSYD", "Overnight Reverse Repurchase Agreements: Treasury Securities Sold by the Federal Reserve", "Federal Reserve Bank of New York", "Billions of USD", "Business Daily", "business_daily"),
    SeriesSpec("SOFR", "Secured Overnight Financing Rate", "Federal Reserve Bank of New York", "Percent", "Business Daily", "business_daily"),
    SeriesSpec("IORB", "Interest Rate on Reserve Balances", "Board of Governors of the Federal Reserve System", "Percent", "Daily, 7-Day", "daily_7_day_administered_rate"),
    SeriesSpec("DTWEXBGS", "Broad U.S. Dollar Index: Goods", "Board of Governors of the Federal Reserve System", "Index", "Business Daily", "business_daily"),
]


def _fetch_rows(spec: SeriesSpec) -> list[tuple[str, float]]:
    with urlopen(spec.source_url, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    parsed: list[tuple[str, float]] = []
    reader = csv.DictReader(raw.splitlines())
    value_key = spec.series_id
    for row in reader:
        obs = str(row.get("observation_date") or "").strip()
        val_text = str(row.get(value_key) or "").strip()
        if not obs or not val_text or val_text == ".":
            continue
        try:
            parsed.append((obs, float(val_text)))
        except Exception:
            continue
    return parsed


def _freshness_state(observation_date: str, expected_update_frequency: str) -> tuple[str, int]:
    obs = date.fromisoformat(observation_date)
    age = (date.today() - obs).days
    if expected_update_frequency == "weekly":
        state = "FRESH" if age <= 10 else "STALE"
    else:
        state = "FRESH" if age <= 4 else "STALE"
    return state, age


def _write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def materialize(max_observations: int) -> dict[str, object]:
    now_iso = datetime.now(timezone.utc).isoformat()
    current_rows: list[dict[str, str]] = []
    materialized_series: list[str] = []
    unavailable_series: list[str] = []

    for spec in SERIES_SPECS:
        points = _fetch_rows(spec)
        if not points:
            unavailable_series.append(spec.series_id)
            continue

        tail = points[-max_observations:] if max_observations > 0 else points

        partition = HISTORY_ROOT / f"series_id={spec.series_id}" / "observations.csv"
        partition_rows: list[dict[str, str]] = []
        for obs_date, value in tail:
            freshness, age_days = _freshness_state(obs_date, spec.expected_update_frequency)
            partition_rows.append(
                {
                    "series_id": spec.series_id,
                    "display_name": spec.display_name,
                    "source_provider": "FRED",
                    "source_agency": spec.source_agency,
                    "units": spec.units,
                    "frequency": spec.frequency,
                    "expected_update_frequency": spec.expected_update_frequency,
                    "observation_date": obs_date,
                    "value": f"{value}",
                    "materialized_at_utc": now_iso,
                    "availability": "AVAILABLE",
                    "freshness_state": freshness,
                    "age_days": str(age_days),
                    "source_url": spec.source_url,
                    "series_url": spec.series_url,
                    "artifact_path": str(partition.relative_to(REPO_ROOT)),
                    "provenance": json.dumps(
                        {
                            "provider": "FRED",
                            "series_id": spec.series_id,
                            "series_name": spec.display_name,
                            "source_agency": spec.source_agency,
                            "retrieval_method": "fredgraph_csv",
                            "source_url": spec.source_url,
                            "series_url": spec.series_url,
                        },
                        sort_keys=True,
                    ),
                }
            )

        _write_csv(partition, partition_rows)

        latest = partition_rows[-1]
        current_row = dict(latest)
        current_row["artifact_path"] = str(CURRENT_PATH.relative_to(REPO_ROOT))
        current_rows.append(current_row)
        materialized_series.append(spec.series_id)

    current_rows_sorted = sorted(current_rows, key=lambda r: str(r.get("series_id") or ""))
    _write_csv(CURRENT_PATH, current_rows_sorted)

    return {
        "materialized_at_utc": now_iso,
        "series_requested": len(SERIES_SPECS),
        "series_materialized": len(materialized_series),
        "series_unavailable": unavailable_series,
        "current_artifact": str(CURRENT_PATH.relative_to(REPO_ROOT)),
        "history_root": str(HISTORY_ROOT.relative_to(REPO_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize canonical macro/liquidity series artifacts from FRED.")
    parser.add_argument(
        "--max-observations",
        type=int,
        default=1000,
        help="Maximum observations to persist per series (0 keeps all).",
    )
    args = parser.parse_args()

    summary = materialize(max_observations=max(0, args.max_observations))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
