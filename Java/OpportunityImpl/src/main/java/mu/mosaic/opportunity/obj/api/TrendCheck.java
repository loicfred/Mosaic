package mu.mosaic.opportunity.obj.api;

import com.google.gson.annotations.SerializedName;
import mu.mosaic.opportunity.service.Formatter;
import org.solarframework.core.util.StringUtils;

import java.util.List;
import java.util.Locale;
import java.util.stream.Collectors;

/**
 * One trend caveat check, written from its {@code kind} (change, groups or gap), so a new check in the API needs no
 * code here.
 */
public record TrendCheck(String id, String kind, boolean triggered, String title,
                         Comparison comparison, Groups groups, Gap gap) implements Check {

    @Override
    public String sentence(Formatter fmt) {
        return switch (String.valueOf(kind)) {
            case "change" -> comparison.label() + ": " + fmt.movement(comparison.unit(), comparison) + ".";
            case "groups" -> groups.sentence(fmt);
            case "gap" -> gap.sentence(fmt);
            default -> title;
        };
    }

    /** A second measure of the business compared over the same windows. */
    public record Comparison(String label, String unit, Window recent, Window previous, Double change,
                             @SerializedName("change_unit") String changeUnit,
                             @SerializedName("change_pct") Double changePct) implements Moved {}

    /** The groups (categories, states) whose measure moved the wrong way by at least the threshold. */
    public record Groups(String label, @SerializedName("group_label") String groupLabel, String unit, Integer flagged, Integer of,
                         List<Group> worst, @SerializedName("worse_when") String worseWhen, Double threshold,
                         @SerializedName("threshold_unit") String thresholdUnit) {

        String sentence(Formatter fmt) {
            boolean up = "up".equals(worseWhen);
            String by = " by " + fmt.threshold(threshold, thresholdUnit) + " or more";
            String measure = String.valueOf(label).toLowerCase(Locale.ROOT);
            String groups = StringUtils.plural(String.valueOf(groupLabel));
            if (worst == null || worst.isEmpty())
                return "In none of the " + of + " " + groups + " with enough orders did the " + measure + (up ? " rise" : " fall") + by + ".";
            return flagged + " of " + of + " " + groups + " with enough orders: the " + measure + (up ? " rose" : " fell") + by + ". Largest: "
                    + worst.stream().map(w -> fmt.groupName(groupLabel, w.name()) + " " + fmt.unit(unit, w.previousValue()) + " → "
                            + fmt.unit(unit, w.recentValue())).collect(Collectors.joining(", ")) + ".";
        }
    }

    public record Group(String name, Window recent, Window previous, Double change,
                        @SerializedName("change_unit") String changeUnit,
                        @SerializedName("change_pct") Double changePct) implements Moved {}

    /** One measure on two sides of a split, e.g. late orders against on-time orders. */
    public record Gap(String label, String unit, Side worse, Side better, @SerializedName("min_orders") Double minOrders) {

        String sentence(Formatter fmt) {
            String figures = label + " in the last 3 months: " + fmt.unit(unit, worse.value()) + " for " + worse.label()
                    + ", " + fmt.unit(unit, better.value()) + " for " + better.label()
                    + " (" + fmt.unit("count", worse.orders()) + " and " + fmt.unit("count", better.orders()) + " orders).";
            boolean enough = worse.orders() != null && better.orders() != null && minOrders != null
                    && worse.orders() >= minOrders && better.orders() >= minOrders;
            return figures + (enough ? " They go together; that does not prove one causes the other." : " Too few orders on one side to judge.");
        }
    }

    public record Side(String label, Double orders, Double value) {}
}
