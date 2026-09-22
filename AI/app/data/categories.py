"""Monthly sales per product category, using the same order rules as the business total."""
from pathlib import Path

import pandas as pd

from app.config import DATA_RANGE, EXCLUDED_STATUSES
from app.data.loaders import load_category_translation, load_items_full, load_products
from app.data.olist import load_orders

CATEGORY_COLUMNS = ["month", "category", "orders", "items", "sales"]
UNKNOWN_CATEGORY = "unknown"


def build_category_monthly(
    datasets_dir: Path,
    data_range: tuple[str, str] = DATA_RANGE,
    excluded_statuses: frozenset[str] = EXCLUDED_STATUSES,
) -> pd.DataFrame:
    orders = load_orders(datasets_dir)
    orders = orders[~orders["order_status"].isin(excluded_statuses)].copy()
    orders["month"] = orders["order_purchase_timestamp"].str.slice(0, 7)
    start, end = data_range
    orders = orders[orders["month"].between(start, end)][["order_id", "month"]]

    products = load_products(datasets_dir).merge(
        load_category_translation(datasets_dir), on="product_category_name", how="left"
    )
    products["category"] = (
        products["product_category_name_english"]
        .fillna(products["product_category_name"])
        .fillna(UNKNOWN_CATEGORY)
    )
    items = load_items_full(datasets_dir)[["order_id", "product_id", "price"]]
    items = items.merge(products[["product_id", "category"]], on="product_id", how="left")
    items["category"] = items["category"].fillna(UNKNOWN_CATEGORY)

    # Inner join keeps only items of eligible orders; each item has exactly one category.
    lines = orders.merge(items, on="order_id", how="inner")
    monthly = (
        lines.groupby(["month", "category"], as_index=False)
        .agg(orders=("order_id", "nunique"), items=("product_id", "size"), sales=("price", "sum"))
    )
    return _fill_missing_pairs(monthly)


def _fill_missing_pairs(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)
    months = pd.period_range(monthly["month"].min(), monthly["month"].max(), freq="M").strftime("%Y-%m")
    grid = pd.MultiIndex.from_product([months, sorted(monthly["category"].unique())], names=["month", "category"])
    filled = monthly.set_index(["month", "category"]).reindex(grid, fill_value=0).reset_index()
    return filled.astype({"orders": int, "items": int, "sales": float})[CATEGORY_COLUMNS]
