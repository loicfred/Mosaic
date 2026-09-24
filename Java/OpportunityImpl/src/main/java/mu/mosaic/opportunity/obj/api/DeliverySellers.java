package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** The sellers that deliver late most often. */
public record DeliverySellers(List<Seller> sellers) {

    public record Seller(@SerializedName("seller_id") String sellerId, @SerializedName("late_rate") Double lateRate, Double late, Double orders) {

        // seller ids are long hashes; the start is enough to tell them apart and keeps long digit runs out of the number check
        public String shortId() { return "seller " + sellerId.substring(0, Math.min(8, sellerId.length())); }
    }
}
