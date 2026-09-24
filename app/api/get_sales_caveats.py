"""Hidden problems behind the sales result: falling categories, worsening delivery and reviews."""

from fastapi import APIRouter, Request

from app.analysis import caveats, delivery, reviews

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/caveats", summary="Checks for hidden problems behind the sales result, each with the figures behind it")
def sales_caveats(request: Request):
    frame = request.app.state.orders.frame
    late = caveats.window_rate(delivery.monthly_late_rate(frame), "late", "delivered")
    low = caveats.window_rate(reviews.monthly_low_review_rate(frame), "low", "reviewed")
    checks = [
        caveats.falling_behind(request.app.state.categories),
        caveats.rate_rising("late_rate_rising", "Late deliveries are becoming more common", late),
        caveats.rate_rising("low_reviews_rising", "Low reviews are becoming more common", low),
        caveats.late_orders_hurt_reviews(reviews.low_review_by_lateness(frame)),
    ]
    return {
        "checks": checks,
        "triggered": sum(check["triggered"] for check in checks),
        "limitations": [
            "A caveat says where to look, not why it happened; things that move together are not proof of cause.",
            "The most recent months can still have orders on their way, so their delivery and review rates may change.",
        ],
    }
