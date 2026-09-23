package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.CaveatWriter;
import mu.mosaic.opportunity.service.ai.InvestmentAdvisor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.function.Function;

/** The overview's two buttons: fetched on demand, because a model can take a while and the page must not wait for it. */
@RestController
public class OverviewAiController {
    private static final int HORIZON = 3;
    private final MosaicApi api;
    private final InvestmentAdvisor advisor;
    private final CaveatWriter caveats;

    public OverviewAiController(MosaicApi api, InvestmentAdvisor advisor, CaveatWriter caveats) {
        this.api = api;
        this.advisor = advisor;
        this.caveats = caveats;
    }

    @GetMapping("/api/overview/advice")
    public ResponseEntity<?> advice() { return answer(api.salesOpportunities(HORIZON), advisor::advise); }

    @GetMapping("/api/overview/caveats")
    public ResponseEntity<?> caveats() { return answer(api.salesCaveats(), caveats::explain); }

    private static ResponseEntity<?> answer(ApiResult evidence, Function<Map<String, Object>, Object> write) {
        if (evidence.data() == null) return ResponseEntity.status(502).body(Map.of("error", evidence.error()));
        return ResponseEntity.ok(write.apply(evidence.data()));
    }
}
