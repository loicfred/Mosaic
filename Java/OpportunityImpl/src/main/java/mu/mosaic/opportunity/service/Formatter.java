package mu.mosaic.opportunity.service;

import org.solarframework.core.util.StringUtils;
import org.springframework.stereotype.Component;

import java.util.Locale;

/**
 * Display formatting for templates, as {@code ${@format.brl(x)}}. Formatting only: a rate (0.0361) is shown as a
 * percentage (3.61%), and an amount in reais also shows its approximate value in US dollars. A missing value shows as
 * a dash, never as zero.
 */
@Component("format")
public class Formatter {
    public static final String MISSING = "—";
    /** Reais per US dollar: a rough average over the data's range (January 2017 to August 2018), for scale only. */
    public static final double BRL_PER_USD = 3.4;

    public String brl(Object value) {
        if (!(value instanceof Number number)) return MISSING;
        String magnitude = String.format(Locale.US, "%,.0f", Math.abs(number.doubleValue()));
        String usd = String.format(Locale.US, "%,.0f", Math.abs(number.doubleValue()) / BRL_PER_USD);
        String sign = number.doubleValue() < 0 && !magnitude.equals("0") ? "−" : "";
        return sign + "BRL " + magnitude + " (≈ " + (usd.equals("0") ? "" : sign) + "USD " + usd + ")";
    }

    public String num(Object value, int digits) {
        return value instanceof Number number
                ? String.format(Locale.US, "%,." + digits + "f", number.doubleValue()) : MISSING;
    }

    /** A fraction as a percentage: 0.0361 -> 3.61%. */
    public String rate(Object value, int digits) {
        return value instanceof Number number
                ? String.format(Locale.US, "%." + digits + "f%%", number.doubleValue() * 100) : MISSING;
    }

    /** A value already in percent, signed: -28.2 -> −28.2%. */
    public String pct(Object value) { return formatSignedNumber(value, "%.1f%%"); }

    /** Percentage points, signed: 3.54 -> +3.5 pp. */
    public String pp(Object value) { return formatSignedNumber(value, "%.1f pp"); }

    /** A signed whole-number change: -1253.3 -> −1,253. */
    public String change(Object value) { return formatSignedNumber(value, "%,.0f"); }

    /** A 0–1 ranking score as a 0–100 score. */
    public String score(Object value) {
        return value instanceof Number number ? String.valueOf(Math.round(number.doubleValue() * 100)) : MISSING;
    }

    public String label(Object value) {
        return value instanceof String text ? StringUtils.readable(text) : MISSING;
    }

    public String date(Object value) {
        return value instanceof String text && text.length() >= 10 ? text.substring(0, 10) : MISSING;
    }

    private static String formatSignedNumber(Object value, String format) {
        if (!(value instanceof Number number)) return MISSING;
        String magnitude = String.format(Locale.US, format, Math.abs(number.doubleValue()));
        // the sign follows what is displayed, so -0.04 shows as 0.0%, not −0.0%
        boolean roundsToZero = magnitude.replaceAll("[^1-9]", "").isEmpty();
        return (roundsToZero ? "" : number.doubleValue() > 0 ? "+" : "−") + magnitude;
    }
}
