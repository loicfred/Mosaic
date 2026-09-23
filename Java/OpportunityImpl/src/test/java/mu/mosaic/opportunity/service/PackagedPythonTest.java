package mu.mosaic.opportunity.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

class PackagedPythonTest {
    @Test
    void unpacksAndReplacesPythonPackage(@TempDir Path dir) throws IOException {
        Path target = dir.resolve("config/py/mosaic");
        PythonApiLauncher.unpack(new ByteArrayInputStream(zip(Map.of("app/main.py", "old", "app/removed.py", "old"))), target);
        Files.createDirectories(target.resolve("datasets"));
        Files.writeString(target.resolve("datasets/orders.csv"), "order_id");
        byte[] zip = zip(Map.of("app/__init__.py", "", "app/main.py", "print('ready')"));

        assertEquals(target, PythonApiLauncher.unpack(new ByteArrayInputStream(zip), target));
        assertEquals("print('ready')", Files.readString(target.resolve("app/main.py")));
        assertFalse(Files.exists(target.resolve("app/removed.py")));
        assertEquals("order_id", Files.readString(target.resolve("datasets/orders.csv")));
    }

    @Test
    void rejectsEntriesOutsideTheTarget(@TempDir Path dir) throws IOException {
        Path target = dir.resolve("config/py/mosaic");
        PythonApiLauncher.unpack(new ByteArrayInputStream(zip(Map.of("app/main.py", "old"))), target);
        byte[] zip = zip(Map.of("app/main.py", "", "../escape.py", "bad"));
        assertThrows(IOException.class, () -> PythonApiLauncher.unpack(new ByteArrayInputStream(zip), target));
        assertFalse(Files.exists(dir.resolve("config/py/escape.py")));
        assertEquals("old", Files.readString(target.resolve("app/main.py")));
    }

    private static byte[] zip(Map<String, String> entries) throws IOException {
        var output = new ByteArrayOutputStream();
        try (var archive = new ZipOutputStream(output)) {
            for (var entry : entries.entrySet()) {
                archive.putNextEntry(new ZipEntry(entry.getKey()));
                archive.write(entry.getValue().getBytes(java.nio.charset.StandardCharsets.UTF_8));
                archive.closeEntry();
            }
        }
        return output.toByteArray();
    }
}
