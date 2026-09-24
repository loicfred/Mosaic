import csv
import json

from fastapi.testclient import TestClient

from app.data.economy import ECONOMY_FILE, SERIES
from app.data.events import HOLIDAYS_FILE, all_events, events_in, retail_dates
from app.main import create_app


def test_retail_dates_follow_their_rules():
    dates = {e["name"]: e["start"] for e in retail_dates(2017)}
    assert dates["Mother's Day"] == "2017-05-14"  # second Sunday of May
    assert dates["Father's Day"] == "2017-08-13"  # second Sunday of August
    assert dates["Black Friday"] == "2017-11-24" and dates["Cyber Monday"] == "2017-11-27"
    assert {e["name"]: e["start"] for e in retail_dates(2018)}["Mother's Day"] == "2018-05-13"


def test_events_are_found_by_every_month_they_touch_without_the_holiday_download(tmp_path):
    every, with_holidays = all_events(tmp_path)
    assert with_holidays is False
    assert [e["name"] for e in events_in(every, "2017-11")] == ["Black Friday", "Cyber Monday"]
    assert "FIFA World Cup" in [e["name"] for e in events_in(every, "2018-07")]  # 14 June to 15 July 2018
    assert events_in(every, "2019-01") == []


def test_downloaded_holidays_are_merged_in_date_order(tmp_path):
    path = tmp_path / HOLIDAYS_FILE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"date": "2017-11-15", "name": "Republic Proclamation Day", "global": True}]), encoding="utf-8")
    every, with_holidays = all_events(tmp_path)
    november = events_in(every, "2017-11")
    assert with_holidays is True
    assert [(e["name"], e["kind"]) for e in november] == [
        ("Republic Proclamation Day", "holiday"), ("Black Friday", "retail"), ("Cyber Monday", "retail")]
    assert november[0]["source"] == "https://date.nager.at"


def test_events_route_filters_by_month(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        may = client.get("/api/context/events?month=2018-05").json()
        assert "Truckers' strike" in [e["name"] for e in may["events"]]
        assert may["holidays_included"] is False and any("app.data.events" in l for l in may["limitations"])


def test_economy_is_unavailable_until_downloaded_then_filtered_by_month(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        missing = client.get("/api/context/economy").json()
        assert missing["available"] is False and missing["months"] == []
        path = datasets_dir / ECONOMY_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["month", *SERIES])
            writer.writeheader()
            writer.writerow({"month": "2018-05", "inflation_ipca_pct": 0.4, "usd_brl": 3.6, "selic_month_pct": 0.52,
                             "selic_target_pct": 6.5, "unemployment_pct": ""})
            writer.writerow({"month": "2018-06", "inflation_ipca_pct": 1.26, "usd_brl": 3.77, "selic_month_pct": 0.52,
                             "selic_target_pct": 6.5, "unemployment_pct": 12.4})
        body = client.get("/api/context/economy?month=2018-05").json()
    assert body["available"] is True
    assert body["months"] == [{"month": "2018-05", "inflation_ipca_pct": 0.4, "usd_brl": 3.6, "selic_month_pct": 0.52,
                               "selic_target_pct": 6.5, "unemployment_pct": None}]  # a missing value stays missing, never 0
