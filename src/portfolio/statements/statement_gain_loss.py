from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

_MONEY_RE = re.compile(r"([+\-]?\$?\(?\d[\d,]*(?:\.\d+)?\)?)")
_ACCOUNT_RE = re.compile(r"([A-Z]\d{2}-\d{6})")
_PERIOD_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*(?:to|-)\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
_MONTH_RANGE_RE = re.compile(
    r"([A-Za-z]+\s+\d{1,2},\s*\d{4})\s*(?:to|-)\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})",
    re.IGNORECASE,
)
_FILENAME_MDY_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")

ALLOWED_SOURCE_PROVENANCE = {
    "fixture-text",
    "pdf-text-extracted",
    "manual-text-extract",
    "ocr-unavailable",
}

ACCOUNT_METADATA_OVERRIDES = {
    "X20-548022": "Individual TOD",
    "Z35-123695": "Individual TOD",
    "Z26-346415": "Joint WROS TOD",
}


class StatementParsingError(RuntimeError):
    def __init__(self, message: str, reason: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


@dataclass(frozen=True)
class StatementSource:
    source_file: str
    extraction_method: str
    confidence: str
    source_provenance: str
    text: str


@dataclass(frozen=True)
class RealizedGainLossBreakdown:
    realized_short_term_net_ytd: float | None = None
    realized_short_term_gain_ytd: float | None = None
    realized_short_term_loss_ytd: float | None = None
    realized_short_term_disallowed_loss_ytd: float | None = None
    realized_long_term_net_ytd: float | None = None
    realized_long_term_gain_ytd: float | None = None
    realized_long_term_loss_ytd: float | None = None
    realized_long_term_disallowed_loss_ytd: float | None = None
    realized_net_gain_loss_ytd: float | None = None


@dataclass(frozen=True)
class IncomeSummary:
    taxable_income_ytd: float | None = None
    dividends_ytd: float | None = None
    long_term_capital_gains_income_ytd: float | None = None


@dataclass(frozen=True)
class StatementPortfolioSummary:
    statement_period_start: str | None
    statement_period_end: str | None
    statement_date: str | None
    source_file: str
    account_number: str | None = None
    account_name: str | None = None
    account_type: str | None = None
    beginning_value_ytd: float | None = None
    additions_ytd: float | None = None
    subtractions_ytd: float | None = None
    fees_ytd: float | None = None
    transfers_between_fidelity_accounts_ytd: float | None = None
    change_in_investment_value_ytd: float | None = None
    ending_value: float | None = None
    taxable_income_ytd: float | None = None
    dividends_ytd: float | None = None
    long_term_capital_gains_income_ytd: float | None = None
    total_including_other_holdings: float | None = None
    confidence: str = "statement-derived"
    extraction_method: str = "text-parse"
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AccountGainLossSummary:
    statement_period_start: str | None
    statement_period_end: str | None
    statement_date: str | None
    source_file: str
    account_number: str
    account_name: str | None
    account_type: str | None
    beginning_value_ytd: float | None = None
    additions_ytd: float | None = None
    subtractions_ytd: float | None = None
    fees_ytd: float | None = None
    transfers_between_fidelity_accounts_ytd: float | None = None
    change_in_investment_value_ytd: float | None = None
    ending_value: float | None = None
    taxable_income_ytd: float | None = None
    dividends_ytd: float | None = None
    long_term_capital_gains_income_ytd: float | None = None
    realized_short_term_net_ytd: float | None = None
    realized_short_term_gain_ytd: float | None = None
    realized_short_term_loss_ytd: float | None = None
    realized_short_term_disallowed_loss_ytd: float | None = None
    realized_long_term_net_ytd: float | None = None
    realized_long_term_gain_ytd: float | None = None
    realized_long_term_loss_ytd: float | None = None
    realized_long_term_disallowed_loss_ytd: float | None = None
    realized_net_gain_loss_ytd: float | None = None
    confidence: str = "statement-derived"
    extraction_method: str = "text-parse"
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StatementGainLossSnapshot:
    statement_period_start: str | None
    statement_period_end: str | None
    statement_date: str | None
    source_files: list[str]
    source_provenance: list[dict[str, str]]
    extraction_timestamp_utc: str
    portfolio_summary: StatementPortfolioSummary | None
    accounts: list[AccountGainLossSummary]
    derived_totals: dict[str, Any]
    reconciliation_notes: list[str]
    warnings: list[str]
    precision_limitations: list[str]
    usage_guidance: dict[str, list[str]]
    scoring_impact: str = "none"
    parse_status: str = "complete"
    promoted_to_latest: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_period": {
                "start": self.statement_period_start,
                "end": self.statement_period_end,
            },
            "statement_date": self.statement_date,
            "source_files": self.source_files,
            "source_provenance": self.source_provenance,
            "extraction_timestamp_utc": self.extraction_timestamp_utc,
            "portfolio_summary": asdict(self.portfolio_summary) if self.portfolio_summary else None,
            "accounts": [asdict(a) for a in self.accounts],
            "derived_totals": self.derived_totals,
            "reconciliation_notes": self.reconciliation_notes,
            "warnings": self.warnings,
            "precision_limitations": self.precision_limitations,
            "usage_guidance": self.usage_guidance,
            "scoring_impact": self.scoring_impact,
            "parse_status": self.parse_status,
            "promoted_to_latest": self.promoted_to_latest,
        }


