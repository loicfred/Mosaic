"""Opportunity Engine: turns verified metrics into evidence-backed findings.

Each detector:
  1. computes its facts with the deterministic analytics engine,
  2. decides whether a threshold is crossed,
  3. quantifies impact with an explicit, stated basis,
  4. scores confidence from evidence strength, history coverage, data quality
     and consistency (see `confidence`),
  5. writes the narrative ONLY from the numbers it computed, so explanations
     cannot contradict the calculations,
  6. names a target metric so the outcome can be measured after action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.ledger import Ledger
from app.analytics.metrics import complete_month_windows, product_line_performance
from app.analytics.patterns import collections, concentration, recurring_streams
from app.core.formatting import date_label, days, mur, pct, pp
from app.opportunities.targets import TARGETS, compute_target

ENGINE_VERSION = "opportunity-engine-1.0"
SEVERITY_WEIGHT = {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0}


@dataclass
class EngineContext:
    ledger: Ledger
    as_of: pd.Timestamp
    data_health: float = 100.0
    prediction: dict[str, Any] | None = None
    projection: dict[str, Any] | None = None  # baseline projection summary
    projection_error_pct: float | None = None  # backtest median error (% of monthly outflow)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Finding:
    detector: str
    fingerprint: str
    kind: str  # risk | opportunity
    category: str
    title: str
    summary: str
    why_it_matters: str
    explanation: str
    severity: str
    confidence: float
    confidence_basis: dict[str, Any]
    impact_low: float | None
    impact_high: float | None
    impact_kind: str  # saving | cash_release | exposure | shortfall | revenue_upside | none
    impact_basis: str
    evidence: list[dict[str, Any]]
    supporting_records: dict[str, Any]
    actions: list[dict[str, Any]]
    scenario_preset: dict[str, Any] | None
    target_metric: str | None
    target_params: dict[str, Any]
    baseline_value: float | None
    expected_change: float | None
    priority_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------ helpers


def confidence(strength: float, ctx: EngineContext, consistency: float = 1.0,
               override: float | None = None, basis_note: str | None = None) -> tuple[float, dict[str, Any]]:
    months = max(0.0, (ctx.as_of - ctx.ledger.start).days / 30.44)
    coverage = min(1.0, months / 12.0)
    quality = max(0.0, min(1.0, ctx.data_health / 100.0))
    strength = float(np.clip(strength, 0, 1))
    consistency = float(np.clip(consistency, 0, 1))
    # Capped at 0.95: rule-based evidence is never presented as certainty.
    score = min(0.95, 0.5 * strength + 0.2 * coverage + 0.2 * quality + 0.1 * consistency)
    basis = {
        "method": "evidence_score",
        "formula": "0.5 x strength + 0.2 x history coverage + 0.2 x data quality + 0.1 x consistency "
                   "(capped at 95%)",
        "strength": round(strength, 3), "coverage": round(coverage, 3),
        "data_quality": round(quality, 3), "consistency": round(consistency, 3),
    }
    if override is not None:
        score = override
        basis = {"method": "model_probability", "note": basis_note}
    if basis_note and override is None:
        basis["note"] = basis_note
    return round(float(score), 3), basis


def severity_from_impact(impact: float | None, monthly_revenue: float, floor: str = "low") -> str:
    order = ["low", "medium", "high", "critical"]
    sev = "low"
    if impact is not None and monthly_revenue > 0:
        r = impact / monthly_revenue
        sev = "critical" if r >= 0.5 else "high" if r >= 0.15 else "medium" if r >= 0.04 else "low"
    return order[max(order.index(sev), order.index(floor))]


def ev(label: str, value: Any, display: str, **extra: Any) -> dict[str, Any]:
    return {"label": label, "value": value, "display": display, **extra}


def _sum(df: pd.DataFrame, group: str) -> float:
    return float(df.loc[df["group"] == group, "amount"].sum())


def _between(ledger: Ledger, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
    t = ledger.tx
    return t[(t["date"] >= lo) & (t["date"] <= hi)]


def monthly_revenue(ledger: Ledger, as_of: pd.Timestamp) -> float:
    return _sum(ledger.window(as_of, 90), "revenue") / 3.0


def period_label(lo: pd.Timestamp, hi: pd.Timestamp) -> str:
    return f"{lo.strftime('%b')} - {hi.strftime('%b %Y')}"


# ------------------------------------------------------------------ detectors


def detect_cash_pressure(ctx: EngineContext) -> Finding | None:
    pred, proj = ctx.prediction, ctx.projection
    if not pred:
        return None
    band = pred["band"]
    below = proj["days_below_buffer"] if proj else 0
    if band == "LOW" and below == 0:
        return None
    buffer_thr = proj["buffer_threshold"] if proj else None
    shortfall = max(0.0, (buffer_thr or 0) - proj["lowest_cash"]) if proj else None
    err = (ctx.projection_error_pct or 0) / 100.0 * ((buffer_thr or 0) / 14 * 30.44)
    impact_low = max(0.0, shortfall - err) if shortfall is not None else None
    impact_high = shortfall + err if shortfall is not None else None
    feats = pred.get("features", {})

    evidence = []
    if pred["mode"] == "model":
        for c in [c for c in pred.get("contributions", []) if c["contribution"] >= 0.25][:4]:
            evidence.append(ev(c["label"], c["value"], c["display"], contribution=round(c["contribution"], 3),
                               source="model driver"))
    evidence.append(ev("Cash today", feats.get("cash"), mur(feats.get("cash")), source="ledger"))
    if proj:
        evidence.append(ev("Projected lowest cash (next 90 days)", proj["lowest_cash"],
                           f"{mur(proj['lowest_cash'])} on {date_label(proj['lowest_cash_date'])}",
                           source="deterministic projection"))
        evidence.append(ev("14-day safety buffer", buffer_thr, mur(buffer_thr), source="ledger"))
    evidence.append(ev("Known obligations due in next 30 days", feats.get("known_obligations_30d"),
                       mur(feats.get("known_obligations_30d")), source="ledger"))

    if pred["mode"] == "model":
        prob = pred["probability"]
        conf, basis = confidence(0, ctx, override=prob,
                                 basis_note=f"Calibrated model probability ({pred['model_version']}); "
                                            f"held-out test ROC-AUC {pred.get('test_roc_auc', 'n/a')}.")
        title = "Cash pressure expected in the next 30 days" if band == "HIGH" else "Cash buffer is tightening"
        summary = (f"The cash-pressure model rates the next 30 days {band} ({prob * 100:.0f}% probability that "
                   f"cash falls below a 14-day buffer).")
    else:
        conf, basis = confidence(1.0, ctx, basis_note="Arithmetic on current balances; no prediction needed.")
        title = "Cash buffer is already below 14 days"
        summary = f"Cash covers only {feats.get('buffer_days', 0):.0f} days of committed outflows today."
    severity = "critical" if band == "HIGH" else "high" if (band == "MODERATE" or below > 0) else "medium"

    top = [c["label"].lower() for c in pred.get("contributions", []) if c["contribution"] >= 0.25][:2]
    expl = summary
    if top:
        expl += f" The strongest drivers are {' and '.join(top)}."
    if proj and proj.get("first_date_below_buffer"):
        expl += (f" On current run-rates cash first drops below the {mur(buffer_thr)} buffer on "
                 f"{date_label(proj['first_date_below_buffer'])} and reaches {mur(proj['lowest_cash'])} "
                 f"on {date_label(proj['lowest_cash_date'])}.")
    expl += " Figures come from the ledger; the probability comes from the model."

    col = collections(ctx.ledger, ctx.as_of)
    actions = []
    if col.get("has_invoices") and col.get("overdue_receivables", 0) > 0:
        worst = max(col["by_customer"], key=lambda r: r["overdue_amount"])
        actions.append({"title": f"Collect overdue invoices from {worst['customer']}",
                        "detail": f"{mur(worst['overdue_amount'])} is overdue "
                                  f"({', '.join(worst['open_invoices'][:4])}).", "effort": "low"})
    actions.append({"title": "Negotiate payment timing or price with the main supplier",
                    "detail": "Moving one weekly payment by 14 days, or a 5-10% price reduction, "
                              "directly lifts the lowest projected balance.", "effort": "medium"})
    actions.append({"title": "Hold discretionary spend until the buffer recovers",
                    "detail": "Marketing top-ups, equipment and owner drawings.", "effort": "low"})
    if proj and proj.get("first_date_below_buffer"):
        actions.append({"title": f"Arrange a short-term facility before {date_label(proj['first_date_below_buffer'])}",
                        "detail": "Only if the actions above do not close the gap.", "effort": "medium"})

    baseline = feats.get("buffer_days")
    return Finding(
        detector="cash_pressure", fingerprint="cash_pressure", kind="risk", category="cash_flow",
        title=title, summary=summary,
        why_it_matters="Falling below two weeks of cash leaves no room for a late customer payment or an "
                       "unexpected bill, and forces expensive short-term borrowing.",
        explanation=expl, severity=severity, confidence=conf, confidence_basis=basis,
        impact_low=round(impact_low, 2) if impact_low is not None else None,
        impact_high=round(impact_high, 2) if impact_high is not None else None,
        impact_kind="shortfall",
        impact_basis=(f"Gap between the projected lowest balance and the 14-day buffer ({mur(buffer_thr)}), "
                      f"widened by the projection's median back-test error "
                      f"({ctx.projection_error_pct or 0:.0f}% of monthly outflows)."),
        evidence=evidence,
        supporting_records={"transactions_90d": int(feats.get("transactions_90d", 0)),
                            "invoices_paid_90d": int(feats.get("invoices_paid_90d", 0)),
                            "prediction_id": pred.get("id")},
        actions=actions,
        scenario_preset={"name": "Supplier -10% and collect 10 days faster",
                         "assumptions": {"supplier_cost_pct": -10, "collection_days_change": -10}},
        target_metric="buffer_days", target_params={}, baseline_value=baseline,
        expected_change=(21 - baseline) if baseline is not None and baseline < 21 else 5.0,
    )


def detect_supplier_inflation(ctx: EngineContext) -> Finding | None:
    # Same complete-month windows as the Overview KPIs, so the narrative can never
    # disagree with the headline numbers.
    L = ctx.ledger
    a0, a1, b0, b1 = complete_month_windows(ctx.as_of, 3)
    A, B = _between(L, a0, a1), _between(L, b0, b1)
    rev_a, rev_b = _sum(A, "revenue"), _sum(B, "revenue")
    cogs_a, cogs_b = _sum(A, "cogs"), _sum(B, "cogs")
    if min(rev_a, rev_b, cogs_a, cogs_b) <= 0:
        return None
    g_cogs = (cogs_a / cogs_b - 1) * 100
    g_rev = (rev_a / rev_b - 1) * 100
    gap = g_cogs - g_rev
    if g_cogs < 5 or gap < 5:
        return None
    ratio_a, ratio_b = cogs_a / rev_a * 100, cogs_b / rev_b * 100
    gm_a, gm_b = 100 - ratio_a, 100 - ratio_b

    sup_a = A[A["group"] == "cogs"].groupby("counterparty")["amount"].sum()
    sup_b = B[B["group"] == "cogs"].groupby("counterparty")["amount"].sum()
    rows = []
    for s in sup_a.index.union(sup_b.index):
        va, vb = float(sup_a.get(s, 0.0)), float(sup_b.get(s, 0.0))
        rows.append((s, va, vb, (va / vb - 1) * 100 if vb else None, va - vb))
    rows.sort(key=lambda r: -r[4])
    top = rows[0]
    # months where the cost ratio exceeded the prior average → consistency
    # consistency: share of the months in the current window above the prior ratio
    A_m = A.assign(m=A["date"].dt.to_period("M"))
    per_block = [_sum(d, "cogs") / max(_sum(d, "revenue"), 1) * 100 for _, d in A_m.groupby("m")]
    consistency = float(np.mean([r > ratio_b for r in per_block]))

    annual_top = top[1] / 3 * 12
    impact_low, impact_high = 0.05 * annual_top, 0.10 * annual_top
    mrev = rev_a / 3
    conf, basis = confidence(min(1.0, gap / 15), ctx, consistency)
    ids = A[(A["group"] == "cogs") & (A["counterparty"] == top[0])]["id"].astype(str).tolist()

    evidence = [
        ev("Supplier costs", round(g_cogs, 1), pct(g_cogs), period=period_label(a0, a1),
           compared_to=period_label(b0, b1)),
        ev("Revenue", round(g_rev, 1), pct(g_rev), period=period_label(a0, a1), compared_to=period_label(b0, b1)),
        ev("Supplier cost per MUR 100 of sales", round(ratio_a, 1), f"MUR {ratio_a:.1f} (was {ratio_b:.1f})"),
        ev("Gross margin", round(gm_a - gm_b, 1), pp(gm_a - gm_b), detail=f"{gm_b:.1f}% → {gm_a:.1f}%"),
        ev(f"{top[0]} spend", round(top[3] or 0, 1), pct(top[3]), detail=f"{mur(top[2])} → {mur(top[1])} per quarter"),
    ]
    rev_verb = "rose" if g_rev >= 0 else "fell"
    expl = (f"Supplier spending rose {pct(g_cogs, signed=False)} between {period_label(b0, b1)} and "
            f"{period_label(a0, a1)} while revenue {rev_verb} {pct(abs(g_rev), signed=False)}. Each MUR 100 of "
            f"sales now needs MUR {ratio_a:.1f} of stock instead of MUR {ratio_b:.1f}, cutting gross margin by "
            f"{abs(gm_a - gm_b):.1f} points. "
            f"{top[0]} accounts for the largest increase ({mur(top[4], signed=True)} over three months).")
    return Finding(
        detector="supplier_cost_inflation", fingerprint="supplier_cost_inflation", kind="risk",
        category="cost_leakage", title=f"Supplier costs up {g_cogs:.0f}% while revenue {'grew' if g_rev >= 0 else 'fell'} "
        f"{abs(g_rev):.0f}%",
        summary=f"Stock costs are growing {gap:.1f} points faster than sales, led by {top[0]}.",
        why_it_matters="When purchase costs grow faster than sales, every sale earns less and the gap "
                       "compounds each month until prices or terms change.",
        explanation=expl, severity=severity_from_impact(impact_high, mrev, "medium"),
        confidence=conf, confidence_basis=basis,
        impact_low=round(impact_low, 2), impact_high=round(impact_high, 2), impact_kind="saving",
        impact_basis=f"Annual saving if {top[0]}'s prices are negotiated down 5-10% "
                     f"(current run-rate {mur(annual_top)} a year).",
        evidence=evidence,
        supporting_records={"transaction_ids": ids[-12:], "suppliers": len(rows),
                            "periods": {"current": [str(a0.date()), str(a1.date())],
                                        "previous": [str(b0.date()), str(b1.date())]}},
        actions=[
            {"title": f"Request a price review from {top[0]}", "detail": "Use the volume you buy "
             f"({mur(annual_top)} a year) to ask for the previous price or a volume discount.", "effort": "medium"},
            {"title": "Get two alternative quotes for your top items", "detail": "Even if you stay, a "
             "competing quote strengthens the negotiation.", "effort": "medium"},
            {"title": "Review selling prices on the affected lines", "detail": "A small price increase can "
             "recover part of the margin if competitors face the same cost rise.", "effort": "low"},
        ],
        scenario_preset={"name": "Supplier prices -10%", "assumptions": {"supplier_cost_pct": -10}},
        target_metric="cogs_to_revenue_pct", target_params={}, baseline_value=round(ratio_a, 2),
        expected_change=round(-(ratio_a - ratio_b) * 0.5, 2),
    )


def detect_slow_collections(ctx: EngineContext) -> Finding | None:
    col = collections(ctx.ledger, ctx.as_of)
    if not col.get("has_invoices") or col["collection_days_recent"] is None or col["collection_days_prior"] is None:
        return None
    delta = col["collection_days_recent"] - col["collection_days_prior"]
    mrev = monthly_revenue(ctx.ledger, ctx.as_of)
    overdue_ratio = col["overdue_receivables"] / mrev if mrev else 0
    if delta < 7 and overdue_ratio < 0.1:
        return None
    worst = max((c for c in col["by_customer"] if c["avg_days_to_pay_recent"] and c["avg_days_to_pay_prior"]),
                key=lambda c: (c["avg_days_to_pay_recent"] - c["avg_days_to_pay_prior"]) * c["invoiced_180d"],
                default=None)
    b2b_daily = sum(c["invoiced_180d"] for c in col["by_customer"]) / 180.0
    release = max(0.0, delta) * b2b_daily
    consistency = 1.0 if worst and worst["avg_days_to_pay_recent"] > worst["avg_days_to_pay_prior"] else 0.5
    conf, basis = confidence(min(1.0, max(delta, 0) / 20 + overdue_ratio), ctx, consistency)
    evidence = [
        ev("Average days to collect", round(delta, 1), f"{days(col['collection_days_prior'])} → "
           f"{days(col['collection_days_recent'])}", detail="invoices paid in last 90 days vs the 180 days before"),
        ev("Overdue receivables", col["overdue_receivables"], mur(col["overdue_receivables"])),
        ev("Open receivables", col["open_receivables"], mur(col["open_receivables"])),
        ev("Standard terms", col["standard_terms_days"], days(col["standard_terms_days"])),
    ]
    if worst:
        evidence.append(ev(worst["customer"], worst["avg_days_to_pay_recent"],
                           f"{days(worst['avg_days_to_pay_prior'])} → {days(worst['avg_days_to_pay_recent'])}",
                           detail=f"{mur(worst['overdue_amount'])} overdue"))
    who = f", mostly {worst['customer']}" if worst else ""
    expl = (f"Customers now take {days(col['collection_days_recent'])} on average to pay, up from "
            f"{days(col['collection_days_prior'])}{who}. {mur(col['overdue_receivables'])} is past due. "
            f"Returning to the previous payment speed would release about {mur(release)} of cash that is "
            "currently sitting with customers.")
    return Finding(
        detector="slow_collections", fingerprint="slow_collections", kind="opportunity", category="collections",
        title=f"Customers paying {delta:.0f} days slower", summary=f"Collection time rose from "
        f"{col['collection_days_prior']:.0f} to {col['collection_days_recent']:.0f} days{who}.",
        why_it_matters="Every extra day customers take is cash the business has already earned but cannot use "
                       "to pay suppliers, staff or VAT.",
        explanation=expl, severity=severity_from_impact(release, mrev, "medium"), confidence=conf,
        confidence_basis=basis, impact_low=round(release * 0.5, 2), impact_high=round(release, 2),
        impact_kind="cash_release",
        impact_basis=f"One-off cash released if collection time falls by {delta * 0.5:.0f}-{delta:.0f} days, "
                     f"at {mur(b2b_daily)} of invoiced sales per day.",
        evidence=evidence,
        supporting_records={"invoice_nos": (worst["open_invoices"] if worst else [])[:10],
                            "customers": len(col["by_customer"]),
                            "invoices_paid_recent": col["invoices_paid_recent"]},
        actions=[
            {"title": f"Send statements and reminders{(' to ' + worst['customer']) if worst else ''}",
             "detail": "List the open invoice numbers and due dates; agree a payment date.", "effort": "low"},
            {"title": "Offer a small early-payment discount", "detail": "For example 1.5% for payment within "
             "10 days on new invoices.", "effort": "low"},
            {"title": "Set a credit limit for late payers", "detail": "Pause new credit sales above an agreed "
             "outstanding amount.", "effort": "medium"},
        ],
        scenario_preset={"name": f"Collect {round(delta)} days faster",
                         "assumptions": {"collection_days_change": -round(delta)}},
        target_metric="collection_days",
        target_params={"customer": worst["customer"]} if worst else {},
        baseline_value=worst["avg_days_to_pay_recent"] if worst else col["collection_days_recent"],
        expected_change=-round(delta * 0.6, 1),
    )


FIXED_COMMITMENT_CATEGORIES = {"Rent", "Software & subscriptions", "Telecom & internet", "Insurance",
                               "Professional fees"}


def _fixed_commitments(ledger: Ledger, as_of: pd.Timestamp) -> list[dict[str, Any]]:
    """Fixed-price recurring commitments (variable bills such as electricity are excluded)."""
    return [s for s in recurring_streams(ledger, as_of) if s["active"]
            and s["category"] in FIXED_COMMITMENT_CATEGORIES and s["stability_cv"] <= 0.2]


def detect_recurring_creep(ctx: EngineContext) -> Finding | None:
    L = ctx.ledger
    now = _fixed_commitments(L, ctx.as_of)
    past_date = ctx.as_of - pd.Timedelta(days=182)
    if (past_date - L.start).days < 60:
        return None
    before = _fixed_commitments(L, past_date)
    total_now = sum(s["monthly_run_rate"] for s in now)
    total_before = sum(s["monthly_run_rate"] for s in before)
    if total_before <= 0:
        return None
    before_map = {s["key"]: s for s in before}
    new = [s for s in now if s["key"] not in before_map]
    raised = []
    for s in now:
        b = before_map.get(s["key"])
        if b and b["monthly_run_rate"] > 0 and s["monthly_run_rate"] > b["monthly_run_rate"] * 1.04:
            raised.append((s, b))
    increase = total_now - total_before
    growth = increase / total_before * 100
    if growth < 5 or increase < 3_000:
        return None
    annual = increase * 12
    evidence = [ev("Fixed commitments per month", round(growth, 1), f"{mur(total_before)} → {mur(total_now)}",
                   detail="rent, subscriptions, telecom, insurance, professional fees")]
    for s, b in raised[:3]:
        evidence.append(ev(s["name"], round((s["monthly_run_rate"] / b["monthly_run_rate"] - 1) * 100, 1),
                           f"{mur(b['monthly_run_rate'])} → {mur(s['monthly_run_rate'])} per month",
                           category=s["category"]))
    for s in new[:3]:
        evidence.append(ev(f"New: {s['name']}", s["monthly_run_rate"], f"{mur(s['monthly_run_rate'])} per month",
                           detail=f"since {date_label(s['first_seen'])}", category=s["category"]))
    new_total = sum(s["monthly_run_rate"] for s in new)
    ids = [i for s in [*new, *[r[0] for r in raised]] for i in s["transaction_ids"]]
    conf, basis = confidence(min(1.0, growth / 20), ctx, 1.0 if raised or new else 0.5)
    parts = []
    if raised:
        parts.append(", ".join(f"{s['name']} (+{(s['monthly_run_rate'] / b['monthly_run_rate'] - 1) * 100:.0f}%)"
                               for s, b in raised[:3]))
    if new:
        parts.append(f"{len(new)} new commitment{'s' if len(new) > 1 else ''} worth {mur(new_total)} a month")
    expl = (f"Fixed monthly commitments rose from {mur(total_before)} to {mur(total_now)} in six months "
            f"({pct(growth)}), adding {mur(annual)} a year. Main changes: {'; '.join(parts)}.")
    return Finding(
        detector="recurring_cost_creep", fingerprint="recurring_cost_creep", kind="opportunity",
        category="cost_leakage", title=f"Fixed costs up {growth:.0f}% in six months",
        summary=f"Monthly commitments grew by {mur(increase)} ({pct(growth)}).",
        why_it_matters="Recurring costs are paid whether sales are good or bad, so they quietly raise the "
                       "revenue needed just to break even.",
        explanation=expl, severity=severity_from_impact(annual * 0.6, monthly_revenue(L, ctx.as_of), "low"),
        confidence=conf, confidence_basis=basis,
        impact_low=round(annual * 0.25, 2), impact_high=round(annual * 0.6, 2), impact_kind="saving",
        impact_basis=f"Assumes 25-60% of the {mur(annual)} annual increase can be renegotiated or cancelled.",
        evidence=evidence, supporting_records={"transaction_ids": ids[-12:], "streams": len(now)},
        actions=[
            {"title": "Review every new subscription added this year", "detail": "Cancel tools that overlap or "
             "are rarely used.", "effort": "low"},
            {"title": "Ask the landlord about a longer lease for a lower rate", "detail": "Relevant if rent "
             "increased; a multi-year term can be traded for a discount.", "effort": "medium"} if any(
                s["category"] == "Rent" for s, _ in raised) else
            {"title": "Renegotiate the largest recurring contract", "detail": "Ask for annual billing discounts.",
             "effort": "medium"},
        ],
        scenario_preset={"name": "Recurring costs -10%", "assumptions": {"recurring_expense_pct": -10}},
        target_metric="recurring_monthly", target_params={}, baseline_value=round(total_now, 2),
        expected_change=round(-increase * 0.4, 2),
    )


def detect_overlapping_tools(ctx: EngineContext) -> Finding | None:
    streams = [s for s in recurring_streams(ctx.ledger, ctx.as_of) if s["active"] and s["function"]
               and s["category"] == "Software & subscriptions"]
    by_func: dict[str, list[dict[str, Any]]] = {}
    for s in streams:
        by_func.setdefault(s["function"], []).append(s)
    groups = [(f, ss) for f, ss in by_func.items() if len(ss) >= 2]
    if not groups:
        return None
    func, ss = max(groups, key=lambda g: sum(s["monthly_run_rate"] for s in g[1]))
    total = sum(s["monthly_run_rate"] for s in ss)
    cheapest = min(s["monthly_run_rate"] for s in ss)
    priciest = max(s["monthly_run_rate"] for s in ss)
    overlap_months = min(s["months_active"] for s in ss)
    conf, basis = confidence(0.8, ctx, 1.0, basis_note="Detected from payee names and descriptions; "
                             "confirm the tools really do the same job.")
    names = " and ".join(s["name"] for s in ss)
    return Finding(
        detector="overlapping_subscriptions", fingerprint=f"overlapping_subscriptions:{func}",
        kind="opportunity", category="cost_leakage",
        title=f"Paying for {len(ss)} {func} tools", summary=f"{names} appear to serve the same purpose.",
        why_it_matters="Duplicate software is one of the easiest savings: nothing changes for customers.",
        explanation=(f"{names} have both been billed for at least {overlap_months} months, costing "
                     f"{mur(total)} a month together. Keeping one would save {mur(cheapest * 12)}-"
                     f"{mur(priciest * 12)} a year."),
        severity="low", confidence=conf, confidence_basis=basis,
        impact_low=round(cheapest * 12, 2), impact_high=round(priciest * 12, 2), impact_kind="saving",
        impact_basis="Annual cost of the tool you cancel (cheaper or more expensive of the two).",
        evidence=[ev(s["name"], s["monthly_run_rate"], f"{mur(s['monthly_run_rate'])} per month",
                     detail=f"since {date_label(s['first_seen'])}") for s in ss],
        supporting_records={"transaction_ids": [i for s in ss for i in s["transaction_ids"]][-12:]},
        actions=[{"title": f"Choose one {func} tool and cancel the other", "detail": "Export data first and "
                  "check the notice period.", "effort": "low"}],
        scenario_preset=None, target_metric="function_subscriptions_monthly", target_params={"function": func},
        baseline_value=round(total, 2), expected_change=round(-cheapest, 2),
    )


def detect_customer_concentration(ctx: EngineContext) -> Finding | None:
    c = concentration(ctx.ledger, ctx.as_of, "customer")
    if not c["top"] or c["top_share_pct"] < 15:
        return None
    top = c["top"][0]
    col = collections(ctx.ledger, ctx.as_of)
    late = next((r for r in col.get("by_customer", []) if r["customer"] == top["name"]), None)
    annual = top["amount"] * 2
    conf, basis = confidence(min(1.0, (c["top_share_pct"] - 10) / 20), ctx, 1.0)
    evidence = [
        ev(f"{top['name']} share of revenue", top["share_pct"], f"{top['share_pct']:.1f}%", period="last 180 days"),
        ev("Revenue from this customer", top["amount"], mur(top["amount"]), period="last 180 days"),
        ev("Top 3 customers' share", c["top3_share_pct"], f"{c['top3_share_pct']:.1f}%"),
        ev(c["unidentified_label"], c["unidentified_amount"], mur(c["unidentified_amount"])),
    ]
    extra = ""
    if late and late["avg_days_to_pay_recent"] and late["avg_days_to_pay_prior"] and \
            late["avg_days_to_pay_recent"] - late["avg_days_to_pay_prior"] >= 7:
        evidence.append(ev("Payment speed", late["avg_days_to_pay_recent"],
                           f"{days(late['avg_days_to_pay_prior'])} → {days(late['avg_days_to_pay_recent'])}"))
        extra = (f" This customer is also paying slower ({days(late['avg_days_to_pay_prior'])} → "
                 f"{days(late['avg_days_to_pay_recent'])}), which raises the risk.")
    return Finding(
        detector="customer_concentration", fingerprint=f"customer_concentration:{top['name']}", kind="risk",
        category="concentration", title=f"{top['share_pct']:.0f}% of revenue depends on one customer",
        summary=f"{top['name']} generated {mur(top['amount'])} in the last 180 days.",
        why_it_matters="Losing or delaying one large account would hit revenue and cash at the same time.",
        explanation=(f"{top['name']} accounts for {top['share_pct']:.1f}% of all revenue over the last 180 days "
                     f"({mur(top['amount'])}).{extra}"),
        severity="high" if c["top_share_pct"] >= 25 else "medium", confidence=conf, confidence_basis=basis,
        impact_low=round(annual * 0.25, 2), impact_high=round(annual, 2), impact_kind="exposure",
        impact_basis="Annual revenue at risk: 25% (partial loss) to 100% (loss of the account), "
                     "based on the last 180 days.",
        evidence=evidence, supporting_records={"customers_identified": c["identified_counterparties"]},
        actions=[
            {"title": f"Secure {top['name']} with a written agreement", "detail": "Volumes, prices and payment "
             "terms for the next 12 months.", "effort": "medium"},
            {"title": "Add two or three new trade accounts", "detail": "Target businesses similar to your top "
             "customer.", "effort": "high"},
        ],
        scenario_preset={"name": f"What if {top['name']} stopped buying?",
                         "assumptions": {"sales_volume_pct": -round(top["share_pct"])}},
        target_metric="top_customer_share", target_params={}, baseline_value=top["share_pct"],
        expected_change=-3.0,
    )


def detect_supplier_concentration(ctx: EngineContext) -> Finding | None:
    c = concentration(ctx.ledger, ctx.as_of, "supplier")
    if not c["top"] or c["top_share_pct"] < 40:
        return None
    top = c["top"][0]
    annual = top["amount"] * 2
    conf, basis = confidence(min(1.0, (c["top_share_pct"] - 30) / 30), ctx, 1.0)
    return Finding(
        detector="supplier_concentration", fingerprint=f"supplier_concentration:{top['name']}", kind="risk",
        category="concentration", title=f"{top['share_pct']:.0f}% of purchases from one supplier",
        summary=f"{top['name']} supplied {mur(top['amount'])} of stock in the last 180 days.",
        why_it_matters="A single dominant supplier sets your prices and can disrupt stock availability.",
        explanation=(f"{top['name']} accounts for {top['share_pct']:.1f}% of purchases "
                     f"({mur(top['amount'])} in 180 days). Price rises or delays from this supplier flow "
                     "straight into your margin and shelves."),
        severity="medium", confidence=conf, confidence_basis=basis,
        impact_low=round(annual * 0.03, 2), impact_high=round(annual * 0.08, 2), impact_kind="saving",
        impact_basis="Typical 3-8% saving from competitive quotes on the dominant supplier's annual spend.",
        evidence=[ev(f"{t['name']}", t["share_pct"], f"{t['share_pct']:.1f}% ({mur(t['amount'])})")
                  for t in c["top"][:4]],
        supporting_records={"suppliers_identified": c["identified_counterparties"]},
        actions=[{"title": "Dual-source your top-selling items", "detail": "Qualify a second supplier for the "
                  "items that make up most of the spend.", "effort": "high"}],
        scenario_preset={"name": "Competitive quotes: supplier prices -5%", "assumptions": {"supplier_cost_pct": -5}},
        target_metric="top_supplier_share", target_params={}, baseline_value=top["share_pct"],
        expected_change=-10.0,
    )


def detect_unusual_transactions(ctx: EngineContext) -> Finding | None:
    recent_cut = ctx.as_of - pd.Timedelta(days=60)
    anomalies = [a for a in ctx.anomalies if pd.Timestamp(a["date"]) > recent_cut]
    dups = [d for d in ctx.duplicates if pd.Timestamp(d["date"]) > recent_cut]
    if not anomalies and not dups:
        return None
    dup_amount = sum(d["amount"] * (d["count"] - 1) for d in dups)
    excess = sum(max(0.0, a["amount"] - (a.get("typical") or 0)) for a in anomalies)
    n = len(anomalies) + len(dups)
    evidence = []
    for d in dups:
        evidence.append(ev(f"Possible duplicate: {d['counterparty']}", d["amount"],
                           f"{mur(d['amount'])} paid {d['count']} times on {date_label(d['date'])}",
                           detail="same date, payee and amount", transaction_ids=d["transaction_ids"]))
    for a in anomalies[:4]:
        evidence.append(ev(f"Unusual: {a['counterparty'] or a['category']}", a["amount"],
                           f"{mur(a['amount'])} on {date_label(a['date'])}", detail=a["reason"],
                           transaction_ids=[a["id"]]))
    strength = 0.9 if dups else 0.6
    conf, basis = confidence(strength, ctx, 1.0, basis_note="Duplicates use an exact-match rule; unusual "
                             "payments come from the anomaly model and need human review.")
    return Finding(
        detector="unusual_transactions", fingerprint="unusual_transactions", kind="risk", category="anomaly",
        title=f"{n} payment{'s need' if n > 1 else ' needs'} review",
        summary=f"{len(dups)} possible duplicate{'s' if len(dups) != 1 else ''} and {len(anomalies)} unusually "
                f"large payment{'s' if len(anomalies) != 1 else ''} in the last 60 days.",
        why_it_matters="Duplicate or unexpected payments are cash that may be recoverable, and can signal "
                       "process or control gaps.",
        explanation=("Flagged for review, not confirmed errors. "
                     + (f"Recovering duplicate payments would return {mur(dup_amount)}. " if dups else "")
                     + (f"Unusual payments total {mur(excess)} above what is normal for those payees." if anomalies else "")),
        severity=severity_from_impact(dup_amount + excess, monthly_revenue(ctx.ledger, ctx.as_of), "medium"),
        confidence=conf, confidence_basis=basis,
        impact_low=round(dup_amount, 2), impact_high=round(dup_amount + excess, 2), impact_kind="cash_release",
        impact_basis="Low: duplicate amounts only. High: plus the excess of unusual payments over each payee's "
                     "typical amount.",
        evidence=evidence,
        supporting_records={"transaction_ids": [i for d in dups for i in d["transaction_ids"]]
                            + [a["id"] for a in anomalies]},
        actions=[
            {"title": "Ask the supplier to refund or credit the duplicate payment", "detail": "Quote both "
             "transaction references.", "effort": "low"} if dups else
            {"title": "Confirm the unusual payments with whoever approved them", "detail": "", "effort": "low"},
            {"title": "Require a second approval for payments above a limit", "detail": "Prevents repeats.",
             "effort": "low"},
        ],
        scenario_preset=None, target_metric=None, target_params={}, baseline_value=None, expected_change=None,
    )


def detect_growth_line(ctx: EngineContext) -> Finding | None:
    lines = product_line_performance(ctx.ledger, ctx.as_of)
    cands = [ln for ln in lines if ln["yoy_change_pct"] is not None and ln["yoy_change_pct"] >= 15
             and ln["share_pct"] >= 12]
    if not cands:
        return None
    best = max(cands, key=lambda ln: ln["yoy_change_pct"])
    A = ctx.ledger.window(ctx.as_of, 90)
    rev, cogs = _sum(A, "revenue"), _sum(A, "cogs")
    gm = (rev - cogs) / rev if rev else 0.3
    annual_line = best["revenue"] * 4
    upside = annual_line * best["yoy_change_pct"] / 100 * gm
    decliners = [ln for ln in lines if ln["yoy_change_pct"] is not None and ln["yoy_change_pct"] <= -10]
    evidence = [ev(best["line"], best["yoy_change_pct"], pct(best["yoy_change_pct"]),
                   detail=f"{mur(best['same_period_last_year'])} → {mur(best['revenue'])} (90 days vs same period "
                          "last year)"),
                ev("Share of walk-in sales", best["share_pct"], f"{best['share_pct']:.1f}%")]
    for d in decliners[:2]:
        evidence.append(ev(d["line"], d["yoy_change_pct"], pct(d["yoy_change_pct"]), detail="declining line"))
    conf, basis = confidence(min(1.0, best["yoy_change_pct"] / 40), ctx,
                             1.0 if (best["change_pct"] or 0) > 0 else 0.5)
    expl = (f"{best['line']} sales are up {pct(best['yoy_change_pct'])} on the same 90 days last year and now "
            f"make up {best['share_pct']:.0f}% of walk-in sales.")
    if decliners:
        expl += f" Meanwhile {decliners[0]['line']} is down {pct(decliners[0]['yoy_change_pct'])}, so shelf space " \
                "and stock budget could shift toward the growing line."
    return Finding(
        detector="growth_product_line", fingerprint=f"growth_product_line:{best['line']}", kind="opportunity",
        category="growth", title=f"{best['line']} growing {best['yoy_change_pct']:.0f}% year on year",
        summary=f"{best['line']} is the fastest-growing product line.", why_it_matters="Backing a line that "
        "customers are already choosing is usually cheaper than creating demand elsewhere.",
        explanation=expl, severity="medium", confidence=conf, confidence_basis=basis,
        impact_low=round(upside * 0.5, 2), impact_high=round(upside, 2), impact_kind="revenue_upside",
        impact_basis=f"Extra gross profit over 12 months if the growth rate continues, at the business-wide "
                     f"gross margin of {gm * 100:.0f}% (line-level costs are not recorded).",
        evidence=evidence, supporting_records={"product_lines": len(lines)},
        actions=[
            {"title": f"Increase stock depth and visibility for {best['line']}", "detail": "Fund it from "
             f"slower lines{(' such as ' + decliners[0]['line']) if decliners else ''} rather than new cash.",
             "effort": "medium"},
            {"title": "Run a targeted promotion for the line", "detail": "Measure it against this baseline.",
             "effort": "low"},
        ],
        scenario_preset={"name": "Grow sales 4% with 20% more marketing",
                         "assumptions": {"sales_volume_pct": 4, "marketing_spend_pct": 20}},
        target_metric="product_line_monthly_revenue", target_params={"line": best["line"]},
        baseline_value=round(best["revenue"] / 3, 2), expected_change=round(best["revenue"] / 3 * 0.08, 2),
    )


DETECTORS = [
    detect_cash_pressure,
    detect_supplier_inflation,
    detect_slow_collections,
    detect_recurring_creep,
    detect_overlapping_tools,
    detect_customer_concentration,
    detect_supplier_concentration,
    detect_unusual_transactions,
    detect_growth_line,
]


def run_engine(ctx: EngineContext) -> list[Finding]:
    findings: list[Finding] = []
    mrev = monthly_revenue(ctx.ledger, ctx.as_of) or 1.0
    for det in DETECTORS:
        f = det(ctx)
        if f is None:
            continue
        mid = ((f.impact_low or 0) + (f.impact_high or 0)) / 2
        f.priority_score = round(SEVERITY_WEIGHT[f.severity] * f.confidence * (1 + min(mid / mrev, 2)), 3)
        findings.append(f)
    return sorted(findings, key=lambda f: -f.priority_score)


def target_label(key: str | None) -> str | None:
    return TARGETS[key]["label"] if key else None


__all__ = ["ENGINE_VERSION", "EngineContext", "Finding", "run_engine", "compute_target", "target_label"]
