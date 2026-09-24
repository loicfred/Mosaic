package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

/** How often a group of orders was rated 1 or 2 stars. */
public record LowReviews(@SerializedName("low_rate") Double lowRate) {}
