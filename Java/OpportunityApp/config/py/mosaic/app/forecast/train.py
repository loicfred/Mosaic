"""Train the sales forecast and save the model with reproducibility metadata.

Run from ``Java/OpportunityApp/config/py/mosaic``: ``python -m app.forecast.train``
"""
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATASETS_DIR, MODELS_DIR
from app.data.olist import build_monthly_sales, dataset_hashes, load_order_items, load_orders
from app.forecast import sales as sf
from app.models import SALES_MODEL, save_artifact

MODEL_VERSION = "sales-ridge-v1"
ARTIFACT_NAME = f"{SALES_MODEL}.joblib"
METADATA_NAME = f"{SALES_MODEL}.json"
LIMITATIONS = [
    "Trained on about 20 monthly observations; treat the forecast as a trend indicator, not a guarantee.",
    "No seasonal term: the single November 2017 peak cannot be learned as a recurring pattern.",
    "Sales are gross item prices booked by purchase month, not profit and not cash received.",
    "Prediction interval width comes from one-step backtest errors and is applied to every horizon.",
]


def train(datasets_dir: Path = DATASETS_DIR, models_dir: Path = MODELS_DIR) -> dict:
    monthly = build_monthly_sales(load_orders(datasets_dir), load_order_items(datasets_dir))
    values = monthly.months["sales"].tolist()
    sf.validate_series_length(values)

    evaluation = sf.backtest(values)
    residual_std = evaluation.pop("residual_std")
    model = sf.fit_model(values)

    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_range": {"start": monthly.months["month"].iloc[0], "end": monthly.months["month"].iloc[-1]},
        "n_months": len(values),
        "dataset_hashes": dataset_hashes(datasets_dir),
        "feature_names": sf.FEATURE_NAMES,
        "evaluation": evaluation,
        "residual_std": residual_std,
        "exclusions": monthly.exclusions,
        "limitations": LIMITATIONS,
    }

    save_artifact(models_dir, SALES_MODEL, model, metadata)
    return metadata


def main() -> None:
    metadata = train()
    print(f"Trained {metadata['model_version']} on {metadata['n_months']} months "
          f"({metadata['data_range']['start']} to {metadata['data_range']['end']})")
    print("Backtest, one step ahead over the last 6 months:")
    for name in ("model", "naive_last", "mean_last_3"):
        scores = metadata["evaluation"][name]
        print(f"  {name:12s} MAE={scores['mae']:>12,.2f}  MAPE={scores['mape']:.2f}%")
    print(f"Saved to {MODELS_DIR / ARTIFACT_NAME} and {MODELS_DIR / METADATA_NAME}")


if __name__ == "__main__":
    main()
