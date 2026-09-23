package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import mu.mosaic.opportunity.service.HelpService;
import mu.mosaic.opportunity.service.MosaicApi;
import mu.mosaic.opportunity.service.ai.LocalAi;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

/** The Help page, as in SolarERP: a guide, the endpoints of both apps, and what the AI side reads and runs. */
@Controller
public class HelpController {
    private final MosaicApi api;
    private final HelpService help;
    private final LocalAi ai;

    public HelpController(MosaicApi api, HelpService help, LocalAi ai) {
        this.api = api;
        this.help = help;
        this.ai = ai;
    }

    @GetMapping("/help")
    public String help(Model model) {
        Breadcrumbs.addTo(model, "help", new Crumb("Help", "/help"));
        model.addAttribute("routes", help.routes());
        api.openApi().addTo(model, "openapi");
        api.datasets().addTo(model, "datasets");
        api.health().addTo(model, "health");
        model.addAttribute("chatbots", ai.chatbots());
        model.addAttribute("aiStatus", ai.status());
        return "help";
    }
}
