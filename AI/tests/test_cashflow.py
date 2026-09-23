import json

import numpy as np
import pytest

from app.data.cashflow import load_cashflow
from app.models import cashflow as cf
from app.models.train_cashflow import train
from tests.conftest import CASHFLOW_MONTHS, CASHFLOW_SPLIT_MONTH, CASHFLOW_TEST_END, CASHFLOW_ZERO_REVENUE_ID, CASHFLOW_ROWS_PER_MONTH


@pytest.fixture
def frame(datasets_dir):
    return load_cashflow(datasets_dir)


def test_load_cashflow_adds_calendar_month_and_handles_zero_revenue(frame):
    zero_row = frame[frame["record_id"] == CASHFLOW_ZERO_REVENUE_ID].iloc[0]
    assert zero_row["revenue_usd"] == 0.0
    assert np.isnan(zero_row["operating_margin"])
    june_a = frame[(frame["month"] == "2024-06")].iloc[0]
    assert june_a["calendar_month"] == 6


def test_temporal_split_keeps_test_to_the_split_month_only(frame):
    train_rows, test_rows = cf.temporal_split(frame, CASHFLOW_SPLIT_MONTH, CASHFLOW_TEST_END)
    assert (train_rows["month"] < CASHFLOW_SPLIT_MONTH).all()
    assert (test_rows["month"] == CASHFLOW_SPLIT_MONTH).all()
    assert len(train_rows) + len(test_rows) == len(frame)
    assert len(test_rows) == CASHFLOW_ROWS_PER_MONTH  # June only


def test_fit_evaluate_and_predict(frame):
    train_rows, test_rows = cf.temporal_split(frame, CASHFLOW_SPLIT_MONTH, CASHFLOW_TEST_END)
    model = cf.fit(train_rows)
    evaluation = cf.evaluate(model, test_rows)
    assert evaluation["n_train"] == len(train_rows)
    assert evaluation["n_test"] == CASHFLOW_ROWS_PER_MONTH
    assert evaluation["n_positive_test"] == CASHFLOW_ROWS_PER_MONTH // 2
    assert evaluation["base_rate"] == pytest.approx(0.5)
    assert cf.beats_baseline(evaluation)  # the fixture separates stressed rows cleanly
    assert 0.0 <= evaluation["average_precision"] <= 1.0
    assert set(evaluation["top_10pct"]) == {"threshold", "flagged", "precision", "recall"}
    scores = cf.predict_risk(model, frame)
    assert scores.shape == (len(frame),)
    assert np.all((scores >= 0) & (scores <= 1))


def test_unknown_sector_at_prediction_time_does_not_crash(frame):
    train_rows, _ = cf.temporal_split(frame, CASHFLOW_SPLIT_MONTH, CASHFLOW_TEST_END)
    model = cf.fit(train_rows)
    unseen = frame.head(3).copy()
    unseen["sector"] = "never_seen_before"
    assert cf.predict_risk(model, unseen).shape == (3,)


def test_train_writes_artifact_with_reproducibility_metadata(datasets_dir, tmp_path):
    models_dir = tmp_path / "models"
    metadata = train(datasets_dir, models_dir, split_month=CASHFLOW_SPLIT_MONTH)
    assert (models_dir / "cashflow_stress.joblib").exists()
    assert json.loads((models_dir / "cashflow_stress.json").read_text(encoding="utf-8")) == metadata
    assert metadata["split_date"] == CASHFLOW_SPLIT_MONTH
    assert metadata["test_end"] == CASHFLOW_TEST_END
    assert metadata["prediction_time"] == "at_snapshot"
    assert isinstance(metadata["evaluation"]["roc_auc"], float)
    assert metadata["limitations"]
    assert set(metadata["dataset_hashes"]) == {"small_business_cashflow.csv"}


def test_beats_baseline_rejects_near_chance_and_single_class_evaluations():
    assert not cf.beats_baseline({"roc_auc": 0.53})
    assert not cf.beats_baseline({"roc_auc": None})
    assert cf.beats_baseline({"roc_auc": cf.MIN_ROC_AUC})