def apply_snapshot_parse_status(
    snapshot: StatementGainLossSnapshot,
    parse_status: str,
    promoted_to_latest: bool,
    warnings_to_add: list[str] | None = None,
) -> StatementGainLossSnapshot:
    merged_warnings = list(snapshot.warnings)
    for warning in warnings_to_add or []:
        if warning and warning not in merged_warnings:
            merged_warnings.append(warning)
    return replace(
        snapshot,
        warnings=merged_warnings,
        parse_status=parse_status,
        promoted_to_latest=promoted_to_latest,
    )


def evaluate_snapshot_completeness(
    snapshot: StatementGainLossSnapshot,
    expected_accounts: set[str] | None = None,
) -> tuple[str, list[str]]:
    expected = expected_accounts or {"X20-548022", "Z26-346415", "Z35-123695"}
    warnings: list[str] = []
    degraded = False

    if not snapshot.statement_date:
        degraded = True
        warnings.append("Statement date missing.")

    if not snapshot.statement_period_start or not snapshot.statement_period_end:
        degraded = True
        warnings.append("Statement period missing or incomplete.")

    if not snapshot.source_files:
        degraded = True
        warnings.append("No source files detected.")

    if not snapshot.source_provenance:
        degraded = True
        warnings.append("Source provenance missing.")

    if not snapshot.accounts:
        degraded = True
        warnings.append("No account numbers detected.")

    account_numbers = {a.account_number for a in snapshot.accounts}
    if not account_numbers:
        degraded = True
        warnings.append("No account numbers detected.")

    portfolio = snapshot.portfolio_summary
    if portfolio is None or portfolio.ending_value is None:
        degraded = True
        warnings.append("Portfolio ending value missing.")

    realized_missing_accounts = []
    for account_number in sorted(expected):
        acct = next((a for a in snapshot.accounts if a.account_number == account_number), None)
        if acct is None:
            continue
        if acct.realized_net_gain_loss_ytd is None:
            degraded = True
            realized_missing_accounts.append(account_number)
            warnings.append(f"Realized gain/loss totals missing for {account_number}.")

    if snapshot.derived_totals.get("combined_realized_net_gain_loss_ytd_all_accounts") is None:
        degraded = True
        warnings.append("Combined realized net gain/loss YTD (all accounts) missing.")

    if portfolio is None or portfolio.change_in_investment_value_ytd is None:
        degraded = True
        warnings.append("Portfolio YTD change in investment value missing.")

    provenance_types = {item.get("source_provenance") for item in snapshot.source_provenance}
    if degraded and "pdf-text-extracted" in provenance_types and realized_missing_accounts:
        warnings.insert(0, "PDF text extraction succeeded but gain/loss tables were not parsed.")

    if degraded:
        warnings.append("Snapshot not promoted to latest.")
        return "degraded", warnings
    return "complete", warnings


