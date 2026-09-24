package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.api.Scenario;
import mu.mosaic.opportunity.service.Formatter;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Turns the API's scenario figures into prose without letting the model invent numbers.
 * <p>The model only rewrites figures it was given. Every number in its reply is checked against the evidence;
 * anything unsupported means the deterministic template is used instead. The authoritative values stay in the
 * cards on the page, never in this text. What to write is the {@code ScenarioNarrator} chatbot's system prompt in
 * config/ai/agents.json.
 */
@Component
public class ScenarioNarrator extends CheckedWriter<Scenario> {
    private static final String UNKNOWN = "an unknown number of";

    public ScenarioNarrator(LocalAi ai, Formatter fmt) { super(ai, LocalAi.Bot.SCENARIO_NARRATOR, fmt); }

    /** @param useModel false when the person unticked the summary: the template is written without asking the model */
    public Narrative explain(Scenario scenario, boolean useModel) {
        return useModel ? explain(scenario) : new Narrative(template(scenario), "template", null, "not_requested");
    }

    /** Only aggregated figures reach the model: no order, customer or seller identifiers. */
    @Override
    public String evidence(Scenario s) {
        StringBuilder lines = new StringBuilder("Here is the scenario evidence, already calculated:\n\n");
        figures(s).forEach((k, v) -> lines.append(k).append(": ").append(v == null ? "unknown" : v).append('\n'));
        return lines.toString().strip();
    }

    private Map<String, Object> figures(Scenario s) {
        Scenario.Consequences c = s.consequences();
        Scenario.LateCase held = c == null || c.late() == null ? null : c.late().rateHeld();
        Scenario.LateCase fitted = c == null || c.late() == null ? null : c.late().rateFitted();
        Scenario.Capacity strain = c == null ? null : c.sellersAtCapacity();
        Scenario.Evidence rates = s.evidence();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("sales_change_pct", s.scenario().salesChangePct());
        out.put("months_ahead", s.scenario().horizon());
        out.put("baseline_monthly_sales_brl", s.baseline() == null ? null : s.baseline().monthlySales());
        out.put("baseline_monthly_orders", s.baseline() == null ? null : s.baseline().monthlyOrders());
        out.put("projected_monthly_sales_brl", c == null ? null : c.projectedMonthlySales());
        out.put("projected_monthly_orders", c == null ? null : c.projectedMonthlyOrders());
        out.put("extra_orders_per_month", c == null ? null : c.extraOrdersPerMonth());
        out.put("average_order_value_brl", rates == null ? null : rates.aov());
        out.put("recent_late_rate_pct", held == null || held.lateRate() == null ? null : held.lateRate() * 100);
        out.put("expected_late_orders_per_month", held == null ? null : held.expectedLatePerMonth());
        out.put("expected_low_reviews_per_month", held == null ? null : held.expectedLowReviewsPerMonth());
        out.put("sales_exposed_to_late_delivery_brl", held == null ? null : held.salesExposedPerMonth());
        out.put("late_rate_if_volume_link_holds_pct", fitted == null || fitted.lateRate() == null ? null : fitted.lateRate() * 100);
        out.put("low_review_rate_when_late_pct", rates == null || rates.pLowGivenLate() == null ? null : rates.pLowGivenLate() * 100);
        out.put("low_review_rate_when_on_time_pct", rates == null || rates.pLowGivenOnTime() == null ? null : rates.pLowGivenOnTime() * 100);
        out.put("sellers_past_their_busiest_month", strain == null ? null : strain.count());
        out.put("active_sellers", strain == null ? null : strain.activeSellers());
        // the model sees figures to two decimals, as the page shows them
        out.replaceAll((key, value) -> value instanceof Double d ? Math.round(d * 100) / 100.0 : value);
        return out;
    }

    @Override
    protected String template(Scenario s) {
        double change = s.scenario().salesChangePct() == null ? 0 : s.scenario().salesChangePct();
        Scenario.Consequences c = s.consequences();
        if (c == null)
            return "There is not enough recent activity in the data to project a " + fmt.num(change, 0, UNKNOWN) + "% sales change, so no consequences were calculated.";
        Scenario.LateCase held = c.late().rateHeld();
        Scenario.Capacity strain = c.sellersAtCapacity();
        String direction = change >= 0 ? "more" : "fewer";
        return "A " + fmt.num(Math.abs(change), 0, UNKNOWN) + "% " + (change >= 0 ? "rise" : "fall") + " in sales over the next " + fmt.num(s.scenario().horizon(), 0, UNKNOWN) + " months would mean about "
                + fmt.num(c.projectedMonthlyOrders(), 0, UNKNOWN) + " orders a month, "
                + fmt.num(c.extraOrdersPerMonth() == null ? null : Math.abs(c.extraOrdersPerMonth()), 0, UNKNOWN) + " " + direction + " than the recent average. "
                + "At the recent late-delivery rate of " + fmt.percentNumber(held.lateRate(), 2, UNKNOWN) + "%, about "
                + fmt.num(held.expectedLatePerMonth(), 0, UNKNOWN) + " of those orders a month could arrive after the "
                + "promised date, carrying roughly " + fmt.num(held.salesExposedPerMonth(), 0, UNKNOWN) + " BRL of sales, and "
                + "about " + fmt.num(held.expectedLowReviewsPerMonth(), 0, UNKNOWN) + " low reviews could follow. "
                + "Around " + fmt.num(strain.count(), 0, UNKNOWN) + " of " + fmt.num(strain.activeSellers(), 0, UNKNOWN) + " active sellers would be "
                + "handling more orders in a month than they ever have. Higher volume and later deliveries moved "
                + "together in past months, but that is an association, not a proven cause, so treat these as "
                + "figures to watch rather than outcomes to expect.";
    }
}
