package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.ScenarioNarrator;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

/** User inputs select a scenario; all figures are calculated by the analytics API. */
@Controller
public class ScenarioPageController {
    private final MosaicApi api;
    private final ScenarioNarrator narrator;
    public ScenarioPageController(MosaicApi api, ScenarioNarrator narrator) {
        this.api = api;
        this.narrator = narrator;
    }
    public record Scenario(Integer horizon, Double salesChangePct, String category, Boolean useModel) {}

    @GetMapping("/what-if")
    public String page(Model model) {
        new Breadcrumbs("what-if", new Breadcrumbs.Crumb("What if?", null)).addTo(model);
        api.salesImpact(3, 0).addTo(model, "impact");
        return "what-if";
    }

    @PostMapping("/api/what-if")
    @ResponseBody
    public ResponseEntity<?> calculate(@RequestBody Scenario input) {
        if (input == null || input.horizon() == null || input.horizon() < 1 || input.horizon() > 6
                || input.salesChangePct() == null || !Double.isFinite(input.salesChangePct())
                || input.salesChangePct() < -30 || input.salesChangePct() > 30
                || (input.category() != null && input.category().length() > 100))
            return ResponseEntity.badRequest().body(Map.of("error", "Choose 1 to 6 months and a sales change between -30% and 30%."));
        String category = input.category() == null || input.category().isBlank() ? null : input.category();
        ApiResult result = api.salesImpact(input.horizon(), input.salesChangePct(), category);
        if (result.data() == null) return ResponseEntity.status(result.status() == 422 ? 400 : 502).body(Map.of("error", result.error()));
        return ResponseEntity.ok(Map.of("evidence", result.data(), "narrative", narrator.explain(result.as(mu.mosaic.opportunity.obj.api.Scenario.class), Boolean.TRUE.equals(input.useModel()))));
    }
}
