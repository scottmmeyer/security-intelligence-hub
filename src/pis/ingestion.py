"""PIS Phase 1 Fidelity ingestion.

This module builds immutable account-level portfolio snapshots from Fidelity
download files and hands them to the storage layer.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from .models import PortfolioSnapshot, PositionSnapshot


_MONEY_REPLACEMENTS = str.maketrans({"$": "", ",": "", "+": "", " ": ""})
_CASH_KEYWORDS = {"CASH", "SPAXX", "FZFXX", "FDRXX", "FCASH", "PENDING"}
_PENDING_DESCRIPTION_KEYWORDS = {"PENDING ACTIVITY", "PENDING", "SETTLEMENT"}


def _parse_float(raw: object) -> Optional[float]:
    cleaned = str(raw or "").strip().translate(_MONEY_REPLACEMENTS)
    if cleaned in {"", "--", "N/A", "n/a"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_symbol(raw: object) -> str:
    symbol = str(raw or "").strip().upper().rstrip("*")
    return symbol if symbol not in {"", "--", "N/A"} else "CASH"


def _find_header_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if "Symbol" in line and "Description" in line and "Current Value" in line:
            return index
    raise ValueError("Could not locate Fidelity header row in portfolio export.")


def _account_key(raw_account_id: str, raw_account_name: str) -> str:
    account_id = str(raw_account_id or "").strip()
    account_name = str(raw_account_name or "").strip()
    if account_id:
        return account_id
    if account_name:
        return account_name
    return "UNKNOWN"


def _snapshot_id(source_filename: str, snapshot_date: str, account_id: str) -> str:
    raw = f"{source_filename}|{snapshot_date}|{account_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"PSNAP-{snapshot_date.replace('-', '')}-{digest}"


def _classify_operational_state(symbol: str, description: str, market_value: Optional[float]) -> str:
    desc_upper = (description or "").upper()
    if any(keyword in desc_upper for keyword in _PENDING_DESCRIPTION_KEYWORDS) or symbol == "PENDING":
        return "PENDING_SETTLEMENT"
    if market_value is not None and market_value < 0:
        return "ACCOUNTING_ADJUSTMENT"
    if "CONTRA" in desc_upper:
        return "ZERO_VALUE_LEGACY_POSITION"
    if market_value is not None and market_value == 0:
        return "CLOSED_POSITION"
    return "ACTIVE_POSITION"


def _infer_security_type(symbol: str, description: str) -> str:
    desc_upper = description.upper()
    if symbol in _CASH_KEYWORDS or "MONEY MARKET" in desc_upper or "CASH" in desc_upper:
        return "Cash"
    if "ETF" in desc_upper or "FUND" in desc_upper:
        return "ETF"
    if "BOND" in desc_upper or "TREASURY" in desc_upper or "NOTE" in desc_upper:
        return "Bond"
    return "Common Stock"


def _is_cash_equivalent(symbol: str, description: str, security_type: str) -> bool:
    desc_upper = description.upper()
    return (
        symbol in _CASH_KEYWORDS
        or security_type == "Cash"
        or "MONEY MARKET" in desc_upper
        or "CASH" in desc_upper
    )


def _recalculate_percent(rows: list[dict[str, object]]) -> None:
    total = sum(float(row["market_value"]) for row in rows if float(row["market_value"]) > 0)
    if total <= 0:
        for row in rows:
            row["percent_of_account"] = 0.0
        return
    for row in rows:
        market_value = float(row["market_value"])
        row["percent_of_account"] = round((market_value / total) * 100.0, 4) if market_value > 0 else 0.0


def _read_fidelity_rows(content: str) -> tuple[list[dict[str, object]], list[str]]:
    lines = content.lstrip("\ufeff").splitlines()
    header_index = _find_header_index(lines)

    data_lines: list[str] = []
    for line in lines[header_index:]:
        if not line.strip():
            break
        data_lines.append(line)

    reader = csv.DictReader(io.StringIO("\n".join(data_lines)))
    rows: list[dict[str, object]] = []
    warnings: list[str] = []

    for row_number, row in enumerate(reader, start=1):
        account_id = _account_key(row.get("Account Number", ""), row.get("Account Name/Number", ""))
        account_name = str(row.get("Account Name", "") or row.get("Account Name/Number", "")).strip()
        symbol = _normalize_symbol(row.get("Symbol", ""))
        description = str(row.get("Description", "")).strip()
        quantity = _parse_float(row.get("Quantity", ""))
        market_value = _parse_float(row.get("Current Value", ""))
        percent_of_account = _parse_float(row.get("Percent Of Account", row.get("Percent of Portfolio", "")))
        cost_basis_total = _parse_float(row.get("Cost Basis Total", ""))

        if not symbol and not description:
            warnings.append(f"Row {row_number}: malformed row without symbol/description was skipped.")
            continue

        if symbol == "CASH" and not description:
            warnings.append(f"Row {row_number}: malformed cash row without description was skipped.")
            continue

        if quantity is None and market_value is None:
            warnings.append(f"Row {row_number}: malformed row without quantity/current value was skipped.")
            continue

        inferred_security_type = _infer_security_type(symbol, description)
        operational_state = _classify_operational_state(symbol, description, market_value)
        is_cash_equivalent = _is_cash_equivalent(symbol, description, inferred_security_type)

        rows.append(
            {
                "account_id": account_id,
                "account_name": account_name or account_id,
                "symbol": symbol,
                "description": description,
                "quantity": quantity or 0.0,
                "market_value": market_value or 0.0,
                "source_percent_of_account": percent_of_account,
                "cost_basis_total": cost_basis_total,
                "security_type": inferred_security_type,
                "operational_state": operational_state,
                "is_cash_equivalent": is_cash_equivalent,
            }
        )

    if not rows:
        raise ValueError("No valid holdings found in Fidelity export.")

    return rows, warnings


def ingest_portfolio_history(
    content: str,
    source_filename: str,
    snapshot_date: str,
) -> tuple[list[PortfolioSnapshot], list[PositionSnapshot], list[str]]:
    """Normalize a Fidelity export into account-level PIS snapshots."""

    created_at_utc = datetime.now(timezone.utc)
    raw_rows, parse_warnings = _read_fidelity_rows(content)
    grouped_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in raw_rows:
        grouped_rows[str(row["account_id"])].append(row)

    snapshot_date_value = date.fromisoformat(snapshot_date)
    snapshots: list[PortfolioSnapshot] = []
    positions: list[PositionSnapshot] = []
    all_warnings = list(parse_warnings)

    for account_id in sorted(grouped_rows):
        account_rows = grouped_rows[account_id]
        account_name = str(account_rows[0]["account_name"])
        snapshot_id = _snapshot_id(source_filename, snapshot_date, account_id)

        seen_symbols: dict[str, int] = {}
        account_warnings: list[str] = []
        account_portfolio_value = 0.0
        account_cash_value = 0.0

        _recalculate_percent(account_rows)

        for row_index, row in enumerate(account_rows, start=1):
            symbol = str(row["symbol"])
            if symbol in seen_symbols:
                account_warnings.append(
                    f"Account {account_id}: duplicate symbol '{symbol}' at row {row_index} (first seen at row {seen_symbols[symbol]})."
                )
            else:
                seen_symbols[symbol] = row_index

            market_value = float(row["market_value"])
            if market_value == 0:
                account_warnings.append(f"Account {account_id}: zero-value position '{symbol}' was retained for audit.")

            account_portfolio_value += market_value
            if bool(row["is_cash_equivalent"]):
                account_cash_value += market_value

            positions.append(
                PositionSnapshot(
                    snapshot_id=snapshot_id,
                    snapshot_date=snapshot_date_value,
                    account_id=account_id,
                    account_name=account_name,
                    symbol=symbol,
                    description=str(row["description"]),
                    quantity=float(row["quantity"]),
                    market_value=market_value,
                    percent_of_account=float(row["percent_of_account"]),
                    source_percent_of_account=row["source_percent_of_account"],
                    cost_basis_total=row["cost_basis_total"],
                    security_type=str(row["security_type"]),
                    operational_state=str(row["operational_state"]),
                    is_cash_equivalent=bool(row["is_cash_equivalent"]),
                    source_file=source_filename,
                    created_at_utc=created_at_utc,
                )
            )

        reported_percent_total = sum(
            float(row["source_percent_of_account"]) for row in account_rows if row["source_percent_of_account"] is not None
        )
        if account_rows and abs(reported_percent_total - 100.0) > 5.0:
            account_warnings.append(
                f"Account {account_id}: reported percent total is {reported_percent_total:.2f}% instead of approximately 100%."
            )

        account_warnings = list(dict.fromkeys(account_warnings))
        all_warnings.extend(account_warnings)

        snapshots.append(
            PortfolioSnapshot(
                snapshot_id=snapshot_id,
                snapshot_date=snapshot_date_value,
                account_id=account_id,
                account_name=account_name,
                source_file=source_filename,
                source_format="FIDELITY_CSV",
                portfolio_value=account_portfolio_value,
                cash_value=account_cash_value,
                equity_value=account_portfolio_value - account_cash_value,
                holding_count=len(account_rows),
                ingestion_status="ACCEPTED" if not account_warnings else "PARTIAL",
                created_at_utc=created_at_utc,
                warnings=tuple(account_warnings),
            )
        )

    return snapshots, positions, list(dict.fromkeys(all_warnings))


def ingest_portfolio_history_file(path: str | Path, snapshot_date: str) -> tuple[list[PortfolioSnapshot], list[PositionSnapshot], list[str]]:
    """Convenience wrapper around :func:`ingest_portfolio_history` for file paths."""

    file_path = Path(path)
    return ingest_portfolio_history(file_path.read_text(encoding="utf-8"), file_path.name, snapshot_date)
