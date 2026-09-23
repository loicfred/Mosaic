package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.LocalAi;
import mu.mosaic.opportunity.service.ai.ScenarioNarrator;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.Map;

@Controller
public class ScenarioController {
    private final MosaicApi api;
    private final ScenarioNarrator narrator;
    private final LocalAi ai;

    public ScenarioController(MosaicApi api, ScenarioNarrator narrator, LocalAi ai) {
        this.api = api;
        this.narrator = narrator;
        this.ai = ai;
    }

    /**
     * A first visit runs the default scenario with the explanation; a submitted form sends its own checkbox state.
     * The page never waits for the model: it shows the template, and the page asks /api/scenario/summary for the AI version.
     */
    @GetMapping("/scenario")
    public String scenario(@RequestParam(defaultValue = "20") double change, @RequestParam(defaultValue = "3") int horizon, @RequestParam(defaultValue = "false") boolean explain, @RequestParam(required = false) String run, Model model) {
        boolean withExplanation = run == null || explain;
        Breadcrumbs.addTo(model, "scenario", new Crumb("What if sales change?", "/scenario"));
        model.addAttribute("change", change);
        model.addAttribute("horizon", horizon);
        model.addAttribute("explain", withExplanation);
        Map<String, Object> scenario = api.salesImpact(horizon, change).addTo(model, "scenario");
        if (scenario != null) model.addAttribute("narrative", narrator.explain(scenario, false));
        model.addAttribute("aiStatus", ai.status());
        return "scenario";
    }
}
