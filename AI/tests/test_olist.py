import pandas as pd
import pytest

from app.data.olist import build_monthly_sales, dataset_hashes, load_order_items, load_orders
from tests.conftest import FIXTURE_MONTHLY_SALES, FIXTURE_MONTHS, write_fixture_csvs


@pytest.fixture
def monthly(datasets_dir):
    return build_monthly_sales(load_orders(datasets_dir), load_order_items(datasets_dir))


def test_months_cover_fixture_range_with_constant_sales(monthly):
    assert list(monthly.months["month"]) == FIXTURE_MONTHS
    assert monthly.months["sales"].tolist() == [FIXTURE_MONTHLY_SALES] * 12


def test_excluded_statuses_are_not_summed_and_are_counted(monthly):
    march = monthly.months.set_index("month").loc["2017-03"]
    assert march["sales"] == FIXTURE_MONTHLY_SALES
    assert monthly.exclusions["statuses"] == {"canceled": 1, "unavailable": 1}


def test_multi_item_order_counts_once_but_sums_every_item(monthly):
    january = monthly.months.set_index("month").loc["2017-01"]
    assert january["orders"] == 2
    assert january["sales"] == 150.0 + 200.0
    assert january["freight"] == 30.0


def test_order_without_items_counts_as_zero_sales(monthly):
    march = monthly.months.set_index("month").loc["2017-03"]
    assert march["orders"] == 3
    assert monthly.exclusions["orders_without_items"] == 1


def test_months_outside_range_are_dropped_and_reported(monthly):
    assert "2016-10" not in monthly.months["month"].values
    assert monthly.exclusions["months_outside_range"] == {"2016-10": 1, "2018-09": 1}


def test_missing_month_inside_span_is_filled_with_zeros(tmp_path):
    write_fixture_csvs(tmp_path, drop_month="2017-06")
    monthly = build_monthly_sales(load_orders(tmp_path), load_order_items(tmp_path))
    june = monthly.months.set_index("month").loc["2017-06"]
    assert list(monthly.months["month"]) == FIXTURE_MONTHS
    assert june["orders"] == 0 and june["sales"] == 0.0


def test_empty_input_gives_empty_series_not_error():
    orders = pd.DataFrame(columns=["order_id", "order_status", "order_purchase_timestamp"])
    items = pd.DataFrame(columns=["order_id", "price", "freight_value"])
    monthly = build_monthly_sales(orders, items)
    assert list(monthly.months.columns) == ["month", "orders", "sales", "freight"]
    assert monthly.months.empty
    assert monthly.exclusions == {
        "statuses": {}, "orders_without_items": 0, "months_outside_range": {},
    }


def test_dataset_hashes_change_when_file_changes(datasets_dir):
    before = dataset_hashes(datasets_dir)
    with open(datasets_dir / "olist_orders_dataset.csv", "a", encoding="utf-8") as f:
        f.write("x,c,delivered,2017-05-01 00:00:00,,,,\n")
    after = dataset_hashes(datasets_dir)
    assert set(before) == {"olist_orders_dataset.csv", "olist_order_items_dataset.csv"}
    assert before["olist_orders_dataset.csv"] != after["olist_orders_dataset.csv"]
    assert before["olist_order_items_dataset.csv"] == after["olist_order_items_dataset.csv"]
