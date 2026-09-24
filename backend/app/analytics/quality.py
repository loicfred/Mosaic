"""Data Health scoring. The same formula is used for the ledger and for imports.

score = 100 x (0.40 x validity + 0.20 x (1 - duplicate rate)
               + 0.20 x category coverage + 0.20 x counterparty completeness)
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.anomalies import duplicate_groups

# Outflow categories where a payee is expected (payroll, bank fees and tax are exempt).
PAYEE_EXPECTED = {"Inventory & supplies", "Rent", "Utilities", "Telecom & internet", "Software & subscriptions",
                  "Marketing", "Insurance", "Repairs & maintenance", "Professional fees",
                  "Transport & logistics", "Equipment", "Other expenses", "Uncategorised"}

WEIGHTS = {"validity": 0.40, "duplicates": 0.20, "coverage": 0.20, "completeness": 0.20}


def health_score(validity: float, duplicate_rate: float, coverage: float, completeness: float) -> dict[str, Any]:
    comps = {"validity": validity, "duplicates": 1 - duplicate_rate, "coverage": coverage,
             "completeness": completeness}
    score = 100 * sum(WEIGHTS[k] * max(0.0, min(1.0, v)) for k, v in comps.items())
    # floor, so 100 is only shown when there is nothing at all to fix
    return {"score": int(score), "components": {k: round(v * 100, 1) for k, v in comps.items()},
            "weights": WEIGHTS}


def ledger_health(tx: pd.DataFrame, anomalies_flagged: int = 0) -> dict[str, Any]:
    """tx must include excluded rows (so we can report them) with columns
    date, direction, amount, category, counterparty, description, excluded."""
    active = tx[~tx["excluded"]] if "excluded" in tx.columns else tx
    n = len(active)
    if n == 0:
        return {**health_score(1, 0, 1, 1), "checks": [], "totals": {"transactions": 0}}
    gid = duplicate_groups(active)
    dup_rows = int(gid.notna().sum())
    dup_groups = int(gid.dropna().nunique())
    extra_copies = dup_rows - dup_groups
    uncategorised = int((active["category"] == "Uncategorised").sum())
    needs_payee = active[(active["direction"] == "outflow") & active["category"].isin(PAYEE_EXPECTED)]
    missing_payee = int(needs_payee["counterparty"].isna().sum())
    dates = pd.to_datetime(active["date"])
    h = health_score(1.0, extra_copies / n, 1 - uncategorised / n,
                     1 - (missing_payee / len(needs_payee) if len(needs_payee) else 0))
    checks = [
        {"key": "valid", "status": "ok", "label": f"{n:,} valid transactions",
         "detail": "Amounts, dates and directions pass database constraints."},
        {"key": "coverage", "status": "ok" if uncategorised == 0 else "warning",
         "label": f"{(1 - uncategorised / n) * 100:.1f}% category coverage",
         "detail": f"{uncategorised} uncategorised transaction(s)." if uncategorised else "All categorised.",
         "count": uncategorised},
        {"key": "duplicates", "status": "ok" if dup_groups == 0 else "warning",
         "label": f"{dup_groups} possible duplicate group(s)" if dup_groups else "No duplicates found",
         "detail": "Same date, direction, amount and payee.", "count": dup_groups},
        {"key": "payees", "status": "ok" if missing_payee == 0 else "warning",
         "label": f"{missing_payee} expense(s) without a payee" if missing_payee else "All expenses have a payee",
         "detail": "Payees are needed for supplier and recurring-cost analysis.", "count": missing_payee},
        {"key": "suspicious", "status": "ok" if anomalies_flagged == 0 else "info",
         "label": f"{anomalies_flagged} unusual payment(s) flagged (all history)" if anomalies_flagged else "No unusual payments",
         "detail": "Flagged by the anomaly model or the 4x-usual-amount rule; review, not errors.",
         "count": anomalies_flagged},
    ]
    return {**h, "checks": checks, "totals": {
        "transactions": n, "excluded": int(tx["excluded"].sum()) if "excluded" in tx.columns else 0,
        "date_min": str(dates.min().date()), "date_max": str(dates.max().date()),
        "uncategorised": uncategorised, "duplicate_groups": dup_groups, "missing_payee": missing_payee,
        "counterparties": int(active["counterparty"].nunique()),
        "customers": int(active.loc[active["direction"] == "inflow", "counterparty"].nunique()),
        "suppliers": int(active.loc[active["direction"] == "outflow", "counterparty"].nunique()),
    }}
