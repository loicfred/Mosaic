"""Transaction anomaly features + deterministic duplicate detection.

Shared by ml/train_anomaly.py and the live service so that training and serving
use identical feature definitions. Features only look at *earlier* transactions
(expanding history) so a payment is judged against what was normal before it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ANOMALY_FEATURES = [
    "log_ratio_counterparty_median",
    "log_ratio_category_median",
    "log_ratio_business_median",
    "is_new_counterparty",
    "is_weekend",
]

EXCLUDED_GROUPS = {"financing"}  # owner drawings / loans are discretionary, not "unusual spend"

# Deterministic companion rule: a payment at least RULE_RATIO x the payee's usual
# amount, with enough history to know what "usual" is. Tax and payroll are excluded
# because quarterly VAT and the 13th-month bonus legitimately vary.
RULE_RATIO = 4.0
RULE_MIN_HISTORY = 3
RULE_EXCLUDED_CATEGORIES = {"Taxes (VAT)", "Payroll"}


def _expanding_prior_median(values: pd.Series, keys: pd.Series) -> pd.Series:
    return values.groupby(keys).transform(lambda s: s.shift(1).expanding().median())


def anomaly_features(tx: pd.DataFrame) -> pd.DataFrame:
    """Return one feature row per scorable outflow, indexed like `tx`.

    Expects columns: date, direction, amount, category, counterparty, group.
    """
    out = tx[(tx["direction"] == "outflow") & (~tx["group"].isin(EXCLUDED_GROUPS))].copy()
    if out.empty:
        return pd.DataFrame(columns=[*ANOMALY_FEATURES, "cp_median", "cat_median"])
    out = out.sort_values("date", kind="stable")
    cp = out["counterparty"].fillna("(none) " + out["category"].astype(str))
    amt = out["amount"].astype(float)
    cp_med = _expanding_prior_median(amt, cp)
    cat_med = _expanding_prior_median(amt, out["category"])
    biz_med = amt.shift(1).expanding().median()
    cp_count = cp.groupby(cp).cumcount()

    ref_cat = cat_med.fillna(biz_med).fillna(amt)
    ref_cp = cp_med.fillna(ref_cat)
    feats = pd.DataFrame(index=out.index)
    feats["log_ratio_counterparty_median"] = np.log(amt / ref_cp.clip(lower=1.0))
    feats["log_ratio_category_median"] = np.log(amt / ref_cat.clip(lower=1.0))
    feats["log_ratio_business_median"] = np.log(amt / biz_med.fillna(amt).clip(lower=1.0))
    feats["is_new_counterparty"] = (cp_count == 0).astype(float)
    feats["is_weekend"] = (pd.to_datetime(out["date"]).dt.weekday >= 5).astype(float)
    feats["cp_history"] = cp_count.astype(float)
    feats["cp_median"] = ref_cp
    feats["cat_median"] = ref_cat
    # The first few transactions of a business have no meaningful history.
    warmup = np.arange(len(out)) < 30
    feats.loc[warmup, ANOMALY_FEATURES[:3]] = 0.0
    return feats


def duplicate_groups(tx: pd.DataFrame) -> pd.Series:
    """Deterministic duplicate detector: same date, direction, amount and counterparty
    (or description when counterparty is missing). Returns a group id per row
    (NaN when the row is unique)."""
    key_cp = tx["counterparty"].fillna(tx["description"].astype(str).str.lower().str.strip())
    key = (tx["date"].astype(str) + "|" + tx["direction"].astype(str) + "|" +
           tx["amount"].round(2).astype(str) + "|" + key_cp.astype(str))
    counts = key.map(key.value_counts())
    gid = key.where(counts > 1)
    return gid


def rule_flags(feats: pd.DataFrame, categories: pd.Series) -> pd.Series:
    """Explainable rule: amount >= RULE_RATIO x payee median with >= RULE_MIN_HISTORY prior payments."""
    return ((feats["log_ratio_counterparty_median"] >= np.log(RULE_RATIO))
            & (feats["cp_history"] >= RULE_MIN_HISTORY)
            & (~categories.reindex(feats.index).isin(RULE_EXCLUDED_CATEGORIES)))


# Only large, material payments are worth an owner's review: a MUR 400 petty-cash
# purchase that is "unusual" is noise. Materiality = 1% of average monthly outflows.
MATERIALITY_SHARE = 0.01
LARGER_THAN_USUAL = np.log(1.5)


def materiality(tx: pd.DataFrame) -> float:
    out = tx[tx["direction"] == "outflow"]
    if out.empty:
        return 0.0
    months = max(1.0, (pd.to_datetime(out["date"]).max() - pd.to_datetime(out["date"]).min()).days / 30.44)
    return float(out["amount"].sum()) / months * MATERIALITY_SHARE


def final_flags(feats: pd.DataFrame, model_flag: pd.Series, rule: pd.Series, amounts: pd.Series,
                threshold: float) -> pd.Series:
    """Combine model and rule; keep only material payments that are larger than usual."""
    new_and_large = (feats["is_new_counterparty"] == 1) & (
        (feats["log_ratio_category_median"] >= LARGER_THAN_USUAL)
        | (feats["log_ratio_business_median"] >= np.log(3.0)))
    larger = (feats["log_ratio_counterparty_median"] >= LARGER_THAN_USUAL) | new_and_large
    material = amounts.reindex(feats.index) >= threshold
    return ((model_flag & larger) | rule) & material
