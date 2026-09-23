package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.Fixtures;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static mu.mosaic.opportunity.obj.ApiData.nestedObject;
import static org.junit.jupiter.api.Assertions.*;

class InvestmentAdvisorTest {
    private final FakeAIService model = new FakeAIService();
    private final Map<String, Object> opportunities = Fixtures.load("opportunities");

    private InvestmentAdvisor advisor(FakeAIService service) { return new InvestmentAdvisor(Agents.on(service)); }

    @Test
    void templateNamesTheStrongestCategoryAndItsLimits() {
        String text = InvestmentAdvisor.template(opportunities);
        assertTrue(text.startsWith("Sales are forecast to rise about 3.9% against the last 3 months. The strongest place to look is health beauty, up 20.3%"), text);
        assertTrue(text.contains("in line with the business") && text.contains("sales are not profit"), text);
    }

    @Test
    void flatSalesSuggestNothingAndNeverAskTheModel() {
        nestedObject(opportunities, "trend").put("increasing", false);
        ScenarioNarrator.Narrative n = advisor(model).advise(opportunities);
        assertTrue(n.text().startsWith("The model does not forecast rising sales"), n.text());
        assertEquals("nothing_to_advise", n.reason());
        assertEquals(0, model.turns);
    }

    @Test
    void noCandidatesIsSaidPlainly() {
        opportunities.put("candidates", List.of());
        assertTrue(InvestmentAdvisor.template(opportunities).endsWith("with enough sales to suggest."));
    }

    @Test
    void promptCarriesRoundedFiguresTheModelMayQuote() {
        String prompt = InvestmentAdvisor.prompt(opportunities);
        assertTrue(prompt.contains("forecast_change_pct: 3.9") && prompt.contains("- health_beauty: sales_change_pct 20.3, sales_added_brl 56,328") && prompt.contains("growth strong, size large, late_deliveries in_line, low_reviews in_line, readiness ready"), prompt);
    }

    @Test
    void aFaithfulAnswerIsUsedAndAnInventedOneIsNot() {
        model.willAnswer("Health beauty grew 20.3% with late deliveries in line with the business, so it could take more stock.");
        ScenarioNarrator.Narrative good = advisor(model).advise(opportunities);
        assertEquals("llm", good.source(), good.reason());
        model.willAnswer("Health beauty could add 250,000 BRL.");
        ScenarioNarrator.Narrative bad = advisor(model).advise(opportunities);
        assertEquals("unsupported_numbers: 250,000", bad.reason());
        assertEquals(InvestmentAdvisor.template(opportunities), bad.text());
    }

    @Test
    void anUnreachableModelKeepsTheTemplate() {
        assertEquals("llm_disabled", advisor(null).advise(opportunities).reason());
        model.available = false;
        assertEquals("llm_unreachable", advisor(model).advise(opportunities).reason());
    }
}
