"""Normalised in-memory view of one business's ledger.

The deterministic engine, the ML feature pipeline and the scenario simulator all
operate on this single structure so that the same number is never computed two
different ways.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.core.taxonomy import CATEGORIES, RECURRING_CANDIDATES

TX_COLUMNS = [
    "id", "date", "direction", "amount", "category", "subcategory", "description",
    "counterparty", "counterparty_type",
]
INV_COLUMNS = ["invoice_no", "customer", "issue_date", "due_date", "amount", "paid_date"]


def _group(cat: str) -> str:
    entry = CATEGORIES.get(cat)
    return entry[1] if entry else "uncategorised"


@dataclass
class Ledger:
    tx: pd.DataFrame  # one row per transaction, sorted by date
    invoices: pd.DataFrame
    opening_cash: float
    opening_date: pd.Timestamp
    daily_cash: pd.Series  # end-of-day cash balance, daily index

    @property
    def start(self) -> pd.Timestamp:
        return self.opening_date

    @property
    def end(self) -> pd.Timestamp:
        if self.tx.empty:
            return self.opening_date
        return pd.Timestamp(self.tx["date"].max())

    def cash_at(self, when: pd.Timestamp) -> float:
        when = pd.Timestamp(when).normalize()
        if when < self.daily_cash.index[0]:
            return self.opening_cash
        s = self.daily_cash.loc[:when]
        return float(s.iloc[-1]) if len(s) else self.opening_cash

    def window(self, end: pd.Timestamp, days: int, offset: int = 0) -> pd.DataFrame:
        """Transactions in (end-offset-days, end-offset]."""
        hi = pd.Timestamp(end) - pd.Timedelta(days=offset)
        lo = hi - pd.Timedelta(days=days)
        t = self.tx
        return t[(t["date"] > lo) & (t["date"] <= hi)]


def build_ledger(
    tx: pd.DataFrame,
    invoices: pd.DataFrame | None,
    opening_cash: float,
    opening_date: date | pd.Timestamp | None = None,
    end_date: date | pd.Timestamp | None = None,
) -> Ledger:
    t = tx.copy()
    if "id" not in t.columns:
        t["id"] = t.get("txn_ref", pd.Series(range(len(t)), index=t.index)).astype(str)
    for col in TX_COLUMNS:
        if col not in t.columns:
            t[col] = None
    t["date"] = pd.to_datetime(t["date"]).dt.normalize()
    t["amount"] = t["amount"].astype(float)
    t["signed"] = np.where(t["direction"] == "inflow", t["amount"], -t["amount"])
    t["group"] = t["category"].map(_group)
    t["is_recurring_cat"] = t["category"].isin(RECURRING_CANDIDATES)
    # Outflows the business is committed to (everything except discretionary owner drawings).
    t["is_obligation"] = (t["direction"] == "outflow") & (t["category"] != "Owner drawings")
    t = t.sort_values("date", kind="stable").reset_index(drop=True)

    inv = invoices.copy() if invoices is not None and len(invoices) else pd.DataFrame(columns=INV_COLUMNS)
    for col in ("issue_date", "due_date", "paid_date"):
        inv[col] = pd.to_datetime(inv[col]) if col in inv.columns else pd.NaT
    if "amount" in inv.columns:
        inv["amount"] = inv["amount"].astype(float)

    start = pd.Timestamp(opening_date) if opening_date is not None else (
        t["date"].min() if len(t) else pd.Timestamp.today().normalize())
    last = pd.Timestamp(end_date) if end_date is not None else (t["date"].max() if len(t) else start)
    idx = pd.date_range(start.normalize(), max(last, start).normalize(), freq="D")
    daily_net = t.groupby("date")["signed"].sum().reindex(idx, fill_value=0.0)
    daily_cash = opening_cash + daily_net.cumsum()
    return Ledger(tx=t, invoices=inv, opening_cash=float(opening_cash),
                  opening_date=start.normalize(), daily_cash=daily_cash)
