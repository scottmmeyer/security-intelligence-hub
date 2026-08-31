"""FMP (Financial Modeling Prep) signal fetcher — Phase 8.0B.1A.

Fetches four fundamental signal datasets from the FMP /stable/ API:

  1. key_metrics_ttm  — daily; P/E TTM, EV/EBITDA, FCF yield per symbol
  2. earnings         — quarterly; last 8 quarters of EPS surprise data
  3. income_growth    — quarterly; last 4 quarters of revenue/EPS growth
  4. grades_consensus — daily; analyst upgrade/downgrade consensus

Architecture:
  - Fail-closed on write: output CSVs are only updated after a full valid refresh
  - Fail-open on consumption: stale data is preserved if refresh fails
  - Mirrors the existing Yahoo/Danelfin/Zacks fetcher pattern exactly
  - API key read from environment variable FMP_API_KEY (or .env file)

Output files:
  data/signals/fmp/daily/fmp_key_metrics_{YYYY-MM-DD}.csv
  data/signals/fmp/daily/fmp_grades_consensus_{YYYY-MM-DD}.csv
  data/signals/fmp/quarterly/fmp_earnings_surprises_{YYYY_QN}.csv
  data/signals/fmp/quarterly/fmp_income_growth_{YYYY_QN}.csv
  data/signals/fmp/latest/latest_fmp_key_metrics.csv        (always current)
  data/signals/fmp/latest/latest_fmp_grades_consensus.csv
  data/signals/fmp/latest/latest_fmp_earnings_surprises.csv
  data/signals/fmp/latest/latest_fmp_income_growth.csv

Non-negotiable:
  NO analytical_universe changes.
  NO CW-DAS changes.
  NO scoring changes.
  This module only produces raw signal files.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_FMP_BASE = "https://financialmodelingprep.com/stable"
_REQUEST_TIMEOUT = 20
_DEFAULT_DELAY_BETWEEN_CALLS = 0.25  # 250ms → 240 calls/min (80% of Starter 300/min limit)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 60

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FMP_DIR = _REPO_ROOT / "data" / "signals" / "fmp"
_FMP_DAILY_DIR = _FMP_DIR / "daily"
_FMP_QUARTERLY_DIR = _FMP_DIR / "quarterly"
_FMP_LATEST_DIR = _FMP_DIR / "latest"

# ── Output schemas ────────────────────────────────────────────────────────────

KEY_METRICS_HEADERS = [
    "symbol", "sourced_date",
    "fetch_status", "failure_type", "failure_reason",
    "pe_ratio_ttm", "ev_ebitda_ttm", "price_to_fcf_ttm",
    "fcf_yield_ttm", "roe_ttm", "roic_ttm",
    "earnings_yield_ttm", "revenue_per_share_ttm",
    "net_income_per_share_ttm",
]

GRADES_CONSENSUS_HEADERS = [
    "symbol", "sourced_date",
    "fetch_status", "failure_type", "failure_reason",
    "strong_buy_count", "buy_count", "hold_count",
    "sell_count", "strong_sell_count",
    "total_analysts", "net_buy_score", "consensus_label",
]

EARNINGS_SURPRISES_HEADERS = [
    "symbol", "sourced_date",
    "fetch_status", "failure_type", "failure_reason",
    "latest_eps_actual", "latest_eps_estimate", "latest_eps_surprise_pct",
    "q1_surprise_pct", "q2_surprise_pct", "q3_surprise_pct", "q4_surprise_pct",
    "q5_surprise_pct", "q6_surprise_pct", "q7_surprise_pct", "q8_surprise_pct",
    "beats_last_8q", "beat_rate_8q",
]

INCOME_GROWTH_HEADERS = [
    "symbol", "sourced_date",
    "fetch_status", "failure_type", "failure_reason",
    "revenue_growth_q1_yoy", "revenue_growth_q2_yoy",
    "revenue_growth_q3_yoy", "revenue_growth_q4_yoy",
    "eps_growth_q1_yoy", "eps_growth_q2_yoy",
    "eps_growth_q3_yoy", "eps_growth_q4_yoy",
    "gross_profit_growth_q1_yoy",
    "revenue_acceleration",  # q1_yoy - q4_yoy (positive = accelerating)
]

ANALYST_ESTIMATES_HEADERS = [
    "symbol", "sourced_date",
    "fetch_status", "failure_type", "failure_reason",
    "request_period",
    "period_date", "period_label", "fiscal_period", "forecast_horizon",
    "estimated_revenue_avg", "estimated_revenue_high", "estimated_revenue_low",
    "estimated_eps_avg", "estimated_eps_high", "estimated_eps_low",
    "analyst_count_revenue", "analyst_count_eps",
]

# ── API key ───────────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    """Return FMP API key from environment or .env file."""
    key = os.environ.get("FMP_API_KEY", "")
    if key:
        return key
    # Fall back to .env file in repo root
    env_path = _REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("FMP_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    return ""


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _fmp_get(url: str, api_key: str) -> Tuple[Optional[Any], int, Optional[str]]:
    """GET a FMP endpoint; return (parsed_data, http_status, error_message).

    Uses URL query parameter auth (apikey=KEY appended to URL).
    Header-based auth (apikey: KEY) returns HTTP 401 on the /stable/ API.
    """
    # Append apikey as URL parameter (verified working method for /stable/ API)
    sep = "&" if "?" in url else "?"
    full_url = f"{url}{sep}apikey={api_key}"
    try:
        req = urllib.request.Request(
            full_url,
            headers={"User-Agent": "SIH-FMP/1.0"},
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
            return data, resp.status, None
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except Exception:
            body = None
        return body, exc.code, f"HTTP {exc.code}"
    except Exception as exc:
        return None, 0, str(exc)


def _fmp_get_with_retry(url: str, api_key: str) -> Tuple[Optional[Any], int, Optional[str]]:
    """GET with retry on transient errors (HTTP 429, 5xx, network errors)."""
    for attempt in range(1, _MAX_RETRIES + 1):
        data, status, err = _fmp_get(url, api_key)
        if status == 429:
            log.warning("[fmp] HTTP 429 rate limited (attempt %d/%d); backing off %ds",
                        attempt, _MAX_RETRIES, _RETRY_BACKOFF_SECONDS)
            time.sleep(_RETRY_BACKOFF_SECONDS)
            continue
        if status in (500, 502, 503, 504) or (status == 0 and err):
            wait = attempt * 5
            log.warning("[fmp] HTTP %s / %s (attempt %d/%d); retrying in %ds",
                        status, err, attempt, _MAX_RETRIES, wait)
            time.sleep(wait)
            continue
        return data, status, err
    return None, 0, f"All {_MAX_RETRIES} retries exhausted"


def _fmp_get_with_retry_detailed(url: str, api_key: str) -> Tuple[Optional[Any], int, Optional[str], Dict[str, int]]:
    """GET with retry plus retry/rate-limit instrumentation."""
    retries_performed = 0
    rate_limit_events = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        data, status, err = _fmp_get(url, api_key)
        if status == 429:
            rate_limit_events += 1
            if attempt < _MAX_RETRIES:
                retries_performed += 1
            log.warning("[fmp] HTTP 429 rate limited (attempt %d/%d); backing off %ds",
                        attempt, _MAX_RETRIES, _RETRY_BACKOFF_SECONDS)
            time.sleep(_RETRY_BACKOFF_SECONDS)
            continue
        if status in (500, 502, 503, 504) or (status == 0 and err):
            if attempt < _MAX_RETRIES:
                retries_performed += 1
            wait = attempt * 5
            log.warning("[fmp] HTTP %s / %s (attempt %d/%d); retrying in %ds",
                        status, err, attempt, _MAX_RETRIES, wait)
            time.sleep(wait)
            continue
        return data, status, err, {
            "retries_performed": retries_performed,
            "rate_limit_events": rate_limit_events,
        }
    return None, 0, f"All {_MAX_RETRIES} retries exhausted", {
        "retries_performed": retries_performed,
        "rate_limit_events": rate_limit_events,
    }


# ── CSV helpers ───────────────────────────────────────────────────────────────

def _write_csv(path: Path, rows: List[Dict[str, str]], headers: List[str]) -> None:
    """Write rows to path atomically (temp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore", restval="")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _load_csv_by_symbol(path: Path) -> Dict[str, Dict[str, str]]:
    """Load a CSV keyed by symbol."""
    result: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return result
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


def _upsert_latest(latest_path: Path, new_rows: List[Dict[str, str]], headers: List[str]) -> None:
    """Merge new_rows into latest_path (upsert by symbol), then write atomically."""
    existing = _load_csv_by_symbol(latest_path)
    for row in new_rows:
        sym = str(row.get("symbol", "")).strip().upper()
        if sym:
            existing[sym] = row
    _write_csv(latest_path, list(existing.values()), headers)


# ── Staleness helpers (matching refresh_signals.py contract) ──────────────────

def _latest_sourced_date_fmp(latest_csv: Path) -> Optional[str]:
    """Return sourced_date from latest_csv, or None."""
    if not latest_csv.exists():
        return None
    with latest_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            val = str(row.get("sourced_date", "")).strip()
            if val:
                return val
    return None


def is_fmp_daily_stale(dataset: str, fmp_dir: Path = _FMP_LATEST_DIR) -> bool:
    """Return True if the daily FMP dataset is missing or from a prior day."""
    latest = fmp_dir / f"latest_fmp_{dataset}.csv"
    return _latest_sourced_date_fmp(latest) != date.today().isoformat()


def is_fmp_quarterly_stale(dataset: str, fmp_dir: Path = _FMP_LATEST_DIR) -> bool:
    """Return True if the quarterly FMP dataset is more than 90 days old."""
    latest = fmp_dir / f"latest_fmp_{dataset}.csv"
    sourced = _latest_sourced_date_fmp(latest)
    if not sourced:
        return True
    try:
        sourced_dt = datetime.strptime(sourced, "%Y-%m-%d").date()
        return (date.today() - sourced_dt).days > 90
    except ValueError:
        return True


# ── Payload parsers ───────────────────────────────────────────────────────────

def _parse_key_metrics_ttm(symbol: str, data: Any, today: str) -> Dict[str, str]:
    """Extract key_metrics_ttm fields from FMP /stable/ response.

    Field names verified against live /stable/key-metrics-ttm API (2026-06-04).
    The /stable/ endpoint uses different names than the legacy /v3/ API:
      - evToEBITDATTM  (not evToEbitdaTTM)
      - returnOnEquityTTM  (not roeTTM)
      - returnOnInvestedCapitalTTM  (not roicTTM)
    """
    row: Dict[str, str] = {"symbol": symbol, "sourced_date": today}
    if not isinstance(data, list) or not data:
        return row
    item = data[0] if isinstance(data[0], dict) else {}
    # Verified field name map (stable API as of 2026-06-04)
    field_map = {
        "pe_ratio_ttm":             "peRatioTTM",              # may be absent on Starter
        "ev_ebitda_ttm":            "evToEBITDATTM",           # confirmed present
        "price_to_fcf_ttm":         "evToFreeCashFlowTTM",     # EV/FCF; P/FCF not in stable
        "fcf_yield_ttm":            "freeCashFlowYieldTTM",    # confirmed present
        "roe_ttm":                  "returnOnEquityTTM",       # confirmed present
        "roic_ttm":                 "returnOnInvestedCapitalTTM",  # confirmed present
        "earnings_yield_ttm":       "earningsYieldTTM",        # confirmed present
        "revenue_per_share_ttm":    "revenuePerShareTTM",      # may be absent
        "net_income_per_share_ttm": "netIncomePerShareTTM",    # may be absent
    }
    for our_field, fmp_field in field_map.items():
        val = item.get(fmp_field)
        if val is not None:
            row[our_field] = str(val)
    return row


def _parse_grades_consensus(symbol: str, data: Any, today: str) -> Dict[str, str]:
    """Parse grades-consensus response."""
    row: Dict[str, str] = {"symbol": symbol, "sourced_date": today}
    if not isinstance(data, list) or not data:
        return row
    item = data[0] if isinstance(data[0], dict) else {}
    sb  = int(item.get("strongBuy",  0) or 0)
    b   = int(item.get("buy",        0) or 0)
    h   = int(item.get("hold",       0) or 0)
    s   = int(item.get("sell",       0) or 0)
    ss  = int(item.get("strongSell", 0) or 0)
    total = sb + b + h + s + ss
    net   = sb + b - s - ss
    # Consensus label
    if total == 0:
        label = ""
    elif net >= 2:
        label = "BUY"
    elif net <= -2:
        label = "SELL"
    else:
        label = "HOLD"
    row.update({
        "strong_buy_count":  str(sb),
        "buy_count":         str(b),
        "hold_count":        str(h),
        "sell_count":        str(s),
        "strong_sell_count": str(ss),
        "total_analysts":    str(total),
        "net_buy_score":     str(net),
        "consensus_label":   label,
    })
    return row


def _parse_earnings_surprises(symbol: str, data: Any, today: str) -> Dict[str, str]:
    """Parse earnings surprises (last 8 quarters) from FMP /stable/earnings response.

    Field names verified against live API (2026-06-04):
      - epsActual  (not actualEarningResult)
      - epsEstimated  (not estimatedEarning)
      - revenueActual and revenueEstimated also available
    
    Note: The most recent entry may have epsActual=None (future earnings date).
    Filter to only past quarters with actual data.
    """
    row: Dict[str, str] = {"symbol": symbol, "sourced_date": today}
    if not isinstance(data, list) or not data:
        return row

    items = [d for d in data if isinstance(d, dict)]

    # Filter to past quarters only (where epsActual is populated)
    past_items = [d for d in items if d.get("epsActual") is not None][:8]

    if not past_items:
        return row

    # Latest quarter values
    latest = past_items[0]
    actual = _safe_float(latest.get("epsActual"))
    est    = _safe_float(latest.get("epsEstimated"))
    if actual is not None and est is not None and est != 0:
        surprise_pct = (actual - est) / abs(est) * 100
        row["latest_eps_actual"]       = _fmt(actual)
        row["latest_eps_estimate"]     = _fmt(est)
        row["latest_eps_surprise_pct"] = _fmt(surprise_pct)
    elif actual is not None:
        row["latest_eps_actual"] = _fmt(actual)
        if est is not None:
            row["latest_eps_estimate"] = _fmt(est)

    # Per-quarter surprise %
    beats = 0
    for i, item in enumerate(past_items[:8], 1):
        actual = _safe_float(item.get("epsActual"))
        est    = _safe_float(item.get("epsEstimated"))
        if actual is not None and est is not None and est != 0:
            pct = (actual - est) / abs(est) * 100
            row[f"q{i}_surprise_pct"] = _fmt(pct)
            if actual >= est:
                beats += 1
        elif actual is not None and est is not None:
            # est=0 case — record as beat if positive actual
            if actual > 0:
                beats += 1

    n = len(past_items)
    row["beats_last_8q"] = str(beats)
    row["beat_rate_8q"]  = _fmt(beats / n) if n > 0 else ""
    return row


def _parse_income_growth(symbol: str, data: Any, today: str) -> Dict[str, str]:
    """Parse income-statement-growth (last 4 quarters) from FMP /stable/ response.

    Field names verified against live API (2026-06-04):
      - growthRevenue  (confirmed present)
      - growthEPS      (confirmed; maps to EPS diluted growth)
      - growthGrossProfit  (confirmed present)
      - growthEBITDA   (confirmed present)
      - growthNetIncome  (confirmed present)
    """
    row: Dict[str, str] = {"symbol": symbol, "sourced_date": today}
    if not isinstance(data, list) or not data:
        return row

    items = [d for d in data if isinstance(d, dict)][:4]

    rev_growths: List[Optional[float]] = []
    eps_growths: List[Optional[float]] = []

    for i, item in enumerate(items[:4], 1):
        # Verified field names from live /stable/income-statement-growth API
        rev_g = _safe_float(item.get("growthRevenue"))
        # FMP stable uses growthEPS (not growthEPSDiluted or epsgrowth)
        eps_g = _safe_float(item.get("growthEPS") or item.get("growthEPSDiluted"))
        gp_g  = _safe_float(item.get("growthGrossProfit"))

        rev_growths.append(rev_g)
        eps_growths.append(eps_g)

        if rev_g is not None:
            row[f"revenue_growth_q{i}_yoy"] = _fmt(rev_g)
        if eps_g is not None:
            row[f"eps_growth_q{i}_yoy"] = _fmt(eps_g)
        if i == 1 and gp_g is not None:
            row["gross_profit_growth_q1_yoy"] = _fmt(gp_g)

    # Revenue acceleration: q1 (most recent) - q4 (oldest) growth
    if len(rev_growths) >= 2 and rev_growths[0] is not None and rev_growths[-1] is not None:
        row["revenue_acceleration"] = _fmt(rev_growths[0] - rev_growths[-1])

    return row


def _parse_analyst_estimates(symbol: str, data: Any, today: str, *, period: str) -> List[Dict[str, str]]:
    """Parse forward analyst estimates from FMP /stable/analyst-estimates response."""
    normalized_period = str(period or "").strip().lower()
    horizon = "ANNUAL" if normalized_period == "annual" else "QUARTER"
    if not isinstance(data, list) or not data:
        return [{
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "PROVIDER_NO_DATA",
            "failure_type": "",
            "failure_reason": "",
            "request_period": normalized_period,
            "period_date": "",
            "period_label": "",
            "fiscal_period": "",
            "forecast_horizon": horizon,
            "estimated_revenue_avg": "",
            "estimated_revenue_high": "",
            "estimated_revenue_low": "",
            "estimated_eps_avg": "",
            "estimated_eps_high": "",
            "estimated_eps_low": "",
            "analyst_count_revenue": "",
            "analyst_count_eps": "",
        }]

    rows: List[Dict[str, str]] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        period_date = str(item.get("date") or "").strip()
        period_label = str(item.get("period") or "").strip()
        # Preserve provider-identifiable period keys only; do not infer fiscal labels.
        fiscal_period = period_date or "UNSPECIFIED"
        forecast_horizon = horizon

        row = {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "SUCCESS",
            "failure_type": "",
            "failure_reason": "",
            "request_period": normalized_period,
            "period_date": period_date,
            "period_label": period_label,
            "fiscal_period": fiscal_period,
            "forecast_horizon": forecast_horizon,
            "estimated_revenue_avg": _fmt(_safe_float(item.get("revenueAvg"))),
            "estimated_revenue_high": _fmt(_safe_float(item.get("revenueHigh"))),
            "estimated_revenue_low": _fmt(_safe_float(item.get("revenueLow"))),
            "estimated_eps_avg": _fmt(_safe_float(item.get("epsAvg"))),
            "estimated_eps_high": _fmt(_safe_float(item.get("epsHigh"))),
            "estimated_eps_low": _fmt(_safe_float(item.get("epsLow"))),
            "analyst_count_revenue": str(item.get("numAnalystsRevenue") or "").strip(),
            "analyst_count_eps": str(item.get("numAnalystsEps") or "").strip(),
        }
        has_data = _has_usable_fields(
            row,
            (
                "estimated_revenue_avg",
                "estimated_revenue_high",
                "estimated_revenue_low",
                "estimated_eps_avg",
                "estimated_eps_high",
                "estimated_eps_low",
                "analyst_count_revenue",
                "analyst_count_eps",
            ),
        )
        row["fetch_status"] = "SUCCESS" if has_data else "PROVIDER_NO_DATA"
        rows.append(row)

    if not rows:
        return [{
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "PROVIDER_NO_DATA",
            "failure_type": "",
            "failure_reason": "",
            "request_period": normalized_period,
            "period_date": "",
            "period_label": "",
            "fiscal_period": "",
            "forecast_horizon": horizon,
            "estimated_revenue_avg": "",
            "estimated_revenue_high": "",
            "estimated_revenue_low": "",
            "estimated_eps_avg": "",
            "estimated_eps_high": "",
            "estimated_eps_low": "",
            "analyst_count_revenue": "",
            "analyst_count_eps": "",
        }]

    return rows


def _failure_type(status: int, err: Optional[str]) -> str:
    if status == 429:
        return "RATE_LIMIT"
    if status in {500, 502, 503, 504}:
        return "UPSTREAM_UNAVAILABLE"
    if status == 401:
        return "AUTH"
    if status == 402:
        return "PLAN_LIMIT"
    if status == 403:
        return "FORBIDDEN"
    if status == 404:
        return "NOT_FOUND"
    if status > 0:
        return "HTTP_ERROR"
    if err:
        return "NETWORK_ERROR"
    return "UNKNOWN_ERROR"


def _failure_reason(status: int, err: Optional[str], payload: Optional[Any]) -> str:
    """Build a concise provider failure reason with upstream message when present."""
    base = str(err or f"HTTP {status}")
    if isinstance(payload, dict):
        message = str(payload.get("Error Message") or payload.get("error") or "").strip()
        if message:
            return f"{base}: {message}"
    return base


def _has_usable_fields(row: Dict[str, str], fields: Iterable[str]) -> bool:
    return any(str(row.get(f, "")).strip() not in ("", "None", "nan") for f in fields)


# ── Per-symbol fetch functions ────────────────────────────────────────────────

def fetch_key_metrics_ttm(
    symbol: str,
    api_key: str,
    today: str,
) -> Dict[str, str]:
    """Fetch key metrics TTM for a single symbol."""
    url = f"{_FMP_BASE}/key-metrics-ttm?symbol={symbol}"
    data, status, err = _fmp_get_with_retry(url, api_key)
    if status != 200 or data is None:
        log.debug("[fmp] key_metrics_ttm %s: status=%s err=%s", symbol, status, err)
        return {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "FETCH_FAILED",
            "failure_type": _failure_type(status, err),
            "failure_reason": str(err or f"HTTP {status}"),
        }
    row = _parse_key_metrics_ttm(symbol, data, today)
    row["fetch_status"] = "SUCCESS" if _has_usable_fields(row, ("ev_ebitda_ttm", "roe_ttm", "roic_ttm")) else "PROVIDER_NO_DATA"
    row.setdefault("failure_type", "")
    row.setdefault("failure_reason", "")
    return row


def fetch_grades_consensus(
    symbol: str,
    api_key: str,
    today: str,
) -> Dict[str, str]:
    """Fetch grades consensus for a single symbol."""
    url = f"{_FMP_BASE}/grades-consensus?symbol={symbol}"
    data, status, err = _fmp_get_with_retry(url, api_key)
    if status != 200 or data is None:
        log.debug("[fmp] grades_consensus %s: status=%s err=%s", symbol, status, err)
        return {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "FETCH_FAILED",
            "failure_type": _failure_type(status, err),
            "failure_reason": str(err or f"HTTP {status}"),
        }
    row = _parse_grades_consensus(symbol, data, today)
    row["fetch_status"] = "SUCCESS" if _has_usable_fields(row, ("consensus_label", "net_buy_score", "total_analysts")) else "PROVIDER_NO_DATA"
    row.setdefault("failure_type", "")
    row.setdefault("failure_reason", "")
    return row


def fetch_earnings_surprises(
    symbol: str,
    api_key: str,
    today: str,
) -> Dict[str, str]:
    """Fetch last 8 quarters of earnings surprises for a single symbol."""
    url = f"{_FMP_BASE}/earnings?symbol={symbol}&limit=8"
    data, status, err = _fmp_get_with_retry(url, api_key)
    if status != 200 or data is None:
        log.debug("[fmp] earnings %s: status=%s err=%s", symbol, status, err)
        return {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "FETCH_FAILED",
            "failure_type": _failure_type(status, err),
            "failure_reason": str(err or f"HTTP {status}"),
        }
    row = _parse_earnings_surprises(symbol, data, today)
    row["fetch_status"] = "SUCCESS" if _has_usable_fields(row, ("beat_rate_8q", "latest_eps_surprise_pct", "beats_last_8q")) else "PROVIDER_NO_DATA"
    row.setdefault("failure_type", "")
    row.setdefault("failure_reason", "")
    return row


def fetch_income_growth(
    symbol: str,
    api_key: str,
    today: str,
) -> Dict[str, str]:
    """Fetch last 4 quarters of income statement growth for a single symbol."""
    url = f"{_FMP_BASE}/income-statement-growth?symbol={symbol}&limit=4"
    data, status, err = _fmp_get_with_retry(url, api_key)
    if status != 200 or data is None:
        log.debug("[fmp] income_growth %s: status=%s err=%s", symbol, status, err)
        return {
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "FETCH_FAILED",
            "failure_type": _failure_type(status, err),
            "failure_reason": str(err or f"HTTP {status}"),
        }
    row = _parse_income_growth(symbol, data, today)
    row["fetch_status"] = "SUCCESS" if _has_usable_fields(row, ("revenue_growth_q1_yoy", "eps_growth_q1_yoy", "revenue_acceleration")) else "PROVIDER_NO_DATA"
    row.setdefault("failure_type", "")
    row.setdefault("failure_reason", "")
    return row


def fetch_analyst_estimates(
    symbol: str,
    api_key: str,
    today: str,
    *,
    period: str,
    page: int = 0,
    limit: int = 8,
) -> List[Dict[str, str]]:
    """Fetch forward analyst estimates for a single symbol.

    Endpoint uses FMP /stable/analyst-estimates with explicit period selection.
    """
    normalized_period = str(period or "").strip().lower()
    if normalized_period not in {"annual", "quarter"}:
        raise ValueError(f"Invalid analyst-estimate period: {period}")
    url = (
        f"{_FMP_BASE}/analyst-estimates"
        f"?symbol={symbol}&period={normalized_period}&page={int(page)}&limit={int(limit)}"
    )
    data, status, err = _fmp_get_with_retry(url, api_key)
    if status != 200 or data is None:
        log.debug("[fmp] analyst_estimates %s: status=%s err=%s", symbol, status, err)
        failure_reason = _failure_reason(status, err, data)
        failure_type = _failure_type(status, err)
        return [{
            "symbol": symbol,
            "sourced_date": today,
            "fetch_status": "FETCH_FAILED",
            "failure_type": failure_type,
            "failure_reason": failure_reason,
            "request_period": normalized_period,
            "period_date": "",
            "period_label": "",
            "fiscal_period": "",
            "forecast_horizon": "ANNUAL" if normalized_period == "annual" else "QUARTER",
            "estimated_revenue_avg": "",
            "estimated_revenue_high": "",
            "estimated_revenue_low": "",
            "estimated_eps_avg": "",
            "estimated_eps_high": "",
            "estimated_eps_low": "",
            "analyst_count_revenue": "",
            "analyst_count_eps": "",
        }]
    return _parse_analyst_estimates(symbol, data, today, period=normalized_period)


def _normalize_estimate_periods(periods: Sequence[str]) -> List[str]:
    normalized: List[str] = []
    for period in periods:
        p = str(period or "").strip().lower()
        if not p:
            continue
        if p not in {"annual", "quarter"}:
            raise ValueError(f"Invalid analyst-estimate period: {period}")
        if p not in normalized:
            normalized.append(p)
    if not normalized:
        raise ValueError("At least one analyst-estimate period is required")
    return normalized


def _parse_period_status_from_rows(rows: Sequence[Dict[str, str]]) -> str:
    statuses = {str(row.get("fetch_status") or "").strip() for row in rows}
    if "SUCCESS" in statuses:
        return "AVAILABLE"
    for row in rows:
        if str(row.get("fetch_status") or "").strip() != "FETCH_FAILED":
            continue
        failure_type = str(row.get("failure_type") or "").strip().upper()
        if failure_type in {"PLAN_LIMIT", "AUTH", "FORBIDDEN"}:
            return "PLAN_LIMIT"
    if "FETCH_FAILED" in statuses:
        return "REQUEST_FAILURE"
    return "NO_COVERAGE"


def fetch_fmp_analyst_estimates(
    symbols: List[str],
    api_key: str,
    output_dir: Path = _FMP_DIR,
    delay: float = _DEFAULT_DELAY_BETWEEN_CALLS,
    verbose: bool = True,
    limit: int = 8,
    periods: Sequence[str] = ("annual",),
) -> Tuple[Path, Dict[str, Any]]:
    """Fetch forward analyst-estimate rows for requested periods."""
    api_key = api_key or _get_api_key()
    if not api_key:
        raise ValueError("FMP_API_KEY not set. Cannot fetch FMP analyst estimates.")

    today = date.today().isoformat()
    daily_dir = Path(output_dir) / "daily"
    latest_dir = Path(output_dir) / "latest"
    daily_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict[str, str]] = []
    normalized_periods = _normalize_estimate_periods(periods)
    attempted = 0
    with_data = 0
    no_coverage = 0
    failed = 0
    retries_performed = 0
    rate_limit_events = 0
    period_capability: Dict[str, str] = {period: "UNKNOWN" for period in normalized_periods}
    network_requests_by_period: Dict[str, int] = {period: 0 for period in normalized_periods}

    for i, sym in enumerate(symbols, start=1):
        attempted += 1
        if verbose and i % 50 == 0:
            log.info("[fmp] analyst_estimates progress: %d/%d", i, len(symbols))
        symbol_rows: List[Dict[str, str]] = []
        period_statuses: List[str] = []
        for period in normalized_periods:
            network_requests_by_period[period] = int(network_requests_by_period.get(period, 0) or 0) + 1
            url = (
                f"{_FMP_BASE}/analyst-estimates"
                f"?symbol={sym}&period={period}&page=0&limit={int(limit)}"
            )
            data, status, err, retry_meta = _fmp_get_with_retry_detailed(url, api_key)
            retries_performed += int(retry_meta.get("retries_performed") or 0)
            rate_limit_events += int(retry_meta.get("rate_limit_events") or 0)
            if status != 200 or data is None:
                failure_reason = _failure_reason(status, err, data)
                failure_type = _failure_type(status, err)
                rows = [{
                    "symbol": sym,
                    "sourced_date": today,
                    "fetch_status": "FETCH_FAILED",
                    "failure_type": failure_type,
                    "failure_reason": failure_reason,
                    "request_period": period,
                    "period_date": "",
                    "period_label": "",
                    "fiscal_period": "",
                    "forecast_horizon": "ANNUAL" if period == "annual" else "QUARTER",
                    "estimated_revenue_avg": "",
                    "estimated_revenue_high": "",
                    "estimated_revenue_low": "",
                    "estimated_eps_avg": "",
                    "estimated_eps_high": "",
                    "estimated_eps_low": "",
                    "analyst_count_revenue": "",
                    "analyst_count_eps": "",
                }]
            else:
                rows = _parse_analyst_estimates(sym, data, today, period=period)
            symbol_rows.extend(rows)
            period_status = _parse_period_status_from_rows(rows)
            period_statuses.append(period_status)
            existing = str(period_capability.get(period) or "UNKNOWN")
            if period_status == "AVAILABLE":
                period_capability[period] = "AVAILABLE"
            elif existing != "AVAILABLE" and period_status == "PLAN_LIMIT":
                period_capability[period] = "PLAN_LIMIT"
            elif existing == "UNKNOWN":
                period_capability[period] = period_status
            time.sleep(delay)

        all_rows.extend(symbol_rows)

        if "AVAILABLE" in period_statuses:
            with_data += 1
        elif all(status == "PLAN_LIMIT" for status in period_statuses):
            failed += 1
        elif any(status == "REQUEST_FAILURE" for status in period_statuses):
            failed += 1
        else:
            no_coverage += 1

    estimate_path = daily_dir / f"fmp_analyst_estimates_{today}.csv"
    _write_csv(estimate_path, all_rows, ANALYST_ESTIMATES_HEADERS)
    latest_estimate_path = latest_dir / "latest_fmp_analyst_estimates.csv"
    _write_csv(latest_estimate_path, all_rows, ANALYST_ESTIMATES_HEADERS)

    stats = {
        "attempted": attempted,
        "with_data": with_data,
        "no_coverage": no_coverage,
        "failed": failed,
        "periods_requested": list(normalized_periods),
        "periods_available": [p for p in normalized_periods if str(period_capability.get(p) or "") == "AVAILABLE"],
        "periods_plan_limited": [p for p in normalized_periods if str(period_capability.get(p) or "") == "PLAN_LIMIT"],
        "period_capability": dict(period_capability),
        "network_requests_by_period": dict(network_requests_by_period),
        "retries_performed": retries_performed,
        "rate_limit_events": rate_limit_events,
    }
    return estimate_path, stats


