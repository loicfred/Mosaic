package mu.mosaic.opportunity.obj.api;

import java.util.List;

/** How recent sales split by one breakdown, largest share first. */
public record SalesMix(Double sales, Double orders, List<Row> rows) {

    public record Row(String group, Double share, Double sales, Double orders) {}
}
