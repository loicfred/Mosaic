"""Whole-business monthly sales forecast: ridge regression on lag features.

All functions are pure and operate on a plain sequence of monthly sales values in
chronological order. Evaluation is a rolling-origin backtest so that every reported
prediction was made using only earlier months.
"""
from collections.abc import Sequence

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LAGS = 3
BACKTEST_MONTHS = 6
MIN_MONTHS = LAGS + 1 + BACKTEST_MONTHS
FEATURE_NAMES = ["trend", "lag_1", "lag_2", "lag_3", "mean_last_3"]
INTERVAL_Z = 1.96


def validate_series_length(values: Sequence[float]) -> None:
    if len(values) < MIN_MONTHS:
        raise ValueError(
            f"Need at least {MIN_MONTHS} months of sales to train and backtest, got {len(values)}"
        )


def feature_row(values: Sequence[float], t: int) -> list[float]:
    """Features for month index ``t`` built only from months before ``t``."""
    lags = [float(values[t - k]) for k in range(1, LAGS + 1)]
    return [float(t), *lags, sum(lags) / LAGS]


def training_matrix(values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    rows = [feature_row(values, t) for t in range(LAGS, len(values))]
    targets = [float(values[t]) for t in range(LAGS, len(values))]
    return np.array(rows, dtype=float), np.array(targets, dtype=float)


def build_model() -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=1.0))])


def fit_model(values: Sequence[float]) -> Pipeline:
    X, y = training_matrix(values)
    return build_model().fit(X, y)


def _predict_next(model: Pipeline, values: Sequence[float]) -> float:
    return float(model.predict(np.array([feature_row(values, len(values))]))[0])


def recursive_forecast(model: Pipeline, values: Sequence[float], horizon: int) -> list[float]:
    """Each predicted month becomes a lag for the next one."""
    history = [float(v) for v in values]
    forecast = []
    for _ in range(horizon):
        prediction = _predict_next(model, history)
        forecast.append(prediction)
        history.append(prediction)
    return forecast


def naive_last(values: Sequence[float], horizon: int) -> list[float]:
    return [float(values[-1])] * horizon


def mean_last_3(values: Sequence[float], horizon: int) -> list[float]:
    return [float(sum(values[-3:]) / 3)] * horizon


def preferred_method(evaluation: dict) -> str:
    """Only select the trained model when its backtest beats both simple rules."""
    return min(("naive_last", "mean_last_3", "model"), key=lambda name: evaluation[name]["mae"])


def forecast_by_method(method: str, model: Pipeline, values: Sequence[float], horizon: int) -> list[float]:
    if method == "naive_last":
        return naive_last(values, horizon)
    if method == "mean_last_3":
        return mean_last_3(values, horizon)
    return recursive_forecast(model, values, horizon)


def error_metrics(actuals: Sequence[float], predictions: Sequence[float]) -> dict:
    errors = [abs(a - p) for a, p in zip(actuals, predictions)]
    percentages = [abs(a - p) / abs(a) * 100 for a, p in zip(actuals, predictions) if a != 0]
    return {
        "mae": float(np.mean(errors)),
        "mape": float(np.mean(percentages)) if percentages else None,
        "skipped_zero_actuals": len(actuals) - len(percentages),
    }


def backtest(values: Sequence[float], backtest_months: int = BACKTEST_MONTHS) -> dict:
    """One-step-ahead rolling-origin evaluation over the last ``backtest_months`` months."""
    values = [float(v) for v in values]
    origins = range(len(values) - backtest_months, len(values))
    predictions = {"model": [], "naive_last": [], "mean_last_3": []}
    for origin in origins:
        history = values[:origin]
        predictions["model"].append(_predict_next(fit_model(history), history))
        predictions["naive_last"].append(naive_last(history, 1)[0])
        predictions["mean_last_3"].append(mean_last_3(history, 1)[0])
    actuals = [values[origin] for origin in origins]

    result = {}
    for name, predicted in predictions.items():
        result[name] = {
            **error_metrics(actuals, predicted),
            "points": [
                {"month_index": origin, "actual": actual, "predicted": pred}
                for origin, actual, pred in zip(origins, actuals, predicted)
            ],
        }
    residuals = np.array(actuals) - np.array(predictions["model"])
    result["residual_std"] = float(np.std(residuals))
    return result


def prediction_interval(point: float, residual_std: float) -> tuple[float, float]:
    half_width = INTERVAL_Z * residual_std
    return point - half_width, point + half_width


def forecast_months(last_month: str, horizon: int) -> list[str]:
    year, month = (int(part) for part in last_month.split("-"))
    labels = []
    for _ in range(horizon):
        month += 1
        if month > 12:
            month, year = 1, year + 1
        labels.append(f"{year:04d}-{month:02d}")
    return labels
