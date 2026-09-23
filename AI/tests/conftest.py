"""Synthetic Olist-shaped fixture: 12 months of 2017 with known, hand-checkable values.

Per month: order ``<month>-a`` (seller s1 in SP, two items 100 + 50, on time, review 5) and
order ``<month>-b`` (seller s2 in RJ, one item 200, late in even months with review 1,
otherwise on time with review 4). Monthly sales are therefore always 350.0.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.config import (
    CASHFLOW_FILE, CUSTOMERS_FILE, GEOLOCATION_FILE, ITEMS_FILE, ORDERS_FILE, PRODUCTS_FILE,
    REVIEWS_FILE, SELLERS_FILE, TRANSLATION_FILE,
)

# Cash-flow fixture: 6 months, 4 rows each (2 healthy, 2 stressed) plus one zero-revenue row,
# unrelated to the Olist fixture above and not joined with it.
CASHFLOW_MONTHS = [f"2024-{m:02d}" for m in range(1, 7)]
CASHFLOW_SPLIT_MONTH = "2024-06"  # test = June only
CASHFLOW_TEST_END = "2024-07"
CASHFLOW_ZERO_REVENUE_ID = "F-zero"

FIXTURE_MONTHS = [f"2017-{m:02d}" for m in range(1, 13)]
FIXTURE_MONTHLY_SALES = 350.0
LATE_B_MONTHS = [m for m in FIXTURE_MONTHS if int(m[-2:]) % 2 == 0]
ORDER_WITH_TWO_REVIEWS = "2017-01-a"
ORDER_WITHOUT_REVIEW = "2017-05-b"
ORDER_WITHOUT_GEOLOCATION = "2017-02-a"
PROMISED_DAYS = 10

GEOLOCATION = {"01000": (-23.55, -46.63), "02000": (-23.50, -46.62), "20000": (-22.90, -43.17)}

COLUMNS = {
    ORDERS_FILE: [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    ITEMS_FILE: [
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    ],
    PRODUCTS_FILE: [
        "product_id", "product_category_name", "product_name_lenght",
        "product_description_lenght", "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ],
    SELLERS_FILE: ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    CUSTOMERS_FILE: [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    ],
    GEOLOCATION_FILE: [
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
        "geolocation_city", "geolocation_state",
    ],
    REVIEWS_FILE: [
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message", "review_creation_date", "review_answer_timestamp",
    ],
    TRANSLATION_FILE: ["product_category_name", "product_category_name_english"],
}

PRODUCTS = [
    {"product_id": "pa", "product_category_name": "cat_a", "product_weight_g": 500,
     "product_length_cm": 10, "product_height_cm": 10, "product_width_cm": 10},
    {"product_id": "pb", "product_category_name": "cat_b", "product_weight_g": 200,
     "product_length_cm": "", "product_height_cm": "", "product_width_cm": ""},
    {"product_id": "pc", "product_category_name": "cat_b", "product_weight_g": 1000,
     "product_length_cm": 20, "product_height_cm": 20, "product_width_cm": 20},
]
SELLERS = [
    {"seller_id": "s1", "seller_zip_code_prefix": "01000", "seller_city": "sao paulo", "seller_state": "SP"},
    {"seller_id": "s2", "seller_zip_code_prefix": "20000", "seller_city": "rio", "seller_state": "RJ"},
]
TRANSLATION = [
    {"product_category_name": "cat_a", "product_category_name_english": "category_a"},
    {"product_category_name": "cat_b", "product_category_name_english": "category_b"},
]


def _ts(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _order(order_id, month, status="delivered", late=False, handover_late=False, with_dates=True):
    purchase = datetime.strptime(f"{month}-15 10:00:00", "%Y-%m-%d %H:%M:%S")
    estimated = purchase + timedelta(days=PROMISED_DAYS)
    carrier = purchase + timedelta(days=5 if handover_late else 2)
    delivered = estimated + timedelta(days=2 if late else -1)
    row = {
        "order_id": order_id, "customer_id": f"c-{order_id}", "order_status": status,
        "order_purchase_timestamp": _ts(purchase), "order_approved_at": _ts(purchase),
        "order_delivered_carrier_date": "", "order_delivered_customer_date": "",
        "order_estimated_delivery_date": _ts(estimated),
    }
    if status == "delivered" and with_dates:
        row["order_delivered_carrier_date"] = _ts(carrier)
        row["order_delivered_customer_date"] = _ts(delivered)
    return row


def _item(order_id, item_id, product_id, seller_id, price, month, freight=10.0):
    limit = datetime.strptime(f"{month}-15 10:00:00", "%Y-%m-%d %H:%M:%S") + timedelta(days=3)
    return {
        "order_id": order_id, "order_item_id": item_id, "product_id": product_id,
        "seller_id": seller_id, "shipping_limit_date": _ts(limit), "price": price,
        "freight_value": freight,
    }


def _customer(order_id, zip_prefix, state):
    return {
        "customer_id": f"c-{order_id}", "customer_unique_id": f"u-{order_id}",
        "customer_zip_code_prefix": zip_prefix, "customer_city": "x", "customer_state": state,
    }


def _review(review_id, order_id, score, answered):
    return {
        "review_id": review_id, "order_id": order_id, "review_score": score,
        "review_comment_title": "", "review_comment_message": "",
        "review_creation_date": answered, "review_answer_timestamp": answered,
    }


def write_fixture_csvs(directory: Path, drop_month: str | None = None, include_cashflow: bool = True) -> None:
    orders, items, customers, reviews = [], [], [], []
    for month in FIXTURE_MONTHS:
        if month == drop_month:
            continue
        a, b = f"{month}-a", f"{month}-b"
        orders.append(_order(a, month))
        items += [_item(a, 1, "pa", "s1", 100.0, month), _item(a, 2, "pb", "s1", 50.0, month)]
        customer_zip = "09999" if a == ORDER_WITHOUT_GEOLOCATION else "02000"
        customers.append(_customer(a, customer_zip, "SP"))
        reviews.append(_review(f"r-{a}", a, 5, f"{month}-28 00:00:00"))

        late = month in LATE_B_MONTHS
        orders.append(_order(b, month, late=late, handover_late=late))
        items.append(_item(b, 1, "pc", "s2", 200.0, month))
        customers.append(_customer(b, "20000", "RJ"))
        if b != ORDER_WITHOUT_REVIEW:
            reviews.append(_review(f"r-{b}", b, 1 if late else 4, f"{month}-28 00:00:00"))
    reviews.append(_review("r-early", ORDER_WITH_TWO_REVIEWS, 2, "2017-01-20 00:00:00"))

    for order_id, status in (("cancelled-1", "canceled"), ("unavailable-1", "unavailable")):
        orders.append(_order(order_id, "2017-03", status=status))
        items.append(_item(order_id, 1, "pa", "s1", 999.0, "2017-03"))
        customers.append(_customer(order_id, "02000", "SP"))
    orders.append(_order("no-items-1", "2017-03"))
    customers.append(_customer("no-items-1", "02000", "SP"))
    orders.append(_order("out-of-range-1", "2016-10"))
    items.append(_item("out-of-range-1", 1, "pa", "s1", 777.0, "2016-10"))
    customers.append(_customer("out-of-range-1", "02000", "SP"))
    orders.append(_order("open-1", "2018-09", status="shipped"))
    items.append(_item("open-1", 1, "pc", "s2", 300.0, "2018-09"))
    customers.append(_customer("open-1", "20000", "RJ"))

    geolocation = [
        {"geolocation_zip_code_prefix": z, "geolocation_lat": lat, "geolocation_lng": lng,
         "geolocation_city": "x", "geolocation_state": "SP"}
        for z, (lat, lng) in GEOLOCATION.items()
    ]
    tables = {
        ORDERS_FILE: orders, ITEMS_FILE: items, PRODUCTS_FILE: PRODUCTS, SELLERS_FILE: SELLERS,
        CUSTOMERS_FILE: customers, GEOLOCATION_FILE: geolocation, REVIEWS_FILE: reviews,
        TRANSLATION_FILE: TRANSLATION,
    }
    for name, rows in tables.items():
        with open(directory / name, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS[name], extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in COLUMNS[name]})

    if include_cashflow:
        write_cashflow_fixture_csv(directory)


def _cashflow_row(record_id: str, month: str, stressed: bool) -> dict:
    if stressed:
        revenue, opex, ar_days, inv_days, loan, injections = 20000.0, 26000.0, 60, 70, 40000.0, 0.0
    else:
        revenue, opex, ar_days, inv_days, loan, injections = 50000.0, 30000.0, 20, 15, 10000.0, 2000.0
    return {
        "record_id": record_id, "sector": "Retail", "employees": 20, "month": month,
        "revenue_usd": revenue, "opex_usd": opex, "accounts_receivable_days": ar_days,
        "inventory_days": inv_days, "loan_balance_usd": loan, "owner_injections_usd": injections,
        "cashflow_stress_next_month": int(stressed),
    }


def write_cashflow_fixture_csv(directory: Path) -> None:
    rows = []
    counter = 0
    for month in CASHFLOW_MONTHS:
        for stressed in (False, False, True, True):
            counter += 1
            rows.append(_cashflow_row(f"F{counter:03d}", month, stressed))
    rows.append({
        "record_id": CASHFLOW_ZERO_REVENUE_ID, "sector": "IT Services", "employees": 5,
        "month": CASHFLOW_MONTHS[0], "revenue_usd": 0.0, "opex_usd": 500.0,
        "accounts_receivable_days": 0, "inventory_days": 0, "loan_balance_usd": 0.0,
        "owner_injections_usd": 0.0, "cashflow_stress_next_month": 1,
    })
    with open(directory / CASHFLOW_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def datasets_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "datasets"
    directory.mkdir()
    write_fixture_csvs(directory)
    return directory
