"""Brazilian public holidays, retail dates, disruptions and sport events as outside context for a month."""

from fastapi import APIRouter, Query, Request

from app.data.events import all_events, events_in

router = APIRouter(prefix="/api/context", tags=["context"])


@router.get("/events", summary="Brazilian holidays, retail dates, disruptions and sport events in a month (external context, not Olist data)")
def events(request: Request, month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    every, with_holidays = all_events(request.app.state.datasets_dir)
    return {
        "sources": {"holiday": "Nager.Date public API (https://date.nager.at)", "retail": "calendar rules",
                    "disruption": "linked page per event", "sport": "linked page per event"},
        "holidays_included": with_holidays,
        "month": month,
        "events": events_in(every, month),
        "limitations": [
            "An event in a month says nothing about its effect; read the effect from the business's own figures.",
            "Things that happen at the same time are not proof of cause.",
        ] + ([] if with_holidays else ["Public holidays are not downloaded yet: run python -m app.data.events."]),
    }