def _parse_money(value: str) -> float | None:
    raw = value.strip()
    if not raw:
        return None
    sign = -1.0 if raw.startswith("-") or raw.startswith("(") else 1.0
    cleaned = raw.replace("$", "").replace(",", "").replace("(", "").replace(")", "")
    cleaned = cleaned.lstrip("+-")
    if not cleaned:
        return None
    try:
        return round(sign * float(cleaned), 2)
    except ValueError:
        return None


def _extract_money_by_label(text: str, label: str) -> float | None:
    pattern = re.compile(rf"{re.escape(label)}\s*[:=]?\s*([+\-]?\$?\(?\d[\d,]*(?:\.\d+)?\)?)", re.IGNORECASE)
    m = pattern.search(text)
    if m:
        return _parse_money(m.group(1))
    return None


def _extract_period(text: str) -> tuple[str | None, str | None]:
    m = _PERIOD_RE.search(text)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _extract_month_name_period(text: str) -> tuple[str | None, str | None]:
    m = _MONTH_RANGE_RE.search(text)
    if not m:
        return None, None
    try:
        start = datetime.strptime(m.group(1).strip(), "%B %d, %Y").date().isoformat()
        end = datetime.strptime(m.group(2).strip(), "%B %d, %Y").date().isoformat()
        return start, end
    except ValueError:
        return None, None


def _extract_period_from_content(text: str) -> tuple[str | None, str | None]:
    start, end = _extract_period(text)
    if start and end:
        return start, end
    return _extract_month_name_period(text)


def _extract_statement_date_from_filename(source_file: str) -> str | None:
    name = Path(source_file).name
    m = _FILENAME_MDY_RE.search(name)
    if not m:
        return None
    month, day, year = m.groups()
    try:
        parsed = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.date().isoformat()


def _resolve_period_and_date(
    text: str,
    source_file: str,
    statement_date: str | None,
    statement_period_start: str | None,
    statement_period_end: str | None,
) -> tuple[str, str, str, list[str]]:
    warnings: list[str] = []
    content_start, content_end = _extract_period_from_content(text)
    filename_date = _extract_statement_date_from_filename(source_file)

    if content_end and filename_date and content_end != filename_date:
        warnings.append(
            "Content-derived statement date overrides filename-derived date."
        )

    p_start = statement_period_start or content_start
    p_end = statement_period_end or content_end or filename_date
    p_date = statement_date or content_end or filename_date

    if not p_date:
        raise StatementParsingError(
            "Unable to detect statement date from content or filename.",
            reason="statement_date_unresolved",
            details={"source_file": source_file},
        )

    if not p_start:
        p_start = p_date
    if not p_end:
        p_end = p_date

    return p_start, p_end, p_date, warnings


def _source_provenance_for_path(path: Path) -> str:
    normalized = str(path).replace("\\", "/")
    if "/tests/fixtures/" in normalized or normalized.startswith("tests/fixtures/"):
        return "fixture-text"
    return "manual-text-extract"


def _ensure_source_provenance(value: str) -> str:
    if value not in ALLOWED_SOURCE_PROVENANCE:
        raise StatementParsingError(
            f"Unsupported source_provenance '{value}'.",
            reason="invalid_source_provenance",
            details={"allowed": sorted(ALLOWED_SOURCE_PROVENANCE), "value": value},
        )
    return value


def _detect_account_type(segment: str, account_number: str) -> str | None:
    override = ACCOUNT_METADATA_OVERRIDES.get(account_number)
    if override:
        return override
    if re.search(r"Joint\s+WROS\s+TOD", segment, re.IGNORECASE):
        return "Joint WROS TOD"
    if re.search(r"Individual\s+TOD", segment, re.IGNORECASE):
        return "Individual TOD"
    return None


