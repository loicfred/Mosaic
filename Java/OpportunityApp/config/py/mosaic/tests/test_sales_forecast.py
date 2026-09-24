import math

import pytest

from app.forecast import sales as sf


def test_feature_row_uses_previous_three_months_and_trend():
    assert sf.feature_row([10, 20, 30, 40], 3) == [3, 30, 20, 10, 20.0]


def test_training_matrix_drops_months_without_complete_lags():
    X, y = sf.training_matrix(list(range(12)))
    assert X.shape == (9, len(sf.FEATURE_NAMES))
    assert y.tolist() == list(range(3, 12))


def test_backtest_only_predicts_observed_months_and_beats_naive_on_linear_series():
    values = [100.0 + 10 * i for i in range(14)]
    result = sf.backtest(values)
    actuals = [p["actual"] for p in result["model"]["points"]]
    assert actuals == values[-6:]
    assert [p["month_index"] for p in result["model"]["points"]] == list(range(8, 14))
    assert result["model"]["mae"] < result["naive_last"]["mae"]
    assert result["naive_last"]["mae"] == pytest.approx(10.0)
    assert result["residual_std"] >= 0.0


def test_recursive_forecast_returns_horizon_floats():
    values = [100.0 + 10 * i for i in range(14)]
    model = sf.fit_model(values)
    forecast = sf.recursive_forecast(model, values, 4)
    assert len(forecast) == 4
    assert all(isinstance(v, float) and math.isfinite(v) for v in forecast)
    assert forecast[0] == pytest.approx(240.0, rel=0.05)


def test_forecast_months_continue_after_last_month_across_year_end():
    assert sf.forecast_months("2018-08", 3) == ["2018-09", "2018-10", "2018-11"]
    assert sf.forecast_months("2017-11", 3) == ["2017-12", "2018-01", "2018-02"]


def test_series_shorter_than_minimum_is_rejected():
    with pytest.raises(ValueError, match="10"):
        sf.validate_series_length([1.0] * 9)
    sf.validate_series_length([1.0] * 10)


def test_error_metrics_skip_zero_actuals_for_mape():
    metrics = sf.error_metrics([0, 10], [5, 12])
    assert metrics["mae"] == pytest.approx(3.5)
    assert metrics["mape"] == pytest.approx(20.0)
    assert metrics["skipped_zero_actuals"] == 1
    assert sf.error_metrics([0, 0], [1, 1])["mape"] is None


def test_train_writes_artifact_and_metadata(datasets_dir, tmp_path):
    import json

    from app.forecast.train import ARTIFACT_NAME, METADATA_NAME, MODEL_VERSION, train

    models_dir = tmp_path / "models"
    metadata = train(datasets_dir, models_dir)

    assert (models_dir / ARTIFACT_NAME).exists()
    on_disk = json.loads((models_dir / METADATA_NAME).read_text(encoding="utf-8"))
    assert on_disk == metadata
    assert metadata["model_version"] == MODEL_VERSION
    assert metadata["n_months"] == 12
    assert metadata["data_range"] == {"start": "2017-01", "end": "2017-12"}
    assert set(metadata["dataset_hashes"]) == {
        "olist_orders_dataset.csv", "olist_order_items_dataset.csv",
    }
    assert isinstance(metadata["evaluation"]["model"]["mae"], float)
    assert metadata["feature_names"] == sf.FEATURE_NAMES
    assert metadata["exclusions"]["orders_without_items"] == 1
