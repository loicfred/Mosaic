package mu.mosaic.opportunity.obj.api;

import java.util.Locale;

/** What every trend reply (delivery, reviews, sellers) says about its measure and how it moved. */
public interface TrendMeasure {
    String measure();

    String label();

    /** "rate", "brl", "days" or "count" */
    String unit();

    String goodDirection();

    String groupLabel();

    TrendChange trend();

    /** "lower" or "higher": which way is good for this measure. */
    default String better() { return "down".equals(goodDirection()) ? "lower" : "higher"; }

    /** The label as it reads inside a sentence: "late-delivery rate". */
    default String measureName() { return String.valueOf(label()).toLowerCase(Locale.ROOT); }
}
