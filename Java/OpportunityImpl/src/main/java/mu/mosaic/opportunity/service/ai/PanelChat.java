package mu.mosaic.opportunity.service.ai;

import mu.mosaic.opportunity.service.Formatter;
import mu.mosaic.opportunity.service.MosaicApi;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIService;
import org.solarframework.ai.memory.Memory;
import org.solarframework.ai.obj.ChatMessage;
import org.solarframework.ai.obj.Conversation;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Follow-up questions about a suggestion or caveats panel, answered by the {@code PanelChat} chatbot from the same
 * figures the panel's answer was written from, and from {@link PanelTools} when the question needs more: any
 * category, the forecast, a what-if scenario, the delivery and review figures, the model-scored orders, and outside
 * context (Brazilian events and the Central Bank's economic figures).
 * <p>The evidence always comes from the server, never from the browser. The earlier turns are sent back by the
 * page, so they only give the model context: a number is allowed only when the panel's figures, the instructions or
 * a tool reply in this conversation hold it, and an answer with any other number is withheld rather than shown.
 * There is no fixed text to fall back to here, so a withheld or unavailable answer says so plainly.
 */
@Component
public class PanelChat {
    private static final String OFFLINE = "The AI is not available right now, so follow-up questions cannot be answered. The figures above still stand.";
    private static final String BUSY = "The AI did not answer this time; it may be busy. Try again in a few seconds.";
    private static final Logger log = LoggerFactory.getLogger(PanelChat.class);
    private static final int MEMORY_TOKENS = 8000;
    // a free cloud tier refuses bursts of requests per minute; one wait and retry usually gets an answer
    private static final long RETRY_WAIT_MILLIS = 4000;
    // words in a question that ask for a chart kind, most specific first ("horizontal bar" before "bar")
    private static final List<Map.Entry<String, String>> KIND_WORDS = List.of(
            Map.entry("doughnut", "doughnut"), Map.entry("donut", "doughnut"), Map.entry("pie", "pie"),
            Map.entry("horizontal", "hbar"), Map.entry("area", "area"), Map.entry("line", "line"),
            Map.entry("bar", "bar"), Map.entry("column", "bar"), Map.entry("histogram", "bar"));
    private final LocalAi ai;
    private final MosaicApi api;
    private final Formatter fmt;
    private final Panels panels;

    public PanelChat(LocalAi ai, MosaicApi api, Formatter fmt, Panels panels) {
        this.ai = ai;
        this.api = api;
        this.fmt = fmt;
        this.panels = panels;
    }

    /** The answer, and the charts of the tools it used; only an answer that passed the number check carries them. */
    public record Answer(Narrative narrative, List<Map<String, Object>> charts) {
        Answer(Narrative narrative) { this(narrative, List.of()); }
    }

    /** One earlier message in the panel: {@code user} or {@code assistant}. */
    public record Turn(String role, String text) {}

    public Answer ask(String evidence, List<Turn> history, String question) {
        Chatbot.Builder configured = ai.bot(LocalAi.Bot.PANEL_CHAT);
        if (configured == null) return new Answer(new Narrative(OFFLINE, "unavailable", null, "llm_disabled"));
        // a fresh toolbox per attempt, since each records the charts of its own calls
        PanelTools toolbox = new PanelTools(api, fmt, panels);
        Chatbot bot = chatbot(configured, toolbox);
        IAIService service = bot.getService();
        String text;
        Conversation conversation;
        try {
            if (!ai.reachable(service)) return new Answer(new Narrative(OFFLINE, "unavailable", null, "llm_unreachable"));
            String prompt = prompt(evidence, history, question);
            try {
                conversation = bot.startConversation();
                text = conversation.run(prompt).text();
            } catch (RuntimeException refused) {
                log.info("Panel chat retrying once after: {}", refused.getMessage());
                Thread.sleep(RETRY_WAIT_MILLIS);
                toolbox = new PanelTools(api, fmt, panels);
                bot = chatbot(configured, toolbox);
                conversation = bot.startConversation();
                text = conversation.run(prompt).text();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return new Answer(new Narrative(BUSY, "unavailable", null, "interrupted"));
        } catch (RuntimeException e) {
            log.warn("Panel chat did not answer: {}", e.getMessage());
            return new Answer(new Narrative(BUSY, "unavailable", null, "llm_unreachable: " + e.getClass().getSimpleName()));
        }
        if (text == null || text.isBlank()) return new Answer(new Narrative(BUSY, "unavailable", service.getModel(), "llm_empty_response"));
        List<String> invented = numberCheck(conversation, evidence).allow(bot.getSystemPrompt()).unsupported(text);
        if (!invented.isEmpty())
            return new Answer(new Narrative("That answer was withheld: it used a figure that is not in the data (" + String.join(", ", invented)
                    + "). Ask about the figures shown in this panel.", "withheld", service.getModel(), "unsupported_numbers: " + String.join(", ", invented)));
        return new Answer(new Narrative(text.strip(), "llm", service.getModel(), null), withAskedKind(toolbox.charts(), question));
    }

    /** Only the toolbox's own tools may run; the memory holds this one question's tool calls and is dropped afterwards. */
    private Chatbot chatbot(Chatbot.Builder configured, PanelTools toolbox) {
        return configured.tools(toolbox).approveToolsWith(call -> toolbox.names().contains(call.name())).memory(new Memory(MEMORY_TOKENS)).build();
    }

    /** The charts drawn as the question asks ("as a pie chart"), where that kind suits the data; otherwise as they are. */
    private List<Map<String, Object>> withAskedKind(List<Map<String, Object>> charts, String question) {
        String asked = question.toLowerCase(Locale.ROOT);
        String kind = KIND_WORDS.stream().filter(w -> asked.contains(w.getKey())).map(Map.Entry::getValue).findFirst().orElse(null);
        if (kind == null) return charts;
        return charts.stream().map(chart -> {
            if (!((List<?>) chart.get("kinds")).contains(kind)) return chart;
            Map<String, Object> redrawn = new LinkedHashMap<>(chart);
            redrawn.put("kind", kind);
            return redrawn;
        }).toList();
    }

    /**
     * What a figure may come from: the panel's figures and every tool reply in this conversation, never the model's
     * own words, and never the earlier turns the page sent back (the prompt holds them, so the evidence is read
     * separately rather than from the prompt).
     */
    private NumberCheck numberCheck(Conversation conversation, String evidence) {
        NumberCheck check = new NumberCheck().allow(evidence);
        for (ChatMessage m : conversation.getMessages())
            if (m.getRole() != null && m.getRole().isTool()) check.allow(m.getText());
        return check;
    }

    /** The panel's figures, then the conversation so far, then the new question; the model sees nothing else. */
    private String prompt(String evidence, List<Turn> history, String question) {
        StringBuilder out = new StringBuilder(evidence.strip()).append("\n\n");
        if (!history.isEmpty()) {
            out.append("Conversation so far:\n");
            for (Turn t : history) out.append("assistant".equals(t.role()) ? "Assistant: " : "User: ").append(t.text().strip()).append('\n');
            out.append('\n');
        }
        return out.append("New question from the business owner: ").append(question.strip()).toString();
    }
}
