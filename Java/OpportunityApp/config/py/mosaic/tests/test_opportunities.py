import pytest
from fastapi.testclient import TestClient

from app.analysis import opportunities
from app.main import create_app


def _category(name, recent, previous, total_change_pct=10.0):
    change = (recent - previous) / previous * 100 if previous else None
    return {"category": name, "recent": recent, "previous": previous, "change_abs": recent - previous,
            "change_pct": change, "total_change_pct": total_change_pct, "share_recent": None,
            "series": [{"month": "2018-01", "orders": 3, "items": 3, "sales": previous}, {"month": "2018-02", "orders": 4, "items": 4, "sales": recent}]}


def _rates(by_category, business=0.10):
    rate = {"business": {"orders": 1000, "rate": business}, "by_group": by_category}
    return {"late_rate": rate, "low_review_rate": rate}


def test_sales_trend_compares_forecast_with_recent_months():
    trend = opportunities.sales_trend([100.0, 200.0, 200.0, 200.0], [220.0, 240.0], recent_months=3)
    assert trend["recent_monthly_mean"] == 200.0 and trend["forecast_monthly_mean"] == 230.0
    assert trend["change_pct"] == pytest.approx(15.0) and trend["increasing"] is True
    assert opportunities.sales_trend([0.0, 0.0], [10.0], 3)["change_pct"] is None
    assert opportunities.sales_trend([], [10.0], 3)["increasing"] is False


def test_candidates_keep_only_categories_growing_with_the_business():
    categories = [
        _category("fast", 30_000.0, 20_000.0),     # +50%
        _category("slow", 21_000.0, 20_000.0),     # +5%, behind the business +10%
        _category("falling", 10_000.0, 20_000.0),
        _category("tiny", 3_000.0, 1_000.0),       # below minimum support
        _category("new", 5_000.0, 0.0),            # no baseline: no percentage change
    ]
    rates = _rates({"fast": {"orders": 100, "rate": 0.10}})
    result = opportunities.investment_candidates(categories, rates, limit=10)
    assert [(c["category"], c["basis"]) for c in result] == [("fast", "growing")]


def test_unreliable_or_unmeasured_categories_rank_after_ready_ones():
    categories = [_category("big_but_late", 90_000.0, 30_000.0), _category("small_ready", 30_000.0, 20_000.0),
                  _category("unmeasured", 60_000.0, 30_000.0)]
    rates = _rates({"big_but_late": {"orders": 100, "rate": 0.20}, "small_ready": {"orders": 100, "rate": 0.11},
                    "unmeasured": {"orders": 5, "rate": 0.0}})
    result = opportunities.investment_candidates(categories, rates, limit=10)
    assert [(c["category"], c["readiness"]) for c in result] == [
        ("small_ready", "ready"), ("unmeasured", "unknown"), ("big_but_late", "fix_first")]
    late = result[2]["checks"]["late_rate"]
    assert late["gap_pp"] == pytest.approx(10.0) and late["within_business"] is False
    assert result[1]["checks"]["late_rate"]["rate"] is None


