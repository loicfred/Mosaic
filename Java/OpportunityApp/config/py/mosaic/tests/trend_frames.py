"""Hand-built order frames for the trend measures: two 3-month windows with chosen outcomes per group."""
import pandas as pd

PREVIOUS = ["2018-03", "2018-04", "2018-05"]
RECENT = ["2018-06", "2018-07", "2018-08"]


def orders(groups: dict[str, dict], group: str) -> pd.DataFrame:
    """groups: name -> {"previous": (orders, positives), "recent": (orders, positives)}, spread over the window's months.

    A positive order is late with a 1-star review; the others are on time with 5 stars. Each order has its own seller
    unless `sellers` in the group's spec says how many share the window's orders.
    """
    rows = []
    for name, spec in groups.items():
        for window, months in (("previous", PREVIOUS), ("recent", RECENT)):
            count, positives = spec[window]
            sellers = spec.get("sellers", {}).get(window, count)
            for i in range(count):
                bad = i < positives
                rows.append({
                    "order_id": f"{name}-{window}-{i}", "order_status": "delivered",
                    "purchase_ts": pd.Timestamp(f"{months[i % 3]}-10"),
                    "late": 1.0 if bad else 0.0, "review_score": 1.0 if bad else 5.0, "low_review": 1.0 if bad else 0.0,
                    "total_price": 100.0, "total_freight": 10.0, "promised_days": 20.0, "delivery_days": 10.0,
                    "seller_id": f"{name}-{window}-seller-{(i // 3) % sellers}", "customer_state": None, "category": None,
                    group: name,
                })
    return pd.DataFrame(rows)
