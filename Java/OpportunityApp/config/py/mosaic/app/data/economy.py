"""Brazil's monthly economic indicators for the months the Olist data covers, from the Central Bank of Brazil.

External context, not Olist data. ``python -m app.data.economy`` downloads the series once from the Central Bank's
public SGS API into ``datasets/external/`` (gitignored, like the other external files); the API only reads that
file and answers "not available" without it. A coincidence between these figures and the business's is not proof
of cause.
"""
import csv
import json
import urllib.request
from pathlib import Path

from app.config import DATASETS_DIR

ECONOMY_FILE = "external/brazil_economy_2017_2018.csv"
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial=01/01/2017&dataFinal=31/08/2018"
# column -> (SGS series code, meaning); the Selic target is daily, so its month holds the last value set that month
SERIES = {
    "inflation_ipca_pct": (433, "Consumer price inflation (IPCA) in the month, %"),
    "usd_brl": (3698, "US dollar in reais, monthly average selling rate"),
    "selic_month_pct": (4390, "Selic interest rate accumulated in the month, %"),
    "selic_target_pct": (432, "Selic target rate set by the Central Bank at the end of the month, % a year"),
    "unemployment_pct": (24369, "Unemployment rate (IBGE PNAD Contínua, rolling quarter ending in the month), %"),
}


def load_economy(datasets_dir: Path = DATASETS_DIR) -> list[dict] | None:
    """The monthly rows with numbers as floats, or None when the file was never downloaded."""
    path = datasets_dir / ECONOMY_FILE
    if not path.is_file():
        return None
    with open(path, encoding="utf-8", newline="") as f:
        return [{k: (v if k == "month" else (float(v) if v else None)) for k, v in row.items()} for row in csv.DictReader(f)]


def _fetch(code: int) -> dict[str, float]:
    with urllib.request.urlopen(SGS_URL.format(code=code), timeout=60) as response:
        rows = json.load(response)
    by_month = {}
    for row in rows:  # dates are dd/mm/yyyy, oldest first, so a daily series keeps each month's last value
        day, month, year = row["data"].split("/")
        by_month[f"{year}-{month}"] = float(row["valor"])
    return by_month


def download(datasets_dir: Path = DATASETS_DIR) -> Path:
    fetched = {column: _fetch(code) for column, (code, _) in SERIES.items()}
    months = sorted(set().union(*fetched.values()))
    path = datasets_dir / ECONOMY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["month", *SERIES])
        writer.writeheader()
        for month in months:
            writer.writerow({"month": month, **{c: fetched[c].get(month, "") for c in SERIES}})
    return path


def main() -> None:
    path = download()
    print(f"Saved {len(load_economy())} months of {len(SERIES)} Central Bank series to {path}")


if __name__ == "__main__":
    main()
