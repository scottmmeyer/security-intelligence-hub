"""Portfolio ingestion, normalization, and validation — Phase B / C / K.

Supported source formats:
  FIDELITY_CSV   — Fidelity portfolio export (positions page)
  GENERIC_CSV    — generic holdings CSV with required column set

Governance:
  - deterministic: same input → same output for a given snapshot date
  - fail-closed: missing required columns cause REJECTED status, not silent gaps
  - lineage-preserving: source_file + created_at_utc on every row
  - snapshot-based: each upload gets a unique portfolio_snapshot_id
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
from datetime import datetime, timezone
from typing import Optional

from .models import PortfolioHolding, PortfolioSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# Format detection
# ─────────────────────────────────────────────────────────────────────────────

# Classic Fidelity export: single combined account column
_FIDELITY_REQUIRED = {
    "Account Name/Number", "Symbol", "Description",
    "Quantity", "Last Price", "Current Value",
}
# Modern Fidelity multi-account export: separate Account Number + Account Name columns
_FIDELITY_REQUIRED_V2 = {
    "Account Number", "Account Name", "Symbol", "Description",
    "Quantity", "Last Price", "Current Value",
}
_GENERIC_REQUIRED = {
    "symbol", "description", "quantity", "market_value",
}


def detect_format(headers: list[str]) -> str:
    """Return 'FIDELITY_CSV' or 'GENERIC_CSV', or raise ValueError."""
    header_set = set(headers)
    if _FIDELITY_REQUIRED.issubset(header_set):
        return "FIDELITY_CSV"
    if _FIDELITY_REQUIRED_V2.issubset(header_set):
        return "FIDELITY_CSV"
    lower = {h.lower() for h in headers}
    generic_lower = {h.lower() for h in _GENERIC_REQUIRED}
    if generic_lower.issubset(lower):
        return "GENERIC_CSV"
    raise ValueError(
        f"Unrecognized portfolio format. Headers found: {sorted(headers)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Normalization helpers
# ─────────────────────────────────────────────────────────────────────────────

_MONEY_RE = re.compile(r"[$,\s+]")


def _parse_float(raw: str) -> Optional[float]:
    cleaned = _MONEY_RE.sub("", str(raw).strip())
    if cleaned in ("", "--", "N/A", "n/a"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_symbol(raw: str) -> str:
    """Upper-case, strip whitespace and Fidelity trailing asterisks (e.g. SPAXX**)."""
    sym = str(raw).strip().upper().rstrip("*")
    # Fidelity uses '--' as a placeholder for cash sweep positions
    return sym if sym not in ("--", "", "N/A") else "CASH"


def _snapshot_id(source_file: str, snapshot_date: str, account_name: str) -> str:
    """Deterministic snapshot ID from key inputs."""
    raw = f"{source_file}|{snapshot_date}|{account_name}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
    clean_date = snapshot_date.replace("-", "")
    return f"PSNAP-{clean_date}-{digest}"


# ─────────────────────────────────────────────────────────────────────────────
# Phase K — Validators
# ─────────────────────────────────────────────────────────────────────────────

class IngestionError(Exception):
    """Hard failure — ingestion must be rejected."""


def _validate_rows(rows: list[dict]) -> list[str]:
    """Return list of non-fatal warning strings (empty = clean)."""
    warnings: list[str] = []
    symbols_seen: dict[str, int] = {}
    total_pct = 0.0
    total_value = 0.0

    for i, row in enumerate(rows):
        sym = row.get("symbol", "")
        mv = row.get("market_value")
        pct = row.get("percent_of_portfolio")

        # Duplicate symbols
        if sym in symbols_seen:
            warnings.append(
                f"Row {i+1}: duplicate symbol '{sym}' — already seen at row {symbols_seen[sym]+1}"
            )
        symbols_seen[sym] = i

        # Negative or zero market value
        if mv is not None and mv < 0:
            warnings.append(f"Row {i+1}: negative market_value {mv} for '{sym}'")
        if mv is not None and mv == 0:
            warnings.append(f"Row {i+1}: zero market_value for '{sym}' — position may be closed")

        if mv is not None:
            total_value += mv
        if pct is not None:
            total_pct += pct

    # Allocation total sanity — soft check (not hard failure for portfolios with
    # sub-account rows or Fidelity cash that rounds oddly)
    if rows and abs(total_pct - 100.0) > 5.0:
        warnings.append(
            f"Percent_of_portfolio sums to {total_pct:.2f}% (expected ≈100%). "
            "Recalculating from market values."
        )

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Fidelity CSV parser
# ─────────────────────────────────────────────────────────────────────────────

def _parse_fidelity(
    content: str,
    source_file: str,
    snapshot_date: str,
    now_utc: str,
) -> tuple[list[dict], str, list[str]]:
    """Parse a Fidelity portfolio CSV export.

    Returns (raw_rows, account_name, warnings).
    Raises IngestionError on hard failures.
    """
    # Fidelity files have preamble lines before the header — find the header row
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Symbol" in line and "Description" in line and "Current Value" in line:
            header_idx = i
            break
    if header_idx is None:
        raise IngestionError("Could not locate header row in Fidelity CSV export.")

    # Re-parse from header line onward; skip footer boilerplate after blank line
    data_lines = []
    for line in lines[header_idx:]:
        stripped = line.strip()
        if not stripped:
            break  # Fidelity appends disclaimer text after a blank line
        data_lines.append(line)

    reader = csv.DictReader(io.StringIO("\n".join(data_lines)))
    headers = reader.fieldnames or []
    header_set = set(headers)
    if not (_FIDELITY_REQUIRED.issubset(header_set) or _FIDELITY_REQUIRED_V2.issubset(header_set)):
        raise IngestionError(f"Fidelity headers incomplete. Found: {headers}")

    # Support both column name variants for account
    _acct_col = "Account Name/Number" if "Account Name/Number" in header_set else "Account Name"
    # Support both percent column variants
    _pct_col = "Percent Of Account" if "Percent Of Account" in header_set else "Percent of Portfolio"

    raw_rows = []
    account_names_seen: list[str] = []
    for row in reader:
        sym = _normalize_symbol(row.get("Symbol", ""))
        desc = str(row.get("Description", "")).strip()
        acct_raw = str(row.get(_acct_col, "")).strip()
        if acct_raw and acct_raw not in account_names_seen:
            account_names_seen.append(acct_raw)

        qty = _parse_float(row.get("Quantity", ""))
        mv = _parse_float(row.get("Current Value", ""))
        pct = _parse_float(row.get(_pct_col, ""))
        cost = _parse_float(row.get("Cost Basis Total", ""))

        # Skip rows with no symbol or no value (Fidelity totals row)
        if not sym or sym == "CASH" and not desc:
            continue
        if mv is None and qty is None:
            continue

        raw_rows.append({
            "symbol": sym,
            "description": desc,
            "quantity": qty or 0.0,
            "market_value": mv or 0.0,
            "percent_of_portfolio": pct,   # recalculated below from market values
            "cost_basis": cost,
            "security_type": _infer_security_type(sym, desc),
            "_acct": acct_raw,
            "_operational_state": _classify_operational_state(sym, desc, mv),
        })

    if not raw_rows:
        raise IngestionError("No valid holdings found in Fidelity export.")

    # Multi-account: use account name list joined, or first entry
    account_name = ", ".join(account_names_seen) if account_names_seen else "UNKNOWN"

    _recalculate_pct(raw_rows)
    warnings = _validate_rows(raw_rows)
    return raw_rows, account_name, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Generic CSV parser
# ─────────────────────────────────────────────────────────────────────────────

def _parse_generic(
    content: str,
    source_file: str,
    snapshot_date: str,
    now_utc: str,
) -> tuple[list[dict], str, list[str]]:
    """Parse a generic holdings CSV.

    Required columns: symbol, description, quantity, market_value
    Optional: percent_of_portfolio, cost_basis, account_name, security_type
    """
    reader = csv.DictReader(io.StringIO(content))
    headers = [h.lower() for h in (reader.fieldnames or [])]
    # Build a lowercase→original map for flexible column access
    col_map = {h.lower(): h for h in (reader.fieldnames or [])}

    def get(row: dict, key: str, fallback: str = "") -> str:
        return str(row.get(col_map.get(key, key), fallback)).strip()

    raw_rows = []
    account_name = "PORTFOLIO"
    for row in reader:
        sym = _normalize_symbol(get(row, "symbol"))
        desc = get(row, "description")
        acct = get(row, "account_name")
        if acct and account_name == "PORTFOLIO":
            account_name = acct

        qty = _parse_float(get(row, "quantity"))
        mv = _parse_float(get(row, "market_value"))
        pct = _parse_float(get(row, "percent_of_portfolio"))
        cost = _parse_float(get(row, "cost_basis"))
        stype = get(row, "security_type") or _infer_security_type(sym, desc)

        if not sym or mv is None:
            continue

        raw_rows.append({
            "symbol": sym,
            "description": desc,
            "quantity": qty or 0.0,
            "market_value": mv,
            "percent_of_portfolio": pct,
            "cost_basis": cost,
            "security_type": stype,
            "_operational_state": _classify_operational_state(sym, desc, mv),
        })

    if not raw_rows:
        raise IngestionError("No valid holdings found in generic CSV.")

    _recalculate_pct(raw_rows)
    warnings = _validate_rows(raw_rows)
    return raw_rows, account_name, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _recalculate_pct(rows: list[dict]) -> None:
    """Recalculate percent_of_portfolio from market values (authoritative).

    Only positive market values contribute to the denominator.  Negative-value
    accounting-adjustment rows (e.g. PENDING ACTIVITY) are excluded from the
    weight calculation so they do not distort the portfolio distribution.
    """
    total = sum(r["market_value"] for r in rows if (r.get("market_value") or 0) > 0)
    if total <= 0:
        return
    for r in rows:
        mv = r.get("market_value") or 0.0
        if mv > 0:
            r["percent_of_portfolio"] = round((mv / total) * 100.0, 4)
        else:
            r["percent_of_portfolio"] = 0.0


_ETF_TICKERS = {
    "VOO", "VTI", "SPY", "QQQ", "IVV", "IWM", "VEA", "VWO", "EFA", "AGG",
    "BND", "BNDX", "GLD", "IAU", "PDBC", "XLE", "OEF", "MDY", "IJR", "VO",
    "VB", "IWC", "IBIT", "FBTC", "EMXC", "SCHP", "SPAXX", "VMFXX",
}

_CASH_KEYWORDS = {"CASH", "SPAXX", "FZFXX", "FDRXX", "FCASH", "PENDING"}

# Descriptions that identify non-investment / operational rows in Fidelity exports.
# These rows must be preserved for audit but excluded from portfolio analytics.
_PENDING_DESCRIPTION_KEYWORDS = {"PENDING ACTIVITY", "PENDING", "SETTLEMENT"}

# Fidelity-internal contra lot symbol pattern: M<2-digit-code>CNT<sequence>.
# These are broker bookkeeping artifacts from corporate actions (mergers, splits,
# tender offers) — they carry quantity but zero market value.
_CONTRA_SYMBOL_RE = re.compile(r'^M\d{2}CNT\d+$')


def _classify_operational_state(sym: str, desc: str, mv: Optional[float]) -> str:
    """Return the HoldingOperationalState for a raw ingestion row.

    States:
      ACTIVE_POSITION           — normal investable holding
      CASH_EQUIVALENT           — assigned by enrichment (not ingestion)
      PENDING_SETTLEMENT        — unsettled / pending activity row
      ACCOUNTING_ADJUSTMENT     — negative market value correction row
      ZERO_VALUE_LEGACY_POSITION— broker-generated contra/residual artifact (mv=0)
      CLOSED_POSITION           — zero market value (position fully liquidated)
    """
    desc_upper = (desc or "").upper()
    if any(kw in desc_upper for kw in _PENDING_DESCRIPTION_KEYWORDS) or sym == "PENDING":
        return "PENDING_SETTLEMENT"
    if mv is not None and mv < 0:
        return "ACCOUNTING_ADJUSTMENT"
    # Broker contra lot: Fidelity M##CNT### pattern or description contains CONTRA.
    # Market value may be 0.0 OR None (Fidelity renders '--' for qty/value fields on
    # contra lots — _parse_float returns None for '--').
    if _CONTRA_SYMBOL_RE.match(sym) or "CONTRA" in desc_upper:
        return "ZERO_VALUE_LEGACY_POSITION"
    if mv is not None and mv == 0:
        return "CLOSED_POSITION"
    return "ACTIVE_POSITION"


def _infer_security_type(symbol: str, description: str) -> str:
    """Best-effort security type inference from symbol and description."""
    desc_upper = description.upper()
    if symbol in _CASH_KEYWORDS or "MONEY MARKET" in desc_upper or "CASH" in desc_upper:
        return "Cash"
    if symbol in _ETF_TICKERS or "ETF" in desc_upper or "FUND" in desc_upper:
        return "ETF"
    if "BOND" in desc_upper or "TREASURY" in desc_upper or "NOTE" in desc_upper:
        return "Bond"
    return "Common Stock"


# ─────────────────────────────────────────────────────────────────────────────
# Public ingestion entry point
# ─────────────────────────────────────────────────────────────────────────────

def ingest_portfolio(
    content: str,
    source_filename: str,
    snapshot_date: str,
) -> tuple[PortfolioSnapshot, list[PortfolioHolding]]:
    """Parse, validate, and normalize a portfolio extract.

    Returns (PortfolioSnapshot, list[PortfolioHolding]).
    Raises IngestionError if the file is fundamentally malformed.

    All holdings are returned in normalized form with SIH classification fields
    set to 'UNKNOWN' — enrichment (Phase D) is a separate step.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    # Strip UTF-8 BOM if present (common in Windows/Excel/Fidelity exports)
    content = content.lstrip("\ufeff")

    # Detect format from first non-empty line headers
    probe = csv.reader(io.StringIO(content))
    first_rows: list[list[str]] = []
    for row in probe:
        if any(cell.strip() for cell in row):
            first_rows.append(row)
        if len(first_rows) >= 20:
            break

    fmt = None
    detected_headers: list[str] = []
    for row in first_rows:
        try:
            fmt = detect_format(row)
            detected_headers = row
            break
        except ValueError:
            continue

    if fmt is None:
        raise IngestionError(
            f"Cannot determine portfolio format from '{source_filename}'. "
            "Expected Fidelity CSV or generic holdings CSV."
        )

    # Parse
    if fmt == "FIDELITY_CSV":
        raw_rows, account_name, warnings = _parse_fidelity(
            content, source_filename, snapshot_date, now_utc
        )
    else:
        raw_rows, account_name, warnings = _parse_generic(
            content, source_filename, snapshot_date, now_utc
        )

    # Build deterministic snapshot ID
    snap_id = _snapshot_id(source_filename, snapshot_date, account_name)
    total_mv = sum(r["market_value"] for r in raw_rows)

    # Build PortfolioHolding list — classification = UNKNOWN until enrichment
    holdings: list[PortfolioHolding] = []
    for r in raw_rows:
        holdings.append(PortfolioHolding(
            portfolio_snapshot_id=snap_id,
            snapshot_date=snapshot_date,
            account_name=account_name,
            symbol=r["symbol"],
            description=r["description"],
            quantity=r["quantity"],
            market_value=r["market_value"],
            percent_of_portfolio=r["percent_of_portfolio"] or 0.0,
            # Classification — filled by enrichment
            asset_class="UNKNOWN",
            geography="UNKNOWN",
            market_cap_bucket="UNKNOWN",
            mega_subtier="N/A",
            sector="UNKNOWN",
            industry="UNKNOWN",
            security_type=r.get("security_type", "Common Stock"),
            cost_basis=r.get("cost_basis"),
            composite_score=None,
            ess_score_text=None,
            zacks_rating=None,
            benchmark_id=None,
            investable_vehicle_id=None,
            source_file=source_filename,
            created_at_utc=now_utc,
            operational_state=r.get("_operational_state", "ACTIVE_POSITION"),
        ))

    snapshot = PortfolioSnapshot(
        portfolio_snapshot_id=snap_id,
        snapshot_date=snapshot_date,
        account_name=account_name,
        total_market_value=total_mv,
        holding_count=len(holdings),
        source_file=source_filename,
        source_format=fmt,
        ingestion_status="ACCEPTED" if not warnings else "PARTIAL",
        normalization_warnings=tuple(warnings),
        created_at_utc=now_utc,
        run_id="",  # assigned by analysis runner
    )

    return snapshot, holdings
