"""When customers buy, how each customer state is served, and how orders are rated."""

from typing import Literal

from fastapi import APIRouter, Query, Request

from app.analysis import breakdowns

router = APIRouter(prefix="/api/breakdowns", tags=["breakdowns"])
LIMITS = ["Observed orders with items, not cancelled, January 2017 to August 2018.", "Things that go together are not proof of cause."]


@router.get("/buying-times", summary="Orders and sales by weekday or by hour of the day")
def buying_times(request: Request, by: Literal["weekday", "hour"] = "weekday"):
    return {"by": by, "slots": breakdowns.buying_times(request.app.state.orders.frame, by), "limitations": LIMITS}


@router.get("/customer-states", summary="Orders, sales, late deliveries, delivery days and low reviews per customer state")
def customer_states(request: Request, min_orders: int = Query(30, ge=1)):
    return {"min_orders": min_orders, "states": breakdowns.by_customer_state(request.app.state.orders.frame, min_orders),
            "limitations": LIMITS + ["A rate needs at least min_orders known outcomes, otherwise it is left empty."]}


@router.get("/review-scores", summary="How many orders got each review score, 1 to 5 stars")
def review_scores(request: Request):
    return {"scores": breakdowns.review_scores(request.app.state.orders.frame), "limitations": LIMITS + ["The latest review per order."]}
