import pytest

from app.analysis import satisfaction
from app.data.orders import build_order_features
from tests.trend_frames import orders


def test_fixture_low_reviews_follow_the_late_orders(datasets_dir):
    frame = build_order_features(datasets_dir).frame
    trend = satisfaction.trend(frame)
    assert (trend["recent"]["value"], trend["previous"]["value"]) == (pytest.approx(2 / 6), pytest.approx(1 / 6))
    assert trend["improving"] is False
    checks = {c["id"]: c for c in satisfaction.caveats(frame)}
    # 2 late and 4 on-time reviewed orders: below the minimum, so no verdict on the gap
    assert checks["late_orders_get_low_reviews"]["gap"]["worse"] == {"label": "late orders", "orders": 2, "value": 1.0}
    assert checks["late_orders_get_low_reviews"]["triggered"] is False


def test_categories_need_better_reviews_and_growing_sales():
    frame = orders({
        "toys": {"previous": (100, 30), "recent": (120, 3)},    # 30% -> 2.5%, sales up
        "books": {"previous": (100, 30), "recent": (80, 2)},    # 30% -> 2.5%, sales down
        "tools": {"previous": (100, 10), "recent": (100, 10)},  # no change
    }, "category")
    found = satisfaction.opportunities(frame, 5)
    assert found["trend"]["improving"] is True
    assert [c["name"] for c in found["candidates"]] == ["toys"]
    assert found["candidates"][0]["sales"]["change_pct"] == pytest.approx(20.0)


def test_late_orders_with_far_more_low_reviews_trigger_the_gap():
    frame = orders({"toys": {"previous": (100, 10), "recent": (100, 40)}}, "category")
    frame.loc[frame["order_id"].str.contains("recent") & (frame["late"] == 0), "review_score"] = 5.0
    check = next(c for c in satisfaction.caveats(frame) if c["id"] == "late_orders_get_low_reviews")
    # 40 late orders all 1-star, 60 on time with none: the starkest gap
    assert check["triggered"] is True and check["gap"]["ratio"] is None
