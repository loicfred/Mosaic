package mu.mosaic.opportunity.obj;

import org.springframework.ui.Model;

import java.util.List;
import java.util.stream.Stream;

/**
 * The trail shown under the header, as in SolarERP's obj/Breadcrumbs: Mosaic, then where the page sits.
 * @param page the sidebar entry to mark as current
 */
public record Breadcrumbs(String page, List<Crumb> crumbs) {

    public record Crumb(String label, String url) {} // the last one is the page itself and is not linked

    public Breadcrumbs(String page, Crumb... trail) { this(page, Stream.concat(Stream.of(new Crumb("Mosaic", "/")), Stream.of(trail)).toList()); }

    /** Marks the page in the sidebar, gives it the trail, and takes the last step as the title. */
    public void addTo(Model model) {
        model.addAttribute("page", page);
        model.addAttribute("crumbs", crumbs);
        model.addAttribute("title", crumbs.getLast().label());
    }
}
