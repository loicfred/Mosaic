"""The whole business, or one category, over some purchase months, measured with every Olist table.

One row per order (``app.state.orders.frame``): items, payments and reviews were already reduced to the order
before joining, so nothing is counted twice. A category is the category of the order's priciest item, as for the
delivery and review rates. Every rate carries its count and total, and a missing denominator gives ``None``,
never 0. Sales are gross item prices of orders not cancelled: not profit, and not the seller's cash.
"""
import pandas as pd

from app.analysis.populations import purchase_month
from app.config import DATA_RANGE

TOP_SELLERS = 10


def placed_orders(frame: pd.DataFrame, months: list[str] | None = None, data_range: tuple[str, str] = DATA_RANGE,
                  with_items: bool = True) -> pd.DataFrame:
    """Orders purchased in the given months (default: the analysed range), with a ``month`` column.

    Only orders with items by default, since sales, freight and categories come from items; ``with_items=False``
    keeps every order, for the cancellation rate, because many cancelled orders never had items recorded.
    """
    month = purchase_month(frame)
    start, end = data_range
    eligible = month.between(start, end)
    if with_items:
        eligible &= frame["n_items"].notna()
    if months is not None:
        eligible &= month.isin(months)
    return frame.loc[eligible].assign(month=month.loc[eligible])


def ratio(flags: pd.Series) -> dict:
    """Share of known 0/1 values that are 1; unknown values are left out of the total."""
    known = flags.dropna()
    total = int(len(known))
    count = int(known.sum())
    return {"count": count, "total": total, "rate": count / total if total else None}


def profile(placed: pd.DataFrame) -> dict:
    """Every measure the data supports for these orders, each with the figures it was computed from."""
    sold = placed[placed["cancelled"] == 0]
    sales = float(sold["total_price"].sum())
    orders = int(len(sold))
    paid = sold[sold["installments"].notna()]
    delivered = sold[sold["delivery_days"].notna()]
    by_seller = sold.groupby("seller_id")["total_price"].sum().sort_values(ascending=False)
    by_state = sold.groupby("customer_state")["total_price"].sum().sort_values(ascending=False)
    return {
        "orders": orders,
        "sales": sales,
        "average_order_value": sales / orders if orders else None,
        "freight_share": float(sold["total_freight"].sum()) / sales if sales > 0 else None,
        "cancel": ratio(placed["cancelled"]),
        "late": ratio(sold["late"]),
        "low_review": ratio(sold["low_review"]),
        "average_review_score": _mean(sold["review_score"]),
        "average_delivery_days": _mean(delivered["delivery_days"]),
        "multi_instalment": ratio((paid["installments"] > 1).astype(float)),
        "average_installments": _mean(paid["installments"]),
        "card_payment": ratio((paid["payment_type"] == "credit_card").astype(float)),
        "returning_customer": ratio(sold["returning_customer"]),
        "sellers": int(sold["seller_id"].nunique()),
        "top_seller_share": float(by_seller.iloc[0]) / sales if sales > 0 and len(by_seller) else None,
        "top_sellers_share": float(by_seller.head(TOP_SELLERS).sum()) / sales if sales > 0 else None,
        "customer_states": int(sold["customer_state"].nunique()),
        "top_state": {"state": by_state.index[0], "share": float(by_state.iloc[0]) / sales} if sales > 0 and len(by_state) else None,
    }


def windows(frame: pd.DataFrame, recent: list[str], previous: list[str]) -> dict:
    """The business and every category, each profiled over the recent months and the months before."""
    now, before = placed_orders(frame, recent), placed_orders(frame, previous)
    earlier = dict(tuple(before.groupby("category")))
    return {
        "business": {"recent": profile(now), "previous": profile(before)},
        "categories": {
            name: {"recent": profile(group), "previous": profile(earlier.get(name, before.iloc[0:0]))}
            for name, group in now.groupby("category")
        },
    }


MIX_TOP = 8


def mix(placed: pd.DataFrame, by: str, top: int = MIX_TOP) -> dict:
    """How sales split by one column: the largest groups, then everything else as one "other" row, with its counts.

    Orders not cancelled, grouped under the order's priciest item for category and seller state. Orders with no
    value in the column (no payment row, for example) are counted separately, never shared out.
    """
    sold = placed[placed["cancelled"] == 0]
    column = sold[by]
    known = sold[column.notna()]
    sales = float(known["total_price"].sum())
    grouped = known.groupby(by).agg(sales=("total_price", "sum"), orders=("order_id", "size")).sort_values("sales", ascending=False)
    rows = [{"group": str(name), "sales": float(r["sales"]), "orders": int(r["orders"]),
             "share": float(r["sales"]) / sales if sales > 0 else None} for name, r in grouped.head(top).iterrows()]
    rest = grouped.iloc[top:]
    if len(rest):
        rows.append({"group": "other", "sales": float(rest["sales"].sum()), "orders": int(rest["orders"].sum()),
                     "share": float(rest["sales"].sum()) / sales if sales > 0 else None, "groups": int(len(rest))})
    return {"by": by, "sales": sales, "orders": int(len(known)), "groups": int(len(grouped)),
            "without_value": int(column.isna().sum()), "rows": rows}


def monthly(frame: pd.DataFrame, data_range: tuple[str, str] = DATA_RANGE) -> list[dict]:
    """Per purchase month, the sums behind each business-level rate, so windows pool counts rather than averaging rates.

    Cancellations count every order placed; the other measures use orders with items that were not cancelled.
    """
    rows = []
    for month, group in placed_orders(frame, data_range=data_range, with_items=False).groupby("month", sort=True):
        sold = group[(group["cancelled"] == 0) & group["n_items"].notna()]
        paid = sold[sold["installments"].notna()]
        returning = sold["returning_customer"].dropna()
        sales = float(sold["total_price"].sum())
        rows.append({
            "month": month,
            "placed": int(len(group)),
            "cancelled": int(group["cancelled"].sum()),
            "orders": int(len(sold)),
            "sales": sales,
            "freight": float(sold["total_freight"].sum()),
            "paid": int(len(paid)),
            "multi_instalment": int((paid["installments"] > 1).sum()),
            "customers": int(len(returning)),
            "returning": int(returning.sum()),
            "average_order_value": sales / len(sold) if len(sold) else None,
            "freight_share": float(sold["total_freight"].sum()) / sales if sales > 0 else None,
            "cancel_rate": int(group["cancelled"].sum()) / len(group) if len(group) else None,
            "multi_instalment_rate": int((paid["installments"] > 1).sum()) / len(paid) if len(paid) else None,
            "returning_rate": int(returning.sum()) / len(returning) if len(returning) else None,
        })
    return rows


def _mean(values: pd.Series) -> float | None:
    known = values.dropna()
    return float(known.mean()) if len(known) else None
