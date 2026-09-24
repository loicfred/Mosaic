from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analytics.ledger import build_ledger
from app.analytics.metrics import summarise
from app.analytics.projection import Assumptions, build_drivers, project, simulate
from app.synthetic.demo import DEMO_END, DEMO_START, coastal_spec
from app.synthetic.generator import generate


@pytest.fixture(scope="module")
def demo_ledger():
    spec = coastal_spec()
    g = generate(spec)
    return build_ledger(g.transactions, g.invoices, spec.opening_cash, DEMO_START, DEMO_END)


def test_metrics_on_hand_made_ledger() -> None:
    tx = pd.DataFrame([
        {"date": "2026-01-01", "direction": "inflow", "amount": 1000.0, "category": "Sales"},
        {"date": "2026-01-02", "direction": "outflow", "amount": 400.0, "category": "Inventory & supplies"},
        {"date": "2026-01-03", "direction": "outflow", "amount": 100.0, "category": "Rent"},
        {"date": "2026-01-04", "direction": "outflow", "amount": 50.0, "category": "Owner drawings"},
    ])
    L = build_ledger(tx, None, 500.0, pd.Timestamp("2026-01-01"))
    s = summarise(L.tx)
    assert s["revenue"] == 1000 and s["cost_of_goods"] == 400 and s["operating_expenses"] == 100
    assert s["gross_margin_pct"] == pytest.approx(60.0)
    assert s["net_cash_flow"] == 450
    assert L.cash_at(pd.Timestamp("2026-01-04")) == pytest.approx(950)


def test_scenario_is_pure_and_consistent(demo_ledger) -> None:
    before = demo_ledger.tx.copy()
    drv = build_drivers(demo_ledger)
    base = project(drv)
    r = simulate(drv, Assumptions(supplier_cost_pct=-10))
    # Supplier outflows fall by exactly 10%; nothing else changes except VAT on the smaller purchases.
    sup = next(b for b in r["breakdown"] if b["driver"] == "suppliers")
    assert sup["scenario"] == pytest.approx(sup["baseline"] * 0.9, rel=1e-6)
    assert r["difference"]["cash_day_90"] > 0
    assert r["baseline"]["cash_day_90"] == pytest.approx(float(base["cash"].iloc[-1]), abs=0.01)
    pd.testing.assert_frame_equal(before, demo_ledger.tx)  # historical records untouched


def test_faster_collections_improve_cash(demo_ledger) -> None:
    drv = build_drivers(demo_ledger)
    r = simulate(drv, Assumptions(collection_days_change=-15))
    assert r["difference"]["lowest_cash"] > 0


def test_simulate_endpoint_does_not_write(client: TestClient, owner: dict) -> None:
    before = client.get("/api/v1/transactions?page_size=1", headers=owner).json()["total"]
    r = client.post("/api/v1/scenarios/simulate", json={"assumptions": {"supplier_cost_pct": -10,
                                                                        "collection_days_change": -10}},
                    headers=owner)
    assert r.status_code == 200 and r.json()["label"].startswith("SIMULATED")
    assert client.get("/api/v1/transactions?page_size=1", headers=owner).json()["total"] == before
    bad = client.post("/api/v1/scenarios/simulate", json={"assumptions": {"supplier_cost_pct": -90}}, headers=owner)
    assert bad.status_code == 422


def test_cash_pressure_prediction_is_explained(client: TestClient, owner: dict) -> None:
    r = client.get("/api/v1/ml/cash-pressure", headers=owner).json()
    p = r["prediction"]
    assert p["mode"] == "model" and p["band"] in {"LOW", "MODERATE", "HIGH"}
    assert 0 <= p["probability"] <= 1 and len(p["contributions"]) == 16
    assert all({"label", "display", "contribution"} <= set(c) for c in p["contributions"])


def test_model_cards_report_real_metrics(client: TestClient, owner: dict) -> None:
    m = client.get("/api/v1/ml/models", headers=owner).json()
    cp = m["cash_pressure"]["metadata"]
    assert m["cash_pressure"]["status"] == "loaded"
    assert 0.5 < cp["test"]["roc_auc"] <= 1 and "baseline_test" in cp and "calibration_bins" in cp["test"]
    assert m["provided_dataset_benchmark"]["models"]["logistic_regression"]["roc_auc_mean"] < 0.7


def test_engine_finds_the_demo_story(client: TestClient, owner: dict) -> None:
    opps = client.get("/api/v1/opportunities", headers=owner).json()
    detectors = {o["detector"] for o in opps}
    assert {"cash_pressure", "supplier_cost_inflation", "slow_collections", "recurring_cost_creep",
            "unusual_transactions", "growth_product_line", "overlapping_subscriptions"} <= detectors
    for o in opps:
        assert o["evidence"] and o["explanation"] and o["provenance"]["engine_version"]
        assert 0 <= o["confidence"] <= 1
        assert o["impact_basis"] if o["impact_high"] is not None else True
    done = next(o for o in opps if o["detector"] == "overlapping_subscriptions")
    assert done["status"] == "completed" and done["outcome"]["status"] == "achieved"


def test_opportunity_lifecycle(client: TestClient, accountant: dict) -> None:
    opp = next(o for o in client.get("/api/v1/opportunities", headers=accountant).json()
               if o["detector"] == "supplier_cost_inflation")
    assert client.patch(f"/api/v1/opportunities/{opp['id']}/status", json={"status": "completed"},
                        headers=accountant).status_code == 409
    for s in ("reviewed", "planned", "in_progress"):
        r = client.patch(f"/api/v1/opportunities/{opp['id']}/status", json={"status": s, "note": f"-> {s}"},
                         headers=accountant)
        assert r.status_code == 200
    d = client.get(f"/api/v1/opportunities/{opp['id']}", headers=accountant).json()
    assert d["action_started_at"] and d["outcome"]["status"] == "too_early"
    assert [e["to"] for e in d["events"] if e["type"] == "status_change"][-3:] == ["reviewed", "planned", "in_progress"]


def test_anomaly_and_duplicate_are_flagged(client: TestClient, owner: dict) -> None:
    flagged = client.get("/api/v1/transactions?flag=anomaly&page_size=50", headers=owner).json()["items"]
    assert any(t["amount"] == 48500.0 for t in flagged)
    dups = client.get("/api/v1/transactions?flag=duplicate", headers=owner).json()["items"]
    assert len(dups) >= 2
