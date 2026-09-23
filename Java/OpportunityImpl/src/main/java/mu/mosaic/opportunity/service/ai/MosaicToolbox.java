package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.Formatter;
import org.solarframework.ai.AITool;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static mu.mosaic.opportunity.obj.ApiData.nestedObject;
import static mu.mosaic.opportunity.obj.ApiData.recordList;

/**
 * Everything the assistant may do: read-only calls to the analytics API, answered as short text formatted the
 * way the site shows it, so the model can quote figures rather than work them out. No tool writes anything,
 * runs SQL or reaches beyond the API.
 */
@Component
public class MosaicToolbox {
    private static final int MAX_ROWS = 12;
    private final MosaicApi api;
    private final Formatter fmt;

    public MosaicToolbox(MosaicApi api, Formatter fmt) {
        this.api = api;
        this.fmt = fmt;
    }

    /** The tools the assistant is allowed to call: exactly the methods below. */
    public static Set<String> names() {
        return Arrays.stream(MosaicToolbox.class.getMethods())
                .filter(method -> method.isAnnotationPresent(AITool.class))
                .map(method -> method.getName())
                .collect(Collectors.toSet());
    }

    @AITool(description = "Monthly gross item sales and orders for the last 6 months, the model's 3-month sales forecast with its range, and how the forecast compared with simple rules. Use for questions about sales trends or the forecast.")
    public String salesOverview() {
        ApiResult history = api.salesHistory();
        ApiResult forecast = api.salesForecast(3);
        if (history.data() == null) return unavailable(history);
        StringBuilder out = new StringBuilder("Observed monthly sales (BRL, gross item sales, not profit):\n");
        List<Map<String, Object>> months = recordList(history.data(), "months");
        months.subList(Math.max(0, months.size() - 6), months.size()).forEach(month -> out
                .append("- ")
                .append(month.get("month"))
                .append(": ")
                .append(fmt.brl(month.get("sales")))
                .append(", ")
                .append(fmt.num(month.get("orders"), 0))
                .append(" orders\n"));
        if (forecast.data() == null) return out.append("Forecast not available: ").append(forecast.error()).toString();
        out.append("Model forecast (a prediction, not a promise):\n");
        recordList(forecast.data(), "forecast").forEach(point -> out
                .append("- ")
                .append(point.get("month"))
                .append(": ")
                .append(fmt.brl(point.get("sales")))
                .append(" (range ")
                .append(fmt.brl(point.get("lower")))
                .append(" to ")
                .append(fmt.brl(point.get("upper")))
                .append(")\n"));
        Map<String, Object> evaluation = nestedObject(forecast.data(), "evaluation");
        out
                .append("Average miss over the last months: model ")
                .append(fmt.brl(nestedObject(evaluation, "model").get("mae")))
                .append(", 'same as last month' rule ")
                .append(fmt.brl(nestedObject(evaluation, "naive_last").get("mae")))
                .append(".\n");
        return out.append("Page: /").toString();
    }

    @AITool(description = "Whether the sales forecast rises and, if it does, the growing categories worth a closer look for investment, each checked against the business's late-delivery and low-review rates. Use for questions about where to invest or grow.")
    public String investmentOpportunities() {
        ApiResult result = api.salesOpportunities(3);
        if (result.data() == null) return unavailable(result);
        Map<String, Object> trend = nestedObject(result.data(), "trend");
        StringBuilder out = new StringBuilder("Average forecast month against the last 3 months: " + fmt.pct(trend.get("change_pct")) + ".\n");
        if (!Boolean.TRUE.equals(trend.get("increasing"))) return out.append("Sales are not forecast to rise, so no category is suggested.").toString();
        List<Map<String, Object>> candidates = recordList(result.data(), "candidates");
        if (candidates.isEmpty()) return out.append("No category grew at least as fast as the business with enough sales.").toString();
        out.append("Growing categories, best candidates first (last 3 months against the 3 before; sales are not profit). Growth is strong, moderate or weak against the business; size is large, medium or small by share of sales:\n");
        candidates.forEach(c -> {
            Map<String, Object> checks = nestedObject(c, "checks");
            out
                    .append("- ")
                    .append(c.get("category"))
                    .append(": ")
                    .append(fmt.pct(c.get("change_pct")))
                    .append(", ")
                    .append(fmt.brl(c.get("change_abs")))
                    .append(" more sales; ")
                    .append(c.get("growth_level"))
                    .append(" growth, ")
                    .append(c.get("size_level"))
                    .append(" category; late ")
                    .append(rateOrUnknown(nestedObject(checks, "late_rate").get("rate")))
                    .append(", low reviews ")
                    .append(rateOrUnknown(nestedObject(checks, "low_review_rate").get("rate")))
                    .append("; ")
                    .append("ready".equals(c.get("readiness")) ? "in line with the business" : "fix_first".equals(c.get("readiness")) ? "fix delivery first" : "not enough data")
                    .append('\n');
        });
        return out.append("Past growth does not prove investing will pay off. Page: /").toString();
    }

