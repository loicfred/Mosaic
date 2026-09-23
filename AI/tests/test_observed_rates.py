"""Keep delivery and review populations consistent at the reporting boundaries."""

import pandas as pd
import pytest

from app.analysis.delivery import monthly_late_rate
from app.analysis.reviews import monthly_low_review_rate


@pytest.mark.parametrize(
    "summarise,label,count_key,total_key,rate_key",
    [
        (monthly_late_rate, "late", "delivered", "late", "late_rate"),
        (monthly_low_review_rate, "low_review", "reviewed", "low", "low_rate"),
    ],
)
def test_monthly_rates_exclude_unknown_outcomes_and_dates(
    summarise, label, count_key, total_key, rate_key,
):
    frame = pd.DataFrame({
        "purchase_ts": pd.to_datetime([
            "2016-12-31", "2017-01-01", "2017-01-20", "2017-01-25",
            "2017-02-28", "2017-03-01", None,
        ]),
        label: [1, 1, 0, None, 0, 1, 1],
    })
    original = frame.copy(deep=True)

    assert summarise(frame, ("2017-01", "2017-02")) == [
        {"month": "2017-01", count_key: 2, total_key: 1, rate_key: 0.5},
        {"month": "2017-02", count_key: 1, total_key: 0, rate_key: 0.0},
    ]
    pd.testing.assert_frame_equal(frame, original)
    assert summarise(frame, ("2018-01", "2018-02")) == []
