package mu.mosaic.opportunity.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.core.util.FileUtils;
import org.solarframework.core.util.SolarHome;
import org.solarframework.runner.python.PythonRunner;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Comparator;

/**
 * Starts the Python analytics API from SolarHome with the website and stops it on shutdown, through
 * SolarFramework's {@link PythonRunner}. An API that is already answering is left alone, so a server started by hand,
 * or kept from an earlier run, is reused.
 * Python reads datasets and models beside the app package in SolarHome/config/py/mosaic. In the repository that folder is
 * the Python project itself, so its app/ is the source the zip was built from and is run as it is, never replaced.
 */
@Component
public class PythonApiLauncher implements SmartLifecycle {
    private static final Logger log = LoggerFactory.getLogger(PythonApiLauncher.class);
    private static final Duration READY_WAIT = Duration.ofSeconds(180);
    private final MosaicApi api;
    private final boolean autostart;
    private final String executable;
    private volatile PythonRunner runner;
    private volatile boolean running;

    public PythonApiLauncher(MosaicApi api, @Value("${mosaic.python.autostart}") boolean autostart, @Value("${mosaic.python.executable:}") String executable) {
        this.api = api;
        this.autostart = autostart;
        this.executable = executable;
    }

    @Override
    public void start() {
        running = true;
        if (!autostart) return;
        Path dir = preparePythonDirectory(); // unpacked even when an API is already running, so its next start runs this build's code
        if (checkIfAlreadyRunning()) return;
        if (dir == null) {
            log.warn("Analytics API not started: no app/main.py in SolarHome/config/py/mosaic. Package mosaic-python.zip.");
            return;
        }
        launchPython(dir);
    }

    private boolean checkIfAlreadyRunning() {
        if (api.health().data() != null) {
            log.info("Analytics API already running; using it as is.");
            return true;
        }
        return false;
    }
    private void launchPython(Path dir) {
        PythonRunner python = PythonRunner.module(dir, "app.main").interpreter(executable);
        if (executable.isBlank() && PythonRunner.venv(dir).isEmpty())
            log.warn("No virtual environment in {}; trying {} from the PATH, which may lack the API's packages.", dir, python.getInterpreter());
        try {
            python.start();
            runner = python;
            Thread.ofVirtual().name("analytics-api-ready").start(() -> awaitPythonReady(python));
        } catch (IOException e) {
            log.warn("Analytics API not started: could not run {} ({}). Set mosaic.python.executable.", python.getInterpreter(), e.getMessage());
        }
    }

    private void awaitPythonReady(PythonRunner python) {
        if (python.awaitReady(() -> api.health().data() != null, READY_WAIT)) {
            log.info("Analytics API ready.");
        } else if (running) {
            String reason = python.isAlive() ? "still starting after " + READY_WAIT.toSeconds() + " s" : "it exited with code " + python.getExitCode() + ", see its output above";
            log.warn("Analytics API not answering: {}", reason);
        }
    }

    @Override
    public void stop() {
        running = false;
        if (runner != null) runner.stop();
    }

    @Override
    public boolean isRunning() { return running; }

    private Path preparePythonDirectory() {
        Path destination = SolarHome.pathTo("config", "py", "mosaic");
        // the Python project's own folder (it has its requirements.txt), whose app/ is edited by hand; the zip only carries app/
        if (Files.isRegularFile(destination.resolve("requirements.txt"))) return Files.isRegularFile(destination.resolve("app/main.py")) ? destination : null;
        try (InputStream archive = getClass().getResourceAsStream("/mosaic-python.zip")) {
            if (archive != null) unpack(archive, destination);
        } catch (IOException e) {
            log.warn("Analytics API not started: could not unpack mosaic-python.zip ({})", e.getMessage());
            return null;
        }
        return Files.isRegularFile(destination.resolve("app/main.py")) ? destination : null;
    }

    /** The archive contains app/ at its root; datasets and models beside it are retained. */
    private static Path unpack(InputStream archive, Path target) throws IOException {
        Path destination = target.toAbsolutePath().normalize();
        Path parent = destination.getParent();
        Files.createDirectories(parent);
        Path staging = Files.createTempDirectory(parent, "mosaic-python-");
        try {
            FileUtils.unzip(archive, staging);
            if (!Files.isRegularFile(staging.resolve("app/main.py"))) throw new IOException("Python archive has no app/main.py");
            replaceAppDirectory(staging.resolve("app"), destination.resolve("app"));
            return target;
        } finally {
            if (Files.exists(staging)) deleteTree(staging);
        }
    }

    private static void replaceAppDirectory(Path stagedApp, Path app) throws IOException {
        Files.createDirectories(app.getParent());
        if (Files.exists(app)) deleteTree(app);
        Files.move(stagedApp, app);
    }

    private static void deleteTree(Path root) throws IOException {
        try (var paths = Files.walk(root)) {
            for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
        }
    }
}
