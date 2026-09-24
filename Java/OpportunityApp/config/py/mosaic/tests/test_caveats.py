import pytest
from fastapi.testclient import TestClient

from app.analysis import caveats
from app.main import create_app


def _months(pairs):
    return [{"month": f"2018-0{i + 1}", "late": late, "delivered": total} for i, (late, total) in enumerate(pairs)]


def test_window_rate_pools_counts_instead_of_averaging_rates():
    # previous: 1/10 and 0/90 -> 1%; a mean of rates would say 5%
    window = caveats.window_rate(_months([(1, 10), (0, 90), (5, 50), (5, 50)]), "late", "delivered", months=2)
    assert window["previous"]["rate"] == pytest.approx(0.01)
    assert window["recent"]["rate"] == pytest.approx(0.10)
    assert window["change_pp"] == pytest.approx(9.0)
    assert window["recent_months"] == ["2018-03", "2018-04"]


def test_window_rate_with_no_orders_has_no_rate_and_no_change():
    window = caveats.window_rate(_months([(0, 0), (0, 0), (1, 10), (1, 10)]), "late", "delivered", months=2)
    assert window["previous"]["rate"] is None and window["change_pp"] is None
    assert caveats.rate_rising("x", "t", window)["triggered"] is False


def test_rate_rising_triggers_from_the_threshold():
    rising = caveats.window_rate(_months([(1, 100), (1, 100), (2, 100), (2, 100)]), "late", "delivered", months=2)
    assert caveats.rate_rising("x", "t", rising)["triggered"] is True
    flat = caveats.window_rate(_months([(1, 100), (1, 100), (1, 100), (2, 100)]), "late", "delivered", months=2)
    assert caveats.rate_rising("x", "t", flat)["triggered"] is False


def test_falling_behind_lists_the_worst_flagged_categories():
    def category(name, change_abs, flagged):
        return {"category": name, "change_pct": -10.0, "change_abs": change_abs, "total_change_pct": 5.0,
                "flags": {"underperforming_total": flagged},
                "series": [{"month": "2018-01", "orders": 1, "items": 1, "sales": 10.0}]}
    result = caveats.falling_behind([category("a", -100.0, True), category("b", -500.0, True), category("c", -900.0, False)])
    assert result["triggered"] is True
    assert result["evidence"]["flagged"] == 2 and result["evidence"]["sales_lost_by_flagged"] == -600.0
    assert [w["category"] for w in result["evidence"]["worst"]] == ["b", "a"]
    assert caveats.falling_behind([])["triggered"] is False


def test_late_orders_hurt_reviews_needs_both_rates():
    def side(rate):
        return {"reviewed": 10, "low": 1, "low_rate": rate}
    assert caveats.late_orders_hurt_reviews({"late": side(0.6), "on_time": side(0.1)})["triggered"] is True
    assert caveats.late_orders_hurt_reviews({"late": side(0.15), "on_time": side(0.1)})["triggered"] is False
    assert caveats.late_orders_hurt_reviews({"late": side(None), "on_time": side(0.0)})["triggered"] is False
    zero = caveats.late_orders_hurt_reviews({"late": side(0.5), "on_time": side(0.0)})
    assert zero["triggered"] is True and zero["evidence"]["ratio"] is None


