package mu.mosaic.opportunity.service;

import mu.mosaic.opportunity.obj.api.Moved;
import org.solarframework.core.util.StringUtils;
import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.Map;

/**
 * Display formatting for templates, as {@code ${@format.brl(x)}}. Formatting only: a rate (0.0361) is shown as a
 * percentage (3.61%), and an amount recorded in reais is displayed converted to US dollars, for easier
 * visualization. A missing value shows as a dash, never as zero.
 */
@Component("format")
public class Formatter {
    private static final String MISSING = "—";
    /** Equal-month mean of Federal Reserve monthly USD/BRL averages, Jan 2017–Aug 2018; for scale only.
     * Source: https://fred.stlouisfed.org/data/EXBZUS */
    private static final double BRL_PER_USD = 3.33;

    public String brl(Object value) {
        if (!(value instanceof Number number)) return MISSING;
        String usd = String.format(Locale.US, "%,.0f", Math.abs(number.doubleValue()) / BRL_PER_USD);
        String sign = number.doubleValue() < 0 && !usd.equals("0") ? "−" : "";
        return sign + "$" + usd;
    }

    public String num(Object value, int digits) { return num(value, digits, MISSING); }

    /** As {@link #num(Object, int)}, with the words to write for a missing value, e.g. "unknown" in the model's evidence. */
    public String num(Object value, int digits, String missing) {
        return value instanceof Number number
                ? String.format(Locale.US, "%,." + digits + "f", number.doubleValue()) : missing;
    }

    /** A fraction as a bare percentage number for the model's evidence: 0.0361 -> "3.6"; {@code missing} when unknown. */
    public String percentNumber(Object rate, int digits, String missing) {
        return rate instanceof Number n ? num(n.doubleValue() * 100, digits, missing) : missing;
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

    /** A trend figure by the API's unit: rate as a percentage, brl as money, days, and counts (averages keep one decimal). */
    public String unit(String unit, Object value) {
        if (!(value instanceof Number n)) return MISSING;
        return switch (String.valueOf(unit)) {
            case "rate" -> rate(n, 1);
            case "brl" -> brl(n);
            case "days" -> num(n, 1) + " days";
            default -> num(n, countDigits(n.doubleValue()));
        };
    }

    /** A trend change by its change_unit ("−6.5 pp", "−2.1 days"); counts add their relative change ("+146, +13.7%"). */
    public String unitChange(Map<String, Object> moved) { return unitChange(moved.get("change"), moved.get("change_unit"), moved.get("change_pct")); }

    public String unitChange(Moved moved) { return unitChange(moved.change(), moved.changeUnit(), moved.changePct()); }

    private String unitChange(Object change, Object changeUnit, Object changePct) {
        if (!(change instanceof Number n)) return "no comparable change";
        String unit = String.valueOf(changeUnit);
        String main = switch (unit) {
            case "pp" -> pp(n);
            case "brl" -> insertDollarSign(formatSignedNumber(n.doubleValue() / BRL_PER_USD, "%,.0f"));
            case "days" -> formatSignedNumber(n, "%,.1f") + " days";
            default -> formatSignedNumber(n, "%,." + countDigits(n.doubleValue()) + "f");
        };
        return "count".equals(unit) && changePct instanceof Number pct ? main + ", " + pct(pct) : main;
    }

    /** "10.1% in the 3 months before, 3.6% in the last 3 (−6.5 pp)", from anything with previous, recent and a change. */
    public String movement(String unit, Moved moved) {
        return unit(unit, moved.previousValue()) + " in the 3 months before, "
                + unit(unit, moved.recentValue()) + " in the last 3 (" + unitChange(moved) + ")";
    }

    /** A group's name: categories are written readably, state codes stay as they are. */
    public String groupName(String groupLabel, Object name) {
        return "category".equals(groupLabel) ? label(name) : String.valueOf(name);
    }

    /** A check's threshold with its unit: "5%", "2 pp", "1.5 days". */
    public String threshold(Object threshold, Object unit) {
        if ("brl".equals(String.valueOf(unit))) {
            double usd = threshold instanceof Number n ? n.doubleValue() / BRL_PER_USD : 0;
            return threshold instanceof Number ? "$" + num(usd, usd == Math.rint(usd) ? 0 : 1) : "?";
        }
        String t = threshold instanceof Number n ? num(n, n.doubleValue() == Math.rint(n.doubleValue()) ? 0 : 1) : "?";
        return switch (String.valueOf(unit)) {
            case "pct" -> t + "%";
            case "pp" -> t + " pp";
            case "days" -> t + " days";
            default -> t;
        };
    }

    /** Whole counts and large averages without decimals; a smaller average such as 135.7 sellers a month keeps one. */
    private int countDigits(double v) { return v == Math.rint(v) || Math.abs(v) >= 1000 ? 0 : 1; }

    public String label(Object value) {
        return value instanceof String text ? StringUtils.readable(text) : MISSING;
    }

    public String date(Object value) {
        return value instanceof String text && text.length() >= 10 ? text.substring(0, 10) : MISSING;
    }

    /** Puts the $ sign after a leading +/− so "+123" becomes "+$123". */
    private String insertDollarSign(String signedMagnitude) {
        return signedMagnitude.startsWith("+") || signedMagnitude.startsWith("−")
                ? signedMagnitude.charAt(0) + "$" + signedMagnitude.substring(1) : "$" + signedMagnitude;
    }

    private String formatSignedNumber(Object value, String format) {
        if (!(value instanceof Number number)) return MISSING;
        String magnitude = String.format(Locale.US, format, Math.abs(number.doubleValue()));
        // the sign follows what is displayed, so -0.04 shows as 0.0%, not −0.0%
        boolean roundsToZero = magnitude.replaceAll("[^1-9]", "").isEmpty();
        return (roundsToZero ? "" : number.doubleValue() > 0 ? "+" : "−") + magnitude;
    }
}
