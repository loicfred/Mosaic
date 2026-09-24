package mu.mosaic.opportunity.obj.api;

import java.util.List;
import java.util.Map;

/** Business measures by month; each month row holds every measure under its key. */
public record SalesMetrics(Map<String, Metric> metrics, List<Map<String, Object>> monthly) {

    public record Metric(String unit, String label) {}

    /** One measure's months. */
    public List<MonthValue> series(String key) {
        return monthly.stream().map(r -> new MonthValue(String.valueOf(r.get("month")), r.get(key) instanceof Number n ? n.doubleValue() : null)).toList();
    }
}
