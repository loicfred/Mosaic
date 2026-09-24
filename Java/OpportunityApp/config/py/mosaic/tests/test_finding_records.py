import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir, tmp_path / 'models')) as client:
        yield client


def test_findings_records_paginate_exact_rate_population(client):
    response = client.get('/api/findings/sales:late_rate_rising/records', params={'page_size': 2})
    assert response.status_code == 200
    body = response.json()
    assert body['summary']['denominator_orders'] == 6
    assert body['summary']['numerator_orders'] == 2
    assert body['summary']['value'] == pytest.approx(2 / 6)
    assert body['total'] == 6
    pages = [client.get('/api/findings/sales:late_rate_rising/records', params={'page_size': 2, 'page': p}).json() for p in range(1, 4)]
    ids = [r['order_id'] for p in pages for r in p['records']]
    assert len(ids) == len(set(ids)) == 6
    numerator = client.get('/api/findings/sales:late_rate_rising/records', params={'population': 'numerator'}).json()
    assert numerator['total'] == 2
    assert all(r['late'] == 1 for r in numerator['records'])


def test_records_empty_unknown_invalid_and_export(client):
    assert client.get('/api/findings/no-such-finding/records').status_code == 404
    assert client.get('/api/findings/sales:late_rate_rising/records?page=0').status_code == 422
    assert client.get('/api/findings?recent_start=2017-13').status_code == 422
    empty = client.get('/api/findings/sales:late_rate_rising/records?category=absent').json()
    assert empty['total'] == 0 and empty['summary']['value'] is None
    export = client.get('/api/findings/sales:late_rate_rising/export')
    assert export.status_code == 200
    rows = list(csv.DictReader(io.StringIO(export.text)))
    assert len(rows) == 6
    assert sum(float(r['numerator_contribution']) for r in rows) == 2
    assert len({r['dataset_version'] for r in rows}) == 1


def test_periods_filters_and_thresholds_do_not_leak(client):
    params = dict(recent_start='2017-02', recent_end='2017-02', previous_start='2017-01', previous_end='2017-01', customer_state='RJ')
    r = client.get('/api/findings/sales:late_rate_rising/records', params=params).json()
    assert r['summary']['denominator_orders'] == 1
    assert r['summary']['value'] == 1
    assert r['records'][0]['order_id'] == '2017-02-b'
    assert client.get('/api/findings', params={**params, 'thresholds': '{"late_rate_rising":101}'}).status_code == 422
    raised = client.get('/api/findings', params={'thresholds': '{"late_rate_rising":100}'}).json()
    assert not next(c for c in raised['checks'] if c['finding_id'] == 'sales:late_rate_rising')['triggered']
    assert client.get('/api/findings/sales:late_rate_rising/records').json()['summary']['denominator_orders'] == 6


def test_default_trend_findings_match_existing_checks(client):
    checks = client.get('/api/findings').json()['checks']
    for measure in ('delivery', 'reviews', 'sellers'):
        original = client.get(f'/api/{measure}/caveats').json()['checks']
        for c in original:
            found = next(f for f in checks if f['finding_id'] == f"{measure}:{c['id']}")
            assert found['triggered'] == c['triggered']
            if 'comparison' in c:
                assert found['comparison'] == c['comparison']


def test_empty_filter_unknown_page_and_exposure(client):
    empty = client.get('/api/findings', params={'category': 'absent'})
    assert empty.status_code == 200 and empty.json()['triggered'] == 0
    assert client.get('/api/findings/trend/delivery', params={'category': 'absent'}).status_code == 200
    assert client.get('/api/findings/trend/nothing').status_code == 404
    late = next(c for c in client.get('/api/findings').json()['checks'] if c['finding_id'] == 'sales:late_rate_rising')
    # the two late orders in the last 3 months (2017-10-b and 2017-12-b) are 200 each
    assert late['exposure']['sales'] == 400.0 and late['exposure']['orders'] == 2
    assert late['threshold'] == {'value': 1.0, 'unit': 'pp'} and late['records_available']
    assert late['size']['unit'] == 'pp' and late['size']['value'] == pytest.approx((2 / 6 - 1 / 6) * 100)
