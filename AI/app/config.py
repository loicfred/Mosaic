"""Runtime paths, dataset files and shared analysis boundaries."""

import os
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = Path(os.environ.get("MOSAIC_DATASETS_DIR", AI_ROOT / "datasets"))
MODELS_DIR = Path(os.environ.get("MOSAIC_MODELS_DIR", AI_ROOT / "models"))
CORS_ORIGINS = os.environ.get("MOSAIC_CORS_ORIGINS", "http://localhost:5173").split(",")

ORDERS_FILE = "olist_orders_dataset.csv"
ITEMS_FILE = "olist_order_items_dataset.csv"
PRODUCTS_FILE = "olist_products_dataset.csv"
SELLERS_FILE = "olist_sellers_dataset.csv"
CUSTOMERS_FILE = "olist_customers_dataset.csv"
GEOLOCATION_FILE = "olist_geolocation_dataset.csv"
REVIEWS_FILE = "olist_order_reviews_dataset.csv"
TRANSLATION_FILE = "product_category_name_translation.csv"
ALL_DATASET_FILES = (
    ORDERS_FILE,
    ITEMS_FILE,
    PRODUCTS_FILE,
    SELLERS_FILE,
    CUSTOMERS_FILE,
    GEOLOCATION_FILE,
    REVIEWS_FILE,
    TRANSLATION_FILE,
)

# Olist has near-empty stub months before and after this range.
DATA_RANGE = ("2017-01", "2018-08")
EXCLUDED_STATUSES = frozenset({"canceled", "unavailable"})
OPEN_STATUSES = frozenset({"shipped", "processing", "invoiced", "approved", "created"})

# Purchases from SPLIT_DATE up to (excluding) TEST_END_DATE form the held-out test period.
SPLIT_DATE = "2018-06-01"
TEST_END_DATE = "2018-09-01"
