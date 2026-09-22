import os
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = Path(os.environ.get("MOSAIC_DATASETS_DIR", AI_ROOT / "datasets"))
MODELS_DIR = Path(os.environ.get("MOSAIC_MODELS_DIR", AI_ROOT / "models"))
CORS_ORIGINS = os.environ.get("MOSAIC_CORS_ORIGINS", "http://localhost:5173").split(",")

ORDERS_FILE = "olist_orders_dataset.csv"
ITEMS_FILE = "olist_order_items_dataset.csv"

# Olist has near-empty stub months before and after this range.
DATA_RANGE = ("2017-01", "2018-08")
EXCLUDED_STATUSES = frozenset({"canceled", "unavailable"})

PRODUCTS_FILE = "olist_products_dataset.csv"
SELLERS_FILE = "olist_sellers_dataset.csv"
CUSTOMERS_FILE = "olist_customers_dataset.csv"
GEOLOCATION_FILE = "olist_geolocation_dataset.csv"
REVIEWS_FILE = "olist_order_reviews_dataset.csv"
TRANSLATION_FILE = "product_category_name_translation.csv"
ALL_DATASET_FILES = (
    ORDERS_FILE, ITEMS_FILE, PRODUCTS_FILE, SELLERS_FILE, CUSTOMERS_FILE,
    GEOLOCATION_FILE, REVIEWS_FILE, TRANSLATION_FILE,
)

# Orders purchased on or after this date form the held-out test period for the risk models.
SPLIT_DATE = "2018-06-01"
OPEN_STATUSES = frozenset({"shipped", "processing", "invoiced", "approved", "created"})
# Purchases from SPLIT_DATE up to (excluding) TEST_END_DATE form the test period.
TEST_END_DATE = "2018-09-01"

# Local OpenAI-compatible LLM (LM Studio by default). Used only to narrate computed evidence.
LLM_BASE_URL = os.environ.get("MOSAIC_LLM_BASE_URL", "http://localhost:1234").rstrip("/")
LLM_MODEL = os.environ.get("MOSAIC_LLM_MODEL", "")  # empty: whatever the server has loaded
LLM_TIMEOUT_SECONDS = float(os.environ.get("MOSAIC_LLM_TIMEOUT_SECONDS", "120"))
# Reasoning models spend part of this budget on hidden reasoning before any visible text.
LLM_MAX_TOKENS = int(os.environ.get("MOSAIC_LLM_MAX_TOKENS", "1500"))
LLM_ENABLED = os.environ.get("MOSAIC_LLM_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
