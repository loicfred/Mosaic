"""Turn the Olist orders and order-items CSVs into one monthly sales series.

Sales here means gross item sales (sum of item ``price``), booked by purchase month.
It excludes freight, payments, costs and any notion of settlement or profit.
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from collections.abc import Iterable

from app.config import DATA_RANGE, EXCLUDED_STATUSES, ITEMS_FILE, ORDERS_FILE

MONTH_COLUMNS = ["month", "orders", "sales", "freight"]


@dataclass(frozen=True)
class MonthlySales:
    months: pd.DataFrame
    exclusions: dict


def load_orders(datasets_dir: Path) -> pd.DataFrame:
    return pd.read_csv(
        datasets_dir / ORDERS_FILE,
        usecols=["order_id", "order_status", "order_purchase_timestamp"],
        dtype=str,
    )


def load_order_items(datasets_dir: Path) -> pd.DataFrame:
    return pd.read_csv(
        datasets_dir / ITEMS_FILE,
        usecols=["order_id", "price", "freight_value"],
        dtype={"order_id": str, "price": float, "freight_value": float},
    )


def build_monthly_sales(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    data_range: tuple[str, str] = DATA_RANGE,
    excluded_statuses: frozenset[str] = EXCLUDED_STATUSES,
) -> MonthlySales:
    excluded_mask = orders["order_status"].isin(excluded_statuses)
    status_counts = orders.loc[excluded_mask, "order_status"].value_counts()
    kept = orders.loc[~excluded_mask, ["order_id", "order_purchase_timestamp"]].copy()
    kept["month"] = kept["order_purchase_timestamp"].str.slice(0, 7)

    # Items are aggregated to order grain before the join so a multi-item order is
    # counted once and no other one-to-many table can inflate the totals.
    per_order = (
        items.groupby("order_id", as_index=False)
        .agg(sales=("price", "sum"), freight=("freight_value", "sum"))
    )
    order_level = kept[["order_id", "month"]].merge(per_order, on="order_id", how="left")
    orders_without_items = int(order_level["sales"].isna().sum())
    order_level[["sales", "freight"]] = order_level[["sales", "freight"]].fillna(0.0)

    monthly = (
        order_level.groupby("month", as_index=False)
        .agg(orders=("order_id", "nunique"), sales=("sales", "sum"), freight=("freight", "sum"))
    )
    start, end = data_range
    in_range = monthly["month"].between(start, end)
    months_outside_range = {
        month: int(count)
        for month, count in zip(monthly.loc[~in_range, "month"], monthly.loc[~in_range, "orders"])
    }
    monthly = _fill_missing_months(monthly.loc[in_range])

    return MonthlySales(
        months=monthly,
        exclusions={
            "statuses": {status: int(count) for status, count in status_counts.items()},
            "orders_without_items": orders_without_items,
            "months_outside_range": months_outside_range,
        },
    )


def _fill_missing_months(monthly: pd.DataFrame) -> pd.DataFrame:
    """Return one row per calendar month between the first and last observed month."""
    if monthly.empty:
        return pd.DataFrame(columns=MONTH_COLUMNS).astype(
            {"month": str, "orders": int, "sales": float, "freight": float}
        )
    full_index = pd.period_range(monthly["month"].min(), monthly["month"].max(), freq="M")
    filled = (
        monthly.set_index("month")
        .reindex(full_index.strftime("%Y-%m"), fill_value=0)
        .rename_axis("month")
        .reset_index()
    )
    return filled.astype({"orders": int, "sales": float, "freight": float})[MONTH_COLUMNS]


def dataset_hashes(datasets_dir: Path, files: Iterable[str] = (ORDERS_FILE, ITEMS_FILE)) -> dict[str, str]:
    return {name: _sha256(datasets_dir / name) for name in files}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
