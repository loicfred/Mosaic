package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** Categories, largest recent sales first, the last 3 months against the 3 before. */
public record Categories(@SerializedName("total_change_pct") Double totalChangePct, Integer count, List<Category> categories) {

    public record Category(String category, Double recent, Double previous,
                           @SerializedName("change_pct") Double changePct,
                           @SerializedName("share_recent") Double shareRecent) {}
}
