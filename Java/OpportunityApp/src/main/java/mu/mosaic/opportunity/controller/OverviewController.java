package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.service.MosaicApi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

/** The sales forecast; its evidence, investment suggestion and caveats open from buttons under the chart. */
@Controller
public class OverviewController {
    static final int FORECAST_HORIZON = 3;
    private final MosaicApi api;

    public OverviewController(MosaicApi api) { this.api = api; }

    @GetMapping("/")
    public String overview(Model model) {
        Breadcrumbs.addTo(model, "overview");
        api.salesHistory().addTo(model, "history");
        api.salesForecast(FORECAST_HORIZON).addTo(model, "forecast");
        return "index";
    }
}
