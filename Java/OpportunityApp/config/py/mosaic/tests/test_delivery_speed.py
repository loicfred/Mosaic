import pytest

from app.analysis import delivery_speed
from app.data.orders import build_order_features
from tests.trend_frames import orders


def test_fixture_late_rate_rose_so_there_is_nothing_to_suggest(datasets_dir):
    # late "b" orders in even months: Oct and Dec of the last 3 against Aug of the 3 before
    frame = build_order_features(datasets_dir).frame
    trend = delivery_speed.trend(frame)
    assert (trend["recent"]["value"], trend["previous"]["value"]) == (pytest.approx(2 / 6), pytest.approx(1 / 6))
    assert trend["improving"] is False
    assert delivery_speed.opportunities(frame, 5)["candidates"] == []


def test_fixture_caveats_stay_quiet_when_nothing_moved(datasets_dir):
    checks = {c["id"]: c for c in delivery_speed.caveats(build_order_features(datasets_dir).frame)}
    assert set(checks) == {"freight_share_rising", "orders_falling", "promised_days_rising", "states_getting_later"}
    assert not any(c["triggered"] for c in checks.values())
    assert checks["orders_falling"]["comparison"]["recent"]["value"] == 2.0


def test_states_improving_faster_than_the_business_are_suggested():
    frame = orders({
        "RJ": {"previous": (100, 20), "recent": (100, 2)},    # 20% -> 2%
        "SP": {"previous": (100, 10), "recent": (100, 9)},    # 10% -> 9%, behind the business
        "AC": {"previous": (10, 5), "recent": (10, 0)},       # too few orders for a verdict
    }, "customer_state")
    found = delivery_speed.opportunities(frame, 5)
    assert found["trend"]["improving"] is True
    assert [c["name"] for c in found["candidates"]] == ["RJ"]
    assert found["candidates"][0]["checks"]["low_review_rate"]["level"] == "better"  # 2% against 11 of 210 for the business
    assert [p["month"] for p in found["candidates"][0]["series"]] == ["2018-03", "2018-04", "2018-05", "2018-06", "2018-07", "2018-08"]


def test_a_state_getting_later_is_a_caveat():
    frame = orders({"RJ": {"previous": (100, 2), "recent": (100, 20)}, "SP": {"previous": (100, 30), "recent": (100, 5)}},
                   "customer_state")
    check = next(c for c in delivery_speed.caveats(frame) if c["id"] == "states_getting_later")
    assert check["triggered"] is True and [g["name"] for g in check["groups"]["worst"]] == ["RJ"]
