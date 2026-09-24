import pandas as pd
import pytest

from app.analysis.categories import analyse_categories
from app.data.categories import build_category_monthly
from tests.conftest import FIXTURE_MONTHS


def test_category_monthly_from_fixture(datasets_dir):
    monthly = build_category_monthly(datasets_dir)
    assert list(monthly.columns) == ["month", "category", "orders", "items", "sales"]
    a = monthly[monthly["category"] == "category_a"].set_index("month")
    b = monthly[monthly["category"] == "category_b"].set_index("month")
    assert list(a.index) == FIXTURE_MONTHS and list(b.index) == FIXTURE_MONTHS
    assert (a["sales"] == 100.0).all() and (b["sales"] == 250.0).all()
    assert (a["items"] == 1).all() and (b["items"] == 2).all()
    assert (a["orders"] == 1).all() and (b["orders"] == 2).all()
    # Category totals equal the whole-business series: no item is counted twice.
    assert monthly.groupby("month")["sales"].sum().eq(350.0).all()
    assert "cancelled-1" not in monthly and monthly["sales"].sum() == 350.0 * 12


def _monthly(series: dict[str, list[float]], start="2017-01") -> pd.DataFrame:
    months = pd.period_range(start, periods=len(next(iter(series.values()))), freq="M").strftime("%Y-%m")
    rows = [
        {"month": m, "category": cat, "orders": 1, "items": 1, "sales": v}
        for cat, values in series.items()
        for m, v in zip(months, values)
    ]
    return pd.DataFrame(rows)


def test_missing_month_is_zero_filled_for_every_category(tmp_path):
    from tests.conftest import write_fixture_csvs

    write_fixture_csvs(tmp_path, drop_month="2017-06")
    monthly = build_category_monthly(tmp_path)
    june = monthly[monthly["month"] == "2017-06"].set_index("category")
    assert sorted(june.index) == ["category_a", "category_b"]
    assert (june["sales"] == 0.0).all() and (june["orders"] == 0).all() and (june["items"] == 0).all()
    assert len(monthly) == 2 * 12


def test_change_and_share_metrics():
    monthly = _monthly({"up": [100] * 9 + [200] * 3, "flat": [100] * 12})
    result = {r["category"]: r for r in analyse_categories(monthly, min_recent_sales=0)}
    up, flat = result["up"], result["flat"]
    assert up["recent"] == 600 and up["previous"] == 300 and up["change_pct"] == 100.0
    assert flat["change_pct"] == 0.0
    assert up["total_change_pct"] == pytest.approx((900 - 600) / 600 * 100)
    assert up["share_recent"] == pytest.approx(600 / 900) and up["share_previous"] == pytest.approx(0.5)
    assert flat["share_change_pp"] == pytest.approx((300 / 900 - 0.5) * 100)


def test_change_pct_is_none_when_previous_is_zero():
    monthly = _monthly({"new": [0] * 9 + [50] * 3, "old": [100] * 12})
    result = {r["category"]: r for r in analyse_categories(monthly, min_recent_sales=0)}
    assert result["new"]["change_pct"] is None
    assert result["new"]["flags"]["underperforming_total"] is False


def test_underperforming_total_requires_gap_and_support():
    monthly = _monthly({"falling": [100] * 9 + [50] * 3, "rising": [100] * 9 + [300] * 3})
    with_support = {r["category"]: r for r in analyse_categories(monthly, min_recent_sales=0)}
    assert with_support["falling"]["flags"]["underperforming_total"] is True
    assert with_support["rising"]["flags"]["underperforming_total"] is False
    evidence = with_support["falling"]["evidence"]["underperforming_total"]
    assert evidence["change_pct"] == -50.0 and evidence["threshold_pp"] == -10.0
    without_support = {r["category"]: r for r in analyse_categories(monthly, min_recent_sales=10_000)}
    assert without_support["falling"]["flags"]["underperforming_total"] is False


def test_latest_month_anomaly_needs_history_and_fires_on_spike():
    steady = [100, 102, 98, 101, 99, 100, 102, 98, 100, 101, 99, 100]
    spiked = steady[:-1] + [400]
    result = {r["category"]: r for r in analyse_categories(_monthly({"s": steady, "x": spiked}), min_recent_sales=0)}
    assert result["s"]["flags"]["latest_month_anomaly"] is False
    assert result["x"]["flags"]["latest_month_anomaly"] is True
    assert result["x"]["evidence"]["latest_month_anomaly"]["latest"] == 400
    short = {r["category"]: r for r in analyse_categories(_monthly({"y": [100, 100, 100, 900]}), min_recent_sales=0)}
    assert short["y"]["flags"]["latest_month_anomaly"] is False


def test_forecast_present_only_with_enough_history():
    long = analyse_categories(_monthly({"c": [100.0 + i for i in range(12)]}), min_recent_sales=0)[0]
    assert len(long["forecast"]) == 3 and long["forecast"][0]["month"] == "2018-01"
    assert long["forecast_reason"] is None
    short = analyse_categories(_monthly({"c": [100.0] * 8}), min_recent_sales=0)[0]
    assert short["forecast"] is None and short["forecast_reason"] == "insufficient_history"


def test_sorted_by_recent_sales_and_series_included():
    monthly = _monthly({"small": [10] * 12, "big": [1000] * 12})
    result = analyse_categories(monthly, min_recent_sales=0)
    assert [r["category"] for r in result] == ["big", "small"]
    assert len(result[0]["series"]) == 12 and set(result[0]["series"][0]) == {"month", "orders", "items", "sales"}
