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
                "flags": {"underperforming_total": flagged}}
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
        "categories_falling_behind", "late_rate_rising", "low_reviews_rising", "late_orders_get_low_reviews"]
    assert body["triggered"] == sum(c["triggered"] for c in body["checks"])
    # the fixture's late orders all get 1 star and on-time ones 4 or 5
    assert body["checks"][3]["triggered"] is True
