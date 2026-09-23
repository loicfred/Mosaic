package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.service.MosaicApi;

import org.solarframework.core.util.StringUtils;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.Set;

@Controller
public class CategoryController {
    static final String FLAG_BEHIND = "underperforming_total", FLAG_ANOMALY = "latest_month_anomaly";
    private static final Set<String> FLAGS = Set.of(FLAG_BEHIND, FLAG_ANOMALY);
    private final MosaicApi api;

    public CategoryController(MosaicApi api) { this.api = api; }

    @GetMapping("/categories")
    public String list(@RequestParam(required = false) String flag, Model model) {
        String f = flag != null && FLAGS.contains(flag) ? flag : null;
        Breadcrumbs.addTo(model, "categories", new Crumb("Category health", "/categories"));
        model.addAttribute("flag", f);
        api.categories(f).addTo(model, "categories");
        return "categories";
    }

    @GetMapping("/categories/{name}")
    public String detail(@PathVariable String name, Model model) {
        Breadcrumbs.addTo(model, "categories", new Crumb("Category health", "/categories"), new Crumb(StringUtils.readable(name), "/categories/" + name));
        model.addAttribute("name", name);
        api.category(name).addTo(model, "category");
        return "category";
    }
}
