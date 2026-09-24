"""Hidden problems behind the sales result: falling categories, worsening delivery and reviews."""

from fastapi import APIRouter, Request

from app.analysis import caveats

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/caveats", summary="Checks for hidden problems behind the sales result, each with the figures behind it")
def sales_caveats(request: Request):
    checks = caveats.sales_checks(request.app.state.orders.frame, request.app.state.categories)
    return {
        "checks": checks,
        "triggered": sum(check["triggered"] for check in checks),
        "limitations": [
            "A caveat says where to look, not why it happened; things that move together are not proof of cause.",
            "The most recent months can still have orders on their way, so their delivery and review rates may change.",
            "Instalments show how customers paid, not when the sellers received the money.",
            "A returning customer placed an earlier order in this data; purchases elsewhere are not visible.",
        ],
    }
