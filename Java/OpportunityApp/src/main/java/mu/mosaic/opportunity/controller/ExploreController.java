package mu.mosaic.opportunity.controller;

import jakarta.servlet.http.HttpServletResponse;
import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.service.MosaicApi;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import java.util.Map;

/** Observed business views. Python supplies every metric and denominator. */
@Controller
public class ExploreController {
    private final MosaicApi api;
    private static final Map<String, String> TITLES = Map.of("quality", "Data quality", "payments", "Payments", "freight", "Freight burden", "cohorts", "Customer cohorts", "models", "Model cards", "entities", "Categories and sellers");
    public ExploreController(MosaicApi api) { this.api = api; }

    @GetMapping("/data-quality") public String quality(Model model) { return page(model, "quality"); }
    @GetMapping("/payments") public String payments(Model model) { return page(model, "payments"); }
    @GetMapping("/freight") public String freight(Model model) { return page(model, "freight"); }
    @GetMapping("/cohorts") public String cohorts(Model model) { return page(model, "cohorts"); }
    @GetMapping("/models") public String models(Model model) { return page(model, "models"); }
    @GetMapping("/entities") public String entities(Model model) { return page(model, "entities"); }

    @GetMapping("/entities/{kind}/{name}")
    public String entity(@PathVariable String kind, @PathVariable String name, Model model, HttpServletResponse response) {
        ApiResult result = (kind.equals("category") || kind.equals("seller")) ? api.exploreEntity(kind, name) : new ApiResult("Unknown entity type.", 404);
        if (result.status() == 404) response.setStatus(404);
        shell(model, "entity", name);
        result.addTo(model, "explore");
        return "explore";
    }

    private String page(Model model, String section) {
        shell(model, section, TITLES.get(section));
        api.explore(section).addTo(model, "explore");
        return "explore";
    }

    private void shell(Model model, String section, String title) {
        String path = section.equals("quality") ? "data-quality" : section.equals("entity") ? "entities" : section;
        new Breadcrumbs(path, new Crumb(title, "/" + path)).addTo(model);
        model.addAttribute("exploreSection", section);
        model.addAttribute("exploreTitle", title);
    }
}

