package mu.mosaic.opportunity;

import org.solarframework.core.util.SolarHome;

import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Pins the site's folders to Java/OpportunityApp whatever directory it was started from. Its database, .env and the
 * Olist source folder are otherwise read relative to the working directory, so an IntelliJ run started from the
 * repository root looked for the database in the wrong place. A -Dsolar.home, SOLAR_HOME or explicit property still wins.
 */
final class ModuleHome {

    private ModuleHome() {
    }

    static void pin() {
        Path home = locate();
        if (home == null) return;
        if (System.getProperty(SolarHome.PROPERTY) == null && System.getenv(SolarHome.VARIABLE) == null) {
            System.setProperty(SolarHome.PROPERTY, home.toString());
        }
        setIfAbsent("spring.config.import", "optional:file:" + home.resolve(".env") + "[.properties]");
        setIfAbsent("mosaic.data.source-dir", home.resolve("../../AI/datasets").normalize().toString());
    }

    /** The module folder: the one holding the pom.xml above target/classes or the packaged jar; null when run from elsewhere. */
    private static Path locate() {
        try {
            Path code = Path.of(OpportunityApp.class.getProtectionDomain().getCodeSource().getLocation().toURI());
            for (Path dir = code; dir != null; dir = dir.getParent()) {
                if (dir.getFileName() != null && dir.getFileName().toString().equals("target")) {
                    Path module = dir.getParent();
                    return module != null && Files.isRegularFile(module.resolve("pom.xml")) ? module : null;
                }
            }
        } catch (URISyntaxException | RuntimeException ignored) {
            // An unusual class location (nested jar, custom loader): keep the working-directory behaviour.
        }
        return null;
    }

    private static void setIfAbsent(String key, String value) {
        if (System.getProperty(key) == null) System.setProperty(key, value);
    }
}
