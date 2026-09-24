from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.analysis.financial_views import cohorts, freight, payments, model_cards
from app.api.get_financial_views import router


@pytest.fixture
def frame():
    return pd.DataFrame({
        'order_id': ['a', 'b', 'c', 'd'],
        'purchase_ts': pd.to_datetime(['2018-01-01', '2018-01-01', '2018-02-02', '2018-02-03']),
        'order_status': ['delivered', 'delivered', 'delivered', 'canceled'],
        'customer_unique_id': ['x', 'x', 'x', 'y'],
        'total_price': [100., 100., 100., 50.], 'total_freight': [10., 10., 20., 5.],
        'payment_total': [110., 110., 120., 55.], 'installments': [3., 1., 2., 1.],
        'payment_type': ['credit_card', 'boleto', 'credit_card', 'boleto'],
        'category': ['books'] * 4, 'seller_id': ['s'] * 4, 'customer_state': ['SP'] * 4,
        'late': [0., 1., 0., float('nan')], 'low_review': [0., 1., 0., float('nan')],
        'review_score': [5., 1., 5., float('nan')],
        'order_delivered_customer_date': pd.to_datetime(['2018-01-03', '2018-01-04', '2018-02-04', None]),
        'order_estimated_delivery_date': pd.to_datetime(['2018-01-05'] * 2 + ['2018-02-05'] * 2),
    })


def test_payments_do_not_multiply_order_values(frame):
    raw = pd.DataFrame({'order_id': ['a', 'a', 'b'], 'payment_type': ['credit_card', 'voucher', 'boleto'],
                        'payment_value': [100., 10., 110.], 'payment_installments': [3, 1, 1]})
    result = payments(frame, raw)
    january = result['monthly'][0]
    assert january['orders'] == 2
    assert january['sales'] == 200
    assert january['payment_total'] == 220
    assert january['average_installments'] == 2
    assert sum(r['payment_total'] for r in result['payment_mix']) == 220
    assert result['monthly'][1]['cancellation_rate'] == .5


def test_cohorts_require_strictly_later_purchase(frame):
    result = cohorts(frame)
    assert result['rows'][0]['customers'] == 1
    assert result['rows'][0]['returning_customers'] == 1
    assert cohorts(frame.iloc[:2])['rows'][0]['returning_customers'] == 0
    assert result['rows'][0]['incomplete'] is True


def test_freight_excludes_cancelled_and_reports_pp(frame):
    row = freight(frame)['categories'][0]
    assert row['sales'] == 100
    assert row['change_pp'] == pytest.approx(10)
    assert row['relative_change'] == pytest.approx(1)
    assert row['rising'] is True


def test_model_cards_gate_missing_stale_and_bad_evaluation():
    models = {'cashflow_stress': (object(), {'dataset_hashes': {'f': 'old'}, 'evaluation': {'roc_auc': .53}})}
    rows = {r['name']: r for r in model_cards(models, {'f': 'new'})['rows']}
    assert rows['cashflow_stress']['status'] == 'stale'
    assert rows['cashflow_stress']['predictions_available'] is False
    assert rows['sales_forecast']['status'] == 'not_trained'
    assert rows['sales_forecast']['train_command']


def test_routes_empty_unknown_and_success(frame, tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.state.orders = SimpleNamespace(frame=frame, exclusions={})
    app.state.monthly = SimpleNamespace(exclusions={})
    app.state.dataset_hashes = {}
    app.state.models = {}
    app.state.datasets_dir = tmp_path
    client = TestClient(app)
    assert client.get('/api/explore/entities/category/unknown').status_code == 404
    assert client.get('/api/explore/entities/category/books').json()['summary']['sales'] == 300
    assert client.get('/api/explore/quality').json()['summary']['orders'] == 4
    app.state.orders = SimpleNamespace(frame=frame.iloc[:0], exclusions={})
    for path in ['quality', 'payments', 'freight', 'cohorts', 'models', 'entities']:
        assert client.get('/api/explore/' + path).status_code == 200
