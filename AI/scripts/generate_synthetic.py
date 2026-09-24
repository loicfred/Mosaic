"""Generate the SYNTHETIC SME training panel (reproducible).

Usage:
    python scripts/generate_synthetic.py            # default: 30 businesses per archetype
    python scripts/generate_synthetic.py --per-archetype 10 --seed 7

Outputs (all synthetic, see data/README.md):
    data/synthetic/panel_businesses.csv
    data/synthetic/panel_transactions.csv.gz
    data/synthetic/panel_invoices.csv.gz
    data/synthetic/cash_pressure_panel.csv   # features + 30-day label per as-of date
"""

from __future__ import annotations

import argparse
import time
from datetime import date

import _paths  # noqa: F401
import pandas as pd
from _paths import DATA

from app.analytics.features import FEATURE_NAMES, compute_features, pressure_label
from app.analytics.ledger import build_ledger
from app.synthetic.generator import generate, random_spec
from app.synthetic.profiles import ARCHETYPES

START = date(2023, 1, 1)
END = date(2025, 12, 31)
ASOF_STEP_DAYS = 14
MIN_HISTORY_DAYS = 120


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-archetype", type=int, default=30)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    out_dir = DATA / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    biz_rows, tx_parts, inv_parts, panel_rows = [], [], [], []
    n = 0
    for a_key in ARCHETYPES:
        for _ in range(args.per_archetype):
            key = f"S{n:04d}"
            spec = random_spec(key, a_key, args.seed * 10_000 + n, START, END)
            gen = generate(spec)
            n += 1
            biz_rows.append({
                "business_key": key, "archetype": a_key, "sector": spec.archetype.sector,
                "base_monthly_revenue": round(spec.base_monthly_revenue, 2),
                "opening_cash": round(spec.opening_cash, 2), "b2b_share": round(spec.b2b_share, 3),
                "n_shocks": len(spec.shocks), "data_label": "synthetic",
            })
            tx = gen.transactions.assign(business_key=key)
            inv = gen.invoices.assign(business_key=key)
            tx_parts.append(tx)
            inv_parts.append(inv)

            ledger = build_ledger(gen.transactions, gen.invoices, spec.opening_cash, START, END)
            as_of = pd.Timestamp(START) + pd.Timedelta(days=MIN_HISTORY_DAYS)
            while as_of <= pd.Timestamp(END) - pd.Timedelta(days=30):
                y = pressure_label(ledger, as_of)
                if y is not None:
                    fr = compute_features(ledger, as_of)
                    panel_rows.append({"business_key": key, "archetype": a_key, "as_of": as_of.date(),
                                       **fr.values, "label": y})
                as_of += pd.Timedelta(days=ASOF_STEP_DAYS)
        print(f"  {a_key}: done ({time.time() - t0:.0f}s)")

    pd.DataFrame(biz_rows).to_csv(out_dir / "panel_businesses.csv", index=False)
    pd.concat(tx_parts).to_csv(out_dir / "panel_transactions.csv.gz", index=False, compression="gzip")
    pd.concat(inv_parts).to_csv(out_dir / "panel_invoices.csv.gz", index=False, compression="gzip")
    panel = pd.DataFrame(panel_rows)[["business_key", "archetype", "as_of", *FEATURE_NAMES, "label"]]
    panel.to_csv(out_dir / "cash_pressure_panel.csv", index=False)
    print(f"Generated {n} synthetic businesses, {len(panel)} labelled as-of rows, "
          f"positive rate {panel['label'].mean():.3f} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
