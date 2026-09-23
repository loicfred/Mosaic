package mu.mosaic.opportunity.service.ai;

import org.solarframework.ai.Chatbot;
import org.solarframework.ai.dto.ChatbotDefinition;
import org.solarframework.ai.spring.AIManager;
import org.solarframework.core.util.SolarHome;

import java.nio.file.Path;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/** The chatbots exactly as the shipped config/ai/agents.json defines them, put on a scripted model. */
final class Agents {
    /** The website ships the config (its working directory holds config/), so the tests read the App's copy. */
    private Agents() {}

    static ChatbotDefinition definition(String name) {
        String previous = System.getProperty(SolarHome.PROPERTY);
        System.setProperty(SolarHome.PROPERTY, Path.of("../OpportunityApp").toAbsolutePath().normalize().toString());
        SolarHome.forgetDataFolder();
        AIManager manager = new AIManager();
        try {
            manager.LoadFromFile();
            return manager.getChatbot(name).getDefinition();
        } finally {
            if (previous == null) System.clearProperty(SolarHome.PROPERTY);
            else System.setProperty(SolarHome.PROPERTY, previous);
            SolarHome.forgetDataFolder();
        }
    }

    /** A LocalAi whose bots run on {@code model}; null means no model is configured. */
    static LocalAi on(FakeAIService model) {
        LocalAi ai = mock(LocalAi.class);
        when(ai.service()).thenReturn(model);
        when(ai.bot(anyString())).thenAnswer(call -> model == null ? null : Chatbot.builder(model).applyDefinition(definition(call.getArgument(0))));
        return ai;
    }
}
