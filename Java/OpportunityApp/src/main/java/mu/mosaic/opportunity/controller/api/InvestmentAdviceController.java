package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.InvestmentAdvisor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** The overview's AI investment advice, fetched after the page has shown the template, because a local model can take minutes. */
@RestController
public class InvestmentAdviceController {
    private static final int HORIZON = 3;
    private final MosaicApi api;
    private final InvestmentAdvisor advisor;

    public InvestmentAdviceController(MosaicApi api, InvestmentAdvisor advisor) {
        this.api = api;
        this.advisor = advisor;
    }

    @GetMapping("/api/overview/advice")
    public ResponseEntity<?> advice() {
        ApiResult opportunities = api.salesOpportunities(HORIZON);
        if (opportunities.data() == null) return ResponseEntity.status(502).body(Map.of("error", opportunities.error()));
        return ResponseEntity.ok(advisor.advise(opportunities.data()));
    }
}
