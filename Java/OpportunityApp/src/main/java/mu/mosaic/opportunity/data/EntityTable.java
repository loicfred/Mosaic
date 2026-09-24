package mu.mosaic.opportunity.data;

import jakarta.persistence.Column;
import jakarta.persistence.Table;
import org.solarframework.db.api.IDatabaseService;

import java.io.IOException;
import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * One entity's table, filled from its CSV file. The file's header names the columns; each must match an entity
 * field's {@code @Column} name and is parsed to that field's type. A blank field is NULL. Rows get IDs 1, 2, 3... in
 * file order, so the table (and an export sorted by ID) keeps the file's row order.
 * <p>Rows go in through JDBC batches in one transaction per table, bound as Hibernate binds the same types
 * (timestamps through {@code setTimestamp}): entity inserts took 191 s for the million geolocation rows.
 */
public record EntityTable(Class<?> entity, String name, Map<String, Class<?>> columnTypes) {
    private static final DateTimeFormatter TIMESTAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final int BATCH = 5000;

    /** The table named by the entity's {@code @Table}, with each {@code @Column} name and its field type. */
    public EntityTable(Class<?> entity) {
        this(entity, entity.getAnnotation(Table.class).name(), Arrays.stream(entity.getDeclaredFields()).filter(f -> f.isAnnotationPresent(Column.class))
                .collect(Collectors.toMap(f -> f.getAnnotation(Column.class).name(), Field::getType)));
    }

    /** Inserts every row of {@code csv} and returns how many there were; a failure leaves the table as it was. */
    public long load(IDatabaseService db, Path csv) throws IOException, SQLException {
        try (CsvReader reader = new CsvReader(csv); Connection con = db.getDataSource().getConnection()) {
            String[] header = reader.next();
            if (header == null || header.length != columnTypes.size() || !columnTypes.keySet().containsAll(List.of(header)))
                throw new IllegalStateException(csv.getFileName() + " has columns " + Arrays.toString(header) + ", its table " + columnTypes.keySet());
            String sql = "INSERT INTO " + name + " (ID, CreatedAt, UpdatedAt, " + String.join(", ", header) + ") VALUES (?, ?, ?" + ", ?".repeat(header.length) + ")";
            Timestamp now = Timestamp.from(Instant.now());
            long rows = 0;
            con.setAutoCommit(false);
            try (PreparedStatement insert = con.prepareStatement(sql)) {
                for (String[] row = reader.next(); row != null; row = reader.next()) {
                    if (row.length != header.length) throw new IllegalStateException(csv.getFileName() + " row " + (rows + 1) + " has " + row.length + " fields, the header " + header.length);
                    insert.setLong(1, ++rows);
                    insert.setTimestamp(2, now);
                    insert.setTimestamp(3, now);
                    for (int i = 0; i < header.length; i++) insert.setObject(i + 4, parse(row[i], columnTypes.get(header[i])));
                    insert.addBatch();
                    if (rows % BATCH == 0) insert.executeBatch();
                }
                insert.executeBatch();
                con.commit();
                return rows;
            } catch (IOException | SQLException | RuntimeException e) {
                con.rollback();
                throw e;
            }
        }
    }

    private Object parse(String text, Class<?> type) {
        if (text.isEmpty()) return null;
        if (type == String.class) return text;
        if (type == Integer.class) return Integer.valueOf(text);
        if (type == Double.class) return Double.valueOf(text);
        if (type == BigDecimal.class) return new BigDecimal(text);
        if (type == LocalDateTime.class) return Timestamp.valueOf(LocalDateTime.parse(text, TIMESTAMP));
        throw new IllegalArgumentException("No CSV parsing for " + type.getName());
    }
}
