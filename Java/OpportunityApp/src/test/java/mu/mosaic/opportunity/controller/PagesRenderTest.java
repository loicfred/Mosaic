package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.service.ai.LocalAi;
import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Measure;
import mu.mosaic.opportunity.service.MosaicApi;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.json.JsonParserFactory;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Renders every page from real API responses (trimmed, in test resources) and with the API failing. */
@SpringBootTest(properties = "mosaic.python.autostart=false")
@AutoConfigureMockMvc
@WithMockUser // every page sits behind the sign-in
class PagesRenderTest {
    private static final String DOWN = "The analytics API is not answering at test.";
    @Autowired MockMvc mvc;
    @MockitoBean MosaicApi api;
    @MockitoBean LocalAi ai;

    /** A real API reply, trimmed, from src/test/resources/api; a fresh, mutable copy each time. */
    private Map<String, Object> fixture(String name) {
        try (var in = getClass().getResourceAsStream("/api/" + name + ".json")) {
            return JsonParserFactory.getJsonParser().parseMap(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private ApiResult ok(String name) { return new ApiResult(fixture(name)); }

    private static final ApiResult FINDINGS = new ApiResult(Map.of("triggered", 1, "ranking_rule", "Triggered checks first.", "dataset_version", "abc123", "limitations", List.of("Coincidence is not cause."),
            "checks", List.of(Map.of("finding_id", "sales:late_rate_rising", "page", "sales", "title", "Late deliveries are becoming more common",
                    "triggered", true, "records_available", true, "exposure", Map.of("sales", 400.0, "basis", "orders in the numerator")))));

    @BeforeEach
    void findingsAnswer() { when(api.findings(anyMap())).thenReturn(FINDINGS); }

    @Test
    void salesPageShowsTheForecastWithItsEvidenceBehindATab() throws Exception {
        when(api.salesHistory()).thenReturn(ok("history"));
        when(api.salesForecast(anyInt())).thenReturn(ok("forecast"));
        mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("<title>Mosaic - Sales</title>"),
                containsString("sales-chart"), containsString("Forecast for 2018-09"),
                matchesRegex("(?s).*<a href=\"/\" aria-current=\"page\">.*"),
                containsString(">Evidence</button>"),
                containsString(">Suggested opportunity</button>"), containsString("data-ask=\"/api/overview/advice/ask\""),
                containsString(">Possible caveats</button>"),
                containsString("data-url=\"/api/overview/caveats\""),
                containsString("href=\"/findings/sales:late_rate_rising\""),
                matchesRegex("(?s).*<div id=\"evidence-panel\" class=\"mt-3\" hidden>.*scored better than the model.*not counted as sales.*"))));
    }

    @Test
    void salesPageStillRendersWhenTheApiIsDown() throws Exception {
        ApiResult down = new ApiResult(DOWN, 502);
        when(api.salesHistory()).thenReturn(down);
        when(api.salesForecast(anyInt())).thenReturn(down);
        mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(containsString(DOWN)));
    }

    @Test
    void untrainedForecastIsReportedAndHistoryStillShows() throws Exception {
        ApiResult untrained = new ApiResult("No trained sales_forecast model found.", 503);
        when(api.salesHistory()).thenReturn(ok("history"));
        when(api.salesForecast(anyInt())).thenReturn(untrained);
        mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("No trained sales_forecast model found."), containsString("sales-chart"))));
    }

    @Test
    void eachTrendPageShowsItsChartButtonsAndEvidence() throws Exception {
        for (Measure m : Measure.values()) {
            when(api.trend(m)).thenReturn(ok("trend-" + m.path() + "-trend"));
            mvc.perform(get("/" + m.path())).andExpect(status().isOk()).andExpect(content().string(allOf(
                    containsString("<title>Mosaic - " + m.title() + "</title>"),
                    containsString(m.question()),
                    containsString("id=\"trend-chart\""),
                    containsString(">Suggested opportunity</button>"),
                    containsString("data-url=\"/api/trend/" + m.path() + "/advice\""),
                    containsString("data-url=\"/api/trend/" + m.path() + "/caveats\""),
                    matchesRegex("(?s).*<a href=\"/" + m.path() + "\" aria-current=\"page\">.*"))));
        }
    }

    @Test
    void deliveryPageStatesTheChangeWithItsFigures() throws Exception {
        when(api.trend(Measure.DELIVERY)).thenReturn(ok("trend-delivery-trend"));
        mvc.perform(get("/delivery")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("3.6%"), containsString("10.1%"), containsString("−6.5 pp"),
                containsString("That is an improvement."),
                containsString("2018-06, 2018-07, 2018-08"),
                containsString("The most recent months can still have orders on their way"))));
    }

    @Test
    @SuppressWarnings("unchecked")
    void aMeasureThatDidNotImproveSaysSo() throws Exception {
        Map<String, Object> trend = fixture("trend-reviews-trend");
        ((Map<String, Object>) trend.get("trend")).put("improving", false);
        when(api.trend(Measure.REVIEWS)).thenReturn(new ApiResult(trend));
        mvc.perform(get("/reviews")).andExpect(status().isOk())
                .andExpect(content().string(containsString("That is not an improvement")));
    }

    @Test
    void trendPageStillRendersWhenTheApiIsDown() throws Exception {
        when(api.trend(Measure.SELLERS)).thenReturn(new ApiResult(DOWN, 502));
        mvc.perform(get("/sellers")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString(DOWN), not(containsString("trend-chart")))));
    }

    @Test
    void removedPagesAreGone() throws Exception {
        for (String path : List.of("/categories", "/risk", "/scenario"))
            mvc.perform(get(path)).andExpect(status().isNotFound());
    }

    @Test
    void helpListsBothAppsEndpointsAndTheDatasetColumns() throws Exception {
        Map<String, Object> openapi = Map.of("paths", Map.of(
                "/api/health", Map.of("get", Map.of("summary", "Health")),
                "/api/scenarios/sales-impact", Map.of("post", Map.of("summary", "Sales Impact", "requestBody", Map.of())),
                "/api/sales/forecast", Map.of("get", Map.of("summary", "Sales Forecast", "parameters", List.of(Map.of("name", "horizon"))))));
        when(api.openApi()).thenReturn(new ApiResult(openapi));
        when(api.datasets()).thenReturn(new ApiResult(Map.of("files", List.of(Map.of("file", "olist_orders_dataset.csv", "columns", List.of("order_id", "order_status"))))));
        when(api.health()).thenReturn(new ApiResult(DOWN, 502));
        mvc.perform(get("/help")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("<code>/help</code>"), containsString("<code>/api/overview/advice</code>"),
                containsString("<code>/api/scenarios/sales-impact</code>"), containsString("JSON body"), containsString(">horizon<"),
                containsString("olist_orders_dataset.csv"), containsString(">order_status<"),
                containsString(DOWN))));
    }
}