def test_endpoint_reports_every_check_on_the_fixture(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        body = client.get("/api/sales/caveats").json()
    assert [c["id"] for c in body["checks"]] == [
        "categories_falling_behind", "late_rate_rising", "low_reviews_rising", "late_orders_get_low_reviews",
        "cancellations_rising", "basket_shrinking", "freight_share_rising", "instalments_rising",
        "few_returning_customers", "sales_rest_on_few_sellers", "sales_rest_on_one_state"]
    assert body["triggered"] == sum(c["triggered"] for c in body["checks"])
    checks = {c["id"]: c for c in body["checks"]}
    # the fixture's late orders all get 1 star and on-time ones 4 or 5
    assert checks["late_orders_get_low_reviews"]["triggered"] is True
    # every month has the same two orders: 175 BRL per order, 30 of 350 in freight, half paid in instalments
    assert checks["basket_shrinking"]["evidence"]["recent"]["value"] == pytest.approx(175.0)
    assert checks["basket_shrinking"]["triggered"] is False
    assert checks["freight_share_rising"]["evidence"]["change_pp"] == pytest.approx(0.0)
    assert checks["instalments_rising"]["evidence"]["recent"]["rate"] == pytest.approx(0.5)
    # the only cancellations are in March, far from the last 3 months: no rise, and never a division by zero
    assert checks["cancellations_rising"]["evidence"]["change_pp"] == pytest.approx(0.0)
    # order b comes from the same person every month, so half of the recent orders are from a returning customer
    assert checks["few_returning_customers"]["evidence"]["rate"] == pytest.approx(0.5)
    assert checks["few_returning_customers"]["triggered"] is False
    # two sellers make all the sales, and RJ buys 200 of every 350 BRL
    assert checks["sales_rest_on_few_sellers"]["evidence"]["share"] == pytest.approx(1.0)
    assert checks["sales_rest_on_one_state"]["evidence"]["state"] == "RJ"
    assert checks["sales_rest_on_one_state"]["evidence"]["share"] == pytest.approx(200 / 350)
    assert checks["sales_rest_on_one_state"]["triggered"] is True


def test_window_ratio_pools_sums_and_handles_an_empty_window():
    months = [{"month": f"2018-0{i}", "sales": sales, "orders": orders} for i, (sales, orders) in
              enumerate([(100.0, 1), (300.0, 3), (150.0, 1), (0.0, 0)], start=1)]
    window = caveats.window_ratio(months, "sales", "orders", months=2)
    assert window["previous"]["value"] == pytest.approx(100.0)  # 400 / 4, not the mean of 100 and 100
    assert window["recent"]["value"] == pytest.approx(150.0)  # the empty month adds nothing, it is not a zero order value
    assert window["change_pct"] == pytest.approx(50.0)
    assert caveats.window_ratio(months[-1:] * 2, "sales", "orders", months=1)["change"] is None


def test_few_returning_customers_triggers_below_the_threshold_only():
    def month(returning, customers):
        return {"month": "2018-01", "returning": returning, "customers": customers}
    assert caveats.few_returning_customers([month(9, 100)] * 3)["triggered"] is True
    assert caveats.few_returning_customers([month(10, 100)] * 3)["triggered"] is False
    assert caveats.few_returning_customers([month(0, 0)] * 3)["evidence"]["rate"] is None


def test_business_profile_windows_on_the_fixture(datasets_dir, tmp_path):
    from app.analysis import business_profile
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        frame = client.app.state.orders.frame
    windows = business_profile.windows(frame, ["2017-02"], ["2017-01"])
    recent = windows["business"]["recent"]
    assert recent["orders"] == 2 and recent["sales"] == pytest.approx(350.0)
    assert recent["average_order_value"] == pytest.approx(175.0)
    assert recent["multi_instalment"] == {"count": 1, "total": 2, "rate": 0.5}
    assert recent["returning_customer"]["count"] == 1  # order b's person bought in January too
    assert recent["top_state"] == {"state": "RJ", "share": pytest.approx(200 / 350)}
    assert set(windows["categories"]) == {"category_a", "category_b"}
    empty = business_profile.profile(frame.iloc[0:0].assign(month=[]))
    assert empty["average_order_value"] is None and empty["cancel"]["rate"] is None and empty["top_state"] is None


def test_sales_mix_splits_sales_and_counts_what_it_cannot_place(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        states = client.get("/api/sales/mix?by=customer_state&months=3").json()
        payments = client.get("/api/sales/mix?by=payment_type&months=12").json()
    # every fixture month: RJ buys 200 and SP buys 150 of 350
    assert [(r["group"], r["sales"]) for r in states["rows"]] == [("RJ", 600.0), ("SP", 450.0)]
    assert states["rows"][0]["share"] == pytest.approx(200 / 350)
    assert sum(r["share"] for r in states["rows"]) == pytest.approx(1.0)
    # order b pays mostly by card (150 of 210), so card is its type; order a is card too
    assert [r["group"] for r in payments["rows"]] == ["credit_card"]


def test_sales_mix_folds_small_groups_into_other():
    import pandas as pd
    from app.analysis import business_profile
    frame = pd.DataFrame({"cancelled": [0.0] * 4, "order_id": list("abcd"), "total_price": [40.0, 30.0, 20.0, 10.0],
                          "category": ["w", "x", "y", "z"]})
    result = business_profile.mix(frame, "category", top=2)
    assert [(r["group"], r["sales"]) for r in result["rows"]] == [("w", 40.0), ("x", 30.0), ("other", 30.0)]
    assert result["rows"][-1]["groups"] == 2 and result["groups"] == 4


def test_sales_metrics_by_month_on_the_fixture(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        body = client.get("/api/sales/metrics").json()
    assert set(body["metrics"]) == {"average_order_value", "freight_share", "cancel_rate", "multi_instalment_rate", "returning_rate"}
    june = next(m for m in body["monthly"] if m["month"] == "2017-06")
    assert june["average_order_value"] == pytest.approx(175.0) and june["multi_instalment_rate"] == pytest.approx(0.5)
    march = next(m for m in body["monthly"] if m["month"] == "2017-03")
    # March holds the cancelled and unavailable orders among the orders placed
    assert march["cancelled"] == 2 and march["cancel_rate"] == pytest.approx(march["cancelled"] / march["placed"])
