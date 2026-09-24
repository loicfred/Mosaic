package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;
import java.util.Map;

/** Where a trend page's improvement points to an opportunity: the groups that improved at least as much as the business. */
public record TrendOpportunities(String measure, String label, String unit,
                                 @SerializedName("good_direction") String goodDirection,
                                 @SerializedName("group_label") String groupLabel,
                                 TrendChange trend, List<Candidate> candidates) implements TrendMeasure {

    public List<Candidate> candidates() { return candidates == null ? List.of() : candidates; }

    /**
     * An improving group and its rates against the business.
     * @param readiness "ready", "fix_first" or "unknown"
     */
    public record Candidate(String name, Window recent, Window previous, Double change,
                            @SerializedName("change_unit") String changeUnit,
                            @SerializedName("change_pct") Double changePct,
                            Map<String, Rate> checks, String readiness) implements Moved {

        public Map<String, Rate> checks() { return checks == null ? Map.of() : checks; }
    }
}
