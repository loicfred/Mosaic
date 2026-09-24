package mu.mosaic.opportunity.obj.api;

import mu.mosaic.opportunity.service.Formatter;

/** One caveat check: whether it found a problem, and the sentence that states its figures. */
public interface Check {
    boolean triggered();

    String sentence(Formatter fmt);
}
