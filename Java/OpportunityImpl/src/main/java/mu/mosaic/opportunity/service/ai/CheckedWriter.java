package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.service.Formatter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIService;

import java.util.List;

/**
 * The base of every writer: a fixed text from the API's figures, which a chatbot may rewrite from the same evidence.
 * The fixed text is kept whenever there is nothing to say, the model is off, fails, answers nothing, or uses a number
 * found neither in the evidence nor in its instructions.
 * @param <T> the API reply the writer reads
 */
public abstract class CheckedWriter<T> {
    private static final Logger log = LoggerFactory.getLogger(CheckedWriter.class);
    protected final Formatter fmt;
    private final LocalAi ai;
    private final LocalAi.Bot bot;

    protected CheckedWriter(LocalAi ai, LocalAi.Bot bot, Formatter fmt) {
        this.ai = ai;
        this.bot = bot;
        this.fmt = fmt;
    }

    /** The fixed text, shown whenever the model's version is not usable. */
    protected abstract String template(T figures);

    /** What the model is given; a follow-up question in the panel is answered from it too. */
    public abstract String evidence(T figures);

    /** The reason the fixed text is enough without asking the model, or null. */
    protected String nothingToSay(T figures) { return null; }

    public Narrative explain(T figures) {
        String fallback = template(figures);
        String nothing = nothingToSay(figures);
        return nothing != null ? new Narrative(fallback, "template", null, nothing) : write(evidence(figures), fallback);
    }

    private Narrative write(String evidence, String fallback) {
        Chatbot.Builder configured = ai.bot(bot);
        if (configured == null) return new Narrative(fallback, "template", null, "llm_disabled");
        Chatbot chatbot = configured.build();
        IAIService service = chatbot.getService();
        String text;
        try {
            if (!ai.reachable(service)) return new Narrative(fallback, "template", null, "llm_unreachable");
            text = chatbot.prompt(evidence);
        } catch (RuntimeException e) {
            log.warn("{} fell back to the template: {}", bot, e.getMessage());
            return new Narrative(fallback, "template", null, "llm_unreachable: " + e.getClass().getSimpleName());
        }
        if (text == null || text.isBlank()) return new Narrative(fallback, "template", service.getModel(), "llm_empty_response");
        List<String> invented = new NumberCheck().allow(evidence).allow(chatbot.getSystemPrompt()).unsupported(text);
        if (!invented.isEmpty()) return new Narrative(fallback, "template", service.getModel(), "unsupported_numbers: " + String.join(", ", invented));
        return new Narrative(text.strip(), "llm", service.getModel(), null);
    }
}
