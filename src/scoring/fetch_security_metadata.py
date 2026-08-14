"""Fetch sector, industry, country, and security type metadata from Yahoo Finance.

Enriches the analytical universe with GICS sector and industry classifications
for use in filtering, grouping, and the Symbol Lookup UI panel.

Output CSV: data/signals/security_metadata/YYYY-MM-DD_security_metadata.csv
            data/signals/security_metadata/latest_security_metadata.csv

Columns:
    symbol, sector, industry, country, quote_type, sourced_date,
    metadata_status, failure_type, failure_reason, attempt_count, last_attempt_utc

Status values:
    SUCCESS
        Metadata payload was returned for at least one of sector/industry/country/quote_type.
    PROVIDER_NO_DATA
        Request succeeded, but provider returned no metadata payload.
    RETRYABLE_FAILURE
        Technical failure classified as retryable (for example timeout/rate-limit/network).
    NONRETRYABLE_FAILURE
        Failure classified as non-retryable.
    EMPTY_DUE_TO_PRIOR_TECHNICAL_FAILURE
        Legacy-status normalization marker for historical empty rows without explicit status.

Reliability behavior:
    - Bounded retry is applied for retryable failures.
    - Optional failed-only targeting can retry only failed/legacy-empty rows from the latest cache.
    - If a technical failure occurs for a symbol with previously successful cached metadata,
      the successful cached metadata fields are preserved instead of being replaced by blanks.

Usage:
    # Fetch for all symbols in base_equity_universe:
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --from-universe data/current/base_equity_universe.csv

    # Fetch for specific symbols:
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --symbols MMM AAPL MSFT

    # Smart refresh: skip symbols already fetched in latest cache
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --from-universe data/current/base_equity_universe.csv --smart-refresh

    # Retry only failed/legacy-empty cache rows with explicit retry policy
    PYTHONPATH=. .venv/bin/python src/scoring/fetch_security_metadata.py \
        --from-universe data/current/base_equity_universe.csv \
        --retry-failed-only --max-retries 3 --retry-backoff-seconds 2.0
"""

from __future__ import annotations

import csv
import random
import time
from datetime import date
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Iterable
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "signals" / "security_metadata"
_DEFAULT_DELAY_MIN = 0.3
_DEFAULT_DELAY_MAX = 1.2
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BACKOFF_SECONDS = 2.0

_OUTPUT_HEADERS = [
    "symbol",
    "sector",
    "industry",
    "country",
    "quote_type",
    "sourced_date",
    "metadata_status",
    "failure_type",
    "failure_reason",
    "attempt_count",
    "last_attempt_utc",
]

STATUS_SUCCESS = "SUCCESS"
STATUS_PROVIDER_NO_DATA = "PROVIDER_NO_DATA"
STATUS_RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
STATUS_NONRETRYABLE_FAILURE = "NONRETRYABLE_FAILURE"
STATUS_EMPTY_DUE_TO_PRIOR_TECHNICAL_FAILURE = "EMPTY_DUE_TO_PRIOR_TECHNICAL_FAILURE"

_FAILED_STATUSES = {
    STATUS_RETRYABLE_FAILURE,
    STATUS_NONRETRYABLE_FAILURE,
    STATUS_EMPTY_DUE_TO_PRIOR_TECHNICAL_FAILURE,
}

_METADATA_FIELDS = ("sector", "industry", "country", "quote_type")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_metadata_payload(row: dict[str, str]) -> bool:
    return any(str(row.get(field, "")).strip() for field in _METADATA_FIELDS)


def _classify_fetch_exception(exc: Exception) -> tuple[str, bool]:
    """Return (failure_type, retryable) for fetch exceptions."""
    text = f"{type(exc).__name__}: {exc}".lower()
    type_name = type(exc).__name__.upper()

    if isinstance(exc, TimeoutError) or "timed out" in text or "timeout" in text:
        return "TIMEOUT", True
    if "too many requests" in text or "429" in text or "ratelimit" in text:
        return "RATE_LIMIT", True
    if "tls" in text or "ssl" in text:
        return "TLS", True
    if isinstance(exc, OSError) or "connection" in text or "tempor" in text or "network" in text:
        return "NETWORK", True
    if "http" in text and any(code in text for code in ("500", "502", "503", "504")):
        return "HTTP_5XX", True

    return type_name, False


def _fetch_security_metadata_once(symbol: str) -> tuple[dict[str, str], str, str, str]:
    """Fetch one symbol once; return data + status + failure classification."""
    import yfinance as yf  # type: ignore

    sym = str(symbol).strip().upper()
    result: dict[str, str] = {
        "sector": "",
        "industry": "",
        "country": "",
        "quote_type": "",
    }

    try:
        ticker = yf.Ticker(sym)
        info = ticker.info or {}
    except Exception as exc:
        failure_type, retryable = _classify_fetch_exception(exc)
        status = STATUS_RETRYABLE_FAILURE if retryable else STATUS_NONRETRYABLE_FAILURE
        return result, status, failure_type, f"{type(exc).__name__}: {exc}"

    result["sector"] = str(info.get("sector") or "").strip()
    result["industry"] = str(info.get("industry") or "").strip()
    result["country"] = str(info.get("country") or "").strip()
    result["quote_type"] = str(info.get("quoteType") or "").strip()

    if _has_metadata_payload(result):
        return result, STATUS_SUCCESS, "", ""
    return result, STATUS_PROVIDER_NO_DATA, "", ""


