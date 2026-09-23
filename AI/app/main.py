"""FastAPI application assembly. Data and models are loaded once at startup into app.state."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.categories import analyse_categories
from app.api import router
from app.api.deps import MODEL_NAMES, load_artifact
from app.config import ALL_DATASET_FILES, CORS_ORIGINS, DATASETS_DIR, MODELS_DIR
from app.data.categories import build_category_monthly
from app.data.olist import build_monthly_sales, dataset_hashes, load_order_items, load_orders
from app.data.orders import build_order_features
from app.models.prepare import prepare_models

def create_app(datasets_dir: Path = DATASETS_DIR, models_dir: Path = MODELS_DIR, auto_train: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.monthly = build_monthly_sales(load_orders(datasets_dir), load_order_items(datasets_dir))
        app.state.categories = analyse_categories(build_category_monthly(datasets_dir))
        app.state.orders = build_order_features(datasets_dir)
        app.state.datasets_dir = datasets_dir
        app.state.dataset_hashes = dataset_hashes(datasets_dir, ALL_DATASET_FILES)
        if auto_train:
            prepare_models(datasets_dir, models_dir, app.state.dataset_hashes)
        app.state.models = {name: load_artifact(models_dir, name) for name in MODEL_NAMES}
        yield

    app = FastAPI(title="Mosaic analytics API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET"], allow_headers=["*"]
    )

    app.include_router(router)
    return app


app = create_app(auto_train=True)


if __name__ == "__main__":
    # Lets `python -m app.main` (or the IDE run button) start the server directly.
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
