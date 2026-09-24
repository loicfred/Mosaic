package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Measure;
import mu.mosaic.opportunity.obj.api.SalesCaveats;
import mu.mosaic.opportunity.obj.api.SalesOpportunities;
import mu.mosaic.opportunity.obj.api.TrendCaveats;
import mu.mosaic.opportunity.obj.api.TrendOpportunities;
import mu.mosaic.opportunity.service.MosaicApi;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.function.Supplier;

/**
 * The suggestion and caveats panels of the Sales and trend pages: which API reply each is written from, and which
 * writer writes it. The buttons, the follow-up chat and the chat's own tools all find a panel here.
 */
@Component
public class Panels {
    private static final int HORIZON = 3;
    private final MosaicApi api;
    private final InvestmentAdvisor advisor;
    private final CaveatWriter caveats;
    private final TrendAdvisor trendAdvisor;
    private final TrendCaveatWriter trendCaveats;

    public Panels(MosaicApi api, InvestmentAdvisor advisor, CaveatWriter caveats, TrendAdvisor trendAdvisor, TrendCaveatWriter trendCaveats) {
        this.api = api;
        this.advisor = advisor;
        this.caveats = caveats;
        this.trendAdvisor = trendAdvisor;
        this.trendCaveats = trendCaveats;
    }

    /** One panel: the API call its figures come from, read as {@code type}, and its writer. */
    public record Panel<T>(Supplier<ApiResult> source, Class<T> type, CheckedWriter<T> writer) {
        public ApiResult figures() { return source.get(); }

        public Narrative explain(ApiResult figures) { return writer.explain(figures.as(type)); }

        public String evidence(ApiResult figures) { return writer.evidence(figures.as(type)); }
    }

    /**
     * @param topic "sales" or a trend page's path
     * @param kind  "advice" or "caveats"
     */
    public Optional<Panel<?>> find(String topic, String kind) {
        if ("sales".equals(topic)) return switch (kind) {
            case "advice" -> Optional.of(new Panel<>(() -> api.salesOpportunities(HORIZON), SalesOpportunities.class, advisor));
            case "caveats" -> Optional.of(new Panel<>(api::salesCaveats, SalesCaveats.class, caveats));
            default -> Optional.empty();
        };
        return Measure.fromPath(topic).flatMap(m -> switch (kind) {
            case "advice" -> Optional.of(new Panel<>(() -> api.trendOpportunities(m), TrendOpportunities.class, trendAdvisor));
            case "caveats" -> Optional.of(new Panel<>(() -> api.trendCaveats(m), TrendCaveats.class, trendCaveats));
            default -> Optional.empty();
        });
    }
}
