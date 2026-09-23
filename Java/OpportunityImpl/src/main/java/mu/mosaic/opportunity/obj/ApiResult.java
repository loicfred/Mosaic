package mu.mosaic.opportunity.obj;

import org.springframework.ui.Model;

import java.util.Map;

/** One call to the analytics API: its JSON body, or a message a person can act on. Exactly one is non-null. */
public record ApiResult(Map<String, Object> data, String error) {
    public static ApiResult ok(Map<String, Object> data) { return new ApiResult(data, null); }
    public static ApiResult failed(String error) { return new ApiResult(null, error); }

    /** Gives the page {@code name} (the JSON body) and {@code nameError} (why it is missing); returns the body. */
    public Map<String, Object> addTo(Model model, String name) {
        model.addAttribute(name, data);
        model.addAttribute(name + "Error", error);
        return data;
    }
}
