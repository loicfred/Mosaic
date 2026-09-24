package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** The late-delivery rate of delivered orders by month. */
public record DeliverySummary(List<Month> monthly) {

    public record Month(String month, @SerializedName("late_rate") Double lateRate, Double late, Double delivered) implements Monthly {}
}
