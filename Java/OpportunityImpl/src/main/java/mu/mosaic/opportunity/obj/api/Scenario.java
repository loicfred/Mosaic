package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

/**
 * A what-if: a sales change applied to the recent months, and what it would mean for orders, late deliveries and
 * sellers. Hypothetical: recent rates applied forward, not a forecast.
 * @param consequences null when there were no recent sales to start from
 */
public record Scenario(Input scenario, Baseline baseline, Consequences consequences, Evidence evidence) {

    public record Input(Integer horizon, @SerializedName("sales_change_pct") Double salesChangePct) {}

    public record Baseline(@SerializedName("monthly_sales") Double monthlySales,
                           @SerializedName("monthly_orders") Double monthlyOrders) {}

    public record Consequences(@SerializedName("projected_monthly_sales") Double projectedMonthlySales,
                               @SerializedName("projected_monthly_orders") Double projectedMonthlyOrders,
                               @SerializedName("extra_orders_per_month") Double extraOrdersPerMonth,
                               Late late,
                               @SerializedName("sellers_at_capacity") Capacity sellersAtCapacity) {}

    /** Late deliveries at the recent rate, and at the rate the volume link fitted in past months would give. */
    public record Late(@SerializedName("rate_held") LateCase rateHeld, @SerializedName("rate_fitted") LateCase rateFitted) {}

    public record LateCase(@SerializedName("late_rate") Double lateRate,
                           @SerializedName("expected_late_per_month") Double expectedLatePerMonth,
                           @SerializedName("expected_low_reviews_per_month") Double expectedLowReviewsPerMonth,
                           @SerializedName("sales_exposed_per_month") Double salesExposedPerMonth) {}

    /** Sellers the change would push past their busiest month. */
    public record Capacity(Integer count, @SerializedName("active_sellers") Integer activeSellers) {}

    public record Evidence(Double aov, @SerializedName("p_low_given_late") Double pLowGivenLate,
                           @SerializedName("p_low_given_on_time") Double pLowGivenOnTime) {}
}
