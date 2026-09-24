package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.obj.Measure;
import mu.mosaic.opportunity.obj.Selection;
import mu.mosaic.opportunity.service.MosaicApi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.Map;

/** The Delivery, Reviews and Sellers pages, laid out as the Sales page: one monthly chart, then evidence, a suggestion and caveats behind tabs. */
@Controller
public class TrendController {
    private final MosaicApi api;

    public TrendController(MosaicApi api) { this.api = api; }

    @GetMapping("/delivery")
    public String delivery(@RequestParam Map<String, String> params, Model model) { return page(params, model, Measure.DELIVERY); }

    @GetMapping("/reviews")
    public String reviews(@RequestParam Map<String, String> params, Model model) { return page(params, model, Measure.REVIEWS); }

    @GetMapping("/sellers")
    public String sellers(@RequestParam Map<String, String> params, Model model) { return page(params, model, Measure.SELLERS); }

    /** With any period or filter chosen, the figures come from the findings API under that selection. */
    private String page(Map<String, String> params, Model model, Measure measure) {
        new Breadcrumbs(measure.path(), new Crumb(measure.title(), "/" + measure.path())).addTo(model);
        model.addAttribute("measure", measure);
        Selection selection = new Selection(params);
        selection.addTo(model);
        (selection.isEmpty() ? api.trend(measure) : api.selectedTrend(measure.path(), selection.parameters())).addTo(model, "trend");
        return "trend";
    }
}
