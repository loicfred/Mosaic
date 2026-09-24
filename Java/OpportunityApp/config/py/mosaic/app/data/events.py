"""Dated Brazilian events that can shape online sales or deliveries between January 2017 and August 2018.

External context, not Olist data, from three kinds of source:

- Public holidays come from the Nager.Date public API. ``python -m app.data.events`` downloads them once into
  ``datasets/external/`` (gitignored, like the other external files); without that file they are simply left out.
- Retail dates follow fixed rules (Mother's Day is the second Sunday of May, Black Friday the day after the fourth
  Thursday of November), so they are calculated, not typed in.
- The few one-off disruptions and sport events no public API lists are kept here, each with the page it comes from.

An event in a month says nothing about its effect on sales; that has to be read from the business's own figures,
and things that coincide are not proof of cause.
"""
import calendar
import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from app.config import DATASETS_DIR

YEARS = (2017, 2018)
HOLIDAYS_FILE = "external/brazil_holidays_2017_2018.json"
NAGER_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/BR"
HOLIDAYS_SOURCE = "https://date.nager.at"

ONE_OFF = [
    {"start": "2017-04-28", "end": "2017-04-28", "kind": "disruption", "name": "General strike",
     "note": "Nationwide general strike against labour and pension reforms.",
     "source": "https://en.wikipedia.org/wiki/2017_Brazilian_general_strike"},
    {"start": "2018-05-21", "end": "2018-05-31", "kind": "disruption", "name": "Truckers' strike",
     "note": "Nationwide truck drivers' strike that blocked roads and fuel supply for about ten days.",
     "source": "https://en.wikipedia.org/wiki/2018_Brazil_truck_drivers%27_strike"},
    {"start": "2018-06-14", "end": "2018-07-15", "kind": "sport", "name": "FIFA World Cup",
     "note": "Held in Russia; Brazil played until its quarter-final on 6 July.",
     "source": "https://en.wikipedia.org/wiki/2018_FIFA_World_Cup"},
]


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def retail_dates(year: int) -> list[dict]:
    """Brazil's main gift-buying dates, calculated from their rules."""
    black_friday = _nth_weekday(year, 11, calendar.THURSDAY, 4) + timedelta(days=1)
    rules = [
        (_nth_weekday(year, 5, calendar.SUNDAY, 2), "Mother's Day", "Second Sunday of May; one of Brazil's biggest gift-buying dates."),
        (date(year, 6, 12), "Dia dos Namorados", "Brazil's Valentine's Day, 12 June; a gift-buying date."),
        (_nth_weekday(year, 8, calendar.SUNDAY, 2), "Father's Day", "Second Sunday of August in Brazil; a gift-buying date."),
        (date(year, 10, 12), "Children's Day", "12 October; a toy and gift-buying date."),
        (black_friday, "Black Friday", "Day after the fourth Thursday of November; the largest online sales day in Brazil."),
        (black_friday + timedelta(days=3), "Cyber Monday", "The Monday after Black Friday; an online sales day."),
    ]
    return [{"start": d.isoformat(), "end": d.isoformat(), "kind": "retail", "name": name, "note": note, "source": "calendar rule"}
            for d, name, note in rules]


def load_holidays(datasets_dir: Path = DATASETS_DIR) -> list[dict] | None:
    path = datasets_dir / HOLIDAYS_FILE
    if not path.is_file():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [{"start": r["date"], "end": r["date"], "kind": "holiday", "name": r["name"],
             "note": "National public holiday" if r.get("global", True) else "Regional public holiday",
             "source": HOLIDAYS_SOURCE} for r in rows]


def all_events(datasets_dir: Path = DATASETS_DIR) -> tuple[list[dict], bool]:
    """Every event in date order, and whether the downloaded holidays were included."""
    holidays = load_holidays(datasets_dir)
    events = [*(holidays or []), *(e for y in YEARS for e in retail_dates(y)), *ONE_OFF]
    return sorted(events, key=lambda e: (e["start"], e["name"])), holidays is not None


def events_in(events: list[dict], month: str | None = None) -> list[dict]:
    """The events touching a "YYYY-MM" month, or all of them when no month is given."""
    return list(events) if month is None else [e for e in events if e["start"][:7] <= month <= e["end"][:7]]


def download(datasets_dir: Path = DATASETS_DIR) -> Path:
    rows = []
    for year in YEARS:
        request = urllib.request.Request(NAGER_URL.format(year=year), headers={"User-Agent": "Mosaic-hackathon"})
        with urllib.request.urlopen(request, timeout=60) as response:
            rows += json.load(response)
    path = datasets_dir / HOLIDAYS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def main() -> None:
    path = download()
    print(f"Saved {len(load_holidays())} Brazilian public holidays for {YEARS[0]}-{YEARS[-1]} from {HOLIDAYS_SOURCE} to {path}")


if __name__ == "__main__":
    main()
