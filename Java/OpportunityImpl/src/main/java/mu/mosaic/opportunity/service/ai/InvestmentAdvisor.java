package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.api.SalesOpportunities;
import mu.mosaic.opportunity.obj.api.SalesOpportunities.Candidate;
import mu.mosaic.opportunity.service.Formatter;
import org.springframework.stereotype.Component;

/**
 * Says where the data points for investment, from the API's candidate categories and their checks, whether or not
 * the sales forecast rises: a falling forecast changes the framing (where to hold or shift effort), never whether
 * something is suggested.
 * <p>As {@link ScenarioNarrator}: the model only rewrites figures it was given, every number in its reply is checked,
 * and the fixed template is kept otherwise ({@link CheckedWriter}). What to write is the {@code InvestmentAdvisor} chatbot's system prompt.
 */
@Component
public class InvestmentAdvisor extends CheckedWriter<SalesOpportunities> {

    public InvestmentAdvisor(LocalAi ai, Formatter fmt) { super(ai, LocalAi.Bot.INVESTMENT_ADVISOR, fmt); }

    @Override
    protected String nothingToSay(SalesOpportunities o) { return o.candidates().isEmpty() ? "nothing_to_advise" : null; }

    /** Rounded aggregates only, so the figures the model may quote are the ones the page shows. */
    @Override
    public String evidence(SalesOpportunities o) {
        SalesOpportunities.Forecast trend = o.trend();
        StringBuilder out = new StringBuilder("Here is the evidence, already calculated. Amounts are gross item sales in BRL, not profit.\n\n")
                .append("forecast_change_pct: ").append(fmt.num(trend.changePct(), 1, "unknown"))
                .append(" (average forecast month against the average of the last ").append(fmt.num(trend.recentMonths(), 0, "unknown")).append(" months)\n")
                .append("forecast_direction: ").append(trend.increasing() ? "rising" : "not rising").append('\n')
                .append("recent_monthly_sales_brl: ").append(fmt.num(trend.recentMonthlyMean(), 0, "unknown")).append('\n')
                .append("forecast_monthly_sales_brl: ").append(fmt.num(trend.forecastMonthlyMean(), 0, "unknown")).append('\n')
                .append("business_late_rate_pct: ").append(fmt.percentNumber(o.businessRate("late_rate").rate(), 1, "unknown")).append('\n')
                .append("business_low_review_rate_pct: ").append(fmt.percentNumber(o.businessRate("low_review_rate").rate(), 1, "unknown")).append('\n')
                .append(o.businessProfile() != null && o.businessProfile().recent() != null ? o.businessProfile().recent().line("business", fmt) + "\n" : "").append('\n')
                .append("Candidate categories (last 3 months against the 3 before), best first. basis: growing = sales up at least as fast as the business; beats_business = falling less than the business; best_available = the smallest falls:\n");
        for (Candidate c : o.candidates()) {
            out.append("- ").append(c.category())
                    .append(": basis ").append(c.basis())
                    .append(", sales_change_pct ").append(fmt.num(c.changePct(), 1, "unknown"))
                    .append(", sales_added_brl ").append(fmt.num(c.changeAbs(), 0, "unknown"))
                    .append(", late_rate_pct ").append(fmt.percentNumber(c.check("late_rate").rate(), 1, "unknown"))
                    .append(", low_review_rate_pct ").append(fmt.percentNumber(c.check("low_review_rate").rate(), 1, "unknown"))
                    .append(", growth ").append(c.growthLevel())
                    .append(", size ").append(c.sizeLevel())
                    .append(", late_deliveries ").append(c.check("late_rate").level())
                    .append(", low_reviews ").append(c.check("low_review_rate").level())
                    .append(c.checked("cancel_rate") ? ", cancellations " + c.check("cancel_rate").level() : "")
                    .append(", readiness ").append(c.readiness())
                    .append(c.risks() != null ? ", risks " + (c.triggeredRisks(fmt).isEmpty() ? "none" : String.join(" and ", c.triggeredRisks(fmt))) : "").append('\n');
            // a response from before the profiles existed has none, and "unknown" figures would only mislead the model
            if (c.profile() != null && c.profile().recent() != null) out.append("  ").append(c.profile().recent().line(c.category(), fmt)).append('\n');
        }
        return out.toString().strip();
    }

    @Override
    protected String template(SalesOpportunities o) {
        SalesOpportunities.Forecast trend = o.trend();
        String head = trend.increasing()
                ? "Sales are forecast to rise about " + fmt.num(trend.changePct(), 1, "unknown") + "% against the last " + fmt.num(trend.recentMonths(), 0, "unknown") + " months. "
                : "Sales are not forecast to rise (" + fmt.num(trend.changePct(), 1, "unknown") + "% against the last " + fmt.num(trend.recentMonths(), 0, "unknown")
                  + " months), so this is about where to hold or shift effort rather than expand. ";
        if (o.candidates().isEmpty()) return head + "No category has enough recent sales to suggest.";
        Candidate top = o.candidates().getFirst();
        String why = switch (top.basis()) {
            case "beats_business" -> ", falling less than the business at ";
            case "best_available" -> ", with the smallest fall at ";
            default -> ", up ";
        };
        String ready = switch (String.valueOf(top.readiness())) {
            case "ready" -> "Its late-delivery, low-review and cancellation rates are in line with the business, so extra volume there looks manageable.";
            case "watch" -> "Its delivery, reviews and cancellations are in line with the business, but watch this: " + String.join(" and ", top.triggeredRisks(fmt)) + ".";
            case "fix_first" -> "Its late-delivery, low-review or cancellation rate is worse than the business, so fix that before pushing more volume.";
            default -> "Too few of its orders were delivered or reviewed to judge its reliability.";
        };
        return head + "The strongest place to look is " + fmt.label(top.category()) + why + fmt.num(top.changePct(), 1, "unknown")
                + "% (" + fmt.num(top.changeAbs(), 0, "unknown") + " BRL against the 3 months before). " + ready
                + " Growth in the past does not prove more investment would pay off, and sales are not profit.";
    }
}
