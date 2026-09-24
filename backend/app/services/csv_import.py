"""Safe CSV parsing and validation for bank / card exports.

Nothing here touches the database. The function returns staged rows with a
status and a list of issues per row; the import service stores them and asks
the user to approve fixes before anything is committed.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.taxonomy import CATEGORIES, UNCATEGORISED, direction_of

HEADER_ALIASES = {
    "date": {"date", "transaction date", "txn date", "value date", "posting date", "booking date"},
    "description": {"description", "details", "narrative", "memo", "particulars", "transaction details"},
    "amount": {"amount", "value", "amount (mur)", "amount mur", "mur", "amount_mur"},
    "debit": {"debit", "withdrawal", "money out", "paid out", "dr"},
    "credit": {"credit", "deposit", "money in", "paid in", "cr"},
    "direction": {"type", "direction", "dr/cr", "debit/credit", "in/out"},
    "category": {"category", "account", "expense category"},
    "counterparty": {"counterparty", "payee", "supplier", "customer", "merchant", "payer", "name"},
    "reference": {"reference", "ref", "invoice", "invoice no", "document no"},
}
CATEGORY_SYNONYMS = {
    "electricity": "Utilities", "water": "Utilities", "utilities": "Utilities",
    "salaries": "Payroll", "salary": "Payroll", "wages": "Payroll", "payroll": "Payroll",
    "stock": "Inventory & supplies", "inventory": "Inventory & supplies", "purchases": "Inventory & supplies",
    "cost of sales": "Inventory & supplies", "supplies": "Inventory & supplies",
    "internet": "Telecom & internet", "telephone": "Telecom & internet", "phone": "Telecom & internet",
    "software": "Software & subscriptions", "subscriptions": "Software & subscriptions",
    "advertising": "Marketing", "ads": "Marketing", "fuel": "Transport & logistics",
    "transport": "Transport & logistics", "delivery": "Transport & logistics", "repairs": "Repairs & maintenance",
    "maintenance": "Repairs & maintenance", "vat": "Taxes (VAT)", "tax": "Taxes (VAT)", "fees": "Bank fees",
    "bank charges": "Bank fees", "sales": "Sales", "income": "Sales", "revenue": "Sales",
    "packaging": "Inventory & supplies", "rent": "Rent", "insurance": "Insurance", "equipment": "Equipment",
    "misc": "Other expenses",
    "other": "Other expenses", "office": "Other expenses", "stationery": "Other expenses",
}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%d/%m/%y", "%Y/%m/%d")
FORMULA_PREFIXES = ("=", "+", "@", "\t", "\r")
MAX_TEXT = 300
MAX_AMOUNT = Decimal("1000000000")


class CsvRejected(Exception):
    """The whole file is unusable (wrong format, unsafe, too large)."""


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", h.strip().lower().replace("_", " "))


def map_headers(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for h in headers:
        n = _norm_header(h)
        for field, aliases in HEADER_ALIASES.items():
            if n in aliases and field not in mapping:
                mapping[field] = h
    return mapping


def decode(data: bytes) -> str:
    if b"\x00" in data[:4096]:
        raise CsvRejected("The file looks binary, not a CSV export.")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise CsvRejected("Could not read the file's text encoding (use UTF-8).")


def parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw: str) -> Decimal | None:
    s = raw.strip().replace(" ", " ")
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    s = re.sub(r"(?i)\b(mur|rs\.?|rs)\b", "", s).replace(",", "").replace(" ", "")
    if s.endswith("-"):
        neg, s = True, s[:-1]
    if not re.fullmatch(r"[+-]?\d+(\.\d{1,2})?", s):
        return None
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    return -v if neg else v


def normalise_category(raw: str) -> str | None:
    s = raw.strip()
    if not s:
        return None
    for c in CATEGORIES:
        if c.lower() == s.lower():
            return c
    return CATEGORY_SYNONYMS.get(s.lower())


def sanitise_text(raw: str) -> tuple[str, bool]:
    s = raw.strip()
    flagged = False
    while s.startswith(FORMULA_PREFIXES) or (s.startswith("-") and len(s) > 1 and not s[1].isdigit()):
        s, flagged = s[1:].lstrip(), True
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    return s[:MAX_TEXT], flagged


PAYEE_STOPWORDS = {"the", "bank", "owner", "landlord", "island", "new", "shop", "city", "global"}


def match_counterparty(desc_lower: str, cps_lower: list[tuple[str, str]]) -> str | None:
    """Known payee named in the description: full name first, then a distinctive first word."""
    for lc, orig in cps_lower:
        if len(lc) >= 4 and lc in desc_lower:
            return orig
    words = set(re.findall(r"[a-z0-9]+", desc_lower))
    for lc, orig in cps_lower:
        first = lc.split()[0] if lc.split() else ""
        if len(first) >= 3 and first not in PAYEE_STOPWORDS and first in words:
            return orig
    return None


def row_key(d: date, direction: str, amount: Decimal, who: str) -> str:
    return f"{d.isoformat()}|{direction}|{amount:.2f}|{who.strip().lower()}"


def parse_csv(data: bytes, *, max_rows: int, today: date, opening_date: date | None,
              existing_keys: set[str], known_counterparties: list[str],
              typical_outflow: float | None) -> dict[str, Any]:
    text = decode(data)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    try:
        headers = next(reader)
    except StopIteration:
        raise CsvRejected("The file is empty.") from None
    mapping = map_headers(headers)
    if "date" not in mapping or "description" not in mapping or not (
            "amount" in mapping or ("debit" in mapping and "credit" in mapping)):
        raise CsvRejected("Missing required columns. Need: date, description and either amount or "
                          "debit + credit.")
    idx = {f: headers.index(h) for f, h in mapping.items()}
    cps_lower = sorted(((c.lower(), c) for c in known_counterparties if c), key=lambda t: -len(t[0]))

    rows: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for n, rec in enumerate(reader, start=2):
        if len(rows) >= max_rows:
            raise CsvRejected(f"Too many rows (limit {max_rows:,}). Split the file.")
        if not any(c.strip() for c in rec):
            continue
        get = lambda f: rec[idx[f]] if f in idx and idx[f] < len(rec) else ""  # noqa: E731
        raw = {f: get(f) for f in idx}
        issues: list[dict[str, str]] = []

        def issue(code: str, field: str, msg: str, level: str) -> None:
            issues.append({"code": code, "field": field, "message": msg, "level": level})

        if len(rec) != len(headers):
            issue("column_count", "*", f"Row has {len(rec)} columns, header has {len(headers)}.", "warning")

        d = parse_date(get("date"))
        if d is None:
            issue("invalid_date", "date", f"'{get('date')[:20]}' is not a valid date.", "error")
        elif d > today:
            issue("future_date", "date", f"{d.isoformat()} is in the future.", "error")
        elif opening_date and d < opening_date:
            issue("before_opening", "date", "Date is before the ledger's opening balance date.", "error")

        direction = None
        amount: Decimal | None = None
        if "amount" in idx:
            amount = parse_amount(get("amount"))
            if amount is None:
                issue("invalid_amount", "amount", f"'{get('amount')[:20]}' is not a valid amount.", "error")
        else:
            dr, cr = parse_amount(get("debit")), parse_amount(get("credit"))
            if (dr is None) == (cr is None):
                issue("invalid_amount", "amount", "Exactly one of debit or credit must be filled.", "error")
            else:
                amount = -abs(dr) if dr is not None else abs(cr)  # type: ignore[arg-type]
        dir_raw = get("direction").strip().lower() if "direction" in idx else ""
        if amount is not None:
            if amount == 0:
                issue("zero_amount", "amount", "Amount is zero.", "error")
            elif abs(amount) > MAX_AMOUNT:
                issue("amount_out_of_range", "amount", "Amount is outside the accepted range.", "error")
            if dir_raw in ("dr", "debit", "out", "outflow", "payment", "expense"):
                direction = "outflow"
            elif dir_raw in ("cr", "credit", "in", "inflow", "receipt", "income"):
                direction = "inflow"
            else:
                direction = "outflow" if amount < 0 else "inflow"
            amount = abs(amount)

        desc, flagged = sanitise_text(get("description"))
        if flagged:
            issue("formula_chars", "description", "Leading spreadsheet-formula characters were removed.",
                  "warning")
        if not desc:
            issue("missing_description", "description", "Description is empty.", "error")
        cp_raw, cp_flag = sanitise_text(get("counterparty")) if "counterparty" in idx else ("", False)
        if cp_flag:
            issue("formula_chars", "counterparty", "Leading spreadsheet-formula characters were removed.",
                  "warning")
        ref, _ = sanitise_text(get("reference")) if "reference" in idx else ("", False)

        cat_raw = get("category").strip() if "category" in idx else ""
        category = normalise_category(cat_raw) if cat_raw else None
        if cat_raw and category is None:
            issue("unknown_category", "category", f"'{cat_raw[:40]}' is not a known category.", "warning")
        if category is None:
            category = UNCATEGORISED
            issue("uncategorised", "category", "No category; a suggestion will be proposed.", "warning")
        elif direction and direction_of(category) and direction_of(category) != direction:
            issue("direction_mismatch", "category", f"{category} is normally an {direction_of(category)}.",
                  "warning")

        suggested_cp = None
        if not cp_raw and direction == "outflow":
            low = desc.lower()
            suggested_cp = match_counterparty(low, cps_lower)
            issue("missing_counterparty", "counterparty", "No payee given." + (
                f" Looks like {suggested_cp}." if suggested_cp else ""), "warning")

        if amount is not None and typical_outflow and direction == "outflow" and float(amount) > 20 * typical_outflow:
            issue("suspicious_amount", "amount", "Much larger than this business's usual payments.", "warning")

        status = "error" if any(i["level"] == "error" for i in issues) else ("warning" if issues else "valid")
        parsed = None
        dup_of = None
        if status != "error" and d and amount is not None and direction:
            who = cp_raw or desc
            k = row_key(d, direction, amount, who)
            if k in existing_keys:
                dup_of = "ledger"
            elif k in seen:
                dup_of = f"row {seen[k]}"
            else:
                seen[k] = n
            if dup_of:
                what = "an existing transaction" if dup_of == "ledger" else dup_of
                issue("duplicate", "*", f"Same date, amount and payee as {what}.", "warning")
                status = "duplicate"
            parsed = {"date": d.isoformat(), "direction": direction, "amount": f"{amount:.2f}",
                      "description": desc, "counterparty": cp_raw or None, "reference": ref or None,
                      "category": category, "suggested_counterparty": suggested_cp, "duplicate_of": dup_of}
        rows.append({"row_number": n, "raw": raw, "parsed": parsed or {}, "status": status, "issues": issues})

    if not rows:
        raise CsvRejected("No data rows found.")
    return {"headers": headers, "mapping": mapping, "rows": rows}
