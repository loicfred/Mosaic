package mu.mosaic.opportunity;

import org.springframework.boot.json.JsonParserFactory;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/** Real API responses, trimmed, from src/test/resources/api. Each call returns a fresh, mutable copy. */
public final class Fixtures {
    private Fixtures() {}

    public static Map<String, Object> load(String name) {
        try (var in = Fixtures.class.getResourceAsStream("/api/" + name + ".json")) {
            return JsonParserFactory.getJsonParser().parseMap(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
