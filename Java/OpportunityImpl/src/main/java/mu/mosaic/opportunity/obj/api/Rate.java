package mu.mosaic.opportunity.obj.api;

/** A share of orders, e.g. the late-delivery rate, with how it compares with the business when the API judged it. */
public record Rate(Double orders, Double rate, String level) {
    /** For a rate the reply does not hold: every figure unknown. */
    public static final Rate NONE = new Rate(null, null, null);
}
