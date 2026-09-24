package mu.mosaic.opportunity.obj.api;

/** One month of a single measure. */
public record MonthValue(String month, Double value) implements Monthly {}
