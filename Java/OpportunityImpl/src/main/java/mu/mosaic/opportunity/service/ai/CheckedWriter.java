package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.service.ai.ScenarioNarrator.Narrative;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIService;

import java.util.List;

/**
 * Has a chatbot rewrite already-calculated evidence, and keeps the fixed text instead whenever the model is off,
 * fails, answers nothing, or uses a number found neither in the evidence nor in its instructions.
 */
final class CheckedWriter {
    private static final Logger log = LoggerFactory.getLogger(CheckedWriter.class);

    private CheckedWriter() {}

    static Narrative write(LocalAi ai, String botName, String evidence, String fallback) {
        Chatbot.Builder configured = ai.bot(botName);
        if (configured == null) return new Narrative(fallback, "template", null, "llm_disabled");
        Chatbot bot = configured.build();
        IAIService service = bot.getService();
        String text;
        try {
            if (!LocalAi.reachable(service)) return new Narrative(fallback, "template", null, "llm_unreachable");
            text = bot.prompt(evidence);
        } catch (RuntimeException e) {
            log.warn("{} fell back to the template: {}", botName, e.getMessage());
            return new Narrative(fallback, "template", null, "llm_unreachable: " + e.getClass().getSimpleName());
        }
        if (text == null || text.isBlank()) return new Narrative(fallback, "template", service.getModel(), "llm_empty_response");
        var allowed = NumberCheck.allowedFromText(evidence);
        allowed.addAll(NumberCheck.allowedFromText(bot.getSystemPrompt()));
        List<String> invented = NumberCheck.unsupported(text, allowed);
        if (!invented.isEmpty()) return new Narrative(fallback, "template", service.getModel(), "unsupported_numbers: " + String.join(", ", invented));
        return new Narrative(text.strip(), "llm", service.getModel(), null);
    }
}
