package mu.mosaic.opportunity.data;

import java.io.BufferedReader;
import java.io.Closeable;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * RFC 4180 rows from a UTF-8 file: quoted fields may hold commas, doubled quotes and line breaks, which are kept as
 * written. A leading byte-order mark is dropped (Olist's translation file has one).
 */
public class CsvReader implements Closeable {
    private final BufferedReader in;

    public CsvReader(Path file) throws IOException {
        in = Files.newBufferedReader(file, StandardCharsets.UTF_8);
        in.mark(1);
        if (in.read() != '﻿') in.reset();
    }

    /** The next row, or null at the end of the file. */
    public String[] next() throws IOException {
        int c = in.read();
        if (c == -1) return null;
        List<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean quoted = false;
        for (; c != -1; c = in.read()) {
            if (quoted) {
                if (c != '"') field.append((char) c);
                else if (peek() == '"') field.append((char) in.read());
                else quoted = false;
            } else if (c == '"') quoted = true;
            else if (c == ',') { fields.add(field.toString()); field.setLength(0); }
            else if (c == '\n') break;
            else if (c != '\r') field.append((char) c);
        }
        fields.add(field.toString());
        return fields.toArray(String[]::new);
    }

    private int peek() throws IOException {
        in.mark(1);
        int c = in.read();
        in.reset();
        return c;
    }

    @Override
    public void close() throws IOException { in.close(); }
}
