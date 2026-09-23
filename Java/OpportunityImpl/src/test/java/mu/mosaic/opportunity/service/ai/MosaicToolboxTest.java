package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.Fixtures;
import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.Formatter;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.*;

class MosaicToolboxTest {
    private final MosaicApi api = mock(MosaicApi.class);
    private final MosaicToolbox tools = new MosaicToolbox(api, new Formatter());

    private static ApiResult ok(String name) { return ApiResult.ok(Fixtures.load(name)); }

    @Test
    void theAllowlistIsExactlyTheAnnotatedMethods() {
        assertEquals(Set.of("salesOverview", "listCategories", "explainCategory", "deliveryAndReviews", "leastReliableSellers", "runSalesScenario", "investmentOpportunities"), MosaicToolbox.names());
    }

    @Test
    void investmentOpportunitiesListReadinessAndLimits() {
        when(api.salesOpportunities(3)).thenReturn(ok("opportunities"));
        String out = tools.investmentOpportunities();
        assertTrue(out.contains("+3.9%") && out.contains("health_beauty: +20.3%, BRL 56,328 (≈ USD 16,567) more sales; strong growth, large category") && out.contains("in line with the business"), out);
        assertTrue(out.endsWith("Past growth does not prove investing will pay off. Page: /"), out);
    }

    @Test
    void aCategoryIsExplainedWithItsRuleAndEvidencePage() {
        when(api.category("sports_leisure")).thenReturn(ok("category"));
        String out = tools.explainCategory("Sports Leisure");
        assertTrue(out.contains("BRL 151,905") && out.contains("−28.2%") && out.contains("FLAGGED") && out.contains("−10.0 pp or lower"), out);
        assertTrue(out.endsWith("Evidence page: /categories/sports_leisure"), out);
    }

    @Test
    void theScenarioLinksToItsPageAndSaysExposureNotLoss() {
        when(api.salesImpact(3, 20.0)).thenReturn(ok("scenario"));
        String out = tools.runSalesScenario(20, 3);
        assertTrue(out.contains("7,520 orders a month") && out.contains("exposure, not money lost") && out.contains("41 of 1,810"), out);
        assertTrue(out.endsWith("Open it: /scenario?run=1&change=20&horizon=3"), out);
    }

    @Test
    void anOutOfRangeScenarioIsRefusedBeforeCallingTheApi() {
        assertTrue(tools.runSalesScenario(500, 3).startsWith("Not run"));
        assertTrue(tools.runSalesScenario(20, 9).startsWith("Not run"));
        verify(api, never()).salesImpact(anyInt(), anyDouble());
    }

    @Test
    void filtersMapToTheApiFlags() {
        when(api.categories("underperforming_total")).thenReturn(ok("categories-behind"));
        assertTrue(tools.listCategories("falling_behind").startsWith("Whole business: −12.7%"));
        when(api.categories(null)).thenReturn(ok("categories"));
        assertTrue(tools.listCategories("anything else").contains("health_beauty"));
    }

    @Test
    void anApiFailureIsToldToTheModelNotThrown() {
        when(api.deliverySummary()).thenReturn(ApiResult.failed("The analytics API is not answering."));
        assertEquals("Not available right now: The analytics API is not answering.", tools.deliveryAndReviews());
    }
}