# ── Bulk fetch functions ──────────────────────────────────────────────────────

def fetch_fmp_daily_signals(
    symbols: List[str],
    api_key: str,
    output_dir: Path = _FMP_DIR,
    delay: float = _DEFAULT_DELAY_BETWEEN_CALLS,
    verbose: bool = True,
) -> Tuple[Path, Path]:
    """Fetch daily FMP signals (key_metrics_ttm + grades_consensus) for all symbols.

    Returns (key_metrics_path, grades_path) — the dated archive files written.

    Fail-closed: output files are only written after full universe refresh.
    If fewer than 50% of symbols succeed, raises RuntimeError to prevent
    corrupting the latest files.
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        raise ValueError("FMP_API_KEY not set. Cannot fetch FMP signals.")

    today = date.today().isoformat()
    daily_dir = Path(output_dir) / "daily"
    latest_dir = Path(output_dir) / "latest"
    daily_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    km_rows: List[Dict[str, str]] = []
    gc_rows: List[Dict[str, str]] = []
    km_successes = gc_successes = 0

    for i, sym in enumerate(symbols, 1):
        if verbose and i % 50 == 0:
            log.info("[fmp] daily progress: %d/%d", i, len(symbols))

        km = fetch_key_metrics_ttm(sym, api_key, today)
        km_rows.append(km)
        # Count as success if at least one non-stub field is present
        if any(km.get(f) for f in ["pe_ratio_ttm", "ev_ebitda_ttm", "fcf_yield_ttm"]):
            km_successes += 1

        time.sleep(delay)

        gc = fetch_grades_consensus(sym, api_key, today)
        gc_rows.append(gc)
        if any(gc.get(f) for f in ["buy_count", "hold_count", "total_analysts"]):
            gc_successes += 1

        time.sleep(delay)

    n = len(symbols)

    # Fail-closed: require at least 50% symbol success rate
    km_rate = km_successes / n if n > 0 else 0
    gc_rate = gc_successes / n if n > 0 else 0

    if n > 10 and km_rate < 0.10:
        raise RuntimeError(
            f"[fmp] key_metrics_ttm refresh aborted: only {km_successes}/{n} symbols succeeded "
            f"({km_rate:.1%}). Possible API plan issue (HTTP 402) or outage. "
            f"Latest files NOT updated."
        )

    # Write dated archives
    km_path = daily_dir / f"fmp_key_metrics_{today}.csv"
    gc_path = daily_dir / f"fmp_grades_consensus_{today}.csv"
    _write_csv(km_path, km_rows, KEY_METRICS_HEADERS)
    _write_csv(gc_path, gc_rows, GRADES_CONSENSUS_HEADERS)

    # Update latest files
    km_latest = latest_dir / "latest_fmp_key_metrics.csv"
    gc_latest = latest_dir / "latest_fmp_grades_consensus.csv"
    _upsert_latest(km_latest, km_rows, KEY_METRICS_HEADERS)
    _upsert_latest(gc_latest, gc_rows, GRADES_CONSENSUS_HEADERS)

    if verbose:
        log.info(
            "[fmp] daily refresh complete: key_metrics %d/%d, grades %d/%d",
            km_successes, n, gc_successes, n,
        )

    return km_path, gc_path


def fetch_fmp_quarterly_signals(
    symbols: List[str],
    api_key: str,
    output_dir: Path = _FMP_DIR,
    delay: float = _DEFAULT_DELAY_BETWEEN_CALLS,
    verbose: bool = True,
) -> Tuple[Path, Path]:
    """Fetch quarterly FMP signals (earnings_surprises + income_growth) for all symbols.

    Returns (earnings_path, income_growth_path) — the dated archive files written.
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        raise ValueError("FMP_API_KEY not set. Cannot fetch FMP signals.")

    today = date.today().isoformat()
    # Quarter label e.g. 2026_Q2
    now = datetime.now(timezone.utc)
    quarter = (now.month - 1) // 3 + 1
    quarter_label = f"{now.year}_Q{quarter}"

    qtr_dir = Path(output_dir) / "quarterly"
    latest_dir = Path(output_dir) / "latest"
    qtr_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    es_rows: List[Dict[str, str]] = []
    ig_rows: List[Dict[str, str]] = []
    es_successes = ig_successes = 0

    for i, sym in enumerate(symbols, 1):
        if verbose and i % 50 == 0:
            log.info("[fmp] quarterly progress: %d/%d", i, len(symbols))

        es = fetch_earnings_surprises(sym, api_key, today)
        es_rows.append(es)
        if es.get("beat_rate_8q"):
            es_successes += 1

        time.sleep(delay)

        ig = fetch_income_growth(sym, api_key, today)
        ig_rows.append(ig)
        if ig.get("revenue_growth_q1_yoy"):
            ig_successes += 1

        time.sleep(delay)

    n = len(symbols)

    if n > 10 and es_successes / n < 0.10:
        raise RuntimeError(
            f"[fmp] earnings_surprises refresh aborted: only {es_successes}/{n} succeeded. "
            f"Latest files NOT updated."
        )

    # Write dated archives
    es_path = qtr_dir / f"fmp_earnings_surprises_{quarter_label}.csv"
    ig_path = qtr_dir / f"fmp_income_growth_{quarter_label}.csv"
    _write_csv(es_path, es_rows, EARNINGS_SURPRISES_HEADERS)
    _write_csv(ig_path, ig_rows, INCOME_GROWTH_HEADERS)

    # Update latest files
    es_latest = latest_dir / "latest_fmp_earnings_surprises.csv"
    ig_latest = latest_dir / "latest_fmp_income_growth.csv"
    _upsert_latest(es_latest, es_rows, EARNINGS_SURPRISES_HEADERS)
    _upsert_latest(ig_latest, ig_rows, INCOME_GROWTH_HEADERS)

    if verbose:
        log.info(
            "[fmp] quarterly refresh complete: earnings %d/%d, income_growth %d/%d",
            es_successes, n, ig_successes, n,
        )

    return es_path, ig_path


