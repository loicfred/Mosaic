import pandas as pd
import pytest

from app.analysis import trends


def _orders(rows):
    """rows: (month, group, value) triples, one per order."""
    return pd.DataFrame(rows, columns=["month", "group", "value"])


def test_windows_split_the_last_months_from_the_ones_before():
    recent, previous = trends.windows(["2018-03", "2018-01", "2018-02", "2018-04", "2018-02"], n=2)
    assert (recent, previous) == (["2018-03", "2018-04"], ["2018-01", "2018-02"])
    assert trends.windows(["2018-01"], n=3) == (["2018-01"], [])


def test_pooled_mean_counts_orders_not_months():
    # 1 late of 10 in one month and 5 of 10... pooled over 12 orders: month means would give 55%, pooled 6/12
    orders = _orders([("m1", "a", 1.0)] + [("m1", "a", 0.0)] * 9 + [("m2", "a", 1.0)] * 1 + [("m2", "a", 0.0)] * 1)
    assert trends.pooled_mean(orders, "value", ["m1", "m2"]) == {"value": pytest.approx(2 / 12), "orders": 12}


def test_empty_window_is_unknown_not_zero():
    orders = _orders([("m1", "a", 1.0)])
    assert trends.pooled_mean(orders, "value", ["m9"]) == {"value": None, "orders": 0}
    assert trends.pooled_ratio(orders.assign(den=0.0), "value", "den", ["m1"])["value"] is None
    assert trends.monthly_mean([], "value", ["m1"])["value"] is None


def test_change_uses_points_for_rates_and_needs_a_base_for_percent():
    assert trends.change(0.25, 0.10, "rate") == {"change": pytest.approx(15.0), "change_unit": "pp", "change_pct": pytest.approx(150.0)}
    assert trends.change(5.0, 0.0, "count")["change_pct"] is None
    assert trends.change(None, 3.0, "brl") == {"change": None, "change_unit": "brl", "change_pct": None}


def test_trend_reads_improvement_against_the_good_direction():
    now, before = {"value": 0.04, "orders": 100}, {"value": 0.10, "orders": 100}
    assert trends.trend(now, before, "rate", "down", [], [])["improving"] is True
    assert trends.trend(now, before, "rate", "up", [], [])["improving"] is False
    assert trends.trend({"value": None, "orders": 0}, before, "rate", "down", [], [])["improving"] is False
    # counts are read as a relative change
    assert trends.trend({"value": 120.0, "orders": 1}, {"value": 100.0, "orders": 1}, "count", "up", [], [])["improving"] is True


def test_group_windows_drop_groups_short_in_either_window():
    rows = ([("r", "big", 0.0)] * 30 + [("p", "big", 1.0)] * 30
            + [("r", "only_recent", 0.0)] * 40
            + [("r", "thin", 0.0)] * 29 + [("p", "thin", 1.0)] * 40)
    groups = trends.group_windows(_orders(rows), "value", "group", ["r"], ["p"], "rate")
    assert [g["name"] for g in groups] == ["big"]
    assert groups[0]["change"] == pytest.approx(-100.0)


def _group(name, recent, previous, orders=100):
    return trends.group_row(name, {"value": recent, "orders": orders}, {"value": previous, "orders": orders}, "rate")


def _rates(by_group, business=0.10):
    return {"low_review_rate": {"business": {"orders": 1000, "rate": business}, "by_group": by_group}}


def test_candidates_keep_groups_improving_at_least_as_much_as_the_business():
    business = trends.trend({"value": 0.05, "orders": 1000}, {"value": 0.10, "orders": 1000}, "rate", "down", [], [])
    groups = [_group("faster", 0.02, 0.12), _group("slower", 0.09, 0.10), _group("worse", 0.20, 0.10)]
    found = trends.candidates(groups, business, "rate", "down", _rates({}), {}, limit=5)
    assert [c["name"] for c in found] == ["faster"]
    assert found[0]["readiness"] == "unknown" and found[0]["share_recent"] == pytest.approx(0.1)


def test_candidates_put_ready_groups_first_and_respect_the_limit():
    business = trends.trend({"value": 0.05, "orders": 1000}, {"value": 0.10, "orders": 1000}, "rate", "down", [], [])
    groups = [_group("bad_reviews", 0.01, 0.20, orders=500), _group("good_reviews", 0.01, 0.20, orders=50)]
    rates = _rates({"bad_reviews": {"orders": 500, "rate": 0.30}, "good_reviews": {"orders": 50, "rate": 0.10}})
    found = trends.candidates(groups, business, "rate", "down", rates, {}, limit=5)
    assert [(c["name"], c["readiness"]) for c in found] == [("good_reviews", "ready"), ("bad_reviews", "fix_first")]
    assert len(trends.candidates(groups, business, "rate", "down", rates, {}, limit=1)) == 1


def test_candidates_are_empty_when_the_business_change_is_unknown():
    business = trends.trend({"value": None, "orders": 0}, {"value": 0.10, "orders": 100}, "rate", "down", [], [])
    assert trends.candidates([_group("a", 0.01, 0.2)], business, "rate", "down", _rates({}), {}, 5) == []


def test_change_check_triggers_from_its_threshold():
    before = {"value": 0.20, "orders": 100}
    at = trends.change_check("x", "t", "l", "rate", {"value": 0.21, "orders": 100}, before, "up", 1.0)
    below = trends.change_check("x", "t", "l", "rate", {"value": 0.2099, "orders": 100}, before, "up", 1.0)
    falling = trends.change_check("y", "t", "l", "count", {"value": 95.0, "orders": 1}, {"value": 100.0, "orders": 1}, "down", 5.0)
    assert (at["triggered"], below["triggered"], falling["triggered"]) == (True, False, True)
    assert at["comparison"]["threshold_unit"] == "pp" and falling["comparison"]["threshold_unit"] == "pct"
    unknown = trends.change_check("z", "t", "l", "rate", {"value": None, "orders": 0}, before, "up", 1.0)
    assert unknown["triggered"] is False


def test_groups_check_names_the_worst_flagged_groups_first():
    groups = [_group("a", 0.13, 0.10), _group("b", 0.30, 0.10), _group("c", 0.11, 0.10)]
    check = trends.groups_check("g", "t", "l", "state", "rate", groups, "up", 2.0)
    assert check["triggered"] is True
    assert (check["groups"]["flagged"], check["groups"]["of"]) == (2, 3)
    assert [g["name"] for g in check["groups"]["worst"]] == ["b", "a"]


def test_gap_check_needs_enough_orders_and_handles_a_zero_side():
    worse, better = {"label": "late", "value": 0.4, "orders": 50}, {"label": "on time", "value": 0.1, "orders": 50}
    assert trends.gap_check("g", "t", "l", "rate", worse, better, 2.0)["gap"]["ratio"] == pytest.approx(4.0)
    assert trends.gap_check("g", "t", "l", "rate", worse, {**better, "value": 0.0}, 2.0)["triggered"] is True
    assert trends.gap_check("g", "t", "l", "rate", {**worse, "orders": 5}, better, 2.0)["triggered"] is False
