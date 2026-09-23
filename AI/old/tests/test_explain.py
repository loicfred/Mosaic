from app.ai import explain
from app.ai.client import ChatResult

EVIDENCE = {
    "scenario": {"horizon": 3, "sales_change_pct": 20.0},
    "baseline": {"monthly_sales": 871772.62, "monthly_orders": 6323.67},
    "consequences": {
        "projected_monthly_sales": 1046127.14,
        "projected_monthly_orders": 7588.4,
        "extra_orders_per_month": 1264.73,
        "late": {
            "rate_held": {
                "late_rate": 0.0361,
                "expected_late_per_month": 273.94,
                "expected_low_reviews_per_month": 843.2,
                "sales_exposed_per_month": 37766.5,
            },
            "rate_fitted": None,
        },
        "sellers_at_capacity": {"count": 529, "active_sellers": 1783, "top": []},
    },
    "evidence": {"aov": 137.86, "p_low_given_late": 0.624, "p_low_given_on_time": 0.092},
}


class StubClient:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def __call__(self, prompt, **kwargs):
        self.calls += 1
        self.prompt = prompt
        return self.result


def settings(enabled=True):
    return explain.LlmSettings(enabled=enabled, base_url="http://x", model="", timeout=5.0)


def test_prompt_contains_evidence_numbers_and_no_raw_identifiers():
    evidence = {**EVIDENCE}
    evidence["consequences"] = {
        **EVIDENCE["consequences"],
        "sellers_at_capacity": {
            "count": 529, "active_sellers": 1783,
            "top": [{"seller_id": "6560211a19b47992c3666cc44a7e94c0", "historical_peak": 90.0}],
        },
    }
    prompt = explain.build_prompt(evidence)
    assert "7588" in prompt or "7,588" in prompt
    assert "only the numbers" in prompt.lower()
    assert "6560211a19b47992c3666cc44a7e94c0" not in prompt
    assert "seller_id" not in prompt and "order_id" not in prompt


def test_allowed_numbers_cover_common_formats():
    allowed = explain.allowed_numbers(EVIDENCE)
    assert "1264" in allowed and "1265" in allowed  # floor and rounded
    assert "1,265" in allowed
    assert "3.61" in allowed  # rate rendered as a percentage
    assert "529" in allowed


def test_verify_accepts_a_narrative_that_only_uses_evidence_numbers():
    text = (
        "Sales rising 20% adds about 1,265 orders a month, taking you to roughly 7,588. "
        "At the recent late rate of 3.61%, about 274 of those arrive late, and 529 of your "
        "1,783 active sellers would pass their busiest month."
    )
    assert explain.verify_numbers(text, explain.allowed_numbers(EVIDENCE)) == []


def test_verify_flags_an_invented_figure():
    text = "Sales rise 20% and profit margin improves by 4,312 reais per month."
    unsupported = explain.verify_numbers(text, explain.allowed_numbers(EVIDENCE))
    assert "4,312" in unsupported or "4312" in unsupported


def test_verify_ignores_small_prose_numbers():
    text = "Over the next 3 months, watch two things and check the top 5 sellers."
    assert explain.verify_numbers(text, explain.allowed_numbers(EVIDENCE)) == []


def test_llm_narrative_is_used_when_faithful():
    faithful = "Orders rise by about 1,265 per month. Around 274 arrive late. Check 529 sellers."
    stub = StubClient(ChatResult(faithful, model="gemma-3-4b"))
    result = explain.explain(EVIDENCE, settings=settings(), complete=stub)
    assert result["source"] == "llm"
    assert result["text"] == faithful
    assert result["model"] == "gemma-3-4b"
    assert result["reason"] is None
    assert stub.calls == 1


def test_template_used_when_model_invents_numbers():
    stub = StubClient(ChatResult("Profit will grow by 99,999 reais."))
    result = explain.explain(EVIDENCE, settings=settings(), complete=stub)
    assert result["source"] == "template"
    assert result["reason"].startswith("unsupported_numbers")
    assert "99,999" not in result["text"]


def test_template_used_on_client_error():
    stub = StubClient(ChatResult(None, error="llm_unreachable: ConnectError"))
    result = explain.explain(EVIDENCE, settings=settings(), complete=stub)
    assert result["source"] == "template"
    assert result["reason"] == "llm_unreachable: ConnectError"
    assert result["text"]


def test_disabled_settings_never_call_the_model():
    stub = StubClient(ChatResult("should not be used"))
    result = explain.explain(EVIDENCE, settings=settings(enabled=False), complete=stub)
    assert stub.calls == 0
    assert result["source"] == "template"
    assert result["reason"] == "llm_disabled"


def test_template_narrative_only_uses_evidence_numbers():
    text = explain.template_narrative(EVIDENCE)
    assert explain.verify_numbers(text, explain.allowed_numbers(EVIDENCE)) == []
    assert "association" in text.lower() or "not a cause" in text.lower()


def test_scenario_without_consequences_still_explains():
    empty = {"scenario": {"horizon": 3, "sales_change_pct": 20.0}, "consequences": None,
             "reason": "no_baseline_activity", "baseline": {}, "evidence": {}}
    result = explain.explain(empty, settings=settings(enabled=False), complete=StubClient(None))
    assert result["source"] == "template"
    assert "not enough" in result["text"].lower() or "no baseline" in result["text"].lower()
