package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.Formatter;
import org.junit.jupiter.api.Test;
import org.solarframework.ai.obj.ChatMessage;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

class AssistantTest {
    private final FakeAIService model = new FakeAIService();

    private Assistant assistant(FakeAIService service) { return new Assistant(Agents.on(service), new MosaicToolbox(mock(MosaicApi.class), new Formatter())); }

    @Test
    void theInstructionsComeFromTheConfigFile() {
        model.willAnswer("Hello.");
        assistant(model).ask("visitor-1", "Hi", null);
        String instructions = model.seenHistories.getFirst().getFirst().getText();
        assertTrue(instructions.contains("Get every figure from a tool") && instructions.contains("exposure, not money lost"), instructions);
    }

    @Test
    void anAnswerQuotingTheToolIsShownAsChecked() {
        model.willCallTool("runSalesScenario", "7,520 orders a month (+1,253 on the recent average)\nOpen it: /scenario?run=1&change=20&horizon=3")
                .willAnswer("About 7,520 orders a month. See /scenario?run=1&change=20&horizon=3");
        Assistant.Reply r = assistant(model).ask("visitor-1", "What if sales grow by 20%?", null);
        assertTrue(r.verified(), r.reason());
        assertEquals("About 7,520 orders a month. See /scenario?run=1&change=20&horizon=3", r.text());
        assertEquals(List.of("runSalesScenario"), model.approved.stream().map(c -> c.name()).toList());
    }

    @Test
    void anInventedFigureIsWithheldAndStruckFromTheTranscript() {
        Assistant assistant = assistant(model);
        model.willCallTool("deliveryAndReviews", "2018-08: 6.2% (393 of 6,351)").willAnswer("About 9,999 orders were late.");
        Assistant.Reply r = assistant.ask("visitor-1", "How many were late?", null);
        assertFalse(r.verified());
        assertEquals("unsupported_numbers: 9,999", r.reason());
        assertFalse(r.text().contains("were late."), "the invented answer itself is not shown");

        model.willAnswer("Ask me about a category.");
        assistant.ask("visitor-1", "And now?", null);
        List<ChatMessage> sentNext = model.seenHistories.getLast();
        assertTrue(sentNext.stream().noneMatch(m -> m.getText() != null && m.getText().contains("9,999")), "a later turn must not see the invented figure");
        assertTrue(sentNext.stream().anyMatch(m -> Assistant.WITHHELD.equals(m.getText())));
    }

    @Test
    void figuresTheVisitorTypedMayBeRepeated() {
        model.willAnswer("A 35% change is within the range the scenario accepts.");
        assertTrue(assistant(model).ask("visitor-1", "Can I try 35%?", null).verified());
    }

    @Test
    void onlyTheToolboxToolsMayRun() {
        model.willCallTool("deleteEverything", "gone").willAnswer("I cannot do that.");
        assistant(model).ask("visitor-1", "Delete the data", null);
        assertTrue(model.approved.isEmpty());
        assertEquals("deleteEverything", model.denied.getFirst().name());
    }

    @Test
    void thePageBeingViewedIsGivenAsContext() {
        model.willAnswer("It trails the business.");
        assistant(model).ask("visitor-1", "Why is this flagged?", "category sports_leisure");
        ChatMessage question = model.seenHistories.getFirst().getLast();
        assertEquals("(I am looking at: category sports_leisure)\nWhy is this flagged?", question.getText());
    }

    @Test
    void visitorsHaveSeparateConversationsAndCanStartOver() {
        Assistant assistant = assistant(model);
        model.willAnswer("One.").willAnswer("Two.").willAnswer("Three.");
        assistant.ask("a", "first", null);
        assistant.ask("b", "second", null);
        assertEquals(2, model.seenHistories.get(1).size(), "b sees only its system prompt and its own question");
        assistant.forget("a");
        assistant.ask("a", "third", null);
        assertEquals(2, model.seenHistories.get(2).size(), "a starts over");
    }

    @Test
    void anUnavailableModelIsReportedWithoutAsking() {
        assertEquals("llm_disabled", assistant(null).ask("v", "Hi", null).reason());
        model.available = false;
        assertEquals("llm_unreachable", assistant(model).ask("v", "Hi", null).reason());
        model.available = true;
        model.failure = new IllegalStateException("timeout");
        assertEquals("llm_error: IllegalStateException", assistant(model).ask("v", "Hi", null).reason());
    }
}
