"""The trend pages' routes: for each measure, its monthly trend, where its improvement points, and the checks behind it.

The three measures answer in one shape (see ``app.analysis.trends``), so their nine routes are registered from one table.
"""

from types import ModuleType

from fastapi import APIRouter, Query, Request

from app.analysis import trends
from app.analysis.findings import TREND_MEASURES

router = APIRouter(tags=["trends"])

# path -> summary of its trend, opportunities and caveats routes
SUMMARIES = {
    "delivery": (
        "Late-delivery rate by month, the last 3 months against the 3 before",
        "If late deliveries are falling, the customer states where delivery improved most",
        "Checks for hidden problems behind faster delivery, each with the figures behind it",
    ),
    "reviews": (
        "Share of 1 or 2 star reviews by month, the last 3 months against the 3 before",
        "If low reviews are falling, the categories where reviews improved while sales grew",
        "Checks for hidden problems behind better reviews, each with the figures behind it",
    ),
    "sellers": (
        "Active sellers a month, the last 3 months against the 3 before",
        "If the seller base is growing, the categories where new sellers also find more orders",
        "Checks for hidden problems behind a growing seller base, each with the figures behind it",
    ),
}


def _register(path: str, measure: ModuleType, summaries: tuple[str, str, str]) -> None:
    # name= keeps each route's OpenAPI operationId as it was when every route had its own module
    trend_summary, opportunities_summary, caveats_summary = summaries

    @router.get(f"/api/{path}/trend", name=f"{path}_trend", summary=trend_summary)
    def trend(request: Request):
        return trends.trend_body(measure, request.app.state.orders.frame)

    @router.get(f"/api/{path}/opportunities", name=f"{path}_opportunities", summary=opportunities_summary)
    def opportunities(request: Request, limit: int = Query(5, ge=1, le=20)):
        return trends.opportunities_body(measure, request.app.state.orders.frame, limit)

    @router.get(f"/api/{path}/caveats", name=f"{path}_caveats", summary=caveats_summary)
    def caveats(request: Request):
        return trends.caveats_body(measure, request.app.state.orders.frame)


for _path, _measure in TREND_MEASURES.items():
    _register(_path, _measure, SUMMARIES[_path])