def _parse_account_summaries(
    text: str,
    statement_period_start: str | None,
    statement_period_end: str | None,
    statement_date: str | None,
    source_file: str,
    extraction_method: str,
    confidence: str,
) -> list[AccountGainLossSummary]:
    matches = list(_ACCOUNT_RE.finditer(text))
    if not matches:
        return []

    accounts: list[AccountGainLossSummary] = []
    for idx, m in enumerate(matches):
        acc = m.group(1)
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment = text[start:end]

        account_type = _detect_account_type(segment, acc)
        account_name = account_type

        summary = AccountGainLossSummary(
            statement_period_start=statement_period_start,
            statement_period_end=statement_period_end,
            statement_date=statement_date,
            source_file=source_file,
            account_number=acc,
            account_name=account_name,
            account_type=account_type,
            beginning_value_ytd=_extract_money_by_label(segment, "YTD Beginning Account Value"),
            additions_ytd=_extract_money_by_label(segment, "YTD Additions"),
            subtractions_ytd=_extract_money_by_label(segment, "YTD Subtractions"),
            fees_ytd=_extract_money_by_label(segment, "YTD Transaction Costs / Fees / Charges"),
            transfers_between_fidelity_accounts_ytd=_extract_money_by_label(
                segment, "YTD Transfers Between Fidelity Accounts"
            ),
            change_in_investment_value_ytd=_extract_money_by_label(segment, "YTD Change in Investment Value"),
            ending_value=_extract_money_by_label(segment, "Ending Account Value"),
            taxable_income_ytd=_extract_money_by_label(segment, "Taxable income YTD"),
            dividends_ytd=_extract_money_by_label(segment, "Dividends YTD"),
            long_term_capital_gains_income_ytd=_extract_money_by_label(
                segment, "Long-term capital gains income YTD"
            ),
            realized_short_term_net_ytd=_extract_money_by_label(segment, "YTD realized net short-term gain/loss"),
            realized_short_term_gain_ytd=_extract_money_by_label(segment, "YTD short-term gain"),
            realized_short_term_loss_ytd=_extract_money_by_label(segment, "YTD short-term loss"),
            realized_short_term_disallowed_loss_ytd=_extract_money_by_label(
                segment, "YTD short-term disallowed loss"
            ),
            realized_long_term_net_ytd=_extract_money_by_label(segment, "YTD realized net long-term gain/loss"),
            realized_long_term_gain_ytd=_extract_money_by_label(segment, "YTD long-term gain"),
            realized_long_term_loss_ytd=_extract_money_by_label(segment, "YTD long-term loss"),
            realized_long_term_disallowed_loss_ytd=_extract_money_by_label(
                segment, "YTD long-term disallowed loss"
            ),
            realized_net_gain_loss_ytd=_extract_money_by_label(segment, "YTD net realized gain/loss"),
            extraction_method=extraction_method,
            confidence=confidence,
            notes=[],
        )

        # Deduplicate repeated account numbers if present in repeated headers.
        if any(a.account_number == summary.account_number for a in accounts):
            continue
        accounts.append(summary)

    return accounts


