package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** A trend page's measure by month and its change over the last 3 months. */
public record TrendFigures(String measure, String label, String unit,
                           @SerializedName("good_direction") String goodDirection,
                           @SerializedName("group_label") String groupLabel,
                           TrendChange trend, List<MonthValue> monthly) implements TrendMeasure {}
