"""What else changes if sales move?

Every figure is derived from observed history and carries the inputs it came from. The
relationship between volume and lateness is a fitted association over few months, never a
cause, and both a "rate holds" and a "rate rises with volume" variant are always returned.
"""
import numpy as np
import pandas as pd

from app.analysis.populations import labelled_orders_in_range
from app.config import DATA_RANGE

RECENT_MONTHS = 3
MIN_FIT_MONTHS = 6
TOP_STRAINED_SELLERS = 10

ASSUMPTIONS = [
    "Basket size stays the same: extra sales are converted to orders at the recent average order value.",
    "Seller mix stays the same: extra orders are shared out in proportion to each seller's recent volume.",
    "The link between monthly volume and late deliveries is an association fitted on few months, not a cause.",
    "Seller capacity is proxied by that seller's busiest month observed in the data.",
    "Sales are gross item sales, not profit and not cash received.",
]
LIMITATIONS = [
    "The scenario projects observed rates forward; it does not model carriers, stock or staffing.",
    "Recent months may under-count late deliveries for orders that had not yet arrived.",
    "A change of this size has not necessarily happened in the data, so the rates may not hold.",
]


def fit_volume_late_rate(monthly_orders, monthly_late_rate) -> dict | None:
    """Least-squares line of late rate on monthly order count."""
    x = np.asarray(monthly_orders, dtype=float)
    y = np.asarray(monthly_late_rate, dtype=float)
    if len(x) < MIN_FIT_MONTHS or np.std(x) == 0 or np.std(y) == 0:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    correlation = float(np.corrcoef(x, y)[0, 1])
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "slope_pp_per_1000_orders": float(slope * 1000 * 100),
        "r_squared": correlation**2,
        "n_months": int(len(x)),
    }


def seller_capacity_strain(
    orders_frame: pd.DataFrame, growth_factor: float, recent_months: int = RECENT_MONTHS,
    top: int = TOP_STRAINED_SELLERS, data_range: tuple[str, str] = DATA_RANGE,
) -> dict:
    """Sellers whose projected monthly orders would exceed their own busiest observed month."""
    per_seller_month = _seller_month_counts(orders_frame, data_range)
    if per_seller_month.empty:
        return {"count": 0, "active_sellers": 0, "growth_factor": growth_factor, "top": []}

    months = sorted(per_seller_month["month"].unique())
    recent = set(months[-recent_months:])
    peak = per_seller_month.groupby("seller_id")["orders"].max()
    recent_mean = (
        per_seller_month[per_seller_month["month"].isin(recent)]
        .groupby("seller_id")["orders"]
        .sum()
        / recent_months
    )

    table = pd.DataFrame({"recent_monthly_orders": recent_mean, "historical_peak": peak.reindex(recent_mean.index)})
    table["projected_monthly_orders"] = table["recent_monthly_orders"] * growth_factor
    above_peak = table["projected_monthly_orders"] > table["historical_peak"]
    strained = table[above_peak].copy()
    strained["over_peak_pct"] = (
        (strained["projected_monthly_orders"] / strained["historical_peak"] - 1) * 100
    )
    strained = strained.sort_values("projected_monthly_orders", ascending=False).head(top)
    return {
        "count": int(above_peak.sum()),
        "active_sellers": int(len(table)),
        "growth_factor": growth_factor,
        "top": [
            {"seller_id": seller_id, **{k: float(v) for k, v in row.items()}}
            for seller_id, row in strained.iterrows()
        ],
    }