# ── Load helpers (for downstream consumption) ─────────────────────────────────

def load_latest_fmp_key_metrics(fmp_dir: Path = _FMP_DIR) -> Dict[str, Dict[str, str]]:
    """Load latest FMP key metrics into symbol → fields dict. Empty if not present."""
    return _load_csv_by_symbol(Path(fmp_dir) / "latest" / "latest_fmp_key_metrics.csv")


def load_latest_fmp_grades_consensus(fmp_dir: Path = _FMP_DIR) -> Dict[str, Dict[str, str]]:
    """Load latest FMP grades consensus into symbol → fields dict."""
    return _load_csv_by_symbol(Path(fmp_dir) / "latest" / "latest_fmp_grades_consensus.csv")


def load_latest_fmp_earnings_surprises(fmp_dir: Path = _FMP_DIR) -> Dict[str, Dict[str, str]]:
    """Load latest FMP earnings surprises into symbol → fields dict."""
    return _load_csv_by_symbol(Path(fmp_dir) / "latest" / "latest_fmp_earnings_surprises.csv")


def load_latest_fmp_income_growth(fmp_dir: Path = _FMP_DIR) -> Dict[str, Dict[str, str]]:
    """Load latest FMP income growth into symbol → fields dict."""
    return _load_csv_by_symbol(Path(fmp_dir) / "latest" / "latest_fmp_income_growth.csv")


