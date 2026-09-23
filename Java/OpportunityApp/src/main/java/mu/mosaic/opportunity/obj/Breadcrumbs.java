package mu.mosaic.opportunity.obj;

import org.springframework.ui.Model;

import java.util.ArrayList;
import java.util.List;

// The trail shown under the header, as in SolarERP's obj/Breadcrumbs: Overview, then where the page sits.
public class Breadcrumbs {

    public record Crumb(String label, String url) {} // the last one is the page itself and is not linked

    private static final Crumb HOME = new Crumb("Overview", "/");

    public static List<Crumb> build(Crumb... trail) {
        List<Crumb> crumbs = new ArrayList<>(List.of(HOME));
        crumbs.addAll(List.of(trail));
        return crumbs;
    }

    /** Marks {@code page} in the sidebar, gives it the trail below Overview, and takes the last step as the title. */
    public static void addTo(Model model, String page, Crumb... trail) {
        List<Crumb> crumbs = build(trail);
        model.addAttribute("page", page);
        model.addAttribute("crumbs", crumbs);
        model.addAttribute("title", crumbs.getLast().label());
    }
}
