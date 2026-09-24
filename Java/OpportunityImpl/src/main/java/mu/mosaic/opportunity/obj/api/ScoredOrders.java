package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** Orders a risk model rated, riskiest first: a predicted risk, not an outcome. */
public record ScoredOrders(@SerializedName("model_version") String modelVersion, List<Order> orders) {

    public record Order(String category, @SerializedName("seller_state") String sellerState,
                        @SerializedName("customer_state") String customerState, Double risk,
                        @SerializedName("total_price") Double totalPrice, @SerializedName("days_late") Double daysLate) {}
}
