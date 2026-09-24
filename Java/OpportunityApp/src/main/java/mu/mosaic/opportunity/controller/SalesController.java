package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.service.MosaicApi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.Map;

/** The Sales page, the site's home: the sales forecast; its evidence, investment suggestion and caveats open from tabs under the chart. */
@Controller
public class SalesController {
    private static final int FORECAST_HORIZON = 3;
    private final MosaicApi api;

    public SalesController(MosaicApi api) { this.api = api; }

    @GetMapping("/")
    public String sales(Model model) {
        new Breadcrumbs("sales", new Crumb("Sales", "/")).addTo(model);
        api.salesHistory().addTo(model, "history");
        api.salesForecast(FORECAST_HORIZON).addTo(model, "forecast");
        api.findings(Map.of()).addTo(model, "findings");
        return "sales";
    }
}
