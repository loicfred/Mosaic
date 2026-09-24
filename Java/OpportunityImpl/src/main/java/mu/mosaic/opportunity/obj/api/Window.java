package mu.mosaic.opportunity.obj.api;

/** A measure over one comparison window, e.g. the last 3 months: its value and the orders behind it. */
public record Window(Double value, Double orders) {}
