package mu.mosaic.opportunity.service.ai;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIService;
import org.solarframework.ai.dto.AgentRun;
import org.solarframework.ai.memory.Memory;
import org.solarframework.ai.obj.ChatMessage;
import org.solarframework.ai.obj.Conversation;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * The chat assistant: the {@code MosaicAssistant} chatbot of config/ai/agents.json, whose only tools are
 * {@link MosaicToolbox}'s read-only calls.
 * <p>One conversation per visitor, kept in memory and never saved. Before a reply is shown, every number in it is
 * checked against what the tools returned and what the person typed; a reply with an unsupported figure is
 * withheld and struck from the transcript, so a later turn cannot repeat it.
 */
@Component
public class Assistant {
    private static final Logger log = LoggerFactory.getLogger(Assistant.class);
    private static final String OFFLINE = "The assistant cannot reach the local model. Start LM Studio's server and load a model, then ask again.";
    static final String WITHHELD = "(An earlier answer was withheld because it contained figures that were not in the data.)";
    private final LocalAi ai;
    private final MosaicToolbox toolbox;
    private final Set<String> allowedTools = MosaicToolbox.names();
    private final Cache<String, Conversation> conversations = Caffeine.newBuilder().expireAfterAccess(Duration.ofMinutes(30)).maximumSize(500).build();
    private volatile Chatbot bot;

    public Assistant(LocalAi ai, MosaicToolbox toolbox) {
        this.ai = ai;
        this.toolbox = toolbox;
    }

    /**
     * @param verified true when every figure in {@code text} was found in the data
     * @param reason   why the model's answer is not shown, when it is not
     */
    public record Reply(String text, boolean verified, String model, String reason) {}

    /** @param context where the person is on the site, e.g. "category sports_leisure"; null when unknown */
    public Reply ask(String visitor, String message, String context) {
        Chatbot assistant = bot();
        if (assistant == null) return new Reply("The assistant is switched off: no language model is configured.", false, null, "llm_disabled");
        IAIService service = assistant.getService();
        if (!LocalAi.reachable(service)) return new Reply(OFFLINE, false, service.getModel(), "llm_unreachable");
        // a generated id, not the visitor key: the id heads every log line and a session id must not end up there
        Conversation c = conversations.get(visitor, k -> assistant.startConversation());
        synchronized (c) {
            return runConversationTurn(c, service.getModel(), message, context);
        }
    }

    private Reply runConversationTurn(Conversation conversation, String model, String message, String context) {
        AgentRun run;
        try {
            String prompt = context == null || context.isBlank() ? message : "(I am looking at: " + context + ")\n" + message;
            run = conversation.run(prompt);
        } catch (RuntimeException e) {
            log.warn("Assistant turn failed: {}", e.getMessage());
            return new Reply("The local model stopped before answering. Try again, or ask a shorter question.", false, model, "llm_error: " + e.getClass().getSimpleName());
        }
        return validateModelReply(conversation, run.text(), model);
    }

    private Reply validateModelReply(Conversation conversation, String answer, String model) {
        List<String> invented = NumberCheck.unsupported(answer, evidence(conversation));
        if (invented.isEmpty()) return new Reply(answer, true, model, null);
        ChatMessage last = conversation.getLastMessage();
        if (last != null && last.getRole().isAssistant()) last.setText(WITHHELD);
        return new Reply("I left that answer out because it used figures I could not find in the data (" + String.join(", ", invented) + "). Ask about a category, deliveries or a scenario and I will quote the data directly.", false, model, "unsupported_numbers: " + String.join(", ", invented));
    }

    /** Starts the visitor's next question on a clean transcript. */
    public void forget(String visitor) { conversations.invalidate(visitor); }

    /** What a figure may come from: the tools' replies, the person's own words and the instructions - anything but the model itself. */
    static Set<String> evidence(Conversation c) {
        Set<String> allowed = new HashSet<>();
        for (ChatMessage m : c.getMessages()) if (!m.getRole().isAssistant()) allowed.addAll(NumberCheck.allowedFromText(m.getText()));
        return allowed;
    }

    /** The configured bot with what only code can give it; built once, and looked for again while there is none. */
    private Chatbot bot() {
        if (bot == null) {
            Chatbot.Builder configured = ai.bot(LocalAi.ASSISTANT);
            if (configured == null) return null;
            // build() hands back the bot the builder keeps shaping, so its attributes can size the memory before the rest is added
            int tokens = configured.build().getDefinition().attribute("maxInputTokens", 6000);
            bot = configured.tools(toolbox).approveToolsWith(call -> allowedTools.contains(call.name())).memory(new Memory(tokens)).build();
        }
        return bot;
    }
}
