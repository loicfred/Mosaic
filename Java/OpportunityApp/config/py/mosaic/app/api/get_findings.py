"""The findings inbox, the orders behind a finding, its CSV export, and a trend page under a chosen selection."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.analysis import findings, trends
from app.analysis.selection import Selection, selection_params

router = APIRouter(prefix="/api/findings", tags=["findings"])
POPULATION = Query("denominator", pattern="^(denominator|numerator)$")


@router.get("", summary="Every check from the sales and trend pages, ranked, with sales exposed and thresholds")
def all_findings(request: Request, selection: Selection = Depends(selection_params)):
    default = selection.describe() == Selection().describe()
    checks = getattr(request.app.state, "default_findings", None) if default else None
    if checks is None:
        with selection.activate():
            checks = findings.all_checks(selection.filter(request.app.state.orders.frame),
                                         request.app.state.categories, selection.thresholds)
        if default:  # the data never changes after startup, so the default list is computed once
            request.app.state.default_findings = checks
    return {"checks": checks, "triggered": sum(c["triggered"] for c in checks), "ranking_rule": findings.RANKING_RULE,
            "selection": selection.describe(), "dataset_version": findings.dataset_version(request.app.state.dataset_hashes),
            "limitations": [*trends.LIMITATIONS, findings.EXPOSURE_NOTE,
                            "Category falling-behind always uses the whole business and the default windows."]}


@router.get("/trend/{measure}", summary="A trend page's figures and checks under the chosen periods, filters and thresholds")
def selected_trend(request: Request, measure: str, selection: Selection = Depends(selection_params)):
    module = findings.TREND_MEASURES.get(measure)
    if module is None:
        raise HTTPException(404, "Unknown trend page")
    frame = selection.filter(request.app.state.orders.frame)
    with selection.activate():
        body = trends.caveats_body(module, frame)
        body["checks"] = [findings.apply_threshold({**c, "finding_id": f"{measure}:{c['id']}"}, selection.thresholds)
                          for c in body["checks"]]
        body["triggered"] = sum(c["triggered"] for c in body["checks"])
        return {**trends.trend_body(module, frame), **body, "selection": selection.describe()}


@router.get("/{finding_id}/records", summary="The orders a finding's rate was computed from, paginated")
def finding_records(request: Request, finding_id: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                    population: str = POPULATION, selection: Selection = Depends(selection_params)):
    return {**_records(request, finding_id, selection, population, page, page_size), "selection": selection.describe()}


@router.get("/{finding_id}/export", summary="A finding's orders as CSV, with its rule and dataset version on every row")
def finding_export(request: Request, finding_id: str, population: str = POPULATION,
                   selection: Selection = Depends(selection_params)):
    result = _records(request, finding_id, selection, population, None, 0)
    version, summary = findings.dataset_version(request.app.state.dataset_hashes), result["summary"]
    out = io.StringIO()
    fields = ["finding_id", "dataset_version", "rule", "recent_months", "numerator_contribution", *(result["records"][0] if result["records"] else [])]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in result["records"]:
        writer.writerow({"finding_id": finding_id, "dataset_version": version, "rule": summary["rule"],
                         "recent_months": " ".join(summary["recent_months"]),
                         "numerator_contribution": int(row[result["numerator_column"]]), **row})
    name = finding_id.replace(":", "-")
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})


def _records(request, finding_id, selection, population, page, page_size):
    with selection.activate():
        result = findings.records_page(selection.filter(request.app.state.orders.frame), finding_id, population, page, page_size)
    if result is None:
        raise HTTPException(404, "No finding with order-level evidence has this id")
    return result
