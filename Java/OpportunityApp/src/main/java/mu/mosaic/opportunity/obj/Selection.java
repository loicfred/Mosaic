package mu.mosaic.opportunity.obj;

import org.springframework.ui.Model;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** The periods and filters the owner chose for the findings and trend pages; they live only in the URL, and a blank field means the default. */
public class Selection {
    private static final List<String> FIELDS = List.of("recent_start", "recent_end", "previous_start", "previous_end", "category", "customer_state");
    private final Map<String, String> chosen = new LinkedHashMap<>();

    public Selection(Map<String, String> params) {
        FIELDS.forEach(key -> { String v = params.get(key); if (v != null && !v.isBlank()) chosen.put(key, v.trim()); });
    }

    public boolean isEmpty() { return chosen.isEmpty(); }

    /** The chosen fields as API query parameters; a copy the caller may add to. */
    public Map<String, String> parameters() { return new LinkedHashMap<>(chosen); }

    /** Gives the page the selection and the same selection as a query string ("" or "?a=b&..."), for links that keep it. */
    public void addTo(Model model) {
        UriComponentsBuilder query = UriComponentsBuilder.newInstance();
        chosen.forEach(query::queryParam);
        model.addAttribute("selection", chosen);
        model.addAttribute("query", query.encode().build().toUriString());
    }
}
