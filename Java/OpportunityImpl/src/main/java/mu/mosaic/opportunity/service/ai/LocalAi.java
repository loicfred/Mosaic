package mu.mosaic.opportunity.service.ai;

import org.solarframework.ai.Chatbot;
import org.solarframework.ai.IAIManager;
import org.solarframework.ai.IAIService;
import org.solarframework.ai.dto.ChatbotDefinition;
import org.solarframework.core.util.EnvValue;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * The site's one way to the language model, through SolarFramework's AI manager.
 * <p>The model and the chatbots' instructions live in {@code config/ai/agents.json}, SolarFramework's own AI config
 * file, as in SolarERP. What a file cannot hold - tools, memory, the tool allowlist - is added in code by whoever
 * uses a bot. Without the file the model is off, and the site keeps working without it.
 * <p>When the file defines a {@value #CLOUD} service and the variable its {@code "${NAME}"} key names is set, every
 * bot runs on that cloud service instead. SolarFramework reads the key from the environment, so it stays out of the
 * committed file.
 */
@Component
public class LocalAi {
    private static final String CLOUD = "Groq";
    private final IAIManager manager;

    /** The chatbots {@code config/ai/agents.json} defines, by the name they have there. */
    public enum Bot {
        SCENARIO_NARRATOR("ScenarioNarrator"), INVESTMENT_ADVISOR("InvestmentAdvisor"), CAVEAT_WRITER("CaveatWriter"),
        TREND_ADVISOR("TrendAdvisor"), TREND_CAVEATS("TrendCaveats"), PANEL_CHAT("PanelChat");

        private final String configName;

        Bot(String configName) { this.configName = configName; }
    }

    public LocalAi(IAIManager manager) {
        this.manager = manager;
        manager.LoadFromFile();
        useCloud();
    }

    /** Points the service the bots use at the cloud service's endpoint, model and key, when that key is set. */
    private void useCloud() {
        IAIService local = manager.getDefaultService();
        if (local == null || !manager.hasService(CLOUD)) return;
        IAIService cloud = manager.getService(CLOUD);
        String key = EnvValue.resolve(cloud.getApiKey());
        if (key == null || key.isBlank() || key.equals("N/A")) return;
        local.setBaseUrl(cloud.getBaseUrl());
        local.setModel(cloud.getModel());
        local.setApiKey(cloud.getApiKey());
    }

    /** Whether a service answers; SolarFramework sends the key, so this holds for the cloud service too. */
    public boolean reachable(IAIService s) {
        try {
            return s.isAvailable();
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
    public Chatbot.Builder bot(Bot bot) {
        Chatbot configured = manager.getChatbot(bot.configName);
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
            // a cloud endpoint names its models but reports no state or capabilities, so tool support stays unknown
            return new Status(true, true, s.getModel(), s.getModelState() == null ? null : s.isModelSupportingTools());
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
