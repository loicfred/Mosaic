package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.service.MosaicApi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class RiskController {
    private final MosaicApi api;

    public RiskController(MosaicApi api) { this.api = api; }

    @GetMapping("/risk")
    public String risk(Model model) {
        Breadcrumbs.addTo(model, "risk", new Crumb("Delivery and reviews", "/risk"));
        api.deliverySummary().addTo(model, "delivery");
        api.openOrders(25).addTo(model, "openOrders");
        api.sellers(30, 25).addTo(model, "sellers");
        api.reviewSummary().addTo(model, "reviews");
        api.unreviewed(15).addTo(model, "unreviewed");
        return "risk";
    }
}
