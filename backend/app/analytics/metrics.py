"""Deterministic financial metrics (cash basis).

Definitions (also in docs/DATA_DICTIONARY.md):
  revenue            inflows in category group 'revenue' (Sales)
  cost of goods      outflows in group 'cogs' (Inventory & supplies)
  operating expenses outflows in group 'operating'
  gross margin       (revenue - cost of goods) / revenue
  operating cash flow revenue + other income - cogs - operating - tax
  net cash flow      all inflows - all outflows (includes financing)
Excluded transactions (confirmed duplicates) never enter any metric.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.ledger import Ledger


def pct_change(cur: float, prev: float) -> float | None:
    if prev is None or abs(prev) < 1e-9:
        return None
    return float((cur - prev) / abs(prev) * 100.0)


def summarise(df: pd.DataFrame) -> dict[str, float]:
    g = df.groupby("group")["amount"].sum() if len(df) else pd.Series(dtype=float)
    rev = float(g.get("revenue", 0.0))
    cogs = float(g.get("cogs", 0.0))
    opex = float(g.get("operating", 0.0))
    tax = float(g.get("tax", 0.0))
    other = float(g.get("other_income", 0.0))
    inflow = float(df.loc[df["direction"] == "inflow", "amount"].sum()) if len(df) else 0.0
    outflow = float(df.loc[df["direction"] == "outflow", "amount"].sum()) if len(df) else 0.0
    return {
        "revenue": rev,
        "cost_of_goods": cogs,
        "operating_expenses": opex,
        "tax": tax,
        "expenses": cogs + opex + tax,
        "gross_profit": rev - cogs,
        "gross_margin_pct": (rev - cogs) / rev * 100 if rev else 0.0,
        "operating_cash_flow": rev + other - cogs - opex - tax,
        "total_inflow": inflow,
        "total_outflow": outflow,
        "net_cash_flow": inflow - outflow,
        "transactions": float(len(df)),
    }


def complete_month_windows(as_of: pd.Timestamp, n: int = 3) -> tuple[pd.Timestamp, pd.Timestamp,
                                                                      pd.Timestamp, pd.Timestamp]:
    """Last n complete calendar months and the n months before them.

    Month-aligned windows avoid calendar artefacts (e.g. a rolling 90-day window
    that happens to contain four payroll runs against three)."""
    as_of = pd.Timestamp(as_of).normalize()
    nxt = as_of + pd.Timedelta(days=1)
    first = nxt if nxt.day == 1 else as_of.replace(day=1)
    a_end = first - pd.Timedelta(days=1)
    a_start = (first - pd.DateOffset(months=n)).normalize()
    b_end = a_start - pd.Timedelta(days=1)
    b_start = (a_start - pd.DateOffset(months=n)).normalize()
    return a_start, a_end, b_start, b_end


def month_comparison(ledger: Ledger, as_of: pd.Timestamp, n: int = 3) -> dict[str, Any]:
    a0, a1, b0, b1 = complete_month_windows(as_of, n)
    t = ledger.tx
    cur = summarise(t[(t["date"] >= a0) & (t["date"] <= a1)])
    prev = summarise(t[(t["date"] >= b0) & (t["date"] <= b1)])
    changes = {k: pct_change(cur[k], prev[k]) for k in cur if k not in ("gross_margin_pct",)}
    changes["gross_margin_pct"] = cur["gross_margin_pct"] - prev["gross_margin_pct"]
    return {"months": n, "current": cur, "previous": prev, "change_pct": changes,
            "current_period": [str(a0.date()), str(a1.date())], "previous_period": [str(b0.date()), str(b1.date())]}


def monthly_series(ledger: Ledger, months: int = 12) -> list[dict[str, Any]]:
    t = ledger.tx
    if t.empty:
        return []
    end = ledger.end
    start = (end - pd.DateOffset(months=months - 1)).replace(day=1)
    t = t[t["date"] >= start].copy()
    t["month"] = t["date"].dt.to_period("M")
    out = []
    closing = ledger.daily_cash.resample("ME").last()
    for m, df in t.groupby("month"):
        s = summarise(df)
        m_end = m.to_timestamp(how="end").normalize()
        partial = m_end > end
        out.append({
            "month": str(m),
            "partial": bool(partial),
            "days_covered": int((min(m_end, end) - m.to_timestamp()).days + 1),
            "revenue": round(s["revenue"], 2),
            "cost_of_goods": round(s["cost_of_goods"], 2),
            "operating_expenses": round(s["operating_expenses"], 2),
            "tax": round(s["tax"], 2),
            "expenses": round(s["expenses"], 2),
            "gross_margin_pct": round(s["gross_margin_pct"], 2),
            "net_cash_flow": round(s["net_cash_flow"], 2),
            "closing_cash": round(float(closing.get(m_end, ledger.cash_at(min(m_end, end)))), 2),
        })
    return out


def cash_series(ledger: Ledger, days: int = 180) -> list[dict[str, Any]]:
    s = ledger.daily_cash
    s = s[s.index > ledger.end - pd.Timedelta(days=days)]
    ma7 = ledger.daily_cash.rolling(7, min_periods=1).mean().reindex(s.index)
    ma30 = ledger.daily_cash.rolling(30, min_periods=1).mean().reindex(s.index)
    return [{"date": str(d.date()), "cash": round(float(v), 2), "ma7": round(float(ma7[d]), 2),
             "ma30": round(float(ma30[d]), 2)} for d, v in s.items()]


def category_breakdown_months(ledger: Ledger, as_of: pd.Timestamp, n: int = 3,
                              direction: str = "outflow") -> list[dict[str, Any]]:
    a0, a1, b0, b1 = complete_month_windows(as_of, n)
    t = ledger.tx
    t = t[t["direction"] == direction]
    cur = t[(t["date"] >= a0) & (t["date"] <= a1)].groupby("category")["amount"].sum()
    prev = t[(t["date"] >= b0) & (t["date"] <= b1)].groupby("category")["amount"].sum()
    total = float(cur.sum()) or 1.0
    return [{"category": c, "amount": round(float(v), 2), "share_pct": round(float(v) / total * 100, 2),
             "previous": round(float(prev.get(c, 0.0)), 2), "change_pct": pct_change(float(v), float(prev.get(c, 0.0))),
             "period": [str(a0.date()), str(a1.date())]}
            for c, v in cur.sort_values(ascending=False).items()]


def product_line_performance(ledger: Ledger, as_of: pd.Timestamp, days: int = 90) -> list[dict[str, Any]]:
    """Revenue by sales sub-category (product line) - retail POS lines only."""
    def lines(df: pd.DataFrame) -> pd.Series:
        s = df[(df["group"] == "revenue") & df["subcategory"].notna() & (df["subcategory"] != "Trade accounts")]
        return s.groupby("subcategory")["amount"].sum()

    cur = lines(ledger.window(as_of, days))
    prev = lines(ledger.window(as_of, days, offset=days))
    ly = lines(ledger.window(as_of, days, offset=365))
    total = float(cur.sum()) or 1.0
    out = []
    for ln, amt in cur.sort_values(ascending=False).items():
        out.append({
            "line": ln, "revenue": round(float(amt), 2), "share_pct": round(float(amt) / total * 100, 2),
            "previous": round(float(prev.get(ln, 0.0)), 2),
            "change_pct": pct_change(float(amt), float(prev.get(ln, 0.0))),
            "same_period_last_year": round(float(ly.get(ln, 0.0)), 2) if len(ly) else None,
            "yoy_change_pct": pct_change(float(amt), float(ly.get(ln, 0.0))) if len(ly) else None,
        })
    return out


def monthly_values(ledger: Ledger, mask_fn, months: int = 6) -> pd.Series:
    """Monthly totals (complete months only) of rows selected by mask_fn."""
    t = ledger.tx
    end = ledger.end
    last_full = (end + pd.Timedelta(days=1)).to_period("M") - 1 if (end + pd.Timedelta(days=1)).day != 1 \
        else end.to_period("M")
    periods = pd.period_range(last_full - (months - 1), last_full, freq="M")
    sel = t[mask_fn(t)]
    s = sel.groupby(sel["date"].dt.to_period("M"))["amount"].sum()
    return s.reindex(periods, fill_value=0.0)


def volatility_ratio(values: pd.Series) -> float:
    v = values.astype(float)
    return float(np.std(v, ddof=0) / np.mean(v)) if len(v) and np.mean(v) > 0 else 0.0
