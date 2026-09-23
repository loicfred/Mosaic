package mu.mosaic.opportunity.service;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.parallel.ResourceLock;
import org.solarframework.core.util.SolarHome;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;

import java.io.IOException;
import java.net.ServerSocket;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/** Runs a stand-in `app.main` (it only sleeps) with the project's real venv interpreter; skipped where there is none. */
@ResourceLock("solar.home")
class PythonApiLauncherTest {
    private static final Path AI = Path.of("../../AI").toAbsolutePath().normalize();
    private static final Path PYTHON = List.of(".venv/Scripts/python.exe", ".venv/bin/python").stream().map(AI::resolve).filter(Files::isRegularFile).findFirst().orElse(null);
    @TempDir Path home;
    private String previousHome;

    @BeforeEach
    void useTemporarySolarHome() {
        previousHome = System.getProperty(SolarHome.PROPERTY);
        System.setProperty(SolarHome.PROPERTY, home.toString());
        SolarHome.forgetDataFolder();
    }

    @AfterEach
    void restoreSolarHome() {
        if (previousHome == null) System.clearProperty(SolarHome.PROPERTY);
        else System.setProperty(SolarHome.PROPERTY, previousHome);
        SolarHome.forgetDataFolder();
    }

    private static Path pythonProject() {
        return SolarHome.pathTo("config", "py", "mosaic");
    }

    private static MosaicApi unreachableApi() throws IOException {
        return new MosaicApi(closedPort(), 2);
    }

    private static List<ProcessHandle> pythonChildren() {
        return ProcessHandle.current().descendants().filter(p -> p.info().command().orElse("").toLowerCase().contains("python")).toList();
    }

    /** Just the two beans, as a host application wires them. */
    @Configuration
    @Import({MosaicApi.class, PythonApiLauncher.class})
    static class Host {}

    /** The path Ctrl+C or an IDE's stop button takes: the whole application context closes. */
    @Test
    void closingTheApplicationStopsTheApi() throws Exception {
        assumeTrue(PYTHON != null, "no AI/.venv interpreter on this machine");
        writeStandIn(pythonProject());
        List<ProcessHandle> started;
        try (var ctx = new SpringApplicationBuilder(Host.class).web(WebApplicationType.NONE).properties("mosaic.api.base-url=" + closedPort(), "mosaic.api.timeout-seconds=2",
                "mosaic.python.autostart=true", "mosaic.python.executable=" + PYTHON.toAbsolutePath()).run()) {
            started = pythonChildren();
            assertFalse(started.isEmpty(), "starting the application should start the API");
        }
        Thread.sleep(500);
        assertTrue(started.stream().noneMatch(ProcessHandle::isAlive), "closing the application must stop the API");
    }

    private static String closedPort() throws IOException {
        try (ServerSocket s = new ServerSocket(0)) { return "http://127.0.0.1:" + s.getLocalPort(); }
    }

    private static void writeStandIn(Path dir) throws IOException {
        Files.createDirectories(dir.resolve("app"));
        Files.writeString(dir.resolve("app/__init__.py"), "");
        Files.writeString(dir.resolve("app/main.py"), "import time\ntime.sleep(120)\n");
    }

    @Test
    void doesNothingWhenSwitchedOff() throws Exception {
        var launcher = new PythonApiLauncher(unreachableApi(), false, "");
        launcher.start();
        assertTrue(launcher.isRunning());
        assertTrue(pythonChildren().isEmpty());
        launcher.stop();
    }

    @Test
    void missingProjectIsReportedNotFatal() throws Exception {
        var launcher = new PythonApiLauncher(unreachableApi(), true, "");
        launcher.start();
        assertTrue(launcher.isRunning(), "the website must still start without the API");
        launcher.stop();
    }
}