def _parse_portfolio_summary(
    text: str,
    statement_period_start: str | None,
    statement_period_end: str | None,
    statement_date: str | None,
    source_file: str,
    extraction_method: str,
    confidence: str,
) -> StatementPortfolioSummary | None:
    ending_portfolio = _extract_money_by_label(text, "Ending Portfolio Value")
    if ending_portfolio is None:
        return None

    return StatementPortfolioSummary(
        statement_period_start=statement_period_start,
        statement_period_end=statement_period_end,
        statement_date=statement_date,
        source_file=source_file,
        beginning_value_ytd=_extract_money_by_label(text, "YTD Beginning Portfolio Value"),
        additions_ytd=_extract_money_by_label(text, "YTD Additions"),
        subtractions_ytd=_extract_money_by_label(text, "YTD Subtractions"),
        fees_ytd=_extract_money_by_label(text, "YTD Transaction Costs / Fees / Charges"),
        transfers_between_fidelity_accounts_ytd=_extract_money_by_label(
            text, "YTD Transfers Between Fidelity Accounts"
        ),
        change_in_investment_value_ytd=_extract_money_by_label(text, "YTD Change in Investment Value"),
        ending_value=ending_portfolio,
        taxable_income_ytd=_extract_money_by_label(text, "Taxable income YTD"),
        dividends_ytd=_extract_money_by_label(text, "Dividends YTD"),
        long_term_capital_gains_income_ytd=_extract_money_by_label(text, "Long-term capital gains income YTD"),
        total_including_other_holdings=_extract_money_by_label(text, "Total Including Other Holdings"),
        extraction_method=extraction_method,
        confidence=confidence,
        notes=[],
    )


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise StatementParsingError(
            "PDF extraction requires pypdf. Install it or provide extracted text."
        ) from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        raise StatementParsingError(
            "PDF did not contain extractable text. OCR is not implemented.",
            reason="ocr_unavailable",
            details={
                "source_file": str(path),
                "source_provenance": "ocr-unavailable",
            },
        )
    return text


