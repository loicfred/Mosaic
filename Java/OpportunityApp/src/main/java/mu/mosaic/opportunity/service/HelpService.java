package mu.mosaic.opportunity.service;

import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.mvc.method.RequestMappingInfo;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/** What the Help page lists about this website, read from Spring itself so it cannot drift from the code. */
@Service
public class HelpService {
    private final RequestMappingHandlerMapping mappings;

    public HelpService(RequestMappingHandlerMapping requestMappingHandlerMapping) { this.mappings = requestMappingHandlerMapping; }

    /** @param kind "Page" for a screen, "JSON" for what the pages' scripts call */
    public record Route(String method, String path, String kind, String handler) {}

    /** Every address this site serves, sorted by path. */
    public List<Route> routes() {
        List<Route> out = new ArrayList<>();
        for (Map.Entry<RequestMappingInfo, HandlerMethod> e : mappings.getHandlerMethods().entrySet()) {
            HandlerMethod h = e.getValue();
            if (!h.getBeanType().getPackageName().startsWith("mu.mosaic.opportunity")) continue;
            String kind = h.getBeanType().getPackageName().endsWith(".api") ? "JSON" : "Page";
            for (String path : e.getKey().getPatternValues())
                for (RequestMethod m : e.getKey().getMethodsCondition().getMethods()) out.add(new Route(m.name(), path, kind, h.getBeanType().getSimpleName() + "." + h.getMethod().getName()));
        }
        out.sort(Comparator.comparing(Route::path).thenComparing(Route::method));
        return out;
    }
}