    @AITool(description = "Product categories with their sales in the last 3 months against the 3 before, compared with the whole business. filter is 'all', 'falling_behind' (flagged for falling well behind the business) or 'unusual_month' (latest month far from usual).")
    public String listCategories(String filter) {
        String flag = switch (filter == null ? "" : filter.toLowerCase(Locale.ROOT)) {
            case "falling_behind", "underperforming_total" -> "underperforming_total";
            case "unusual_month", "latest_month_anomaly" -> "latest_month_anomaly";
            default -> null;
        };
        ApiResult result = api.categories(flag);
        if (result.data() == null) return unavailable(result);
        StringBuilder out = new StringBuilder("Whole business: " + fmt.pct(result.data().get("total_change_pct")) + " (last 3 months against the 3 before). " + result.data().get("count") + " categories match; largest recent sales first:\n");
        recordList(result.data(), "categories").stream().limit(MAX_ROWS).forEach(category -> out
                .append("- ")
                .append(category.get("category"))
                .append(": ")
                .append(fmt.brl(category.get("recent")))
                .append(" recent, ")
                .append(fmt.brl(category.get("previous")))
                .append(" before, ")
                .append(fmt.pct(category.get("change_pct")))
                .append(flags(nestedObject(category, "flags")))
                .append(", evidence page /categories/")
                .append(category.get("category"))
                .append('\n'));
        return out.toString();
    }

    @AITool(description = "Why one product category is or is not flagged: its change against the whole business, the rule and threshold, and whether its latest month is unusual. category is the code, e.g. 'sports_leisure'.")
    public String explainCategory(String category) {
        String code = category == null ? "" : category.strip().toLowerCase(Locale.ROOT).replace(' ', '_');
        ApiResult result = api.category(code);
        if (result.data() == null) return unavailable(result);
        Map<String, Object> categoryData = result.data(), underperformance = nestedObject(nestedObject(categoryData, "evidence"), "underperforming_total"), anomaly = nestedObject(nestedObject(categoryData, "evidence"), "latest_month_anomaly"), flags = nestedObject(categoryData, "flags");
        StringBuilder out = new StringBuilder(code + ": " + fmt.brl(categoryData.get("recent")) + " in the last 3 months, " + fmt.brl(categoryData.get("previous")) + " in the 3 before, a change of " + fmt.pct(categoryData.get("change_pct")) + ". The whole business changed " + fmt.pct(categoryData.get("total_change_pct")) + ".\n");
        out
                .append("Falling behind the business: ")
                .append(Boolean.TRUE.equals(flags.get("underperforming_total")) ? "FLAGGED" : "not flagged")
                .append(". Gap ")
                .append(fmt.pp(underperformance.get("gap_pp")))
                .append("; the rule flags a gap of ")
                .append(fmt.pp(underperformance.get("threshold_pp")))
                .append(" or lower, with at least ")
                .append(fmt.brl(underperformance.get("min_support_sales")))
                .append(" of sales across both periods (this category: ")
                .append(fmt.brl(underperformance.get("support_sales")))
                .append(").\n");
        if (anomaly.containsKey("expected"))
            out
                    .append("Unusual latest month: ")
                    .append(Boolean.TRUE.equals(flags.get("latest_month_anomaly")) ? "FLAGGED" : "not flagged")
                    .append(". Latest month ")
                    .append(fmt.brl(anomaly.get("latest")))
                    .append(" against an average of ")
                    .append(fmt.brl(anomaly.get("expected")))
                    .append(" for the 3 months before; flagged when the difference exceeds ")
                    .append(fmt.brl(anomaly.get("threshold")))
                    .append(".\n");
        else out.append("Unusual latest month: not checked, too little history.\n");
        out.append("A flag says where to look, not why it happened. Evidence page: /categories/").append(code);
        return out.toString();
    }

    @AITool(description = "Late deliveries and low reviews: the recent share of orders delivered late, how often late and on-time orders get a 1 or 2 star review, and how well the late-delivery model ranks orders.")
    public String deliveryAndReviews() {
        ApiResult delivery = api.deliverySummary();
        ApiResult reviews = api.reviewSummary();
        if (delivery.data() == null) return unavailable(delivery);
        StringBuilder out = new StringBuilder("Share of delivered orders that arrived late, by month:\n");
        List<Map<String, Object>> monthly = recordList(delivery.data(), "monthly");
        monthly.subList(Math.max(0, monthly.size() - 4), monthly.size()).forEach(month -> out
                .append("- ")
                .append(month.get("month"))
                .append(": ")
                .append(fmt.rate(month.get("late_rate"), 1))
                .append(" (")
                .append(fmt.num(month.get("late"), 0))
                .append(" of ")
                .append(fmt.num(month.get("delivered"), 0))
                .append(")\n"));
        if (reviews.data() != null) {
            Map<String, Object> late = nestedObject(nestedObject(reviews.data(), "by_lateness"), "late"), onTime = nestedObject(nestedObject(reviews.data(), "by_lateness"), "on_time");
            out
                    .append("1 or 2 star reviews: ")
                    .append(fmt.rate(late.get("low_rate"), 1))
                    .append(" of late orders, ")
                    .append(fmt.rate(onTime.get("low_rate"), 1))
                    .append(" of on-time orders. This shows they go together, not that one causes the other.\n");
        }
        Map<String, Object> model = nestedObject(delivery.data(), "model"), evaluation = nestedObject(model, "evaluation");
        if (!evaluation.isEmpty()) out
                .append("Late-delivery model: ranking quality (ROC AUC) ")
                .append(fmt.num(evaluation.get("roc_auc"), 2))
                .append("; of the riskiest 10% it flags, ")
                .append(fmt.rate(nestedObject(evaluation, "top_10pct").get("precision"), 1))
                .append(" were late. Its scores rank orders; they are not chances.\n");
        return out.append("Page: /risk").toString();
    }

