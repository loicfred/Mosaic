package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.api.Check;
import mu.mosaic.opportunity.service.Formatter;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * A caveat writer: one line per check, found problems first; the same lines are the model's only evidence, and
 * there is nothing to explain when no check found a problem.
 */
public abstract class CheckListWriter<T> extends CheckedWriter<T> {

    protected CheckListWriter(LocalAi ai, LocalAi.Bot bot, Formatter fmt) { super(ai, bot, fmt); }

    protected abstract List<? extends Check> checks(T figures);

    /** What the checks looked behind, e.g. "the sales result". */
    protected abstract String result(T figures);

    @Override
    public String evidence(T figures) { return "Here are the checks, already calculated:\n\n" + template(figures); }

    @Override
    protected String nothingToSay(T figures) { return checks(figures).stream().noneMatch(Check::triggered) ? "nothing_found" : null; }

    @Override
    protected String template(T figures) {
        List<String> found = new ArrayList<>(), clear = new ArrayList<>();
        for (Check check : checks(figures)) (check.triggered() ? found : clear).add(check.sentence(fmt));
        StringBuilder out = new StringBuilder(found.isEmpty()
                ? "None of the checks found a hidden problem behind " + result(figures) + ".\n"
                : "Found behind " + result(figures) + ":\n" + found.stream().map(l -> "• " + l + "\n").collect(Collectors.joining()));
        if (!clear.isEmpty()) out.append("\nChecked, nothing found:\n").append(clear.stream().map(l -> "• " + l + "\n").collect(Collectors.joining()));
        return out.append("\nA caveat says where to look, not why it happened.").toString();
    }
}