def test_category_rates_use_only_the_given_months(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        frame = client.app.state.orders.frame
    rates = opportunities.category_rates(frame, ["2017-02"], data_range=("2017-01", "2017-12"))
    late = rates["late_rate"]
    assert late["business"] == {"orders": 2, "rate": 0.5}
    assert sum(c["orders"] for c in late["by_group"].values()) == 2
    cancel = opportunities.category_rates(frame, ["2017-03"], data_range=("2017-01", "2017-12"))["cancel_rate"]
    # March: the two regular orders, one cancelled and one unavailable order with items (no-items-1 has no category)
    assert cancel["business"]["orders"] == 5
    assert cancel["by_group"]["category_a"] == {"orders": 3, "rate": pytest.approx(2 / 3)}


def test_endpoint_needs_the_sales_model(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        assert client.get("/api/sales/opportunities").status_code == 503


def test_endpoint_always_answers_whatever_the_forecast(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models", auto_train=True)) as client:
        body = client.get("/api/sales/opportunities").json()
    # the forecast is context now, never a reason to stay silent; the fixture's categories are too small to suggest
    assert "trend" in body and body["reason"] == "no_categories_with_enough_sales" and body["candidates"] == []


def test_when_nothing_grows_the_categories_beating_the_business_are_suggested():
    categories = [_category("holding", 19_000.0, 20_000.0, total_change_pct=-12.0),   # -5%, better than -12%
                  _category("sinking", 15_000.0, 20_000.0, total_change_pct=-12.0)]   # -25%
    result = opportunities.investment_candidates(categories, _rates({}), 10)
    assert [(c["category"], c["basis"]) for c in result] == [("holding", "beats_business")]


def test_when_everything_falls_behind_the_smallest_falls_are_still_suggested():
    categories = [_category("bad", 15_000.0, 20_000.0, total_change_pct=-5.0), _category("worse", 10_000.0, 20_000.0, total_change_pct=-5.0),
                  _category("tiny", 100.0, 200.0, total_change_pct=-5.0)]  # below the minimum support, never suggested
    result = opportunities.investment_candidates(categories, _rates({}), 10)
    assert [(c["category"], c["basis"]) for c in result] == [("bad", "best_available"), ("worse", "best_available")]

@pytest.mark.parametrize("change, total, expected", [
    (40.0, 10.0, "strong"), (30.0, 10.0, "strong"), (20.0, 10.0, "moderate"), (14.9, 10.0, "weak"),
    (None, 10.0, "unknown"), (5.0, None, "unknown"),
])
def test_growth_level_is_judged_against_the_business(change, total, expected):
    assert opportunities.growth_level(change, total) == expected


def test_size_and_rate_levels_use_their_thresholds():
    assert [opportunities.size_level(s) for s in (0.05, 0.02, 0.009, None)] == ["large", "medium", "small", "unknown"]
    assert [opportunities.rate_level(g) for g in (2.1, 2.0, -2.0, -2.1, None)] == ["worse", "in_line", "in_line", "better", "unknown"]


def test_candidates_carry_their_levels():
    category = {**_category("fast", 30_000.0, 20_000.0), "share_recent": 0.2}
    rates = _rates({"fast": {"orders": 100, "rate": 0.05}})
    [c] = opportunities.investment_candidates([category], rates, limit=1)
    assert (c["growth_level"], c["size_level"], c["checks"]["late_rate"]["level"]) == ("strong", "large", "better")


def _profile(top_seller_share=0.2, freight_share=0.15, average_order_value=100.0, sellers=10):
    return {"top_seller_share": top_seller_share, "freight_share": freight_share,
            "average_order_value": average_order_value, "sellers": sellers}


def test_profile_risks_trigger_at_their_thresholds():
    business = _profile(freight_share=0.15)
    risks = {r["id"]: r for r in opportunities.profile_risks(
        _profile(top_seller_share=0.5, freight_share=0.20, average_order_value=95.0), _profile(average_order_value=100.0), business)}
    assert risks["depends_on_one_seller"]["triggered"] is True
    assert risks["freight_heavy"]["gap_pp"] == pytest.approx(5.0) and risks["freight_heavy"]["triggered"] is True
    assert risks["basket_shrinking"]["change_pct"] == pytest.approx(-5.0) and risks["basket_shrinking"]["triggered"] is True
    calm = opportunities.profile_risks(_profile(top_seller_share=0.49, freight_share=0.19, average_order_value=96.0),
                                       _profile(), business)
    assert not any(r["triggered"] for r in calm)


def test_profile_risks_without_a_previous_basket_do_not_guess():
    risks = {r["id"]: r for r in opportunities.profile_risks(_profile(), _profile(average_order_value=None), _profile())}
    assert risks["basket_shrinking"]["change_pct"] is None and risks["basket_shrinking"]["triggered"] is False


def test_a_profile_risk_turns_a_ready_category_into_watch():
    categories = [_category("steady", 30_000.0, 20_000.0), _category("one_seller", 40_000.0, 20_000.0)]
    rates = _rates({"steady": {"orders": 100, "rate": 0.10}, "one_seller": {"orders": 100, "rate": 0.10}})
    profiles = {"steady": {"recent": _profile(), "previous": _profile()},
                "one_seller": {"recent": _profile(top_seller_share=0.8, sellers=2), "previous": _profile()}}
    result = opportunities.investment_candidates(categories, rates, 10, profiles, _profile())
    assert [(c["category"], c["readiness"]) for c in result] == [("steady", "ready"), ("one_seller", "watch")]
    assert result[1]["profile"]["recent"]["sellers"] == 2
