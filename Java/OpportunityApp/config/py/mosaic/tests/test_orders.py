import math

import pandas as pd
import pytest

from app.data.orders import (
    DELIVERY_OUTCOME_FEATURES, PURCHASE_TIME_FEATURES, build_order_features, haversine_km,
)
from tests.conftest import (
    GEOLOCATION, ORDER_WITH_TWO_REVIEWS, ORDER_WITHOUT_GEOLOCATION, ORDER_WITHOUT_REVIEW,
    PROMISED_DAYS,
)


@pytest.fixture(scope="module")
def features(tmp_path_factory):
    from tests.conftest import write_fixture_csvs

    directory = tmp_path_factory.mktemp("datasets")
    write_fixture_csvs(directory)
    return build_order_features(directory)


@pytest.fixture(scope="module")
def rows(features):
    return features.frame.set_index("order_id")


def test_one_row_per_order_and_feature_columns_present(features):
    assert features.frame["order_id"].is_unique
    for column in PURCHASE_TIME_FEATURES + DELIVERY_OUTCOME_FEATURES:
        assert column in features.frame.columns, column


def test_multi_item_order_is_aggregated_once(rows):
    row = rows.loc["2017-01-a"]
    assert row["n_items"] == 2
    assert row["n_sellers"] == 1
    assert row["total_price"] == 150.0
    assert row["total_freight"] == 20.0
    assert row["total_weight_g"] == 700.0
    assert row["max_volume_cm3"] == 1000.0
    assert row["freight_ratio"] == pytest.approx(20.0 / 150.0)


def test_category_and_seller_come_from_priciest_item(rows):
    row = rows.loc["2017-01-a"]
    assert row["category"] == "category_a"
    assert row["seller_id"] == "s1"
    assert row["seller_state"] == "SP"
    assert row["customer_state"] == "SP"
    assert row["same_state"] == 1


def test_distance_uses_zip_centroids_and_is_nan_when_missing(rows):
    (lat1, lng1), (lat2, lng2) = GEOLOCATION["01000"], GEOLOCATION["02000"]
    assert rows.loc["2017-01-a", "distance_km"] == pytest.approx(haversine_km(lat1, lng1, lat2, lng2))
    assert 5.0 < rows.loc["2017-01-a", "distance_km"] < 7.0
    assert math.isnan(rows.loc[ORDER_WITHOUT_GEOLOCATION, "distance_km"])


def test_time_features(rows):
    row = rows.loc["2017-03-b"]
    assert row["promised_days"] == PROMISED_DAYS
    assert row["purchase_month"] == 3
    assert row["purchase_weekday"] == pd.Timestamp("2017-03-15").weekday()


def test_delivery_outcomes(rows):
    on_time, late = rows.loc["2017-01-b"], rows.loc["2017-02-b"]
    assert on_time["late"] == 0 and on_time["days_late"] == -1 and on_time["delivery_days"] == 9
    assert late["late"] == 1 and late["days_late"] == 2 and late["delivery_days"] == 12
    assert on_time["handover_late"] == 0 and late["handover_late"] == 1


def test_open_order_has_no_delivery_labels(rows):
    row = rows.loc["open-1"]
    assert row["delivered"] == 0
    assert math.isnan(row["late"]) and math.isnan(row["days_late"]) and math.isnan(row["delivery_days"])


def test_seller_history_excludes_current_order_and_is_nan_for_first(rows):
    assert math.isnan(rows.loc["2017-01-b", "seller_prior_late_rate"])
    assert rows.loc["2017-01-b", "seller_prior_orders"] == 0
    assert rows.loc["2017-02-b", "seller_prior_orders"] == 1
    assert rows.loc["2017-02-b", "seller_prior_late_rate"] == 0.0
    assert rows.loc["2017-03-b", "seller_prior_orders"] == 2
    assert rows.loc["2017-03-b", "seller_prior_late_rate"] == 0.5
    # s1 never delivers late: rate stays 0 once it has history.
    assert rows.loc["2017-12-a", "seller_prior_late_rate"] == 0.0


def test_latest_review_is_selected_and_missing_review_is_nan(rows):
    assert rows.loc[ORDER_WITH_TWO_REVIEWS, "review_score"] == 5
    assert rows.loc[ORDER_WITH_TWO_REVIEWS, "low_review"] == 0
    assert rows.loc["2017-02-b", "low_review"] == 1
    assert math.isnan(rows.loc[ORDER_WITHOUT_REVIEW, "review_score"])
    assert math.isnan(rows.loc[ORDER_WITHOUT_REVIEW, "low_review"])


def test_order_without_items_keeps_labels_but_nan_features(rows):
    row = rows.loc["no-items-1"]
    assert math.isnan(row["total_price"]) and pd.isna(row["category"])
    assert row["delivered"] == 1 and row["late"] == 0


def test_exclusion_counts(features):
    assert features.exclusions == {
        "delivered_without_delivery_date": 0,
        "orders_without_items": 1,
        "orders_without_geolocation": 1,
        "delivered_without_review": 3,  # no-items-1, 2017-05-b, out-of-range-1
        "orders_with_multiple_reviews": 1,
        "orders_without_payment": 3,  # no-items-1, out-of-range-1 and open-1 have no payment rows
    }


def test_payments_are_reduced_to_one_row_per_order(features):
    frame = features.frame.set_index("order_id")
    split = frame.loc["2017-02-b"]  # card 150 in 3 instalments plus a 60 voucher
    assert split["payment_total"] == pytest.approx(210.0)
    assert split["installments"] == 3
    assert split["payment_methods"] == 2
    assert split["payment_type"] == "credit_card"
    assert frame.loc["2017-02-a", "installments"] == 1
    assert pd.isna(frame.loc["no-items-1", "payment_total"])  # no payment rows is missing, not zero
    assert len(features.frame) == features.frame["order_id"].nunique()


def test_returning_customer_counts_only_earlier_orders_of_the_same_person(features):
    frame = features.frame.set_index("order_id")
    assert frame.loc["2017-01-b", "returning_customer"] == 0.0  # the person's first order
    assert frame.loc["2017-02-b", "returning_customer"] == 1.0
    assert (frame.loc[[f"{m}-a" for m in ("2017-01", "2017-06")], "returning_customer"] == 0.0).all()


def test_cancelled_marks_excluded_statuses_only(features):
    frame = features.frame.set_index("order_id")
    assert frame.loc["cancelled-1", "cancelled"] == 1.0
    assert frame.loc["unavailable-1", "cancelled"] == 1.0
    assert frame.loc["open-1", "cancelled"] == 0.0
    assert frame.loc["2017-02-a", "cancelled"] == 0.0
