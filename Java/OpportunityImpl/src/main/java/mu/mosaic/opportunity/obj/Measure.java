package mu.mosaic.opportunity.obj;

import java.util.Arrays;
import java.util.Optional;

/**
 * The measures with a trend page, each laid out as the Sales page for one figure; the title is the page name. The API path comes from here, never
 * from the request, so no free text reaches a URL.
 */
public enum Measure {
    DELIVERY("delivery", "Delivery", "Are deliveries getting faster?"),
    REVIEWS("reviews", "Reviews", "Are customers happier?"),
    SELLERS("sellers", "Sellers", "Are more sellers selling?");

    private final String path, title, question;

    Measure(String path, String title, String question) {
        this.path = path;
        this.title = title;
        this.question = question;
    }

    public String path() { return path; }

    public String title() { return title; }

    public String question() { return question; }

    public static Optional<Measure> fromPath(String path) {
        return Arrays.stream(values()).filter(m -> m.path.equals(path)).findFirst();
    }
}
