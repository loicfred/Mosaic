package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.service.ai.ScenarioNarrator.Narrative;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIService;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Locale;
import java.util.Map;

import static mu.mosaic.opportunity.obj.ApiData.nestedObject;
import static mu.mosaic.opportunity.obj.ApiData.recordList;

/**
 * When the sales forecast rises, says where the data points for investment, from the API's growing categories and
 * their delivery and review checks.
 * <p>As {@link ScenarioNarrator}: the model only rewrites figures it was given, every number in its reply is checked,
 * and the fixed template is kept otherwise. What to write is the {@code InvestmentAdvisor} chatbot's system prompt.
 */
@Component
public class InvestmentAdvisor {
    private static final Logger log = LoggerFactory.getLogger(InvestmentAdvisor.class);
    private final LocalAi ai;

    public InvestmentAdvisor(LocalAi ai) { this.ai = ai; }

    public Narrative advise(Map<String, Object> opportunities) {
        String fallback = template(opportunities);
        if (!Boolean.TRUE.equals(nestedObject(opportunities, "trend").get("increasing")) || recordList(opportunities, "candidates").isEmpty())
            return new Narrative(fallback, "template", null, "nothing_to_advise");
        Chatbot.Builder configured = ai.bot(LocalAi.ADVISOR);
        if (configured == null) return new Narrative(fallback, "template", null, "llm_disabled");
        Chatbot bot = configured.build();
        IAIService service = bot.getService();
        String evidence = prompt(opportunities), text;
        try {
            if (!service.isAvailable()) return new Narrative(fallback, "template", null, "llm_unreachable");
            text = bot.prompt(evidence);
        } catch (RuntimeException e) {
            log.warn("Investment advice fell back to the template: {}", e.getMessage());
            return new Narrative(fallback, "template", null, "llm_unreachable: " + e.getClass().getSimpleName());
        }
        if (text == null || text.isBlank()) return new Narrative(fallback, "template", service.getModel(), "llm_empty_response");
        var allowed = NumberCheck.allowedFromText(evidence);
        allowed.addAll(NumberCheck.allowedFromText(bot.getSystemPrompt()));
        List<String> invented = NumberCheck.unsupported(text, allowed);
        if (!invented.isEmpty()) return new Narrative(fallback, "template", service.getModel(), "unsupported_numbers: " + String.join(", ", invented));
        return new Narrative(text.strip(), "llm", service.getModel(), null);
    }

    /** Rounded aggregates only, so the figures the model may quote are the ones the page shows. */
    static String prompt(Map<String, Object> o) {
        Map<String, Object> trend = nestedObject(o, "trend");
        StringBuilder out = new StringBuilder("Here is the evidence, already calculated. Amounts are gross item sales in BRL, not profit.\n\n")
                .append("forecast_change_pct: ").append(fmt(trend.get("change_pct"), 1))
                .append(" (average forecast month against the average of the last ").append(fmt(trend.get("recent_months"), 0)).append(" months)\n")
                .append("recent_monthly_sales_brl: ").append(fmt(trend.get("recent_monthly_mean"), 0)).append('\n')
                .append("forecast_monthly_sales_brl: ").append(fmt(trend.get("forecast_monthly_mean"), 0)).append('\n')
                .append("business_late_rate_pct: ").append(fmt(pct(nestedObject(nestedObject(o, "business_rates"), "late_rate").get("rate")), 1)).append('\n')
                .append("business_low_review_rate_pct: ").append(fmt(pct(nestedObject(nestedObject(o, "business_rates"), "low_review_rate").get("rate")), 1)).append("\n\n")
                .append("Growing categories (last 3 months against the 3 before), best candidates first:\n");
        for (Map<String, Object> c : recordList(o, "candidates")) {
            Map<String, Object> checks = nestedObject(c, "checks");
            out.append("- ").append(c.get("category"))
                    .append(": sales_change_pct ").append(fmt(c.get("change_pct"), 1))
                    .append(", sales_added_brl ").append(fmt(c.get("change_abs"), 0))
                    .append(", late_rate_pct ").append(fmt(pct(nestedObject(checks, "late_rate").get("rate")), 1))
                    .append(", low_review_rate_pct ").append(fmt(pct(nestedObject(checks, "low_review_rate").get("rate")), 1))
                    .append(", growth ").append(c.get("growth_level"))
                    .append(", size ").append(c.get("size_level"))
                    .append(", late_deliveries ").append(nestedObject(checks, "late_rate").get("level"))
                    .append(", low_reviews ").append(nestedObject(checks, "low_review_rate").get("level"))
                    .append(", readiness ").append(c.get("readiness")).append('\n');
        }
        return out.toString().strip();
    }

    /** The fixed advice, shown at once and whenever the model's version is not usable. */
    public static String template(Map<String, Object> o) {
        Map<String, Object> trend = nestedObject(o, "trend");
        if (!Boolean.TRUE.equals(trend.get("increasing")))
            return "The model does not forecast rising sales for the coming months, so no category is suggested for investment. Check the categories falling behind instead.";
        List<Map<String, Object>> candidates = recordList(o, "candidates");
        String head = "Sales are forecast to rise about " + fmt(trend.get("change_pct"), 1) + "% against the last " + fmt(trend.get("recent_months"), 0) + " months. ";
        if (candidates.isEmpty()) return head + "No category grew at least as fast as the business with enough sales to suggest.";
        Map<String, Object> top = candidates.getFirst();
        String ready = "ready".equals(top.get("readiness"))
                ? "Its late-delivery and low-review rates are in line with the business, so extra volume there looks manageable."
                : "fix_first".equals(top.get("readiness"))
                ? "Its late-delivery or low-review rate is worse than the business, so fix delivery before pushing more volume."
                : "Too few of its orders were delivered or reviewed to judge its reliability.";
        return head + "The strongest place to look is " + label(top.get("category")) + ", up " + fmt(top.get("change_pct"), 1)
                + "% with about " + fmt(top.get("change_abs"), 0) + " BRL more sales than the 3 months before. " + ready
                + " Growth in the past does not prove more investment would pay off, and sales are not profit.";
    }

    private static String label(Object code) { return String.valueOf(code).replace('_', ' '); }
    private static Double pct(Object v) { return v instanceof Number n ? n.doubleValue() * 100 : null; }
    private static String fmt(Object v, int digits) { return v instanceof Number n ? String.format(Locale.US, "%,." + digits + "f", n.doubleValue()) : "unknown"; }
}
