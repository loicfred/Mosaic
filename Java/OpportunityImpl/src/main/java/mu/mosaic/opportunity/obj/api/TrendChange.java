package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

/** A trend page's measure, the last 3 months against the 3 before; improving follows the measure's good direction. */
public record TrendChange(Window recent, Window previous, Double change,
                          @SerializedName("change_unit") String changeUnit,
                          @SerializedName("change_pct") Double changePct,
                          boolean improving) implements Moved {}
