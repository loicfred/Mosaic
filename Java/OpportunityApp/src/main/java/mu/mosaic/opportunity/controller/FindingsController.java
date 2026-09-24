package mu.mosaic.opportunity.controller;

import jakarta.servlet.http.HttpServletResponse;
import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.obj.Selection;
import mu.mosaic.opportunity.service.MosaicApi;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Every check in one ranked list, and the orders behind one of them. The periods, filters and thresholds live only in the URL. */
@Controller
public class FindingsController {
    private static final List<String> RECORDS = List.of("page", "page_size", "population");
    private final MosaicApi api;

    public FindingsController(MosaicApi api) { this.api = api; }

    @GetMapping("/findings")
    public String findings(@RequestParam Map<String, String> params, Model model) {
        new Breadcrumbs("findings", new Crumb("Findings", "/findings")).addTo(model);
        Selection selection = new Selection(params);
        selection.addTo(model);
        Map<String, String> request = selection.parameters();
        // each t.<finding id> field becomes one entry of the API's thresholds JSON; the API rejects values outside 0-100
        String thresholds = params.entrySet().stream()
                .filter(e -> e.getKey().matches("t\\.[a-z_]+:[a-z_]+") && e.getValue().matches("-?\\d+(\\.\\d+)?"))
                .map(e -> "\"" + e.getKey().substring(2) + "\":" + e.getValue())
                .collect(Collectors.joining(","));
        if (!thresholds.isEmpty()) request.put("thresholds", "{" + thresholds + "}");
        api.findings(request).addTo(model, "findings");
        return "findings";
    }

    @GetMapping("/findings/{id}")
    public String finding(@PathVariable String id, @RequestParam Map<String, String> params, Model model, HttpServletResponse response) {
        new Breadcrumbs("findings", new Crumb("Findings", "/findings"), new Crumb(id, null)).addTo(model);
        model.addAttribute("findingId", id);
        Selection selection = new Selection(params);
        selection.addTo(model);
        Map<String, String> request = selection.parameters();
        RECORDS.stream().filter(params::containsKey).forEach(key -> request.put(key, params.get(key)));
        ApiResult result = api.findingRecords(id, request);
        if (result.status() == 404) response.setStatus(404);
        result.addTo(model, "records");
        return "finding";
    }

    @GetMapping("/findings/{id}/export")
    public ResponseEntity<String> export(@PathVariable String id, @RequestParam Map<String, String> params) {
        Map<String, String> request = new Selection(params).parameters();
        if (params.containsKey("population")) request.put("population", params.get("population"));
        return api.findingExport(id, request);
    }
}
