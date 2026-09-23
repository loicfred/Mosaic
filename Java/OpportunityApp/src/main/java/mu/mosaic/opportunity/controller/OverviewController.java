package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.ApiData;
import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.InvestmentAdvisor;
import mu.mosaic.opportunity.service.ai.LocalAi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

/** The sales forecast and, when it rises, where the data points for investment. */
@Controller
public class OverviewController {
    static final int FORECAST_HORIZON = 3;
    private final MosaicApi api;
    private final LocalAi ai;

    public OverviewController(MosaicApi api, LocalAi ai) {
        this.api = api;
        this.ai = ai;
    }

    @GetMapping("/")
    public String overview(Model model) {
        Breadcrumbs.addTo(model, "overview");
        api.salesHistory().addTo(model, "history");
        api.salesForecast(FORECAST_HORIZON).addTo(model, "forecast");
        var opportunities = api.salesOpportunities(FORECAST_HORIZON).addTo(model, "opportunities");
        if (opportunities != null) model.addAttribute("advice", InvestmentAdvisor.template(opportunities));
        model.addAttribute("aiStatus", ai.status());
        return "index";
    }
}
