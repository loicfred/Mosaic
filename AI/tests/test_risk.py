import json

import numpy as np
import pandas as pd
import pytest

from app.data.orders import build_order_features
from app.models import risk
from app.models.train_risk import train_all
from tests.conftest import write_fixture_csvs

FIXTURE_SPLIT = "2017-10-01"


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory):
    directory = tmp_path_factory.mktemp("datasets")
    write_fixture_csvs(directory)
    return directory


@pytest.fixture(scope="module")
def frame(fixture_dir):
    return build_order_features(fixture_dir).frame


def test_temporal_split_keeps_test_after_split_and_inside_test_window(frame):
    population = risk.MODEL_SPECS["late_delivery"].population(frame)
    train, test = risk.temporal_split(population, FIXTURE_SPLIT, "2018-09-01")
    assert (train["purchase_ts"] < pd.Timestamp(FIXTURE_SPLIT)).all()
    assert (test["purchase_ts"] >= pd.Timestamp(FIXTURE_SPLIT)).all()
    assert len(test) == 6  # Oct-Dec a and b orders
    assert len(train) + len(test) == len(population)


def test_population_only_keeps_rows_with_a_label(frame):
    late = risk.MODEL_SPECS["late_delivery"].population(frame)
    review = risk.MODEL_SPECS["low_review"].population(frame)
    assert late["late"].notna().all() and "open-1" not in late["order_id"].values
    assert review["low_review"].notna().all() and "2017-05-b" not in review["order_id"].values


def test_fit_evaluate_and_predict(frame):
    spec = risk.MODEL_SPECS["late_delivery"]
    train, test = risk.temporal_split(spec.population(frame), FIXTURE_SPLIT, "2018-09-01")
    model = risk.fit(spec, train)
    evaluation = risk.evaluate(model, spec, test)
    assert evaluation["n_train"] == len(train) and evaluation["n_test"] == 6
    assert evaluation["n_positive_test"] == 2
    assert 0.0 <= evaluation["roc_auc"] <= 1.0
    assert 0.0 <= evaluation["average_precision"] <= 1.0
    assert evaluation["base_rate"] == pytest.approx(2 / 6)
    assert set(evaluation["top_10pct"]) == {"threshold", "flagged", "precision", "recall"}
    probabilities = risk.predict_risk(model, spec, frame)
    assert probabilities.shape == (len(frame),)
    assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_unknown_category_at_prediction_time_does_not_crash(frame):
    spec = risk.MODEL_SPECS["late_delivery"]
    train, _ = risk.temporal_split(spec.population(frame), FIXTURE_SPLIT, "2018-09-01")
    model = risk.fit(spec, train)
    unseen = frame.head(3).copy()
    unseen["category"] = "never_seen_before"
    unseen["seller_state"] = "ZZ"
    assert risk.predict_risk(model, spec, unseen).shape == (3,)


def test_evaluate_with_single_class_test_reports_none_for_rank_metrics(frame):
    spec = risk.MODEL_SPECS["late_delivery"]
    train, test = risk.temporal_split(spec.population(frame), FIXTURE_SPLIT, "2018-09-01")
    model = risk.fit(spec, train)
    evaluation = risk.evaluate(model, spec, test[test["late"] == 0])
    assert evaluation["roc_auc"] is None and evaluation["average_precision"] is None


def test_train_all_writes_both_artifacts(fixture_dir, tmp_path):
    models_dir = tmp_path / "models"
    metadata = train_all(fixture_dir, models_dir, split_date=FIXTURE_SPLIT)
    assert set(metadata) == {"late_delivery", "low_review"}
    for name, meta in metadata.items():
        assert (models_dir / f"{name}.joblib").exists()
        assert json.loads((models_dir / f"{name}.json").read_text(encoding="utf-8")) == meta
        assert meta["split_date"] == FIXTURE_SPLIT
        assert len(meta["dataset_hashes"]) == 8
        assert isinstance(meta["evaluation"]["roc_auc"], float)
        assert meta["limitations"]
    assert metadata["low_review"]["prediction_time"] == "after_delivery"
    assert "days_late" in metadata["low_review"]["feature_names"]
    assert "days_late" not in metadata["late_delivery"]["feature_names"]
