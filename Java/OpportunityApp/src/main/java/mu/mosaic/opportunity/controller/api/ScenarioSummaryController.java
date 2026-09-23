package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.ScenarioNarrator;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** The scenario page's AI summary, fetched after the page has shown the template, because a local model can take minutes. */
@RestController
public class ScenarioSummaryController {
    private final MosaicApi api;
    private final ScenarioNarrator narrator;

    public ScenarioSummaryController(MosaicApi api, ScenarioNarrator narrator) {
        this.api = api;
        this.narrator = narrator;
    }

    @GetMapping("/api/scenario/summary")
    public ResponseEntity<?> summary(@RequestParam double change, @RequestParam int horizon) {
        ApiResult scenario = api.salesImpact(horizon, change);
        if (scenario.data() == null) return ResponseEntity.status(502).body(Map.of("error", scenario.error()));
        return ResponseEntity.ok(narrator.explain(scenario.data(), true));
    }
}
