package mu.mosaic.opportunity.obj.api;

/** Anything the API compares over two windows: the last 3 months against the 3 before, and the change between them. */
public interface Moved {
    Window recent();

    Window previous();

    Double change();

    /** "pp", "pct", "brl", "days" or "count" */
    String changeUnit();

    Double changePct();

    default Double recentValue() { return recent() == null ? null : recent().value(); }

    default Double previousValue() { return previous() == null ? null : previous().value(); }

    default Double recentOrders() { return recent() == null ? null : recent().orders(); }
}
