package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.Fixtures;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ScenarioNarratorTest {
    private final FakeAIService model = new FakeAIService();
    private final Map<String, Object> scenario = Fixtures.load("scenario");

    private ScenarioNarrator narrator(FakeAIService service) { return new ScenarioNarrator(Agents.on(service)); }

    @Test
    void templateStatesTheFiguresAndTheirLimits() {
        String text = ScenarioNarrator.template(scenario);
        assertTrue(text.startsWith("A 20% change in sales over the next 3 months would mean about 7,520 orders a month, 1,253 more than the recent average."), text);
        assertTrue(text.contains("3.61%") && text.contains("41 of 1,810") && text.contains("association, not a proven cause"), text);
    }

    @Test
    void templateSaysSoWhenThereIsNothingToProject() {
        scenario.put("consequences", null);
        assertTrue(ScenarioNarrator.template(scenario).startsWith("There is not enough recent activity"));
    }

    @Test
    void promptCarriesAggregatesButNoIdentifiers() {
        String prompt = ScenarioNarrator.prompt(scenario);
        assertTrue(prompt.startsWith("Here is the scenario evidence") && prompt.contains("projected_monthly_orders: 7519.6"), prompt);
        assertFalse(prompt.contains("6560211a19b47992c3666cc44a7e94c0"), "seller ids must not reach the model");
    }

    @Test
    void theInstructionsComeFromTheConfigFile() {
        model.willAnswer("Watch late deliveries.");
        narrator(model).explain(scenario, true);
        String instructions = model.seenHistories.getFirst().getFirst().getText();
        assertTrue(instructions.contains("Use only the numbers given in the evidence") && instructions.contains("association"), instructions);
    }

    @Test
    void aFaithfulAnswerIsUsed() {
        model.willAnswer("Orders could reach about 7,520 a month, and at 3.61% about 272 could arrive late.");
        ScenarioNarrator.Narrative n = narrator(model).explain(scenario, true);
        assertEquals("llm", n.source());
        assertEquals("fake-model", n.model());
    }

    @Test
    void anInventedFigureFallsBackToTheTemplate() {
        model.willAnswer("Orders could reach 9,999 a month.");
        ScenarioNarrator.Narrative n = narrator(model).explain(scenario, true);
        assertEquals("template", n.source());
        assertEquals("unsupported_numbers: 9,999", n.reason());
        assertEquals(ScenarioNarrator.template(scenario), n.text());
    }

    @Test
    void anUntickedSummaryNeverAsksTheModel() {
        assertEquals("not_requested", narrator(model).explain(scenario, false).reason());
        assertEquals(0, model.turns);
    }

    @Test
    void noModelConfiguredOrReachableStillGivesTheTemplate() {
        assertEquals("llm_disabled", narrator(null).explain(scenario, true).reason());
        model.available = false;
        assertEquals("llm_unreachable", narrator(model).explain(scenario, true).reason());
        assertEquals(0, model.turns);
    }

    @Test
    void aFailingModelFallsBackInsteadOfBreakingThePage() {
        model.failure = new IllegalStateException("connection reset");
        ScenarioNarrator.Narrative n = narrator(model).explain(scenario, true);
        assertEquals("template", n.source());
        assertEquals("llm_unreachable: IllegalStateException", n.reason());
    }
}
