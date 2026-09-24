"""Brazil's monthly economic indicators from the Central Bank, as outside context for the business's months."""

from fastapi import APIRouter, Query, Request

from app.data.economy import SERIES, load_economy

router = APIRouter(prefix="/api/context", tags=["context"])


@router.get("/economy", summary="Brazil's inflation, dollar rate, interest rate and unemployment by month (Central Bank data, external context)")
def economy(request: Request, month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    rows = load_economy(request.app.state.datasets_dir)
    body = {
        "source": "Central Bank of Brazil, SGS public API (series " + ", ".join(str(code) for code, _ in SERIES.values()) + ").",
        "series": {column: meaning for column, (_, meaning) in SERIES.items()},
        "limitations": [
            "National figures, not the business's own; a coincidence with its sales is not proof of cause.",
            "Unemployment is a rolling three-month average.",
        ],
    }
    if rows is None:
        return {**body, "available": False, "reason": "not_downloaded: run python -m app.data.economy", "months": []}
    return {**body, "available": True, "months": [r for r in rows if month is None or r["month"] == month]}
