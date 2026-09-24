package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** Orders and sales by weekday or by hour. */
public record BuyingTimes(List<Slot> slots) {

    public record Slot(String slot, Double orders, @SerializedName("share_of_orders") Double shareOfOrders) {}
}
