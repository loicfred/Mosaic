package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.api.Check;
import mu.mosaic.opportunity.obj.api.TrendCaveats;
import mu.mosaic.opportunity.service.Formatter;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * The hidden problems behind a trend page's result; the {@code TrendCaveats} chatbot may rewrite them, checked by
 * {@link CheckedWriter}.
 */
@Component
public class TrendCaveatWriter extends CheckListWriter<TrendCaveats> {

    public TrendCaveatWriter(LocalAi ai, Formatter fmt) { super(ai, LocalAi.Bot.TREND_CAVEATS, fmt); }

    @Override
    protected List<? extends Check> checks(TrendCaveats caveats) { return caveats.checks(); }

    @Override
    protected String result(TrendCaveats caveats) { return "the change in the " + caveats.measureName(); }

    /**
     * Which way the page's measure moved, stated first: without it the model assumed a caveat meant the measure had
     * worsened, and called a late-delivery rate that fell from 10.1% to 3.6% "higher".
     */
    @Override
    public String evidence(TrendCaveats caveats) {
        if (caveats.trend() == null) return super.evidence(caveats);
        return "The " + caveats.measureName() + (caveats.trend().improving() ? " improved" : " did not improve") + ": "
                + fmt.movement(caveats.unit(), caveats.trend()) + " (" + caveats.better() + " is better). The checks below look for problems behind that result; "
                + "never describe the measure as moving the other way.\n\n" + super.evidence(caveats);
    }
}