def fetch_security_metadata(symbol: str) -> dict[str, str]:
    """Backward-compatible wrapper returning metadata fields only."""
    data, _status, _failure_type, _failure_reason = _fetch_security_metadata_once(symbol)
    return data


def _fetch_security_metadata_with_retry(
    symbol: str,
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = _DEFAULT_RETRY_BACKOFF_SECONDS,
) -> tuple[dict[str, str], str, str, str, int]:
    """Fetch one symbol with bounded retry for retryable failures."""
    attempts = 0
    last_data: dict[str, str] = {
        "sector": "",
        "industry": "",
        "country": "",
        "quote_type": "",
    }
    last_status = STATUS_RETRYABLE_FAILURE
    last_failure_type = "UNKNOWN"
    last_failure_reason = ""

    retries = max(1, int(max_retries))
    for attempt in range(1, retries + 1):
        attempts = attempt
        data, status, failure_type, failure_reason = _fetch_security_metadata_once(symbol)
        last_data = data
        last_status = status
        last_failure_type = failure_type
        last_failure_reason = failure_reason
        if status != STATUS_RETRYABLE_FAILURE:
            return data, status, failure_type, failure_reason, attempts
        if attempt < retries and retry_backoff_seconds > 0:
            time.sleep(retry_backoff_seconds * attempt)

    return last_data, last_status, last_failure_type, last_failure_reason, attempts


def _normalize_existing_row_status(row: dict[str, str]) -> dict[str, str]:
    """Normalize legacy rows that predate explicit metadata status fields."""
    normalized = dict(row)
    raw_status = str(normalized.get("metadata_status", "")).strip().upper()
    if raw_status:
        normalized["metadata_status"] = raw_status
        return normalized
    if _has_metadata_payload(normalized):
        normalized["metadata_status"] = STATUS_SUCCESS
    else:
        normalized["metadata_status"] = STATUS_EMPTY_DUE_TO_PRIOR_TECHNICAL_FAILURE
    return normalized


def _row_needs_failed_retry(row: Optional[dict[str, str]]) -> bool:
    if not row:
        return True
    status = str(row.get("metadata_status", "")).strip().upper()
    if status in _FAILED_STATUSES:
        return True
    if not status and not _has_metadata_payload(row):
        return True
    return False


def load_latest_security_metadata(
    signals_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> dict[str, dict[str, str]]:
    """Load latest security metadata cache into a symbol → field dict."""
    signals_dir = Path(signals_dir)
    latest_path = signals_dir / "latest_security_metadata.csv"
    if not latest_path.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    with latest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_OUTPUT_HEADERS, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)


