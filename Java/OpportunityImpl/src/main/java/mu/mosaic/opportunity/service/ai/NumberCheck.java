package mu.mosaic.opportunity.service.ai;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Keeps the model from inventing figures: every number in its text must be one it was given.
 * <p>The evidence is the API's JSON and the text the tools returned. Each figure is accepted in the ways a
 * writer would repeat it — rounded, with thousands separators, or as a percentage of a rate (0.0361 → 3.61).
 */
public final class NumberCheck {
    private static final Pattern NUMBER = Pattern.compile("\\d[\\d,]*(?:\\.\\d+)?");
    /** "three months", "top 5 sellers": small whole numbers are prose, not claims. */
    static final int SMALL_NUMBER_MAX = 12;
    private static final String[] FORMATS = {"%.0f", "%,.0f", "%.1f", "%,.1f", "%.2f", "%,.2f"};

    private NumberCheck() {}

    /** Every accepted rendering of every figure in a JSON body (maps, lists, numbers, and numbers written inside strings). */
    public static Set<String> allowedFrom(Object json) {
        Set<String> out = new HashSet<>();
        collect(json, out);
        return out;
    }

    /** Every accepted rendering of every number written in a text, e.g. a tool's reply. */
    public static Set<String> allowedFromText(String text) {
        Set<String> out = new HashSet<>();
        if (text == null) return out;
        Matcher m = NUMBER.matcher(text);
        while (m.find()) {
            out.add(m.group());
            Double v = parse(m.group());
            if (v != null) out.addAll(renderings(v));
        }
        return out;
    }

    /** Numbers in the text that no evidence supports, as written. */
    public static List<String> unsupported(String text, Set<String> allowed) {
        List<String> out = new ArrayList<>();
        if (text == null) return out;
        Matcher m = NUMBER.matcher(text);
        while (m.find()) {
            String token = m.group().replaceAll(",$", "");
            Double v = parse(token);
            if (v == null || (v <= SMALL_NUMBER_MAX && v == Math.floor(v))) continue;
            if (allowed.contains(token) || allowed.contains(token.replace(",", ""))) continue;
            out.add(token);
        }
        return out;
    }

    static Set<String> renderings(double value) {
        Set<String> out = new HashSet<>();
        for (double candidate : new double[]{value, value * 100}) {
            double abs = Math.abs(candidate);
            for (String f : FORMATS) out.add(String.format(Locale.US, f, abs));
            out.add(String.valueOf((long) abs));
        }
        return out;
    }

    private static void collect(Object node, Set<String> out) {
        switch (node) {
            case Number n -> out.addAll(renderings(n.doubleValue()));
            case String s -> out.addAll(allowedFromText(s));
            case Map<?, ?> m -> m.values().forEach(v -> collect(v, out));
            case List<?> l -> l.forEach(v -> collect(v, out));
            case null, default -> {}
        }
    }

    private static Double parse(String token) {
        try {
            return Double.parseDouble(token.replace(",", ""));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