def load_statement_source(source_path: str | Path | None = None, text: str | None = None) -> StatementSource:
    if text is not None:
        return StatementSource(
            source_file="inline_text",
            extraction_method="text-provided",
            confidence="statement-derived",
            source_provenance="manual-text-extract",
            text=text,
        )

    if source_path is None:
        raise StatementParsingError("Either source_path or text must be provided.")

    path = Path(source_path)
    if not path.exists():
        raise StatementParsingError(f"Statement source not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        extracted = _extract_pdf_text(path)
        return StatementSource(
            source_file=str(path),
            extraction_method="pdf-text-extraction",
            confidence="statement-derived",
            source_provenance="pdf-text-extracted",
            text=extracted,
        )
    if suffix in {".txt", ".md"}:
        provenance = _source_provenance_for_path(path)
        return StatementSource(
            source_file=str(path),
            extraction_method="text-file",
            confidence="statement-derived",
            source_provenance=_ensure_source_provenance(provenance),
            text=path.read_text(encoding="utf-8"),
        )

    raise StatementParsingError(
        f"Unsupported statement source format: {path.suffix}. Use .pdf or .txt/.md"
    )


def _derive_totals(
    accounts: list[AccountGainLossSummary],
    main_statement_account_numbers: set[str],
) -> dict[str, Any]:
    def _sum(attr: str, subset: list[AccountGainLossSummary]) -> float | None:
        vals = [getattr(a, attr) for a in subset if getattr(a, attr) is not None]
        if not vals:
            return None
        return round(sum(vals), 2)

    all_accounts = accounts
    main_accounts = [a for a in accounts if a.account_number in main_statement_account_numbers]

    return {
        "portfolio_vs_account_total_provenance": {
            "statement_level_totals": "authoritative",
            "account_level_summaries": "statement-derived",
            "cross_account_combined_totals": "derived",
            "operator_validation_values": "operator-supplied",
        },
        "combined_realized_net_gain_loss_ytd_all_accounts": _sum("realized_net_gain_loss_ytd", all_accounts),
        "combined_realized_net_gain_loss_ytd_main_statement_accounts": _sum(
            "realized_net_gain_loss_ytd", main_accounts
        ),
        "combined_change_in_investment_value_ytd_all_accounts": _sum(
            "change_in_investment_value_ytd", all_accounts
        ),
        "account_counts": {
            "all_accounts": len(all_accounts),
            "main_statement_accounts": len(main_accounts),
        },
    }


def build_snapshot_from_sources(
    sources: list[StatementSource],
    statement_date: str | None = None,
    statement_period_start: str | None = None,
    statement_period_end: str | None = None,
    main_statement_account_numbers: set[str] | None = None,
) -> StatementGainLossSnapshot:
    if not sources:
        raise StatementParsingError("At least one statement source is required.")

    account_map: dict[str, AccountGainLossSummary] = {}
    portfolio_summary: StatementPortfolioSummary | None = None
    warnings: list[str] = []
    resolved_start: str | None = statement_period_start
    resolved_end: str | None = statement_period_end
    resolved_date: str | None = statement_date

    for src in sources:
        _ensure_source_provenance(src.source_provenance)
        p_start, p_end, p_date, src_warnings = _resolve_period_and_date(
            src.text,
            src.source_file,
            statement_date,
            statement_period_start,
            statement_period_end,
        )
        warnings.extend(src_warnings)
        resolved_start = resolved_start or p_start
        resolved_end = resolved_end or p_end
        resolved_date = resolved_date or p_date

        parsed_portfolio = _parse_portfolio_summary(
            src.text,
            p_start,
            p_end,
            p_date,
            src.source_file,
            src.extraction_method,
            src.confidence,
        )
        if parsed_portfolio and portfolio_summary is None:
            portfolio_summary = parsed_portfolio

        for acct in _parse_account_summaries(
            src.text,
            p_start,
            p_end,
            p_date,
            src.source_file,
            src.extraction_method,
            src.confidence,
        ):
            account_map[acct.account_number] = acct

    accounts = sorted(account_map.values(), key=lambda a: a.account_number)
    main_set = main_statement_account_numbers or {"X20-548022", "Z35-123695"}
    derived_totals = _derive_totals(accounts, main_set)

    reconciliation_notes = [
        "Main portfolio statement aggregates X20 and Z35. Do not add X20/Z35 account totals to main statement totals.",
        "Joint account Z26 can be included in derived cross-statement totals when explicitly requested.",
    ]

    if portfolio_summary is None:
        warnings.append("No portfolio-level summary detected in provided statement sources.")

    usage_guidance = {
        "use_for": [
            "operator awareness",
            "tax-aware context",
            "after-tax caution flags",
            "realized gain/loss tracking",
            "A+ path tax context",
            "cash/deployment review context",
        ],
        "do_not_use_for": [
            "change ESS/CW-DAS/UCF/CRA scores",
            "change recommendations",
            "change ranking",
            "change allocation targets",
            "change deployment queue ordering",
            "execute trades",
            "override current holdings values",
        ],
    }

    return StatementGainLossSnapshot(
        statement_period_start=(statement_period_start or (portfolio_summary.statement_period_start if portfolio_summary else None) or resolved_start),
        statement_period_end=(statement_period_end or (portfolio_summary.statement_period_end if portfolio_summary else None) or resolved_end),
        statement_date=(statement_date or (portfolio_summary.statement_date if portfolio_summary else None) or resolved_date),
        source_files=[s.source_file for s in sources],
        source_provenance=[
            {
                "source_file": s.source_file,
                "source_provenance": s.source_provenance,
            }
            for s in sources
        ],
        extraction_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        portfolio_summary=portfolio_summary,
        accounts=accounts,
        derived_totals=derived_totals,
        reconciliation_notes=reconciliation_notes,
        warnings=warnings,
        precision_limitations=[
            "Parsed from broker statement text; formatting/layout changes can reduce extraction reliability.",
            "OCR is not performed. Scanned-image PDFs without embedded text will fail gracefully.",
            "Use broker tax documents as authoritative sources for filing.",
        ],
        usage_guidance=usage_guidance,
    )


def _format_money(val: float | None) -> str:
    if val is None:
        return "n/a"
    sign = "-" if val < 0 else ""
    return f"{sign}${abs(val):,.2f}"


def _account_table_rows(accounts: list[AccountGainLossSummary]) -> list[str]:
    rows = [
        "| Account | Ending Value | YTD Change in Investment Value | Net Realized Gain/Loss YTD |",
        "|---|---:|---:|---:|",
    ]
    for a in accounts:
        rows.append(
            f"| {a.account_number} | {_format_money(a.ending_value)} | "
            f"{_format_money(a.change_in_investment_value_ytd)} | {_format_money(a.realized_net_gain_loss_ytd)} |"
        )
    return rows


def write_snapshot_artifacts(snapshot: StatementGainLossSnapshot, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    date_str = snapshot.statement_date or "unknown"

    json_path = out / f"STATEMENT_GAIN_LOSS_{date_str}.json"
    md_path = out / f"STATEMENT_GAIN_LOSS_{date_str}.md"

    json_path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")

    portfolio = snapshot.portfolio_summary
    lines = [
        f"# Statement Gain/Loss Snapshot ({date_str})",
        "",
        "## Executive Summary",
        f"- Parse status: {snapshot.parse_status}",
        f"- Promoted to latest: {'yes' if snapshot.promoted_to_latest else 'no'}",
        f"- Statement period: {snapshot.statement_period_start} to {snapshot.statement_period_end}",
        f"- Statement date: {snapshot.statement_date}",
        f"- Portfolio ending value: {_format_money(portfolio.ending_value if portfolio else None)}",
        f"- Portfolio YTD change in investment value: {_format_money(portfolio.change_in_investment_value_ytd if portfolio else None)}",
        f"- Combined realized net gain/loss (all parsed accounts): {_format_money(snapshot.derived_totals.get('combined_realized_net_gain_loss_ytd_all_accounts'))}",
        "",
        "## Warnings",
        *([f"- {w}" for w in snapshot.warnings] if snapshot.warnings else ["- none"]),
        "",
        "## Source Provenance",
        *[
            f"- {item['source_file']}: {item['source_provenance']}"
            for item in snapshot.source_provenance
        ],
        "",
        "## Per-Account Realized Gain/Loss",
        * _account_table_rows(snapshot.accounts),
        "",
        "## Statement-Level YTD Investment Value",
        "| Metric | Value |",
        "|---|---:|",
        f"| YTD Beginning Portfolio Value | {_format_money(portfolio.beginning_value_ytd if portfolio else None)} |",
        f"| YTD Additions | {_format_money(portfolio.additions_ytd if portfolio else None)} |",
        f"| YTD Subtractions | {_format_money(portfolio.subtractions_ytd if portfolio else None)} |",
        f"| YTD Transaction Costs / Fees / Charges | {_format_money(portfolio.fees_ytd if portfolio else None)} |",
        f"| YTD Transfers Between Fidelity Accounts | {_format_money(portfolio.transfers_between_fidelity_accounts_ytd if portfolio else None)} |",
        f"| YTD Change in Investment Value | {_format_money(portfolio.change_in_investment_value_ytd if portfolio else None)} |",
        "",
        "## Combined Totals",
        f"- Combined realized net gain/loss YTD (all parsed accounts): {_format_money(snapshot.derived_totals.get('combined_realized_net_gain_loss_ytd_all_accounts'))}",
        f"- Combined realized net gain/loss YTD (main statement accounts only): {_format_money(snapshot.derived_totals.get('combined_realized_net_gain_loss_ytd_main_statement_accounts'))}",
        f"- Combined change in investment value YTD (all parsed accounts): {_format_money(snapshot.derived_totals.get('combined_change_in_investment_value_ytd_all_accounts'))}",
        "",
        "## Tax-Awareness Caveats",
        "- Statement-derived values are for situational awareness and tax-aware context only.",
        "- Broker statement layouts may vary; verify critical numbers before filing or execution decisions.",
        "- Main statement totals and account totals can overlap; avoid double counting.",
        "",
        "## SIH Usage Rules",
        "### Use Statement-Derived Data For",
        * [f"- {x}" for x in snapshot.usage_guidance["use_for"]],
        "",
        "### Do Not Use Statement-Derived Data To",
        * [f"- {x}" for x in snapshot.usage_guidance["do_not_use_for"]],
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return json_path, md_path
