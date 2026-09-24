package mu.mosaic.opportunity.obj;

import org.solarframework.json.JSONItem;
import org.springframework.ui.Model;

import java.util.Map;

/**
 * One call to the analytics API: its JSON body, or a message a person can act on. Exactly one is non-null. Pages
 * render the body as it is; Java code reads it as one of the typed replies in {@code obj.api}.
 */
public record ApiResult(Map<String, Object> data, String error, int status) {
    public ApiResult(Map<String, Object> data) { this(data, null, 200); }

    public ApiResult(String error, int status) { this(null, error, status); }

    public boolean failed() { return data == null; }

    /** The body as a typed reply; null when the call failed. */
    public <T> T as(Class<T> type) {
        return failed() ? null : JSONItem.SimpleGSON.fromJson(JSONItem.SimpleGSON.toJsonTree(data), type);
    }

    /** Gives the page {@code name} (the JSON body) and {@code nameError} (why it is missing); returns the body. */
    public Map<String, Object> addTo(Model model, String name) {
        model.addAttribute(name, data);
        model.addAttribute(name + "Error", error);
        return data;
    }
}
