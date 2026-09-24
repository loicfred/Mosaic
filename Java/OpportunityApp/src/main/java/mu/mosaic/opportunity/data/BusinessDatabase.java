package mu.mosaic.opportunity.data;

import mu.mosaic.opportunity.obj.entity.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.core.util.SolarHome;
import org.solarframework.db.api.IDatabaseManager;
import org.solarframework.db.api.IDatabaseService;
import org.springframework.beans.factory.SmartInitializingSingleton;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.SQLException;
import java.util.List;
import java.util.stream.Stream;

/**
 * The business database: one table per Olist file, plus the separate small-business cash-flow practice file. Tables still empty are filled from the original CSV files, and when
 * the export folder lacks a table's file the whole database is written there, which is what the Python API reads. Runs
 * once every bean exists and before any is started, so the API is launched on files that are already there.
 */
@Component
public class BusinessDatabase implements SmartInitializingSingleton {
    private static final Logger log = LoggerFactory.getLogger(BusinessDatabase.class);
    private static final List<EntityTable> TABLES = Stream.of(OlistOrder.class, OlistOrderItem.class, OlistOrderPayment.class,
            OlistOrderReview.class, OlistCustomer.class, OlistSeller.class, OlistProduct.class, OlistGeolocation.class, OlistCategoryTranslation.class,
            SmallBusinessCashflow.class).map(EntityTable::new).toList();
    private final IDatabaseManager manager;
    private final boolean prepareOnStart;
    private final Path sourceDir, exportDir;

    public BusinessDatabase(IDatabaseManager manager, @Value("${mosaic.data.prepare-on-start}") boolean prepareOnStart,
                            @Value("${mosaic.data.source-dir}") String sourceDir) {
        this.manager = manager;
        this.prepareOnStart = prepareOnStart;
        this.sourceDir = Path.of(sourceDir).toAbsolutePath().normalize();
        this.exportDir = SolarHome.pathTo("config", "py", "mosaic", "datasets");
    }

    @Override
    public void afterSingletonsInstantiated() {
        if (!prepareOnStart) return;
        IDatabaseService db = manager.getDefaultService();
        db.createSchemaIfMissing(TABLES.stream().<Class<?>>map(EntityTable::entity).toList());
        for (EntityTable table : TABLES)
            if (db.doQueryValueNoCache(Long.class, "SELECT COUNT(*) FROM " + table.name()).orElse(0L) == 0) load(db, table);
        // Reading the original CSVs from the export folder itself: an export would rewrite them, and the models,
        // which record the originals' hashes, would then refuse to answer (409).
        if (exportDir.equals(sourceDir)) return;
        if (TABLES.stream().allMatch(t -> Files.isRegularFile(exportDir.resolve(t.name() + ".csv")))) return;
        long start = System.nanoTime();
        db.exportCsv(exportDir);
        log.info("Exported the business database to {} in {} s.", exportDir, String.format("%.1f", (System.nanoTime() - start) / 1e9));
    }

    private void load(IDatabaseService db, EntityTable table) {
        Path csv = sourceDir.resolve(table.name() + ".csv");
        if (!Files.isRegularFile(csv)) {
            log.warn("Table {} is empty and {} is missing: nothing to import. Set mosaic.data.source-dir.", table.name(), csv);
            return;
        }
        long start = System.nanoTime();
        try {
            long rows = table.load(db, csv);
            manager.resetCacheForClass(table.entity(), true, true); // written past SolarFramework, so its cached reads are stale
            log.info("Imported {} rows into {} in {} s.", rows, table.name(), String.format("%.1f", (System.nanoTime() - start) / 1e9));
        } catch (IOException | SQLException e) {
            throw new IllegalStateException("Import of " + csv + " failed", e);
        }
    }
}
