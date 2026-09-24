package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** Customer states, most orders first, with their delivery and review figures. */
public record CustomerStates(List<State> states) {

    public record State(String state, Double orders, @SerializedName("late_rate") Double lateRate,
                        @SerializedName("average_delivery_days") Double averageDeliveryDays,
                        @SerializedName("low_review_rate") Double lowReviewRate) {

        /** @param key "orders", "late_rate", "average_delivery_days" or "low_review_rate" */
        public Double measure(String key) {
            return switch (key) {
                case "orders" -> orders;
                case "late_rate" -> lateRate;
                case "average_delivery_days" -> averageDeliveryDays;
                case "low_review_rate" -> lowReviewRate;
                default -> null;
            };
        }
    }
}
