package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.obj.Breadcrumbs;
import mu.mosaic.opportunity.obj.Breadcrumbs.Crumb;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

/** Static application and author information. */
@Controller
public class AboutController {
    @GetMapping("/about")
    public String about(Model model) {
        new Breadcrumbs("about", new Crumb("About", "/about")).addTo(model);
        return "about";
    }
}