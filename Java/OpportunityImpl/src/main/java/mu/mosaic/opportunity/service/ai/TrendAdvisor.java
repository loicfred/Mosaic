package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.api.TrendOpportunities;
import mu.mosaic.opportunity.obj.api.TrendOpportunities.Candidate;
import mu.mosaic.opportunity.service.Formatter;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.stream.Collectors;

/**
 * On a trend page, says where an improvement points to an opportunity, from the API's improving groups and their
 * checks against the business. As {@link InvestmentAdvisor}: the {@code TrendAdvisor} chatbot only rewrites the
 * figures given, checked by {@link CheckedWriter}, and the fixed text is kept otherwise.
 */
@Component
public class TrendAdvisor extends CheckedWriter<TrendOpportunities> {

    public TrendAdvisor(LocalAi ai, Formatter fmt) { super(ai, LocalAi.Bot.TREND_ADVISOR, fmt); }

    @Override
    protected String nothingToSay(TrendOpportunities o) { return o.candidates().isEmpty() ? "nothing_to_advise" : null; }

    /** The fixed text plus every candidate's figures, written as the page writes them. */
    @Override
    public String evidence(TrendOpportunities o) {
        StringBuilder out = new StringBuilder("Here is the evidence, already calculated. The measure is the ")
                .append(o.measureName()).append(", and ").append(o.better()).append(" is better.\n\n")
                .append(template(o)).append("\n\nCandidates, best first:\n");
        for (Candidate c : o.candidates()) {
            out.append("- ").append(fmt.groupName(o.groupLabel(), c.name())).append(": ").append(fmt.movement(o.unit(), c))
                    .append(", orders in the last 3 months ").append(fmt.unit("count", c.recentOrders()))
                    .append(", readiness ").append(c.readiness());
            c.checks().forEach((name, check) -> out.append(", ").append(name.replace('_', ' ')).append(' ').append(check.level()));
            out.append('\n');
        }
        return out.toString().strip();
    }

    @Override
    protected String template(TrendOpportunities o) {
        String group = String.valueOf(o.groupLabel());
        if (o.trend() == null || !o.trend().improving())
            return "The " + o.measureName() + " did not improve" + (o.trend() == null ? "" : ": " + fmt.movement(o.unit(), o.trend()))
                    + ". No " + group + " is suggested; see the possible caveats instead.";
        String head = "The " + o.measureName() + " improved: " + fmt.movement(o.unit(), o.trend()) + ". ";
        List<Candidate> candidates = o.candidates();
        if (candidates.isEmpty())
            return head + "No " + group + " improved at least as much as the business with enough orders in both periods to suggest.";
        Candidate top = candidates.getFirst();
        String others = candidates.size() < 2 ? "" : " Also worth a look: " + candidates.subList(1, candidates.size()).stream()
                .map(c -> fmt.groupName(group, c.name())).collect(Collectors.joining(", ")) + ".";
        return head + "The strongest place to look is " + fmt.groupName(group, top.name()) + ": " + fmt.movement(o.unit(), top)
                + ", with " + fmt.unit("count", top.recentOrders()) + " orders in the last 3 months. " + readiness(top) + " " + hint(o.measure())
                + others + " Past change does not prove that acting on it would pay off.";
    }

    private String readiness(Candidate c) {
        List<String> names = c.checks().keySet().stream().map(key -> switch (key) {
            case "late_rate" -> "late-delivery rate";
            case "low_review_rate" -> "low-review rate";
            default -> key.replace('_', ' ');
        }).toList();
        String checked = String.join(" and ", names), verb = names.size() > 1 ? " are " : " is ";
        return switch (String.valueOf(c.readiness())) {
            case "ready" -> "Its " + checked + verb + "in line with the business or better.";
            case "fix_first" -> "Its " + checked + verb + "worse than the business, so fix that first.";
            default -> "Too few of its orders had a known " + checked + " to judge it against the business.";
        };
    }

    private String hint(String measure) {
        return switch (String.valueOf(measure)) {
            case "delivery" -> "Faster delivery there could be worth telling customers in that state about.";
            case "reviews" -> "Its customers are happier while its sales grow, so it could deserve more stock or promotion.";
            case "sellers" -> "New sellers there are also finding more orders, so recruiting sellers there could pay off.";
            default -> "";
        };
    }
}
