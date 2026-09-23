package mu.mosaic.opportunity.obj;

import java.util.List;
import java.util.Map;

/** Reads optional nested blocks from the analytics API's JSON responses. */
public final class ApiData {
    private ApiData() {}

    @SuppressWarnings("unchecked")
    public static Map<String, Object> nestedObject(Map<String, Object> body, String key) {
        return body != null && body.get(key) instanceof Map<?, ?> value
                ? (Map<String, Object>) value : Map.of();
    }

    @SuppressWarnings("unchecked")
    public static List<Map<String, Object>> recordList(Map<String, Object> body, String key) {
        return body != null && body.get(key) instanceof List<?> value
                ? (List<Map<String, Object>>) value : List.of();
    }

    /** The last record of a list, e.g. the latest month; null when absent or empty. */
    public static Map<String, Object> last(Map<String, Object> body, String key) {
        List<Map<String, Object>> records = recordList(body, key);
        return records.isEmpty() ? null : records.getLast();
    }
}
