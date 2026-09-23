"""Turn computed scenario evidence into prose, without letting the model invent numbers.

The language model only rewrites figures it was given. Every number in its reply is checked
against the evidence; anything unsupported means the deterministic template is used instead.
The authoritative values stay in the JSON the API returns, never in this text.
"""
import json
import re
from dataclasses import dataclass

from app.ai.client import ChatResult, complete as default_complete

NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")
SMALL_NUMBER_MAX = 12  # "three months", "top 5 sellers" and similar prose
PROMPT_TEMPLATE = """You are helping a small-business owner understand a sales scenario.

Here is the scenario evidence, already calculated:

{evidence}

Write three short paragraphs:
1. What changes if this happens.
2. What to watch, especially delivery reliability and customer reviews.
3. One concrete thing to check next.

Rules:
- Use only the numbers given above. Do not calculate, estimate or invent any other number.
- Say that the link between order volume and late delivery is an association seen in past
  months, not a proven cause.
- Do not promise outcomes. Write "could" or "would", never "will".
- Plain language, no bullet points, no headings, under 180 words.
- Answer directly with the three paragraphs. Keep any thinking brief.
"""


@dataclass(frozen=True)
class LlmSettings:
    enabled: bool
    base_url: str
    model: str
    timeout: float


def explain(evidence: dict, *, settings: LlmSettings, complete=None) -> dict:
    fallback = template_narrative(evidence)
    if not settings.enabled:
        return _result(fallback, "template", None, "llm_disabled")

    # Resolved at call time so the transport can be swapped (and stubbed) without re-import.
    complete = complete or default_complete
    response: ChatResult = complete(
        build_prompt(evidence), base_url=settings.base_url, model=settings.model,
        timeout=settings.timeout,
    )
    if response is None or response.text is None:
        reason = response.error if response is not None else "llm_no_response"
        return _result(fallback, "template", None, reason)

    unsupported = verify_numbers(response.text, allowed_numbers(evidence))
    if unsupported:
        return _result(fallback, "template", response.model, f"unsupported_numbers: {', '.join(unsupported)}")
    return _result(response.text, "llm", response.model, None)


def _result(text: str, source: str, model: str | None, reason: str | None) -> dict:
    return {"text": text, "source": source, "model": model, "reason": reason}


def build_prompt(evidence: dict) -> str:
    return PROMPT_TEMPLATE.format(evidence=json.dumps(_prompt_evidence(evidence), indent=2))


def _prompt_evidence(evidence: dict) -> dict:
    """Only aggregated figures reach the model: no order, customer or seller identifiers."""
    scenario = evidence.get("scenario", {})
    baseline = evidence.get("baseline", {})
    consequences = evidence.get("consequences") or {}
    rates = evidence.get("evidence", {})
    held = (consequences.get("late") or {}).get("rate_held") or {}
    fitted = (consequences.get("late") or {}).get("rate_fitted") or {}
    strain = consequences.get("sellers_at_capacity") or {}
    return {
        "sales_change_pct": scenario.get("sales_change_pct"),
        "months_ahead": scenario.get("horizon"),
        "baseline_monthly_sales_brl": _round(baseline.get("monthly_sales")),
        "baseline_monthly_orders": _round(baseline.get("monthly_orders")),
        "projected_monthly_sales_brl": _round(consequences.get("projected_monthly_sales")),
        "projected_monthly_orders": _round(consequences.get("projected_monthly_orders")),
        "extra_orders_per_month": _round(consequences.get("extra_orders_per_month")),
        "average_order_value_brl": _round(rates.get("aov")),
        "recent_late_rate_pct": _round(_pct(held.get("late_rate"))),
        "expected_late_orders_per_month": _round(held.get("expected_late_per_month")),
        "expected_low_reviews_per_month": _round(held.get("expected_low_reviews_per_month")),
        "sales_exposed_to_late_delivery_brl": _round(held.get("sales_exposed_per_month")),
        "late_rate_if_volume_link_holds_pct": _round(_pct(fitted.get("late_rate"))),
        "low_review_rate_when_late_pct": _round(_pct(rates.get("p_low_given_late"))),
        "low_review_rate_when_on_time_pct": _round(_pct(rates.get("p_low_given_on_time"))),
        "sellers_past_their_busiest_month": strain.get("count"),
        "active_sellers": strain.get("active_sellers"),
    }


