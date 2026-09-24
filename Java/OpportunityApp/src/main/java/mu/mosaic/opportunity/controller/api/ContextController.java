package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;

/** Only reads context already stored by the Python API. */
@RestController
public class ContextController {
    private final MosaicApi api;
    public ContextController(MosaicApi api) { this.api = api; }

    @GetMapping("/api/chart-context")
    public Map<String, Object> context() {
        ApiResult events = api.events(null), economy = api.economy(null);
        Map<String, Object> eventData = events.data() == null ? Map.of() : events.data();
        Map<String, Object> economyData = economy.data() == null ? Map.of() : economy.data();
        boolean available = Boolean.TRUE.equals(eventData.get("holidays_included")) || Boolean.TRUE.equals(economyData.get("available"));
        return Map.of("available", available, "events", eventData, "economy", economyData);
    }
}
