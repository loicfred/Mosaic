package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.ai.Panels;
import mu.mosaic.opportunity.service.ai.Panels.Panel;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.Optional;

/**
 * The suggestion and caveats buttons of the overview and the trend pages: fetched on demand, because a model can take
 * a while and the page must not wait for it.
 */
@RestController
public class AiButtonsController {
    private final Panels panels;

    public AiButtonsController(Panels panels) { this.panels = panels; }

    @GetMapping("/api/overview/advice")
    public ResponseEntity<?> advice() { return answer(panels.find("sales", "advice")); }

    @GetMapping("/api/overview/caveats")
    public ResponseEntity<?> caveats() { return answer(panels.find("sales", "caveats")); }

    @GetMapping("/api/trend/{measure}/advice")
    public ResponseEntity<?> trendAdvice(@PathVariable String measure) { return answer(panels.find(measure, "advice")); }

    @GetMapping("/api/trend/{measure}/caveats")
    public ResponseEntity<?> trendCaveats(@PathVariable String measure) { return answer(panels.find(measure, "caveats")); }

    /** The written answer plus the API figures it was written from, which the page draws as charts. */
    private ResponseEntity<?> answer(Optional<Panel<?>> panel) {
        if (panel.isEmpty()) return ResponseEntity.status(404).body(Map.of("error", "There is no such panel."));
        ApiResult figures = panel.get().figures();
        if (figures.failed()) return ResponseEntity.status(502).body(Map.of("error", figures.error()));
        Map<String, Object> body = panel.get().explain(figures).toJson();
        body.put("evidence", figures.data());
        return ResponseEntity.ok(body);
    }
}
