package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;
import mu.mosaic.opportunity.service.Formatter;

import java.util.List;
import java.util.stream.Collectors;

/** The hidden problems the API checks for behind a good sales result. */
public record SalesCaveats(List<SalesCheck> checks) {

    public List<SalesCheck> checks() { return checks == null ? List.of() : checks; }

    /** One check; its evidence holds only the figures its id needs. */
    public record SalesCheck(String id, boolean triggered, String title, Evidence evidence) implements Check {

        @Override
        public String sentence(Formatter fmt) {
            Evidence e = evidence;
            return switch (String.valueOf(id)) {
                case "categories_falling_behind" -> e.flagged() + " of " + e.categories() + " categories fell well behind the business ("
                        + fmt.pct(e.totalChangePct()) + " overall), with " + fmt.brl(e.salesLostByFlagged() == null ? null : -e.salesLostByFlagged())
                        + " less sales between them. Largest drops: "
                        + e.worst().stream().map(c -> fmt.label(c.category()) + " " + fmt.pct(c.changePct())).collect(Collectors.joining(", ")) + ".";
                case "late_rate_rising" -> rate("Orders delivered late", fmt);
                case "low_reviews_rising" -> rate("Orders reviewed 1 or 2 stars", fmt);
                case "late_orders_get_low_reviews" -> (e.period() == null ? "Overall, l" : "From " + e.period().start() + " to " + e.period().end() + ", l")
                        + "ate orders got a 1 or 2 star review " + fmt.rate(e.late().lowRate(), 1)
                        + " of the time, on-time orders " + fmt.rate(e.onTime().lowRate(), 1) + ". They go together; that does not prove one causes the other.";
                case "cancellations_rising" -> rate("Orders cancelled or unavailable", fmt);
                case "instalments_rising" -> rate("Orders paid in more than one instalment", fmt)
                        + " Instalments show how customers paid, not when the sellers were paid.";
                case "basket_shrinking" -> "Average order value: " + fmt.brl(e.recent().value()) + " in the last 3 months against "
                        + fmt.brl(e.previous().value()) + " in the 3 before (" + fmt.pct(e.changePct()) + ").";
                case "freight_share_rising" -> "Freight came to " + fmt.rate(e.recent().value(), 1) + " of item sales in the last 3 months against "
                        + fmt.rate(e.previous().value(), 1) + " in the 3 before (" + fmt.pp(e.changePp()) + ").";
                case "few_returning_customers" -> "Only " + fmt.rate(e.rate(), 1) + " of the last 3 months' orders came from someone who had ordered before ("
                        + fmt.num(e.returning(), 0) + " of " + fmt.num(e.customers(), 0) + "), so growth rests on new customers.";
                case "sales_rest_on_few_sellers" -> "The top " + e.topSellers() + " of " + fmt.num(e.sellers(), 0) + " sellers made "
                        + fmt.rate(e.share(), 1) + " of the last 3 months' sales.";
                case "sales_rest_on_one_state" -> "Customers in " + e.state() + " bought " + fmt.rate(e.share(), 1)
                        + " of the last 3 months' sales, across " + fmt.num(e.states(), 0) + " states.";
                default -> title;
            };
        }

        private String rate(String what, Formatter fmt) {
            return what + ": " + fmt.rate(evidence.recent().rate(), 1) + " in the last 3 months against "
                    + fmt.rate(evidence.previous().rate(), 1) + " in the 3 before (" + fmt.pp(evidence.changePp())
                    + "). Recent months may still have orders on their way.";
        }
    }

    /** Every figure any sales check reports; a check fills only its own. */
    public record Evidence(Integer flagged, Integer categories,
                           @SerializedName("total_change_pct") Double totalChangePct,
                           @SerializedName("sales_lost_by_flagged") Double salesLostByFlagged,
                           List<Category> worst, Period recent, Period previous,
                           @SerializedName("change_pp") Double changePp,
                           @SerializedName("change_pct") Double changePct,
                           LowReviews late, @SerializedName("on_time") LowReviews onTime, DateRange period,
                           Double rate, Double returning, Double customers,
                           @SerializedName("top_sellers") Integer topSellers, Double sellers, Double share,
                           String state, Double states) {

        public List<Category> worst() { return worst == null ? List.of() : worst; }
    }

    public record Category(String category, @SerializedName("change_pct") Double changePct) {}

    /** A window of a rate or an average: the check fills the one it measures. */
    public record Period(Double rate, Double value) {}

    public record DateRange(String start, String end) {}
}
