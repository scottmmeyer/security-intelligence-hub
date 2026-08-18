from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse


_SCORE_RE = re.compile(r"\b(10|[1-9])\s*out\s+of\s+10\b", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_LONG_DATE_RE = re.compile(
    r"\b(last\s+update|updated?)\b[^\n]*?\b([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\b",
    re.IGNORECASE,
)
_PAIR_PATH_RE = re.compile(r"^/stocks/([A-Za-z0-9.\-]+)-vs-([A-Za-z0-9.\-]+)$", re.IGNORECASE)
_SINGLE_PATH_RE = re.compile(r"^/stock/([A-Za-z0-9.\-]+)$", re.IGNORECASE)
_TICKER_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]{0,4}$")

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True)
class ParsedObservation:
    symbol: str
    danelfin_raw: int
    sourced_date: str | None


def _parse_long_date(text: str) -> str | None:
    clean = text.replace(",", " ").strip()
    parts = [p for p in clean.split() if p]
    if len(parts) < 3:
        return None
    month = _MONTHS.get(parts[0].lower())
    if not month:
        return None
    try:
        day = int(parts[1])
        year = int(parts[2])
        parsed = date(year=year, month=month, day=day)
    except Exception:
        return None
    return parsed.isoformat()


def extract_source_date(page_text: str) -> str | None:
    iso_match = _ISO_DATE_RE.search(page_text)
    if iso_match:
        return iso_match.group(1)

    long_match = _LONG_DATE_RE.search(page_text)
    if not long_match:
        return None
    return _parse_long_date(long_match.group(2))


def extract_scores(page_text: str) -> list[int]:
    scores: list[int] = []
    for m in _SCORE_RE.finditer(page_text):
        raw = int(m.group(1))
        if 1 <= raw <= 10:
            scores.append(raw)
    return scores


def _symbols_from_url(url: str) -> tuple[str, ...]:
    parsed = urlparse(url)
    path = parsed.path or ""
    single = _SINGLE_PATH_RE.match(path)
    if single:
        symbol = single.group(1).upper()
        if _TICKER_LIKE_RE.match(symbol):
            return (symbol,)
        return tuple()
    pair = _PAIR_PATH_RE.match(path)
    if pair:
        left = pair.group(1).upper()
        right = pair.group(2).upper()
        if _TICKER_LIKE_RE.match(left) and _TICKER_LIKE_RE.match(right):
            return (left, right)
        return tuple()
    return tuple()


def parse_single_stock_page(url: str, page_text: str) -> ParsedObservation:
    symbols = _symbols_from_url(url)
    if len(symbols) != 1:
        raise ValueError("single-stock URL does not contain exactly one symbol")
    scores = extract_scores(page_text)
    if not scores:
        raise ValueError("no Danelfin score found on single-stock page")
    return ParsedObservation(symbol=symbols[0], danelfin_raw=scores[0], sourced_date=extract_source_date(page_text))


def parse_pair_page(
    url: str,
    page_text: str,
    *,
    expected_symbols: tuple[str, str] | None = None,
) -> tuple[ParsedObservation, ParsedObservation]:
    symbols = _symbols_from_url(url)
    if len(symbols) != 2:
        symbols = tuple(s.strip().upper() for s in (expected_symbols or ()) if s and s.strip())
    if len(symbols) != 2:
        raise ValueError("pair-page symbols unavailable from URL and expected_symbols")

    scores = extract_scores(page_text)
    if len(scores) < 2:
        raise ValueError("pair-page requires at least two Danelfin scores")

    sourced_date = extract_source_date(page_text)
    return (
        ParsedObservation(symbol=symbols[0], danelfin_raw=scores[0], sourced_date=sourced_date),
        ParsedObservation(symbol=symbols[1], danelfin_raw=scores[1], sourced_date=sourced_date),
    )
