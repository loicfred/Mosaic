import pandas as pd
import pytest

from app.analysis import seller_base
from app.data.orders import build_order_features
from tests.trend_frames import orders


def test_fixture_counts_distinct_sellers_a_month(datasets_dir):
    frame = build_order_features(datasets_dir).frame
    rows = seller_base.monthly(frame)
    # s1 and s2 sell every month; the cancelled and unavailable orders of March are not sales
    assert {row["value"] for row in rows} == {2}
    assert next(row for row in rows if row["month"] == "2017-03")["orders"] == 2
    assert seller_base.trend(frame)["improving"] is False


def test_categories_with_more_sellers_and_more_orders_are_suggested():
    frame = orders({
        "toys": {"previous": (90, 0), "recent": (120, 0), "sellers": {"previous": 3, "recent": 12}},
        "books": {"previous": (90, 0), "recent": (60, 0), "sellers": {"previous": 3, "recent": 12}},   # orders fell
        "tools": {"previous": (90, 0), "recent": (90, 0), "sellers": {"previous": 3, "recent": 3}},    # no growth
    }, "category")
    found = seller_base.opportunities(frame, 5)
    assert found["trend"]["improving"] is True
    assert [c["name"] for c in found["candidates"]] == ["toys"]
    toys = found["candidates"][0]
    assert (toys["previous"]["value"], toys["recent"]["value"]) == (3.0, 12.0)


def test_more_sellers_sharing_fewer_orders_is_a_caveat():
    frame = orders({"toys": {"previous": (90, 0), "recent": (60, 0), "sellers": {"previous": 3, "recent": 12}}}, "category")
    checks = {c["id"]: c for c in seller_base.caveats(frame)}
    assert checks["orders_per_seller_falling"]["triggered"] is True
    per_seller = checks["orders_per_seller_falling"]["comparison"]
    assert (per_seller["previous"]["value"], per_seller["recent"]["value"]) == (pytest.approx(10.0), pytest.approx(60 / 36))
    assert checks["categories_crowding"]["groups"]["flagged"] == 1


def test_new_sellers_delivering_late_more_often_is_a_caveat():
    # every recent seller is new in these frames; established sellers only exist when they sold before
    frame = orders({"toys": {"previous": (90, 0), "recent": (90, 45)}}, "category")
    old = orders({"old": {"previous": (60, 0), "recent": (60, 0)}}, "category")
    old["seller_id"] = "established"
    check = next(c for c in seller_base.caveats(pd.concat([frame, old])) if c["id"] == "new_sellers_late_more_often")
    assert check["gap"]["worse"]["value"] == pytest.approx(0.5) and check["gap"]["better"]["value"] == 0.0
    assert check["triggered"] is True
