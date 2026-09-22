"""Category health: recent change versus the business total, anomalies and short forecasts.

Deterministic rules with their inputs exposed as evidence, so every flag can be explained.
"""
import numpy as np
import pandas as pd

from app.forecast import sales as sf

RECENT_MONTHS = 3
MIN_RECENT_SALES = 10_000.0
UNDERPERFORM_GAP_PP = -10.0
ANOMALY_MIN_HISTORY = 6
ANOMALY_SIGMA = 2.0
FORECAST_HORIZON = 3


def analyse_categories(
    monthly: pd.DataFrame,
    recent_months: int = RECENT_MONTHS,
    min_recent_sales: float = MIN_RECENT_SALES,
) -> list[dict]:
    pivot = monthly.pivot(index="month", columns="category", values="sales").sort_index().fillna(0.0)
    months = list(pivot.index)
    total = pivot.sum(axis=1)
    total_windows = _windows(total.to_numpy(), recent_months)
    total_change_pct = _pct_change(total_windows["recent"], total_windows["previous"])
    by_category = {name: group.sort_values("month") for name, group in monthly.groupby("category")}

    results = []
    for category in pivot.columns:
        values = pivot[category].to_numpy(dtype=float)
        windows = _windows(values, recent_months)
        change_pct = _pct_change(windows["recent"], windows["previous"])
        share_recent = _share(windows["recent"], total_windows["recent"])
        share_previous = _share(windows["previous"], total_windows["previous"])
        underperforming = _underperforming_total(change_pct, total_change_pct, windows, min_recent_sales)
        anomaly = _latest_month_anomaly(values)
        forecast, reason = _forecast(values, months[-1])
        results.append({
            "category": category,
            "recent": windows["recent"],
            "previous": windows["previous"],
            "change_abs": windows["recent"] - windows["previous"],
            "change_pct": change_pct,
            "share_recent": share_recent,
            "share_previous": share_previous,
            "share_change_pp": _pp(share_recent, share_previous),
            "total_change_pct": total_change_pct,
            "flags": {"underperforming_total": underperforming["flag"], "latest_month_anomaly": anomaly["flag"]},
            "evidence": {"underperforming_total": underperforming["evidence"], "latest_month_anomaly": anomaly["evidence"]},
            "forecast": forecast,
            "forecast_reason": reason,
            "series": by_category[category][["month", "orders", "items", "sales"]].to_dict(orient="records"),
        })
    results.sort(key=lambda r: r["recent"], reverse=True)
    return results


def _windows(values: np.ndarray, recent_months: int) -> dict:
    recent = float(values[-recent_months:].sum()) if len(values) else 0.0
    previous_slice = values[-2 * recent_months:-recent_months] if len(values) > recent_months else values[:0]
    return {"recent": recent, "previous": float(previous_slice.sum()), "months": recent_months}


def _pct_change(recent: float, previous: float) -> float | None:
    return (recent - previous) / previous * 100 if previous > 0 else None


def _share(part: float, whole: float) -> float | None:
    return part / whole if whole > 0 else None


def _pp(share_now: float | None, share_before: float | None) -> float | None:
    return (share_now - share_before) * 100 if share_now is not None and share_before is not None else None


def _underperforming_total(change_pct, total_change_pct, windows, min_recent_sales) -> dict:
    support = windows["recent"] + windows["previous"]
    gap_pp = change_pct - total_change_pct if change_pct is not None and total_change_pct is not None else None
    flag = gap_pp is not None and gap_pp <= UNDERPERFORM_GAP_PP and support >= min_recent_sales
    return {
        "flag": bool(flag),
        "evidence": {
            "change_pct": change_pct, "total_change_pct": total_change_pct, "gap_pp": gap_pp,
            "threshold_pp": UNDERPERFORM_GAP_PP, "support_sales": support, "min_support_sales": min_recent_sales,
        },
    }


def _latest_month_anomaly(values: np.ndarray) -> dict:
    """Latest month compared with the mean of the previous three, scaled by the usual month-to-month noise."""
    earlier = values[:-1]
    if len(earlier) < ANOMALY_MIN_HISTORY:
        return {"flag": False, "evidence": {"reason": "insufficient_history", "months_available": int(len(earlier))}}
    latest = float(values[-1])
    expected = float(earlier[-3:].mean())
    noise_std = float(np.diff(earlier).std())
    threshold = ANOMALY_SIGMA * noise_std
    flag = noise_std > 0 and abs(latest - expected) > threshold
    return {
        "flag": bool(flag),
        "evidence": {"latest": latest, "expected": expected, "deviation": latest - expected,
                     "noise_std": noise_std, "threshold": threshold, "sigma": ANOMALY_SIGMA},
    }


def _forecast(values: np.ndarray, last_month: str) -> tuple[list[dict] | None, str | None]:
    if len(values) < sf.MIN_MONTHS:
        return None, "insufficient_history"
    history = values.tolist()
    model = sf.fit_model(history)
    labels = sf.forecast_months(last_month, FORECAST_HORIZON)
    points = sf.recursive_forecast(model, history, FORECAST_HORIZON)
    return [{"month": m, "sales": p} for m, p in zip(labels, points)], None
