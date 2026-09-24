package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.api.Check;
import mu.mosaic.opportunity.obj.api.SalesCaveats;
import mu.mosaic.opportunity.service.Formatter;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * The hidden problems behind a good sales result, from the API's caveat checks. Each check states its figures in one
 * sentence; the {@code CaveatWriter} chatbot may rewrite them, checked by {@link CheckedWriter}.
 */
@Component
public class CaveatWriter extends CheckListWriter<SalesCaveats> {

    public CaveatWriter(LocalAi ai, Formatter fmt) { super(ai, LocalAi.Bot.CAVEAT_WRITER, fmt); }

    @Override
    protected List<? extends Check> checks(SalesCaveats caveats) { return caveats.checks(); }

    @Override
    protected String result(SalesCaveats caveats) { return "the sales result"; }
}
