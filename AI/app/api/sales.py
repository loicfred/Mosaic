"""Whole-business sales history and forecast routes."""
from fastapi import APIRouter, Query, Request

from app.api.deps import require_model
from app.data.olist import MonthlySales
from app.forecast import sales as sf

router = APIRouter(prefix="/api/sales", tags=["sales"])

MAX_HORIZON = 6
SALES_MODEL = "sales_forecast"
TRAIN_COMMAND = "python -m app.forecast.train"


@router.get("/history")
def sales_history(request: Request):
    return serialise_history(request.app.state.monthly)


@router.get("/forecast")
def sales_forecast(request: Request, horizon: int = Query(3, ge=1, le=MAX_HORIZON)):
    model, metadata = require_model(request, SALES_MODEL, TRAIN_COMMAND)
    return serialise_forecast(request.app.state.monthly, model, metadata, horizon)


def serialise_history(monthly: MonthlySales) -> dict:
    months = monthly.months
    data_range = None
    if not months.empty:
        data_range = {"start": months["month"].iloc[0], "end": months["month"].iloc[-1]}
    return {
        "unit": "BRL",
        "measure": "gross_item_sales",
        "range": data_range,
        "months": months.to_dict(orient="records"),
        "exclusions": monthly.exclusions,
    }


def serialise_forecast(monthly: MonthlySales, model, metadata: dict, horizon: int) -> dict:
    months = monthly.months["month"].tolist()
    values = monthly.months["sales"].tolist()
    labels = sf.forecast_months(months[-1], horizon)

    forecast = []
    for label, point in zip(labels, sf.recursive_forecast(model, values, horizon)):
        lower, upper = sf.prediction_interval(point, metadata["residual_std"])
        forecast.append({"month": label, "sales": point, "lower": lower, "upper": upper})

    return {
        "model_version": metadata["model_version"],
        "trained_at": metadata["trained_at"],
        "unit": "BRL",
        "measure": "gross_item_sales",
        "horizon": horizon,
        "forecast": forecast,
        "baselines": {
            "naive_last": _label(labels, sf.naive_last(values, horizon)),
            "mean_last_3": _label(labels, sf.mean_last_3(values, horizon)),
        },
        "evaluation": {
            name: _evaluation_with_month_labels(scores, months)
            for name, scores in metadata["evaluation"].items()
        },
        "limitations": metadata["limitations"],
    }


def _evaluation_with_month_labels(scores: dict, months: list[str]) -> dict:
    """Backtest points are stored by month index; the API reports the month label instead."""
    points = [
        {"month": months[p["month_index"]], "actual": p["actual"], "predicted": p["predicted"]}
        for p in scores["points"]
    ]
    return {**{k: v for k, v in scores.items() if k != "points"}, "points": points}


def _label(labels: list[str], points: list[float]) -> list[dict]:
    return [{"month": label, "sales": point} for label, point in zip(labels, points)]
