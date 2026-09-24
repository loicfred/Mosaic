"""Reproduce every model artefact from scratch.

    python scripts/train_all.py            # uses the committed synthetic panel
    python scripts/train_all.py --regenerate   # also regenerates the synthetic panel (~5 min)
"""

from __future__ import annotations

import subprocess
import sys

from _paths import DATA, ROOT


def run(*args: str) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)  # noqa: S603 - fixed local scripts


def main() -> None:
    if "--regenerate" in sys.argv or not (DATA / "synthetic" / "cash_pressure_panel.csv").exists():
        run("scripts/generate_synthetic.py")
    run("ml/train_cash_pressure.py")
    run("ml/train_anomaly.py")
    run("ml/train_categoriser.py")
    run("ml/benchmark_provided_csv.py")
    print("All models trained. Artefacts and evaluation reports are in models/.")


if __name__ == "__main__":
    main()
