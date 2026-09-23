package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.Fixtures;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static mu.mosaic.opportunity.obj.ApiData.recordList;
import static org.junit.jupiter.api.Assertions.*;

class CaveatWriterTest {
    private final FakeAIService model = new FakeAIService();
    private final Map<String, Object> caveats = Fixtures.load("caveats");

    private CaveatWriter writer(FakeAIService service) { return new CaveatWriter(Agents.on(service)); }

    @Test
    void templateListsFoundProblemsFirstWithTheirFigures() {
        String text = CaveatWriter.template(caveats);
        assertTrue(text.startsWith("Found behind the sales result:\n• 18 of 74 categories fell well behind the business (−12.7% overall), with BRL 461,022"), text);
        assertTrue(text.contains("Late orders got a 1 or 2 star review 62.4% of the time, on-time orders 9.2%"), text);
        assertTrue(text.contains("Checked, nothing found:\n• Orders delivered late: 3.6% in the last 3 months against 10.1% in the 3 before (−6.5 pp)"), text);
    }

    @Test
    void nothingFoundIsSaidWithoutAskingTheModel() {
        recordList(caveats, "checks").forEach(check -> check.put("triggered", false));
        var n = writer(model).explain(caveats);
        assertTrue(n.text().startsWith("None of the checks found a hidden problem"), n.text());
        assertEquals(0, model.turns);
    }

    @Test
    void theModelMayOnlyQuoteTheChecks() {
        model.willAnswer("18 of 74 categories fell behind, and late orders got low reviews 62.4% of the time.");
        assertEquals("llm", writer(model).explain(caveats).source());
        model.willAnswer("About 30% of customers could leave.");
        var n = writer(model).explain(caveats);
        assertEquals("unsupported_numbers: 30", n.reason());
        assertEquals(CaveatWriter.template(caveats), n.text());
    }

    @Test
    void noModelKeepsTheFixedList() {
        assertEquals("llm_disabled", writer(null).explain(caveats).reason());
        caveats.put("checks", List.of());
        assertTrue(CaveatWriter.template(caveats).startsWith("None of the checks"));
    }
}
