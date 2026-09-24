"""Shared eligibility rules for observed order outcomes."""

import pandas as pd

from app.config import DATA_RANGE
from app.data.records import records


def labelled_orders_in_range(
    frame: pd.DataFrame, label: str, data_range: tuple[str, str],
) -> pd.DataFrame:
    """Select known outcomes in an inclusive purchase-month range without changing the source."""
    month = purchase_month(frame)
    start, end = data_range
    eligible = frame[label].notna() & month.between(start, end)
    # An unfiltered month Series would repopulate an empty result through index alignment.
    return frame.loc[eligible].assign(month=month.loc[eligible])


def monthly_rate(frame: pd.DataFrame, label: str, total: str, count: str,
                 data_range: tuple[str, str] = DATA_RANGE) -> list[dict]:
    """Per purchase month: orders with a known `label` (`total`), those where it is 1 (`count`) and `<count>_rate`."""
    labelled = labelled_orders_in_range(frame, label, data_range)
    monthly = labelled.groupby("month").agg(**{total: (label, "size"), count: (label, "sum")}).reset_index()
    monthly[count] = monthly[count].astype(int)
    monthly[f"{count}_rate"] = monthly[count] / monthly[total]
    return records(monthly)


def purchase_month(frame: pd.DataFrame) -> pd.Series:
    """The "YYYY-MM" purchase month: the label built once at load time, or formatted here for a frame without it."""
    return frame["purchase_period"] if "purchase_period" in frame else frame["purchase_ts"].dt.strftime("%Y-%m")
