package mu.mosaic.opportunity.service.ai;

import java.util.LinkedHashMap;
import java.util.Map;

/** A written answer: @param source "llm" when the model wrote it, "template" otherwise, with the reason in {@code reason} */
public record Narrative(String text, String source, String model, String reason) {

    /** The answer's fields for a JSON reply, which the caller may add to. */
    public Map<String, Object> toJson() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("text", text);
        body.put("source", source);
        body.put("model", model);
        body.put("reason", reason);
        return body;
    }
}
