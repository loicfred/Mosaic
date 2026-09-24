package mu.mosaic.opportunity.obj.api;

import java.util.List;

/** Observed gross item sales and orders by month. */
public record SalesHistory(List<Month> months) {

    public record Month(String month, Double sales, Double orders) implements Monthly {}
}