    @AITool(description = "Sellers with at least 30 delivered orders who deliver late most often, with their late rate recently and before.")
    public String leastReliableSellers() {
        ApiResult result = api.sellers(30, 10);
        if (result.data() == null) return unavailable(result);
        StringBuilder out = new StringBuilder("Least reliable sellers (at least 30 delivered orders):\n");
        recordList(result.data(), "sellers").forEach(seller -> out
                .append("- seller ")
                .append(seller.get("seller_id"))
                .append(": ")
                .append(fmt.rate(seller.get("late_rate"), 1))
                .append(" late over ")
                .append(seller.get("orders"))
                .append(" orders; last 3 months ")
                .append(seller.get("recent_late_rate") == null ? "no orders" : fmt.rate(seller.get("recent_late_rate"), 1))
                .append(", before that ")
                .append(fmt.rate(seller.get("earlier_late_rate"), 1))
                .append('\n'));
        return out.append("Page: /risk").toString();
    }

    @AITool(description = "A hypothetical scenario: what a sales change of salesChangePct percent (from -50 to 100) for months months (1 to 6) would mean for orders, late deliveries, low reviews and sellers pushed past their busiest month. Recent rates applied forward, not a forecast.")
    public String runSalesScenario(double salesChangePct, int months) {
        if (salesChangePct < -50 || salesChangePct > 100 || months < 1 || months > 6) return "Not run: the sales change must be between -50 and 100 percent and the months between 1 and 6.";
        ApiResult result = api.salesImpact(months, salesChangePct);
        if (result.data() == null) return unavailable(result);
        String link = "/scenario?run=1&change=" + String.format(Locale.US, "%.0f", salesChangePct) + "&horizon=" + months;
        Map<String, Object> consequences = nestedObject(result.data(), "consequences");
        if (consequences.isEmpty()) return "No scenario: there were no sales in the recent months to start from.";
        Map<String, Object> held = nestedObject(nestedObject(consequences, "late"), "rate_held"), fitted = nestedObject(nestedObject(consequences, "late"), "rate_fitted"), capacity = nestedObject(consequences, "sellers_at_capacity");
        StringBuilder out = new StringBuilder("Hypothetical, sales change " + fmt.pct(salesChangePct) + " for " + months + " months:\n");
        out
                .append("- ")
                .append(fmt.num(consequences.get("projected_monthly_orders"), 0))
                .append(" orders a month (")
                .append(fmt.change(consequences.get("extra_orders_per_month")))
                .append(" on the recent average)\n");
        out
                .append("- if the recent late rate of ")
                .append(fmt.rate(held.get("late_rate"), 2))
                .append(" holds: ")
                .append(fmt.num(held.get("expected_late_per_month"), 0))
                .append(" late deliveries and ")
                .append(fmt.num(held.get("expected_low_reviews_per_month"), 0))
                .append(" low reviews a month, ")
                .append(fmt.brl(held.get("sales_exposed_per_month")))
                .append(" of sales a month in late orders (exposure, not money lost)\n");
        if (!fitted.isEmpty()) out
                .append("- if the past link between volume and lateness holds (an association, not a cause): late rate ")
                .append(fmt.rate(fitted.get("late_rate"), 2))
                .append(", ")
                .append(fmt.num(fitted.get("expected_late_per_month"), 0))
                .append(" late deliveries a month\n");
        out
                .append("- ")
                .append(fmt.num(capacity.get("count"), 0))
                .append(" of ")
                .append(fmt.num(capacity.get("active_sellers"), 0))
                .append(" active sellers would handle more orders in a month than they ever have\n");
        return out.append("Open it: ").append(link).toString();
    }

    private static String unavailable(ApiResult r) { return "Not available right now: " + r.error(); }

    private String rateOrUnknown(Object rate) { return rate == null ? "too few orders" : fmt.rate(rate, 1); }

    private static String flags(Map<String, Object> f) {
        return (Boolean.TRUE.equals(f.get("underperforming_total")) ? ", flagged: falling behind" : "") + (Boolean.TRUE.equals(f.get("latest_month_anomaly")) ? ", flagged: unusual latest month" : "");
    }

}
