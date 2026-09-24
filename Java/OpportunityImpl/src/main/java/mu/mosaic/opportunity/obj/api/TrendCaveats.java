package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** A trend page's caveat checks: problems that may hide behind its measure's result. */
public record TrendCaveats(String measure, String label, String unit,
                           @SerializedName("good_direction") String goodDirection,
                           @SerializedName("group_label") String groupLabel,
                           TrendChange trend, List<TrendCheck> checks) implements TrendMeasure {

    public List<TrendCheck> checks() { return checks == null ? List.of() : checks; }
}