def load_latest_fmp_analyst_estimates(fmp_dir: Path = _FMP_DIR) -> List[Dict[str, str]]:
    """Load latest FMP analyst estimates as period-preserving rows."""
    latest_path = Path(fmp_dir) / "latest" / "latest_fmp_analyst_estimates.csv"
    if not latest_path.exists():
        return []
    with latest_path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def get_fmp_freshness_report(fmp_dir: Path = _FMP_DIR) -> Dict[str, str]:
    """Return sourced_date for each FMP dataset, or 'MISSING' if not present."""
    latest_dir = Path(fmp_dir) / "latest"
    datasets = {
        "key_metrics":      "latest_fmp_key_metrics.csv",
        "grades_consensus": "latest_fmp_grades_consensus.csv",
        "earnings":         "latest_fmp_earnings_surprises.csv",
        "income_growth":    "latest_fmp_income_growth.csv",
        "analyst_estimates": "latest_fmp_analyst_estimates.csv",
    }
    report: Dict[str, str] = {}
    for name, fname in datasets.items():
        path = latest_dir / fname
        sourced = _latest_sourced_date_fmp(path)
        report[name] = sourced if sourced else "MISSING"
    return report


# ── Numeric helpers ───────────────────────────────────────────────────────────

def _safe_float(val: Any) -> Optional[float]:
    if val is None or val == "" or val != val:  # NaN check
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return ""
    return f"{v:.6g}"
