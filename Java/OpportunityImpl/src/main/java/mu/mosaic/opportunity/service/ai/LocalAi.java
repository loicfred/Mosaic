package mu.mosaic.opportunity.service.ai;

import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIManager;
import org.solarframework.ai.IAIService;
import org.solarframework.ai.dto.ChatbotDefinition;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * The site's one way to the language model, through SolarFramework's AI manager.
 * <p>The model and the chatbots' instructions live in {@code config/ai/agents.json}, SolarFramework's own AI config
 * file, as in SolarERP. What a file cannot hold - tools, memory, the tool allowlist - is added in code by whoever
 * uses a bot. Without the file the model is off, and the site keeps working without it.
 * <p>When the {@value #CLOUD_KEY} environment variable is set and the file defines a {@value #CLOUD} service, every
 * bot runs on that cloud service instead, so the key stays out of the committed file.
 */
@Component
public class LocalAi {
    static final String CLOUD = "Groq", CLOUD_KEY = "GROQ_API_KEY";
    public static final String ASSISTANT = "MosaicAssistant", NARRATOR = "ScenarioNarrator", ADVISOR = "InvestmentAdvisor", CAVEATS = "CaveatWriter";
    private final IAIManager manager;

    @Autowired
    public LocalAi(IAIManager manager) { this(manager, System.getenv()); }

    /** @param env where the cloud key is looked for; tests pass their own so the machine's key cannot change them */
    LocalAi(IAIManager manager, Map<String, String> env) {
        this.manager = manager;
        manager.LoadFromFile();
        useCloud(manager, env);
    }

    /** Points the service the bots use at the cloud service's endpoint and model, with the key from the environment. */
    static void useCloud(IAIManager manager, Map<String, String> env) {
        String key = env.get(CLOUD_KEY);
        IAIService local = manager.getDefaultService();
        if (key == null || key.isBlank() || local == null || !manager.hasService(CLOUD)) return;
        IAIService cloud = manager.getService(CLOUD);
        local.setBaseUrl(cloud.getBaseUrl());
        local.setModel(cloud.getModel());
        local.setApiKey(key);
    }

    /**
     * Whether a service answers. SolarFramework asks LM Studio's own API, which a cloud endpoint does not have, so
     * an https endpoint is taken as up and a failing call falls back to the template like any other failure.
     */
    public static boolean reachable(IAIService s) {
        try {
            return s.getBaseUrl() != null && s.getBaseUrl().startsWith("https://") || s.isAvailable();
        } catch (RuntimeException e) {
            return false;
        }
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
            if (!reachable(s)) return new Status(true, false, s.getModel(), null);
            if (s.getBaseUrl().startsWith("https://")) return new Status(true, true, s.getModel(), null);
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
