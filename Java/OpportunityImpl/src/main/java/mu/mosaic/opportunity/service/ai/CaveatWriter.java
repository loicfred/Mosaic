package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.service.Formatter;
import mu.mosaic.opportunity.service.ai.ScenarioNarrator.Narrative;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static mu.mosaic.opportunity.obj.ApiData.nestedObject;
import static mu.mosaic.opportunity.obj.ApiData.recordList;

/**
 * The hidden problems behind a good sales result, from the API's caveat checks. Each check becomes one sentence
 * with its figures; the {@code CaveatWriter} chatbot may rewrite them, checked by {@link CheckedWriter}.
 */
@Component
public class CaveatWriter {
    private static final Formatter FMT = new Formatter();
    private final LocalAi ai;

    public CaveatWriter(LocalAi ai) { this.ai = ai; }

    public Narrative explain(Map<String, Object> caveats) {
        String fallback = template(caveats);
        if (recordList(caveats, "checks").stream().noneMatch(CaveatWriter::triggered)) return new Narrative(fallback, "template", null, "nothing_found");
        return CheckedWriter.write(ai, LocalAi.CAVEATS, "Here are the checks, already calculated:\n\n" + fallback, fallback);
    }

    /** One line per check, found problems first; the same lines are the model's only evidence. */
    static String template(Map<String, Object> caveats) {
        List<String> found = new ArrayList<>(), clear = new ArrayList<>();
        for (Map<String, Object> check : recordList(caveats, "checks")) (triggered(check) ? found : clear).add(sentence(check));
        StringBuilder out = new StringBuilder(found.isEmpty()
                ? "None of the checks found a hidden problem behind the sales result.\n"
                : "Found behind the sales result:\n" + found.stream().map(line -> "• " + line).collect(Collectors.joining("\n")) + "\n");
        if (!clear.isEmpty()) out.append("\nChecked, nothing found:\n").append(clear.stream().map(line -> "• " + line).collect(Collectors.joining("\n"))).append('\n');
        return out.append("\nA caveat says where to look, not why it happened.").toString();
    }

    private static boolean triggered(Map<String, Object> check) { return Boolean.TRUE.equals(check.get("triggered")); }

    private static String sentence(Map<String, Object> check) {
        Map<String, Object> e = nestedObject(check, "evidence");
        return switch (String.valueOf(check.get("id"))) {
            case "categories_falling_behind" -> e.get("flagged") + " of " + e.get("categories") + " categories fell well behind the business ("
                    + FMT.pct(e.get("total_change_pct")) + " overall), with " + FMT.brl(neg(e.get("sales_lost_by_flagged"))) + " less sales between them. Largest drops: "
                    + recordList(e, "worst").stream().map(c -> FMT.label(c.get("category")) + " " + FMT.pct(c.get("change_pct"))).collect(Collectors.joining(", ")) + ".";
            case "late_rate_rising" -> rate("Orders delivered late", e);
            case "low_reviews_rising" -> rate("Orders reviewed 1 or 2 stars", e);
            case "late_orders_get_low_reviews" -> "Late orders got a 1 or 2 star review " + FMT.rate(nestedObject(e, "late").get("low_rate"), 1)
                    + " of the time, on-time orders " + FMT.rate(nestedObject(e, "on_time").get("low_rate"), 1) + ". They go together; that does not prove one causes the other.";
            default -> String.valueOf(check.get("title"));
        };
    }

    private static String rate(String what, Map<String, Object> e) {
        return what + ": " + FMT.rate(nestedObject(e, "recent").get("rate"), 1) + " in the last 3 months against "
                + FMT.rate(nestedObject(e, "previous").get("rate"), 1) + " in the 3 before (" + FMT.pp(e.get("change_pp"))
                + "). Recent months may still have orders on their way.";
    }

    private static Object neg(Object v) { return v instanceof Number n ? -n.doubleValue() : v; }
}
