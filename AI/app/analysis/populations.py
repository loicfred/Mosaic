"""Shared eligibility rules for observed order outcomes."""

import pandas as pd


def labelled_orders_in_range(
    frame: pd.DataFrame, label: str, data_range: tuple[str, str],
) -> pd.DataFrame:
    """Select known outcomes in an inclusive purchase-month range without changing the source."""
    month = frame["purchase_ts"].dt.strftime("%Y-%m")
    start, end = data_range
    eligible = frame[label].notna() & month.between(start, end)
    # An unfiltered month Series would repopulate an empty result through index alignment.
    return frame.loc[eligible].assign(month=month.loc[eligible])
