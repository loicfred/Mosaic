package mu.mosaic.opportunity.service.ai;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Keeps the model from inventing figures: every number in its text must be one it was given.
 * <p>Each check collects the numbers of the texts the model was shown (the evidence, its instructions, tool replies),
 * accepting each in the ways a writer would repeat it — rounded, with thousands separators, or as a percentage of a
 * rate (0.0361 → 3.61).
 */
public final class NumberCheck {
    private static final Pattern NUMBER = Pattern.compile("\\d[\\d,]*(?:\\.\\d+)?");
    /** "three months", "top 5 sellers": small whole numbers are prose, not claims. */
    private static final int SMALL_NUMBER_MAX = 12;
    private static final Pattern MONEY_BEFORE = Pattern.compile("(?i)(?:\\b(?:BRL|USD)|R\\$|US\\$)\\s*$");
    private static final Pattern QUANTITY_AFTER = Pattern.compile("(?i)^\\s*(?:%|pp\\b|percentage\\s+points?\\b|percent\\b|BRL\\b|USD\\b|R\\$|US\\$|reais\\b|dollars?\\b)");
    private static final String[] FORMATS = {"%.0f", "%,.0f", "%.1f", "%,.1f", "%.2f", "%,.2f"};
    // Some models group thousands with a no-break, narrow no-break or thin space ("2 032 405"); a plain space is left
    // alone, so two separate numbers are never read as one.
    private static final Pattern SPACED_THOUSANDS = Pattern.compile("(?<=\\d)[\u00A0\u202F\u2009](?=\\d{3}(?!\\d))");
    /** "461 k", "461 thousand", "1.2 million" after a figure: the figure is that scale, rounded as written. */
    private static final Pattern SCALE = Pattern.compile("^\\s?(k\\b|K\\b|thousand|mil\\b|million|m\\b|M\\b)");
    private final Set<String> allowed = new HashSet<>();

    /** Allows every number written in a text, e.g. the evidence or a tool's reply. */
    public NumberCheck allow(String text) {
        if (text == null) return this;
        Matcher m = NUMBER.matcher(text);
        while (m.find()) {
            allowed.add(m.group());
            Double v = parse(m.group());
            if (v != null) addRenderings(v);
        }
        return this;
    }

    /** Numbers in the text that nothing allowed supports, as written. */
    public List<String> unsupported(String text) {
        List<String> out = new ArrayList<>();
        if (text == null) return out;
        text = SPACED_THOUSANDS.matcher(text).replaceAll(",");
        Matcher m = NUMBER.matcher(text);
        while (m.find()) {
            String token = m.group().replaceAll(",$", "");
            Double v = parse(token);
            if (v == null) continue;
            if (v <= SMALL_NUMBER_MAX && v == Math.floor(v) && !explicitSmallClaim(text, m.start(), m.end())) continue;
            if (allowed.contains(token) || allowed.contains(token.replace(",", ""))) continue;
            if (scaledFromEvidence(token, v, text.substring(m.end()))) continue;
            out.add(token);
        }
        return out;
    }

    private boolean explicitSmallClaim(String text, int start, int end) {
        return MONEY_BEFORE.matcher(text.substring(0, start)).find()
                || QUANTITY_AFTER.matcher(text.substring(end)).find();
    }

    /**
     * Whether a figure written in thousands or millions is a faithful rounding of one the evidence holds, e.g.
     * "BRL 461 k" for 461,022. Only with a scale word right after it, so a bare "461" still has to be in the evidence.
     */
    private boolean scaledFromEvidence(String token, double value, String after) {
        Matcher scale = SCALE.matcher(after);
        if (!scale.find()) return false;
        double factor = scale.group(1).toLowerCase(Locale.ROOT).startsWith("m") ? 1_000_000 : 1_000;
        int dot = token.indexOf('.');
        double half = 0.5 * Math.pow(10, -(dot < 0 ? 0 : token.length() - dot - 1));
        for (String a : allowed) {
            Double given = parse(a);
            if (given != null && given >= factor && Math.abs(given / factor - value) <= half) return true;
        }
        return false;
    }

    private void addRenderings(double value) {
        for (double candidate : new double[]{value, value * 100}) {
            double abs = Math.abs(candidate);
            for (String f : FORMATS) allowed.add(String.format(Locale.US, f, abs));
            allowed.add(String.valueOf((long) abs));
        }
    }

    private Double parse(String token) {
        try {
            return Double.parseDouble(token.replace(",", ""));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