def compute_sales_impact(
    monthly, orders_frame: pd.DataFrame, horizon: int, sales_change_pct: float,
    recent_months: int = RECENT_MONTHS, data_range: tuple[str, str] = DATA_RANGE,
) -> dict:
    months = monthly.months
    recent = months.tail(recent_months)
    baseline_sales = float(recent["sales"].mean()) if len(recent) else 0.0
    baseline_orders = float(recent["orders"].mean()) if len(recent) else 0.0
    scenario = {"horizon": horizon, "sales_change_pct": sales_change_pct, "recent_months": recent_months}
    baseline_block = {
        "months": list(recent["month"]) if len(recent) else [],
        "monthly_sales": baseline_sales,
        "monthly_orders": baseline_orders,
    }
    if baseline_orders <= 0 or baseline_sales <= 0:
        return {
            "scenario": scenario, "baseline": baseline_block, "consequences": None,
            "reason": "no_baseline_activity", "evidence": {}, "assumptions": ASSUMPTIONS,
            "limitations": LIMITATIONS,
        }

    evidence = _observed_rates(orders_frame, recent, data_range)
    growth_factor = 1 + sales_change_pct / 100
    projected_sales = baseline_sales * growth_factor
    projected_orders = projected_sales / evidence["aov"]

    consequences = {
        "projected_monthly_sales": projected_sales,
        "projected_monthly_orders": projected_orders,
        "extra_orders_per_month": projected_orders - baseline_orders,
        "horizon_sales": projected_sales * horizon,
        "horizon_orders": projected_orders * horizon,
        "late": {
            "rate_held": _late_outcome(evidence["recent_late_rate"], projected_orders, horizon, evidence, "recent_3_month_rate"),
            "rate_fitted": _fitted_late_outcome(evidence["volume_late_fit"], projected_orders, horizon, evidence),
        },
        "sellers_at_capacity": seller_capacity_strain(orders_frame, growth_factor, recent_months, data_range=data_range),
    }
    return {
        "scenario": scenario, "baseline": baseline_block, "consequences": consequences,
        "reason": None, "evidence": evidence, "assumptions": ASSUMPTIONS, "limitations": LIMITATIONS,
    }


def _seller_month_counts(orders_frame: pd.DataFrame, data_range: tuple[str, str]) -> pd.DataFrame:
    if orders_frame.empty or "seller_id" not in orders_frame:
        return pd.DataFrame(columns=["seller_id", "month", "orders"])
    frame = orders_frame[orders_frame["seller_id"].notna()].copy()
    frame["month"] = frame["purchase_ts"].dt.strftime("%Y-%m")
    start, end = data_range
    frame = frame[frame["month"].between(start, end)]
    return frame.groupby(["seller_id", "month"], as_index=False).size().rename(columns={"size": "orders"})


def _observed_rates(orders_frame, recent, data_range) -> dict:
    labelled = _labelled_orders(orders_frame, data_range)
    recent_month_labels = set(recent["month"])
    recent_labelled = labelled[labelled["month"].isin(recent_month_labels)]
    reviewed = labelled[labelled["low_review"].notna()]

    by_month = labelled.groupby("month").agg(orders=("late", "size"), late_rate=("late", "mean"))
    return {
        "aov": float(recent["sales"].sum() / recent["orders"].sum()),
        "recent_late_rate": float(recent_labelled["late"].mean()) if len(recent_labelled) else 0.0,
        "recent_late_orders": int(recent_labelled["late"].sum()) if len(recent_labelled) else 0,
        "recent_delivered_orders": int(len(recent_labelled)),
        "p_low_given_late": _conditional_low_review(reviewed, late=1),
        "p_low_given_on_time": _conditional_low_review(reviewed, late=0),
        "volume_late_fit": fit_volume_late_rate(by_month["orders"], by_month["late_rate"]),
        "baseline_months": list(recent["month"]),
    }


def _labelled_orders(orders_frame: pd.DataFrame, data_range: tuple[str, str]) -> pd.DataFrame:
    if orders_frame.empty:
        return pd.DataFrame(columns=["month", "late", "low_review"])
    return labelled_orders_in_range(orders_frame, "late", data_range)


def _conditional_low_review(reviewed: pd.DataFrame, late: int) -> float:
    subset = reviewed[reviewed["late"] == late]
    return float(subset["low_review"].mean()) if len(subset) else 0.0


def _late_outcome(late_rate: float, projected_orders: float, horizon: int, evidence: dict, basis: str) -> dict:
    late_rate = float(np.clip(late_rate, 0.0, 1.0))
    expected_late = projected_orders * late_rate
    on_time = projected_orders - expected_late
    expected_low = (
        expected_late * evidence["p_low_given_late"] + on_time * evidence["p_low_given_on_time"]
    )
    return {
        "basis": basis,
        "late_rate": late_rate,
        "expected_late_per_month": expected_late,
        "expected_late_over_horizon": expected_late * horizon,
        "expected_low_reviews_per_month": expected_low,
        "expected_low_reviews_over_horizon": expected_low * horizon,
        "sales_exposed_per_month": expected_late * evidence["aov"],
        "sales_exposed_over_horizon": expected_late * evidence["aov"] * horizon,
    }


def _fitted_late_outcome(fit: dict | None, projected_orders: float, horizon: int, evidence: dict) -> dict | None:
    if fit is None:
        return None
    predicted = fit["intercept"] + fit["slope"] * projected_orders
    outcome = _late_outcome(predicted, projected_orders, horizon, evidence, "fitted_volume_relationship")
    outcome["fit"] = fit
    return outcome
