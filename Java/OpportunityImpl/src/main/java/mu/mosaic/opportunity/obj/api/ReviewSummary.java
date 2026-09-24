package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

/** How often late and on-time orders get a 1 or 2 star review. */
public record ReviewSummary(@SerializedName("by_lateness") ByLateness byLateness) {

    public record ByLateness(LowReviews late, @SerializedName("on_time") LowReviews onTime) {}
}