def allowed_numbers(evidence: dict) -> set[str]:
    """Every rendering of every evidence figure the model may legitimately repeat."""
    allowed: set[str] = set()
    for value in _numeric_values(evidence):
        allowed.update(_renderings(value))
    for value in _prompt_evidence(evidence).values():
        if isinstance(value, (int, float)):
            allowed.update(_renderings(value))
    return allowed


def _numeric_values(node) -> list[float]:
    if isinstance(node, bool):
        return []
    if isinstance(node, (int, float)):
        return [float(node)]
    if isinstance(node, dict):
        return [v for child in node.values() for v in _numeric_values(child)]
    if isinstance(node, list):
        return [v for child in node for v in _numeric_values(child)]
    return []


def _renderings(value: float) -> set[str]:
    candidates: set[float] = {value, _pct(value) or 0.0}
    out: set[str] = set()
    for candidate in candidates:
        for number in (candidate, abs(candidate)):
            out.add(f"{number:.0f}")
            out.add(f"{int(number)}")
            out.add(f"{number:,.0f}")
            out.add(f"{number:.1f}")
            out.add(f"{number:,.1f}")
            out.add(f"{number:.2f}")
            out.add(f"{number:,.2f}")
    return out


def verify_numbers(text: str, allowed: set[str]) -> list[str]:
    """Numbers in the text that no evidence value supports."""
    unsupported = []
    for token in NUMBER_PATTERN.findall(text):
        bare = token.replace(",", "")
        try:
            value = float(bare)
        except ValueError:
            continue
        if value <= SMALL_NUMBER_MAX and value == int(value):
            continue
        if token in allowed or bare in allowed:
            continue
        unsupported.append(token)
    return unsupported


def template_narrative(evidence: dict) -> str:
    consequences = evidence.get("consequences")
    scenario = evidence.get("scenario", {})
    change = scenario.get("sales_change_pct", 0.0)
    horizon = scenario.get("horizon", 0)
    if not consequences:
        return (
            f"There is not enough recent activity in the data to project a {_num(change)}% "
            "sales change, so no consequences were calculated."
        )

    held = (consequences.get("late") or {}).get("rate_held") or {}
    strain = consequences.get("sellers_at_capacity") or {}
    direction = "more" if change >= 0 else "fewer"
    return (
        f"A {_num(abs(change))}% change in sales over the next {_num(horizon)} months would mean about "
        f"{_num(consequences.get('projected_monthly_orders'))} orders a month, "
        f"{_num(abs(consequences.get('extra_orders_per_month', 0)))} {direction} than the recent average. "
        f"At the recent late-delivery rate of {_num(_pct(held.get('late_rate')), 2)}%, about "
        f"{_num(held.get('expected_late_per_month'))} of those orders a month could arrive after the "
        f"promised date, carrying roughly {_num(held.get('sales_exposed_per_month'))} BRL of sales, and "
        f"about {_num(held.get('expected_low_reviews_per_month'))} low reviews could follow. "
        f"Around {_num(strain.get('count'))} of {_num(strain.get('active_sellers'))} active sellers would be "
        "handling more orders in a month than they ever have. Higher volume and later deliveries moved "
        "together in past months, but that is an association, not a proven cause, so treat these as "
        "figures to watch rather than outcomes to expect."
    )


def _pct(value) -> float | None:
    return value * 100 if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _round(value, digits: int = 2):
    return round(value, digits) if isinstance(value, (int, float)) and not isinstance(value, bool) else value


def _num(value, digits: int = 0) -> str:
    if not isinstance(value, (int, float)):
        return "an unknown number of"
    return f"{value:,.{digits}f}"
