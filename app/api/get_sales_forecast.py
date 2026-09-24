"""Sales forecast with baselines and backtest evidence."""

from fastapi import APIRouter, Query, Request

from app.api.deps import SALES_MODEL, SALES_TRAIN_COMMAND, require_model
from app.data.olist import MonthlySales
from app.forecast import sales as sales_forecasting

router = APIRouter(prefix="/api/sales", tags=["sales"])

MAX_HORIZON = 6


@router.get("/forecast")
def sales_forecast(request: Request, horizon: int = Query(3, ge=1, le=MAX_HORIZON)):
    model, metadata = require_model(request, SALES_MODEL, SALES_TRAIN_COMMAND)
    return serialise_forecast(request.app.state.monthly, model, metadata, horizon)


def serialise_forecast(monthly: MonthlySales, model, metadata: dict, horizon: int) -> dict:
    months = monthly.months["month"].tolist()
    values = monthly.months["sales"].tolist()
    labels = sales_forecasting.forecast_months(months[-1], horizon)

    forecast = []
    for label, point in zip(labels, sales_forecasting.recursive_forecast(model, values, horizon)):
        lower, upper = sales_forecasting.prediction_interval(point, metadata["residual_std"])
        forecast.append({"month": label, "sales": point, "lower": lower, "upper": upper})

    return {
        "model_version": metadata["model_version"],
        "trained_at": metadata["trained_at"],
        "unit": "BRL",
        "measure": "gross_item_sales",
        "horizon": horizon,
        "forecast": forecast,
        "baselines": {
            "naive_last": _label_forecast_points(labels, sales_forecasting.naive_last(values, horizon)),
            "mean_last_3": _label_forecast_points(labels, sales_forecasting.mean_last_3(values, horizon)),
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
        {"month": months[point["month_index"]], "actual": point["actual"], "predicted": point["predicted"]}
        for point in scores["points"]
    ]
    return {**{key: value for key, value in scores.items() if key != "points"}, "points": points}


def _label_forecast_points(labels: list[str], points: list[float]) -> list[dict]:
    return [{"month": label, "sales": point} for label, point in zip(labels, points)]
