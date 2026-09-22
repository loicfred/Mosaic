"""CSV loaders for the Olist tables. Each returns only the columns the app uses."""
from pathlib import Path

import pandas as pd

from app.config import (
    CUSTOMERS_FILE, GEOLOCATION_FILE, ITEMS_FILE, ORDERS_FILE, PRODUCTS_FILE,
    REVIEWS_FILE, SELLERS_FILE, TRANSLATION_FILE,
)

ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp", "order_delivered_carrier_date",
    "order_delivered_customer_date", "order_estimated_delivery_date",
]


def load_orders_full(datasets_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        datasets_dir / ORDERS_FILE,
        usecols=["order_id", "customer_id", "order_status", *ORDER_DATE_COLUMNS],
        dtype=str,
    )
    for column in ORDER_DATE_COLUMNS:
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def load_items_full(datasets_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        datasets_dir / ITEMS_FILE,
        usecols=["order_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"],
        dtype={"order_id": str, "product_id": str, "seller_id": str, "shipping_limit_date": str},
    )
    frame["shipping_limit_date"] = pd.to_datetime(frame["shipping_limit_date"], errors="coerce")
    return frame


def load_products(datasets_dir: Path) -> pd.DataFrame:
    return pd.read_csv(
        datasets_dir / PRODUCTS_FILE,
        usecols=[
            "product_id", "product_category_name", "product_weight_g",
            "product_length_cm", "product_height_cm", "product_width_cm",
        ],
        dtype={"product_id": str, "product_category_name": str},
    )


def load_sellers(datasets_dir: Path) -> pd.DataFrame:
    return pd.read_csv(
        datasets_dir / SELLERS_FILE,
        usecols=["seller_id", "seller_zip_code_prefix", "seller_state"],
        dtype=str,
    )


def load_customers(datasets_dir: Path) -> pd.DataFrame:
    return pd.read_csv(
        datasets_dir / CUSTOMERS_FILE,
        usecols=["customer_id", "customer_zip_code_prefix", "customer_state"],
        dtype=str,
    )


def load_geolocation(datasets_dir: Path) -> pd.DataFrame:
    return pd.read_csv(
        datasets_dir / GEOLOCATION_FILE,
        usecols=["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"],
        dtype={"geolocation_zip_code_prefix": str},
    )


def load_reviews(datasets_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        datasets_dir / REVIEWS_FILE,
        usecols=["review_id", "order_id", "review_score", "review_answer_timestamp"],
        dtype={"review_id": str, "order_id": str, "review_answer_timestamp": str},
    )
    frame["review_answer_timestamp"] = pd.to_datetime(frame["review_answer_timestamp"], errors="coerce")
    return frame


def load_category_translation(datasets_dir: Path) -> pd.DataFrame:
    # The translation file starts with a UTF-8 byte-order mark.
    return pd.read_csv(datasets_dir / TRANSLATION_FILE, dtype=str, encoding="utf-8-sig")
