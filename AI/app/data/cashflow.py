"""Load the small-business cash-flow snapshot table and add the columns the model needs.

Each row is one business's one month; ``record_id`` is a row id, not a business id, so rows
cannot be linked across months into a single business's history. There is no join here and
nothing to double count.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import CASHFLOW_FILE

COLUMNS = [
    "record_id", "sector", "employees", "month", "revenue_usd", "opex_usd",
    "accounts_receivable_days", "inventory_days", "loan_balance_usd",
    "owner_injections_usd", "cashflow_stress_next_month",
]


def load_cashflow(datasets_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        datasets_dir / CASHFLOW_FILE,
        usecols=COLUMNS,
        dtype={"record_id": str, "sector": str, "month": str},
    )
    frame["calendar_month"] = frame["month"].str.slice(5, 7).astype(int)
    frame["operating_margin"] = np.where(
        frame["revenue_usd"] > 0, (frame["revenue_usd"] - frame["opex_usd"]) / frame["revenue_usd"], np.nan
    )
    return frame