def fetch_security_metadata_for_symbols(
    symbols: Iterable[str],
    *,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    delay_min: float = _DEFAULT_DELAY_MIN,
    delay_max: float = _DEFAULT_DELAY_MAX,
    smart_refresh: bool = False,
    retry_failed_only: bool = False,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = _DEFAULT_RETRY_BACKOFF_SECONDS,
    verbose: bool = True,
    collect_stats: bool = False,
) -> Path | tuple[Path, dict[str, int]]:
    """Fetch metadata for all symbols, merge with existing cache, write CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_path = output_dir / f"{today}_security_metadata.csv"
    latest_path = output_dir / "latest_security_metadata.csv"

    symbol_list = [str(s).strip().upper() for s in symbols if str(s).strip()]

    # Smart refresh: load existing cache and skip already-fetched symbols
    existing: dict[str, dict[str, str]] = {}
    if latest_path.exists():
        existing = {
            sym: _normalize_existing_row_status(row)
            for sym, row in load_latest_security_metadata(output_dir).items()
        }
    if smart_refresh and verbose:
        print(f"Smart refresh: {len(existing)} symbols already cached")

    if retry_failed_only:
        to_fetch = [s for s in symbol_list if _row_needs_failed_retry(existing.get(s))]
    elif smart_refresh:
        to_fetch = [s for s in symbol_list if s not in existing]
    else:
        to_fetch = symbol_list

    if verbose:
        print(f"Fetching metadata for {len(to_fetch)} symbols (skipping {len(symbol_list) - len(to_fetch)} cached)...")

    new_rows: dict[str, dict[str, str]] = {}
    stats = {
        "requested": len(symbol_list),
        "attempted": len(to_fetch),
        "skipped_checkpoint": len(symbol_list) - len(to_fetch),
        "retried_failed_checkpoint": 0,
        "success": 0,
        "provider_no_data": 0,
        "retryable_failure": 0,
        "nonretryable_failure": 0,
        "preserved_existing_rows": 0,
    }
    if retry_failed_only:
        stats["retried_failed_checkpoint"] = len(to_fetch)

    for i, sym in enumerate(to_fetch, start=1):
        if verbose:
            print(f"[{i}/{len(to_fetch)}] {sym}...", end=" ", flush=True)

        data, status, failure_type, failure_reason, attempts = _fetch_security_metadata_with_retry(
            sym,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        time.sleep(random.uniform(delay_min, delay_max))

        existing_row = existing.get(sym, {})
        row_payload = dict(data)
        if status in (STATUS_RETRYABLE_FAILURE, STATUS_NONRETRYABLE_FAILURE):
            if _has_metadata_payload(existing_row):
                # Preserve previously successful metadata on technical failure.
                for field in _METADATA_FIELDS:
                    row_payload[field] = str(existing_row.get(field, "")).strip()
                stats["preserved_existing_rows"] += 1
            else:
                for field in _METADATA_FIELDS:
                    row_payload[field] = ""

        if status == STATUS_SUCCESS:
            stats["success"] += 1
        elif status == STATUS_PROVIDER_NO_DATA:
            stats["provider_no_data"] += 1
        elif status == STATUS_RETRYABLE_FAILURE:
            stats["retryable_failure"] += 1
        else:
            stats["nonretryable_failure"] += 1

        row = {
            "symbol": sym,
            "sector": row_payload["sector"],
            "industry": row_payload["industry"],
            "country": row_payload["country"],
            "quote_type": row_payload["quote_type"],
            "sourced_date": today,
            "metadata_status": status,
            "failure_type": failure_type,
            "failure_reason": failure_reason,
            "attempt_count": str(attempts),
            "last_attempt_utc": _utc_now_iso(),
        }
        new_rows[sym] = row

        if verbose:
            parts = []
            if row["sector"]:
                parts.append(row["sector"])
            if row["industry"]:
                parts.append(row["industry"])
            if row["country"]:
                parts.append(row["country"])
            if row["quote_type"] and row["quote_type"] != "EQUITY":
                parts.append(row["quote_type"])
            parts.append(f"status={status}")
            if failure_type:
                parts.append(f"failure={failure_type}")
            print(" | ".join(parts) if parts else f"status={status}")

    # Merge: new rows override existing, preserve existing for symbols not re-fetched
    merged: dict[str, dict[str, str]] = {**existing, **new_rows}

    # Output in the order of the requested symbol list (preserving original order)
    ordered_rows = [merged[s] for s in symbol_list if s in merged]
    # Append any symbols from existing that weren't in the request
    seen = set(symbol_list)
    for s, row in existing.items():
        if s not in seen:
            ordered_rows.append(row)

    _write_csv(output_path, ordered_rows)
    _write_csv(latest_path, ordered_rows)

    with_sector = sum(1 for r in ordered_rows if r.get("sector"))
    etf_count = sum(1 for r in ordered_rows if r.get("quote_type") == "ETF")

    if verbose:
        print(
            f"\nSecurity metadata fetch complete: "
            f"{with_sector}/{len(ordered_rows)} with sector, "
            f"{etf_count} ETFs, "
            f"success={stats['success']}, "
            f"provider_no_data={stats['provider_no_data']}, "
            f"retryable_failure={stats['retryable_failure']}, "
            f"nonretryable_failure={stats['nonretryable_failure']}, "
            f"preserved_existing_rows={stats['preserved_existing_rows']} "
            f"→ {output_path}"
        )

    if collect_stats:
        return output_path, stats
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch sector/industry metadata from Yahoo Finance.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", nargs="+", help="Symbols to fetch")
    group.add_argument("--from-universe", help="Path to base_equity_universe.csv or analytical_universe.csv")
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUTPUT_DIR))
    parser.add_argument("--delay-min", type=float, default=_DEFAULT_DELAY_MIN)
    parser.add_argument("--delay-max", type=float, default=_DEFAULT_DELAY_MAX)
    parser.add_argument("--smart-refresh", action="store_true", help="Skip symbols already in latest cache")
    parser.add_argument(
        "--retry-failed-only",
        action="store_true",
        help=(
            "Retry only symbols with failed/legacy-empty status in latest cache; "
            "preserves successful rows"
        ),
    )
    parser.add_argument("--max-retries", type=int, default=_DEFAULT_MAX_RETRIES)
    parser.add_argument("--retry-backoff-seconds", type=float, default=_DEFAULT_RETRY_BACKOFF_SECONDS)
    args = parser.parse_args()

    if args.symbols:
        symbols = args.symbols
    else:
        universe_path = Path(args.from_universe)
        with universe_path.open("r", encoding="utf-8", newline="") as f:
            symbols = [row["symbol"] for row in csv.DictReader(f) if row.get("symbol", "").strip()]
        # Deduplicate while preserving order
        seen_set: set[str] = set()
        unique: list[str] = []
        for s in symbols:
            su = s.strip().upper()
            if su not in seen_set:
                seen_set.add(su)
                unique.append(su)
        symbols = unique
        print(f"Loaded {len(symbols)} unique symbols from {universe_path.name}")

    fetch_security_metadata_for_symbols(
        symbols,
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        smart_refresh=args.smart_refresh,
        retry_failed_only=args.retry_failed_only,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
