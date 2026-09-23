package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.ApiData;
import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.service.MosaicApi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class OverviewController {
    static final int FORECAST_HORIZON = 3;
    private final MosaicApi api;

    public OverviewController(MosaicApi api) { this.api = api; }

    @GetMapping("/")
    public String overview(Model model) {
        Breadcrumbs.addTo(model, "overview");
        model.addAttribute("latestSales", ApiData.last(api.salesHistory().addTo(model, "history"), "months"));
        api.salesForecast(FORECAST_HORIZON).addTo(model, "forecast");
        model.addAttribute("latestDelivery", ApiData.last(api.deliverySummary().addTo(model, "delivery"), "monthly"));
        model.addAttribute("latestReviews", ApiData.last(api.reviewSummary().addTo(model, "reviews"), "monthly"));
        api.categories(null).addTo(model, "allCategories");
        api.categories(CategoryController.FLAG_BEHIND).addTo(model, "behind");
        return "index";
    }
}
