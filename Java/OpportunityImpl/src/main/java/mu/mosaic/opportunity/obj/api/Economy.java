package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;
import java.util.Map;

/** Brazil's monthly economic indicators from the Central Bank: outside context, national figures. */
public record Economy(boolean available, List<Month> months, Map<String, String> series) {

    public record Month(String month,
                        @SerializedName("inflation_ipca_pct") Double inflationIpcaPct,
                        @SerializedName("usd_brl") Double usdBrl,
                        @SerializedName("selic_target_pct") Double selicTargetPct,
                        @SerializedName("unemployment_pct") Double unemploymentPct) implements Monthly {

        /** @param column the API's column name, e.g. "usd_brl" */
        public Double indicator(String column) {
            return switch (column) {
                case "inflation_ipca_pct" -> inflationIpcaPct;
                case "usd_brl" -> usdBrl;
                case "selic_target_pct" -> selicTargetPct;
                case "unemployment_pct" -> unemploymentPct;
                default -> null;
            };
        }
    }
}
