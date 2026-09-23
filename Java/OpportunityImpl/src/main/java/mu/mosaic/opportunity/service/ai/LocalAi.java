package mu.mosaic.opportunity.service.ai;

import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIManager;
import org.solarframework.ai.IAIService;
import org.solarframework.ai.dto.ChatbotDefinition;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * The site's one way to the language model, through SolarFramework's AI manager.
 * <p>The model and the chatbots' instructions live in {@code config/ai/agents.json}, SolarFramework's own AI config
 * file, as in SolarERP. What a file cannot hold - tools, memory, the tool allowlist - is added in code by whoever
 * uses a bot. Without the file the model is off, and the site keeps working without it.
 */
@Component
public class LocalAi {
    public static final String ASSISTANT = "MosaicAssistant", NARRATOR = "ScenarioNarrator";
    private final IAIManager manager;

    public LocalAi(IAIManager manager) {
        this.manager = manager;
        manager.LoadFromFile();
    }

    /** The configured service, or null when no model is configured. */
    public IAIService service() {
        IAIService s = manager.getDefaultService();
        return s == null || s.getBaseUrl() == null || s.getBaseUrl().isBlank() ? null : s;
    }

    /** A chatbot from the config file, on its service, ready for the tools and memory only code can give it; null when there is none. */
    public Chatbot.Builder bot(String name) {
        Chatbot configured = manager.getChatbot(name);
        if (configured == null || service() == null) return null;
        return Chatbot.builder(configured.getService()).applyDefinition(configured.getDefinition());
    }

    /** The chatbots the config file defines, for the Help page. */
    public List<ChatbotDefinition> chatbots() { return manager.getChatbotDefinitions(); }

    /** Asks the model server; a server that does not answer is reported, never thrown. */
    public Status status() {
        IAIService s = service();
        if (s == null) return new Status(false, false, null, null);
        try {
            if (!s.isAvailable()) return new Status(true, false, s.getModel(), null);
            return new Status(true, true, s.getModel(), s.isModelSupportingTools());
        } catch (RuntimeException e) {
            return new Status(true, false, s.getModel(), null);
        }
    }

    /**
     * @param enabled   a model is configured
     * @param reachable its server answered
     * @param tools     whether the model says it can call tools; null when unknown
     */
    public record Status(boolean enabled, boolean reachable, String model, Boolean tools) {}
}
