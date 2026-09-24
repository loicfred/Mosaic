package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;
import mu.mosaic.opportunity.service.Formatter;

import java.util.List;
import java.util.Map;

/** Where the data points for investment: the sales forecast's direction and the candidate categories, best first. */
public record SalesOpportunities(Forecast trend, List<Candidate> candidates,
                                 @SerializedName("business_rates") Map<String, Rate> businessRates,
                                 @SerializedName("business_profile") Profiles businessProfile) {

    public List<Candidate> candidates() { return candidates == null ? List.of() : candidates; }

    public Rate businessRate(String name) { return businessRates == null ? Rate.NONE : businessRates.getOrDefault(name, Rate.NONE); }

    /** The average forecast month against the average of the last months. */
    public record Forecast(@SerializedName("recent_months") Double recentMonths,
                           @SerializedName("recent_monthly_mean") Double recentMonthlyMean,
                           @SerializedName("forecast_monthly_mean") Double forecastMonthlyMean,
                           @SerializedName("change_pct") Double changePct, boolean increasing) {}

    /**
     * A category worth a look.
     * @param basis     "growing" (up at least as fast as the business), "beats_business" (falling less) or "best_available"
     * @param readiness "ready", "watch", "fix_first" or "unknown"
     * @param risks     null in a reply from before the profiles existed
     */
    public record Candidate(String category, String basis,
                            @SerializedName("change_pct") Double changePct,
                            @SerializedName("change_abs") Double changeAbs,
                            @SerializedName("growth_level") String growthLevel,
                            @SerializedName("size_level") String sizeLevel,
                            Map<String, Rate> checks, String readiness, List<Risk> risks, Profiles profile) {

        public String basis() { return basis == null ? "growing" : basis; }

        public Rate check(String name) { return checks == null ? Rate.NONE : checks.getOrDefault(name, Rate.NONE); }

        public boolean checked(String name) { return checks != null && checks.containsKey(name); }

        /** The triggered profile risks, in words. */
        public List<String> triggeredRisks(Formatter fmt) {
            return risks == null ? List.of() : risks.stream().filter(Risk::triggered).map(r -> r.describe(fmt)).toList();
        }
    }

    /** A risk the growth figures alone do not show, e.g. sales resting on one seller. */
    public record Risk(String id, boolean triggered, Double value, Double business, @SerializedName("change_pct") Double changePct) {

        String describe(Formatter fmt) {
            return switch (String.valueOf(id)) {
                case "depends_on_one_seller" -> "one seller makes " + fmt.percentNumber(value, 0, "unknown") + "% of its sales";
                case "freight_heavy" -> "freight is " + fmt.percentNumber(value, 1, "unknown") + "% of its sales against "
                        + fmt.percentNumber(business, 1, "unknown") + "% for the business";
                case "basket_shrinking" -> "its average order fell " + fmt.num(changePct, 1, "unknown") + "%";
                default -> String.valueOf(id);
            };
        }
    }

    public record Profiles(Profile recent, Profile previous) {}

    /** Basket, freight, payments, repeat customers and the seller base over one window. */
    public record Profile(@SerializedName("average_order_value") Double averageOrderValue,
                          @SerializedName("freight_share") Double freightShare,
                          Rate cancel,
                          @SerializedName("multi_instalment") Rate multiInstalment,
                          @SerializedName("card_payment") Rate cardPayment,
                          @SerializedName("returning_customer") Rate returningCustomer,
                          Double sellers,
                          @SerializedName("top_seller_share") Double topSellerShare,
                          @SerializedName("average_review_score") Double averageReviewScore) {

        /** The profile figures the model may quote, as one evidence line. */
        public String line(String who, Formatter fmt) {
            return who + " last 3 months: average_order_value_brl " + fmt.num(averageOrderValue, 0, "unknown")
                    + ", freight_share_pct " + fmt.percentNumber(freightShare, 1, "unknown")
                    + ", cancel_rate_pct " + fmt.percentNumber(cancel == null ? null : cancel.rate(), 1, "unknown")
                    + ", multi_instalment_pct " + fmt.percentNumber(multiInstalment == null ? null : multiInstalment.rate(), 1, "unknown")
                    + ", card_payment_pct " + fmt.percentNumber(cardPayment == null ? null : cardPayment.rate(), 1, "unknown")
                    + ", returning_customer_pct " + fmt.percentNumber(returningCustomer == null ? null : returningCustomer.rate(), 1, "unknown")
                    + ", sellers " + fmt.num(sellers, 0, "unknown")
                    + ", top_seller_share_pct " + fmt.percentNumber(topSellerShare, 1, "unknown")
                    + ", average_review_score " + fmt.num(averageReviewScore, 1, "unknown");
        }
    }
}
