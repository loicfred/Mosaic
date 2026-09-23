"""Order-grain feature table shared by the risk models and the risk API.

Every one-to-many table (items, reviews) is reduced to one row per order before joining, so
an order is never counted twice. Outcome columns are NaN where the outcome is unknown.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app.data.geo import haversine_km, zip_centroids
from app.data.category_names import with_category_name
from app.data.loaders import (
    load_category_translation, load_customers, load_geolocation, load_items_full,
    load_orders_full, load_products, load_reviews, load_sellers,
)

CATEGORICAL_FEATURES = ["category", "seller_state", "customer_state"]
PURCHASE_TIME_FEATURES = [
    "n_items", "n_sellers", "total_price", "total_freight", "freight_ratio", "total_weight_g",
    "max_volume_cm3", "category", "seller_state", "customer_state", "same_state", "distance_km",
    "purchase_month", "purchase_weekday", "promised_days", "seller_prior_orders",
    "seller_prior_late_rate",
]
DELIVERY_OUTCOME_FEATURES = ["delivery_days", "days_late", "late", "handover_late"]
LOW_REVIEW_MAX_SCORE = 2


@dataclass(frozen=True)
class OrderFeatures:
    frame: pd.DataFrame
    exclusions: dict


def build_order_features(datasets_dir: Path) -> OrderFeatures:
    orders = load_orders_full(datasets_dir)
    item_features = _aggregate_items(
        load_items_full(datasets_dir), load_products(datasets_dir),
        load_category_translation(datasets_dir), load_sellers(datasets_dir),
    )
    frame = orders.merge(item_features, on="order_id", how="left")
    frame = frame.merge(load_customers(datasets_dir), on="customer_id", how="left")
    frame = _add_distance(frame, zip_centroids(load_geolocation(datasets_dir)))
    frame = _add_time_features(frame)
    frame = _add_delivery_outcomes(frame)
    frame, multiple_reviews = _add_latest_review(frame, load_reviews(datasets_dir))
    frame = _add_seller_history(frame)

    delivered = frame["delivered"] == 1
    exclusions = {
        "delivered_without_delivery_date": int((delivered & frame["order_delivered_customer_date"].isna()).sum()),
        "orders_without_items": int(frame["n_items"].isna().sum()),
        "orders_without_geolocation": int((frame["n_items"].notna() & frame["distance_km"].isna()).sum()),
        "delivered_without_review": int((delivered & frame["review_score"].isna()).sum()),
        "orders_with_multiple_reviews": multiple_reviews,
    }
    return OrderFeatures(frame=frame.reset_index(drop=True), exclusions=exclusions)


def _aggregate_items(items, products, translation, sellers) -> pd.DataFrame:
    products = with_category_name(products, translation)
    products["volume_cm3"] = (
        products["product_length_cm"] * products["product_height_cm"] * products["product_width_cm"]
    )
    enriched = items.merge(
        products[["product_id", "category", "product_weight_g", "volume_cm3"]], on="product_id", how="left"
    )
    totals = enriched.groupby("order_id").agg(
        n_items=("product_id", "size"),
        n_sellers=("seller_id", "nunique"),
        total_price=("price", "sum"),
        total_freight=("freight_value", "sum"),
        total_weight_g=("product_weight_g", lambda s: s.sum(min_count=1)),
        max_volume_cm3=("volume_cm3", "max"),
        shipping_limit=("shipping_limit_date", "min"),
    )
    # Category and seller are taken from the highest-priced item; ties broken by product_id.
    priciest = (
        enriched.sort_values(["order_id", "price", "product_id"], ascending=[True, False, True])
        .drop_duplicates("order_id")
        .set_index("order_id")[["category", "seller_id"]]
    )
    result = totals.join(priciest).reset_index()
    result = result.merge(sellers, on="seller_id", how="left")
    result["freight_ratio"] = np.where(result["total_price"] > 0, result["total_freight"] / result["total_price"], np.nan)
    return result


def _add_distance(frame: pd.DataFrame, centroids: pd.DataFrame) -> pd.DataFrame:
    seller_geo = centroids.rename(columns={"lat": "seller_lat", "lng": "seller_lng"})
    customer_geo = centroids.rename(columns={"lat": "customer_lat", "lng": "customer_lng"})
    frame = frame.merge(seller_geo, left_on="seller_zip_code_prefix", right_index=True, how="left")
    frame = frame.merge(customer_geo, left_on="customer_zip_code_prefix", right_index=True, how="left")
    frame["distance_km"] = haversine_km(
        frame["seller_lat"], frame["seller_lng"], frame["customer_lat"], frame["customer_lng"]
    )
    both_known = frame["seller_state"].notna() & frame["customer_state"].notna()
    frame["same_state"] = np.where(both_known, (frame["seller_state"] == frame["customer_state"]).astype(float), np.nan)
    return frame.drop(columns=["seller_lat", "seller_lng", "customer_lat", "customer_lng"])


def _calendar_days(later: pd.Series, earlier: pd.Series) -> pd.Series:
    return (later.dt.normalize() - earlier.dt.normalize()).dt.days


def _add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    purchase = frame["order_purchase_timestamp"]
    frame["purchase_ts"] = purchase
    frame["purchase_month"] = purchase.dt.month
    frame["purchase_weekday"] = purchase.dt.weekday
    frame["promised_days"] = _calendar_days(frame["order_estimated_delivery_date"], purchase)
    return frame


def _add_delivery_outcomes(frame: pd.DataFrame) -> pd.DataFrame:
    delivered_at = frame["order_delivered_customer_date"]
    frame["delivered"] = (frame["order_status"] == "delivered").astype(int)
    frame["delivery_days"] = _calendar_days(delivered_at, frame["order_purchase_timestamp"])
    frame["days_late"] = _calendar_days(delivered_at, frame["order_estimated_delivery_date"])
    labelled = (frame["delivered"] == 1) & delivered_at.notna()
    frame["late"] = np.where(labelled, (frame["days_late"] > 0).astype(float), np.nan)
    handover_known = frame["order_delivered_carrier_date"].notna() & frame["shipping_limit"].notna()
    frame["handover_late"] = np.where(
        handover_known, (frame["order_delivered_carrier_date"] > frame["shipping_limit"]).astype(float), np.nan
    )
    return frame


def _add_latest_review(frame: pd.DataFrame, reviews: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    per_order = reviews.groupby("order_id").size()
    multiple = int((per_order > 1).sum())
    latest = (
        reviews.sort_values(["order_id", "review_answer_timestamp", "review_id"])
        .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
    )
    frame = frame.merge(latest, on="order_id", how="left")
    frame["low_review"] = np.where(
        frame["review_score"].notna(), (frame["review_score"] <= LOW_REVIEW_MAX_SCORE).astype(float), np.nan
    )
    return frame, multiple


def _add_seller_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Expanding late rate over the seller's earlier orders, never including the order itself."""
    frame = frame.sort_values(["purchase_ts", "order_id"], kind="stable")
    known = frame["late"].notna().astype(int)
    late = frame["late"].fillna(0)
    by_seller = frame["seller_id"]
    prior_known = known.groupby(by_seller).cumsum() - known
    prior_late = late.groupby(by_seller).cumsum() - late
    frame["seller_prior_orders"] = prior_known.fillna(0).astype(int)
    frame["seller_prior_late_rate"] = np.where(prior_known > 0, prior_late / prior_known.replace(0, np.nan), np.nan)
    return frame
