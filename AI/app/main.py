"""FastAPI application assembly. Data and models are loaded once at startup into app.state."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.categories import analyse_categories
from app.api import categories, risk, sales, scenarios
from app.api.deps import load_artifact
from app.config import ALL_DATASET_FILES, CORS_ORIGINS, DATASETS_DIR, MODELS_DIR
from app.data.categories import build_category_monthly
from app.data.olist import build_monthly_sales, dataset_hashes, load_order_items, load_orders
from app.data.orders import build_order_features

MODEL_NAMES = (sales.SALES_MODEL, risk.LATE_MODEL, risk.REVIEW_MODEL)


def create_app(datasets_dir: Path = DATASETS_DIR, models_dir: Path = MODELS_DIR) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.monthly = build_monthly_sales(load_orders(datasets_dir), load_order_items(datasets_dir))
        app.state.categories = analyse_categories(build_category_monthly(datasets_dir))
        app.state.orders = build_order_features(datasets_dir)
        app.state.dataset_hashes = dataset_hashes(datasets_dir, ALL_DATASET_FILES)
        app.state.models = {name: load_artifact(models_dir, name) for name in MODEL_NAMES}
        yield

    app = FastAPI(title="Mosaic analytics API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET"], allow_headers=["*"]
    )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "model_loaded": app.state.models[sales.SALES_MODEL][0] is not None,
            "models": {name: model is not None for name, (model, _) in app.state.models.items()},
        }

    app.include_router(sales.router)
    app.include_router(categories.router)
    app.include_router(risk.router)
    app.include_router(scenarios.router)
    return app


app = create_app()


if __name__ == "__main__":
    # Lets `python -m app.main` (or the IDE run button) start the server directly.
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
