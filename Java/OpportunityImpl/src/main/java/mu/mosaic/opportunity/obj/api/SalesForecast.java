package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** The sales forecast with its range, and how its past predictions compared with simple rules. */
public record SalesForecast(@SerializedName("forecast_method") String forecastMethod, List<Point> forecast, Evaluation evaluation) {

    public record Point(String month, Double sales, Double lower, Double upper) implements Monthly {}

    /** The average miss on held-out months of the model and of two simple rules. */
    public record Evaluation(Score model, @SerializedName("naive_last") Score naiveLast, @SerializedName("mean_last_3") Score meanLast3) {}

    public record Score(Double mae) {}
}
