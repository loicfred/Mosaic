from types import SimpleNamespace
import pandas as pd
import pytest
from app.analysis.impact import compute_sales_impact


def scenario(category="books", unknown=False):
    monthly = SimpleNamespace(months=pd.DataFrame({"month": ["2018-06", "2018-07", "2018-08"], "orders": [2, 2, 2], "sales": [40, 40, 40]}))
    frame = pd.DataFrame([{"purchase_period": month, "category": cat, "total_price": price, "order_status": "delivered", "seller_id": cat, "late": None if unknown else late, "low_review": None if unknown else late} for month in monthly.months.month for cat, price, late in [("books", 10.05, 0.), ("toys", 29.95, 1.)]])
    return compute_sales_impact(monthly, frame, 3, 10, category=category)


def test_category_uses_selected_orders_and_money_rounding():
    result = scenario()
    assert result["baseline"]["monthly_orders"] == 1
    assert result["baseline"]["monthly_sales"] == 10.05
    assert result["consequences"]["projected_monthly_sales"] == 11.06
    assert result["consequences"]["projected_monthly_orders"] == pytest.approx(1.1)
    assert result["available_categories"] == ["books", "toys"]


def test_unknown_outcomes_remain_unavailable():
    result = scenario(unknown=True)
    assert result["consequences"]["late"]["rate_held"] is None
    assert result["baseline"]["monthly_late_orders"] is None


def test_unknown_category_is_rejected():
    with pytest.raises(ValueError, match="category"):
        scenario("missing")

def test_route_rejects_unknown_category_and_nonfinite_change():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.get_sales_impact import router
    app = FastAPI()
    app.include_router(router)
    app.state.orders = SimpleNamespace(frame=pd.DataFrame({"category": ["books"]}))
    with TestClient(app) as client:
        assert client.post("/api/scenarios/sales-impact", json={"category": "missing"}).status_code == 422
        assert client.post("/api/scenarios/sales-impact", json={"sales_change_pct": "NaN"}).status_code == 422
