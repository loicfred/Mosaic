package mu.mosaic.opportunity.service.ai;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.ai.IAIService;
import org.solarframework.ai.Chatbot;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import static mu.mosaic.opportunity.obj.ApiData.nestedObject;

/**
 * Turns the API's scenario figures into prose without letting the model invent numbers.
 * <p>The model only rewrites figures it was given. Every number in its reply is checked against the evidence;
 * anything unsupported means the deterministic template is used instead. The authoritative values stay in the
 * cards on the page, never in this text. What to write is the {@code ScenarioNarrator} chatbot's system prompt in
 * config/ai/agents.json. Moved here from the Python API (see AI/old/) so the project has one LLM client.
 */
@Component
public class ScenarioNarrator {
    private static final Logger log = LoggerFactory.getLogger(ScenarioNarrator.class);
    private final LocalAi ai;

    public ScenarioNarrator(LocalAi ai) { this.ai = ai; }

    /** @param source "llm" when the model wrote it, "template" otherwise, with the reason in {@code reason} */
    public record Narrative(String text, String source, String model, String reason) {}

    /** @param useModel false when the person unticked the summary: the template is written without asking the model */
    public Narrative explain(Map<String, Object> scenario, boolean useModel) {
        String fallback = template(scenario);
        if (!useModel) return new Narrative(fallback, "template", null, "not_requested");
        Chatbot.Builder configured = ai.bot(LocalAi.NARRATOR);
        if (configured == null) return new Narrative(fallback, "template", null, "llm_disabled");
        Chatbot bot = configured.build();
        IAIService service = bot.getService();
        String text;
        String evidencePrompt;
        try {
            if (!LocalAi.reachable(service)) return new Narrative(fallback, "template", null, "llm_unreachable");
            evidencePrompt = prompt(scenario);
            text = bot.prompt(evidencePrompt);
        } catch (RuntimeException e) {
            log.warn("Scenario summary fell back to the template: {}", e.getMessage());
            return new Narrative(fallback, "template", null, "llm_unreachable: " + e.getClass().getSimpleName());
        }
        if (text == null || text.isBlank()) return new Narrative(fallback, "template", service.getModel(), "llm_empty_response");
        var allowed = NumberCheck.allowedFrom(scenario);
        allowed.addAll(NumberCheck.allowedFromText(evidencePrompt));
        allowed.addAll(NumberCheck.allowedFromText(bot.getSystemPrompt()));
        List<String> invented = NumberCheck.unsupported(text, allowed);
        if (!invented.isEmpty()) return new Narrative(fallback, "template", service.getModel(), "unsupported_numbers: " + String.join(", ", invented));
        return new Narrative(text.strip(), "llm", service.getModel(), null);
    }

    /** The message the model gets: the evidence only; what to write is the chatbot's system prompt. */
    static String prompt(Map<String, Object> scenario) {
        StringBuilder lines = new StringBuilder("Here is the scenario evidence, already calculated:\n\n");
        evidence(scenario).forEach((k, v) -> lines.append(k).append(": ").append(v == null ? "unknown" : v).append('\n'));
        return lines.toString().strip();
    }

    /** Only aggregated figures reach the model: no order, customer or seller identifiers. */
    static Map<String, Object> evidence(Map<String, Object> s) {
        Map<String, Object> scenario = nestedObject(s, "scenario");
        Map<String, Object> baseline = nestedObject(s, "baseline");
        Map<String, Object> consequences = nestedObject(s, "consequences");
        Map<String, Object> rates = nestedObject(s, "evidence");
        Map<String, Object> late = nestedObject(consequences, "late");
        Map<String, Object> held = nestedObject(late, "rate_held");
        Map<String, Object> fitted = nestedObject(late, "rate_fitted");
        Map<String, Object> strain = nestedObject(consequences, "sellers_at_capacity");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("sales_change_pct", scenario.get("sales_change_pct"));
        out.put("months_ahead", scenario.get("horizon"));
        out.put("baseline_monthly_sales_brl", round(baseline.get("monthly_sales")));
        out.put("baseline_monthly_orders", round(baseline.get("monthly_orders")));
        out.put("projected_monthly_sales_brl", round(consequences.get("projected_monthly_sales")));
        out.put("projected_monthly_orders", round(consequences.get("projected_monthly_orders")));
        out.put("extra_orders_per_month", round(consequences.get("extra_orders_per_month")));
        out.put("average_order_value_brl", round(rates.get("aov")));
        out.put("recent_late_rate_pct", round(pct(held.get("late_rate"))));
        out.put("expected_late_orders_per_month", round(held.get("expected_late_per_month")));
        out.put("expected_low_reviews_per_month", round(held.get("expected_low_reviews_per_month")));
        out.put("sales_exposed_to_late_delivery_brl", round(held.get("sales_exposed_per_month")));
        out.put("late_rate_if_volume_link_holds_pct", round(pct(fitted.get("late_rate"))));
        out.put("low_review_rate_when_late_pct", round(pct(rates.get("p_low_given_late"))));
        out.put("low_review_rate_when_on_time_pct", round(pct(rates.get("p_low_given_on_time"))));
        out.put("sellers_past_their_busiest_month", strain.get("count"));
        out.put("active_sellers", strain.get("active_sellers"));
        return out;
    }

    static String template(Map<String, Object> s) {
        Map<String, Object> scenario = nestedObject(s, "scenario"), c = nestedObject(s, "consequences");
        double change = num(scenario.get("sales_change_pct"));
        if (s == null || s.get("consequences") == null)
            return "There is not enough recent activity in the data to project a " + fmt(change, 0) + "% sales change, so no consequences were calculated.";
        Map<String, Object> held = nestedObject(nestedObject(c, "late"), "rate_held"), strain = nestedObject(c, "sellers_at_capacity");
        String direction = change >= 0 ? "more" : "fewer";
        return "A " + fmt(Math.abs(change), 0) + "% change in sales over the next " + fmt(scenario.get("horizon"), 0) + " months would mean about "
                + fmt(c.get("projected_monthly_orders"), 0) + " orders a month, "
                + fmt(Math.abs(num(c.get("extra_orders_per_month"))), 0) + " " + direction + " than the recent average. "
                + "At the recent late-delivery rate of " + fmt(pct(held.get("late_rate")), 2) + "%, about "
                + fmt(held.get("expected_late_per_month"), 0) + " of those orders a month could arrive after the "
                + "promised date, carrying roughly " + fmt(held.get("sales_exposed_per_month"), 0) + " BRL of sales, and "
                + "about " + fmt(held.get("expected_low_reviews_per_month"), 0) + " low reviews could follow. "
                + "Around " + fmt(strain.get("count"), 0) + " of " + fmt(strain.get("active_sellers"), 0) + " active sellers would be "
                + "handling more orders in a month than they ever have. Higher volume and later deliveries moved "
                + "together in past months, but that is an association, not a proven cause, so treat these as "
                + "figures to watch rather than outcomes to expect.";
    }

    private static Double pct(Object v) { return v instanceof Number n ? n.doubleValue() * 100 : null; }
    private static double num(Object v) { return v instanceof Number n ? n.doubleValue() : 0; }
    private static Object round(Object v) { return v instanceof Number n ? Math.round(n.doubleValue() * 100) / 100.0 : v; }
    private static String fmt(Object v, int digits) { return v instanceof Number n ? String.format(Locale.US, "%,." + digits + "f", n.doubleValue()) : "an unknown number of"; }
}
