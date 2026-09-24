package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** One category's sales, change, share of the business, flags and short forecast. */
public record CategoryDetail(String category, Double recent, Double previous,
                             @SerializedName("change_pct") Double changePct,
                             @SerializedName("total_change_pct") Double totalChangePct,
                             @SerializedName("share_recent") Double shareRecent,
                             @SerializedName("share_previous") Double sharePrevious,
                             Flags flags, List<Point> series, List<Point> forecast) {

    public record Flags(@SerializedName("underperforming_total") boolean underperformingTotal,
                        @SerializedName("latest_month_anomaly") boolean latestMonthAnomaly) {}

    public record Point(String month, Double sales) implements Monthly {}
}
