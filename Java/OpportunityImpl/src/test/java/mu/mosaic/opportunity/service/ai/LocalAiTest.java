package mu.mosaic.opportunity.service.ai;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.parallel.ResourceLock;
import org.solarframework.ai.spring.AIManager;
import org.solarframework.core.util.SolarHome;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

@ResourceLock("solar.home")
class LocalAiTest {
    private String previousHome;

    private void useHome(Path home) {
        previousHome = System.getProperty(SolarHome.PROPERTY);
        System.setProperty(SolarHome.PROPERTY, home.toString());
        SolarHome.forgetDataFolder();
    }

    @AfterEach
    void restoreHome() {
        if (previousHome == null) System.clearProperty(SolarHome.PROPERTY);
        else System.setProperty(SolarHome.PROPERTY, previousHome);
        SolarHome.forgetDataFolder();
    }

    @Test
    void theShippedConfigDefinesTheModelAndBothBots() {
        useHome(Path.of("../OpportunityApp").toAbsolutePath().normalize());
        LocalAi ai = new LocalAi(new AIManager(), java.util.Map.of());
        assertEquals("http://localhost:1234", ai.service().getBaseUrl());
        assertEquals("google/gemma-4-e4b", ai.service().getModel());
        assertNotNull(ai.bot(LocalAi.ASSISTANT));
        assertNotNull(ai.bot(LocalAi.NARRATOR));
        assertEquals(6000, Agents.definition(LocalAi.ASSISTANT).attribute("maxInputTokens", 0));
    }

    @Test
    void noConfigMeansNoModelAndAnEmptyDefaultFile(@TempDir Path dir) {
        useHome(dir);
        Path missing = SolarHome.pathTo("config", "ai", "agents.json");
        LocalAi ai = new LocalAi(new AIManager());
        assertNull(ai.service());
        assertNull(ai.bot(LocalAi.ASSISTANT));
        assertFalse(ai.status().enabled());
        assertTrue(Files.isRegularFile(missing));
    }

    @Test
    void theCloudKeyMovesTheBotsToTheCloudServiceAndItsAbsenceLeavesThemLocal() {
        AIManager manager = new AIManager();
        manager.makeNewService("LMStudio", "http://localhost:1234", "N/A", "local-model");
        manager.makeNewService(LocalAi.CLOUD, "https://api.groq.com/openai", "N/A", "cloud-model");
        LocalAi.useCloud(manager, java.util.Map.of());
        assertEquals("http://localhost:1234", manager.getDefaultService().getBaseUrl());
        LocalAi.useCloud(manager, java.util.Map.of(LocalAi.CLOUD_KEY, "gsk_test"));
        assertEquals("https://api.groq.com/openai", manager.getDefaultService().getBaseUrl());
        assertEquals("cloud-model", manager.getDefaultService().getModel());
        assertEquals("gsk_test", manager.getDefaultService().getApiKey());
        assertTrue(LocalAi.reachable(manager.getDefaultService()));
    }
}
