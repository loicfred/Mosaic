"""Read-only observed financial views and saved model evaluations."""
import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from app.analysis import financial_views as views
from app.data.loaders import load_payments

router = APIRouter(prefix='/api/explore')


@router.get('/quality', summary='Dataset coverage, exclusions and checksums')
def quality(request: Request) -> dict:
    return views.quality(request.app.state)


@router.get('/payments', summary='Customer payment mix and order value by month')
def payments(request: Request) -> dict:
    try:
        raw = load_payments(request.app.state.datasets_dir)
    except FileNotFoundError:
        raw = pd.DataFrame(columns=['order_id', 'payment_type', 'payment_value'])
    result = views.payments(request.app.state.orders.frame, raw)
    result['payment_rows_available'] = not raw.empty
    return result


@router.get('/freight', summary='Freight share by month, category and customer state')
def freight(request: Request) -> dict:
    return views.freight(request.app.state.orders.frame)


@router.get('/cohorts', summary='Observed returning customers by first purchase month')
def cohorts(request: Request) -> dict:
    return views.cohorts(request.app.state.orders.frame)


@router.get('/models', summary='Saved model evaluations, baselines and availability')
def models(request: Request) -> dict:
    return views.model_cards(request.app.state.models, request.app.state.dataset_hashes)


@router.get('/entities', summary='Categories and sellers available for inspection')
def entities(request: Request) -> dict:
    return views.entities(request.app.state.orders.frame)


@router.get('/entities/{kind}/{name}', summary='Observed category or seller outcomes against the business')
def entity_detail(request: Request, kind: str, name: str) -> dict:
    result = views.entity_detail(request.app.state.orders.frame, kind, name)
    if result is None:
        raise HTTPException(404, 'Unknown category or seller')
    return result
