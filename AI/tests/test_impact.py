import pandas as pd
import pytest

from app.analysis import impact
from app.data.olist import build_monthly_sales, load_order_items, load_orders
from app.data.orders import build_order_features


@pytest.fixture(scope="module")
def fixture_state(tmp_path_factory):
    from tests.conftest import write_fixture_csvs

    directory = tmp_path_factory.mktemp("datasets")
    write_fixture_csvs(directory)
    monthly = build_monthly_sales(load_orders(directory), load_order_items(directory))
    return monthly, build_order_features(directory).frame


@pytest.fixture(scope="module")
def baseline(fixture_state):
    monthly, frame = fixture_state
    return impact.compute_sales_impact(monthly, frame, horizon=3, sales_change_pct=0.0)


def test_fit_volume_late_rate_reports_slope_and_fit():
    orders = [1000 * i for i in range(1, 7)]
    rates = [0.02 * i for i in range(1, 7)]
    fit = impact.fit_volume_late_rate(orders, rates)
    assert fit["slope_pp_per_1000_orders"] == pytest.approx(2.0)
    assert fit["r_squared"] == pytest.approx(1.0)
    assert fit["n_months"] == 6
    assert fit["intercept"] == pytest.approx(0.0, abs=1e-9)


def test_fit_is_none_with_too_few_points_or_no_variation():
    assert impact.fit_volume_late_rate([1000, 2000, 3000], [0.02, 0.04, 0.06]) is None
    assert impact.fit_volume_late_rate([1000] * 6, [0.02, 0.03, 0.04, 0.05, 0.06, 0.07]) is None


def test_baseline_uses_last_three_months(baseline, fixture_state):
    monthly, _ = fixture_state
    recent = monthly.months.tail(3)
    assert baseline["baseline"]["months"] == list(recent["month"])
    assert baseline["baseline"]["monthly_sales"] == pytest.approx(recent["sales"].mean())
    assert baseline["baseline"]["monthly_orders"] == pytest.approx(recent["orders"].mean())
    assert baseline["evidence"]["aov"] == pytest.approx(
        recent["sales"].sum() / recent["orders"].sum()
    )


def test_zero_change_keeps_orders_flat(baseline):
    c = baseline["consequences"]
    assert c["extra_orders_per_month"] == pytest.approx(0.0)
    assert c["projected_monthly_orders"] == pytest.approx(baseline["baseline"]["monthly_orders"])


def test_projected_orders_scale_with_sales_change(fixture_state):
    monthly, frame = fixture_state
    result = impact.compute_sales_impact(monthly, frame, horizon=3, sales_change_pct=20.0)
    base = result["baseline"]["monthly_orders"]
    assert result["consequences"]["projected_monthly_orders"] == pytest.approx(base * 1.2)
    assert result["consequences"]["extra_orders_per_month"] == pytest.approx(base * 0.2)
    assert result["consequences"]["horizon_orders"] == pytest.approx(base * 1.2 * 3)


def test_negative_change_reduces_orders(fixture_state):
    monthly, frame = fixture_state
    result = impact.compute_sales_impact(monthly, frame, horizon=2, sales_change_pct=-25.0)
    assert result["consequences"]["extra_orders_per_month"] < 0
    assert result["consequences"]["horizon_orders"] == pytest.approx(
        result["consequences"]["projected_monthly_orders"] * 2
    )


def test_late_variants_and_low_review_split(fixture_state):
    monthly, frame = fixture_state
    result = impact.compute_sales_impact(monthly, frame, horizon=1, sales_change_pct=0.0)
    c = result["consequences"]
    held = c["late"]["rate_held"]
    orders = c["projected_monthly_orders"]
    assert held["late_rate"] == pytest.approx(result["evidence"]["recent_late_rate"])
    assert held["expected_late_per_month"] == pytest.approx(orders * held["late_rate"])
    assert held["sales_exposed_per_month"] == pytest.approx(
        held["expected_late_per_month"] * result["evidence"]["aov"]
    )
    on_time = orders - held["expected_late_per_month"]
    expected_low = (
        held["expected_late_per_month"] * result["evidence"]["p_low_given_late"]
        + on_time * result["evidence"]["p_low_given_on_time"]
    )
    assert held["expected_low_reviews_per_month"] == pytest.approx(expected_low)


def test_fitted_late_rate_is_clipped_into_unit_interval(fixture_state):
    monthly, frame = fixture_state
    result = impact.compute_sales_impact(monthly, frame, horizon=1, sales_change_pct=100.0)
    fitted = result["consequences"]["late"]["rate_fitted"]
    if fitted is not None:
        assert 0.0 <= fitted["late_rate"] <= 1.0


def test_seller_strain_counts_only_sellers_above_their_own_peak(fixture_state):
    monthly, frame = fixture_state
    flat = impact.compute_sales_impact(monthly, frame, horizon=1, sales_change_pct=0.0)
    assert flat["consequences"]["sellers_at_capacity"]["count"] == 0
    surge = impact.compute_sales_impact(monthly, frame, horizon=1, sales_change_pct=100.0)
    strain = surge["consequences"]["sellers_at_capacity"]
    assert strain["count"] >= 1
    assert strain["active_sellers"] == 2
    top = strain["top"][0]
    assert top["projected_monthly_orders"] > top["historical_peak"]
    assert top["over_peak_pct"] > 0


def test_no_baseline_activity_returns_reason_not_error():
    empty_months = pd.DataFrame(
        [{"month": "2017-01", "orders": 0, "sales": 0.0, "freight": 0.0}]
    )
    monthly = type("M", (), {"months": empty_months, "exclusions": {}})()
    result = impact.compute_sales_impact(monthly, pd.DataFrame(), horizon=3, sales_change_pct=20.0)
    assert result["consequences"] is None
    assert result["reason"] == "no_baseline_activity"


def test_assumptions_and_limitations_are_returned(baseline):
    assert any("basket" in a.lower() for a in baseline["assumptions"])
    assert any("association" in a.lower() or "cause" in a.lower() for a in baseline["assumptions"])
    assert baseline["scenario"]["horizon"] == 3
