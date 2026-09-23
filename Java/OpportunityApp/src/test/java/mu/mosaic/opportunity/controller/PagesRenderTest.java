package mu.mosaic.opportunity.controller;

import mu.mosaic.opportunity.Fixtures;
import mu.mosaic.opportunity.service.ai.LocalAi;
import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.MosaicApi;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

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

    private static Map<String, Object> fixture(String name) { return Fixtures.load(name); }

    private static ApiResult ok(String name) { return ApiResult.ok(fixture(name)); }

    @Test
    void overviewShowsTheHiddenProblemAndTheHonestForecastComparison() throws Exception {
        when(api.salesHistory()).thenReturn(ok("history"));
        when(api.salesForecast(anyInt())).thenReturn(ok("forecast"));
        when(api.deliverySummary()).thenReturn(ok("delivery-summary"));
        when(api.reviewSummary()).thenReturn(ok("review-summary"));
        when(api.categories(isNull())).thenReturn(ok("categories"));
        when(api.categories(eq(CategoryController.FLAG_BEHIND))).thenReturn(ok("categories-behind"));
        mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("−12.7%"),
                containsString("18 of 74"),
                containsString("BRL 848,860"),
                containsString("scored better than the model"),
                containsString("not counted as sales"))));
    }

    @Test
    void overviewStillRendersWhenTheApiIsDown() throws Exception {
        ApiResult down = ApiResult.failed(DOWN);
        when(api.salesHistory()).thenReturn(down);
        when(api.salesForecast(anyInt())).thenReturn(down);
        when(api.deliverySummary()).thenReturn(down);
        when(api.reviewSummary()).thenReturn(down);
        when(api.categories(any())).thenReturn(down);
        mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(containsString(DOWN)));
    }

    @Test
    void untrainedForecastIsReportedAndHistoryStillShows() throws Exception {
        when(api.salesHistory()).thenReturn(ok("history"));
        when(api.salesForecast(anyInt())).thenReturn(ApiResult.failed("No trained sales_forecast model found."));
        when(api.deliverySummary()).thenReturn(ok("delivery-summary"));
        when(api.reviewSummary()).thenReturn(ok("review-summary"));
        when(api.categories(any())).thenReturn(ok("categories"));
        mvc.perform(get("/")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("No trained sales_forecast model found."), containsString("sales-chart"))));
    }

    @Test
    void categoryListWithoutAFilterShowsAll() throws Exception {
        when(api.categories(isNull())).thenReturn(ok("categories"));
        mvc.perform(get("/categories")).andExpect(status().isOk()).andExpect(content().string(containsString("Health beauty")));
    }

    @Test
    void categoryListFiltersOnlyByKnownFlags() throws Exception {
        when(api.categories(isNull())).thenReturn(ok("categories"));
        mvc.perform(get("/categories").param("flag", "drop table")).andExpect(status().isOk())
                .andExpect(content().string(allOf(containsString("Health beauty"), containsString("/categories/health_beauty"))));
    }

    @Test
    void categoryEvidenceIsReadable() throws Exception {
        when(api.category("sports_leisure")).thenReturn(ok("category"));
        mvc.perform(get("/categories/sports_leisure")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("Flagged: this category trails the business"),
                containsString("−15.5 pp"),
                containsString("Flag when the gap is −10.0 pp or lower"),
                containsString("Not flagged: the latest month is within its usual swing."))));
    }

    @Test
    void pagesShareTheShellWithSidebarAndBreadcrumbs() throws Exception {
        when(api.category("sports_leisure")).thenReturn(ok("category"));
        mvc.perform(get("/categories/sports_leisure")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("<title>Mosaic - Sports leisure</title>"),
                containsString("id=\"sidebar\""),
                matchesRegex("(?s).*<a href=\"/categories\" aria-current=\"page\">.*"),
                matchesRegex("(?s).*aria-label=\"Breadcrumb\".*<a href=\"/\"[^>]*>Overview</a>.*<a href=\"/categories\"[^>]*>Category health</a>\\s*</li>\\s*<li[^>]*aria-current=\"page\">\\s*<span>Sports leisure</span>.*"),
                containsString("Every number comes from the Mosaic analytics API"))));
    }

    @Test
    @SuppressWarnings("unchecked")
    void shortHistoryCategoryExplainsWhatWasNotChecked() throws Exception {
        Map<String, Object> c = fixture("category");
        ((Map<String, Object>) c.get("evidence")).put("latest_month_anomaly", Map.of("reason", "insufficient_history", "months_available", 4));
        c.put("forecast", null);
        c.put("forecast_reason", "insufficient_history");
        when(api.category("new_thing")).thenReturn(ApiResult.ok(c));
        mvc.perform(get("/categories/new_thing")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("only 4 earlier months"), containsString("does not have enough monthly history"))));
    }

    @Test
    void riskPageShowsScoresNotChances() throws Exception {
        when(api.deliverySummary()).thenReturn(ok("delivery-summary"));
        when(api.openOrders(anyInt())).thenReturn(ok("open-orders"));
        when(api.sellers(anyInt(), anyInt())).thenReturn(ok("sellers"));
        when(api.reviewSummary()).thenReturn(ok("review-summary"));
        when(api.unreviewed(anyInt())).thenReturn(ok("unreviewed"));
        mvc.perform(get("/risk")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("62.4%"), containsString("not a percentage chance"), containsString("no recent orders"), containsString(">92<"))));
    }

    @Test
    void riskPageHandlesUntrainedModels() throws Exception {
        Map<String, Object> summary = fixture("delivery-summary");
        summary.put("model", null);
        when(api.deliverySummary()).thenReturn(ApiResult.ok(summary));
        when(api.openOrders(anyInt())).thenReturn(ApiResult.failed("No trained late_delivery model found."));
        when(api.sellers(anyInt(), anyInt())).thenReturn(ok("sellers"));
        when(api.reviewSummary()).thenReturn(ok("review-summary"));
        when(api.unreviewed(anyInt())).thenReturn(ApiResult.failed("No trained low_review model found."));
        mvc.perform(get("/risk")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("Not trained yet"), containsString("No trained late_delivery model found."), containsString("No trained low_review model found."))));
    }

    @Test
    void firstScenarioVisitAsksForTheExplanation() throws Exception {
        when(api.salesImpact(3, 20.0)).thenReturn(ok("scenario"));
        when(ai.status()).thenReturn(new LocalAi.Status(false, false, null, null));
        mvc.perform(get("/scenario")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("+1,253 on the recent average"),
                containsString("association fitted on 20 months"),
                containsString("41 of 1,810"),
                containsString("exposure, not money lost"),
                containsString("A 20% change in sales over the next 3 months would mean about 7,520 orders a month"),
                containsString("Written from a fixed template."),
                not(containsString("data-summary-url")),
                containsString("Local AI: switched off."))));
    }

    @Test
    void theAiSummaryIsAskedForAfterThePageOnlyWhenWantedAndReachable() throws Exception {
        when(api.salesImpact(3, 20.0)).thenReturn(ok("scenario"));
        when(ai.status()).thenReturn(new LocalAi.Status(true, true, "fake-model", true));
        mvc.perform(get("/scenario")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("data-summary-url=\"/api/scenario/summary?change=20.0&amp;horizon=3\""), containsString("Local AI: connected (fake-model)"))));
        mvc.perform(get("/scenario").param("run", "1")).andExpect(status().isOk()).andExpect(content().string(not(containsString("data-summary-url"))));
    }

    @Test
    void helpListsBothAppsEndpointsAndTheDatasetColumns() throws Exception {
        Map<String, Object> openapi = Map.of("paths", Map.of(
                "/api/health", Map.of("get", Map.of("summary", "Health")),
                "/api/scenarios/sales-impact", Map.of("post", Map.of("summary", "Sales Impact", "requestBody", Map.of())),
                "/api/sales/forecast", Map.of("get", Map.of("summary", "Sales Forecast", "parameters", List.of(Map.of("name", "horizon"))))));
        when(api.openApi()).thenReturn(ApiResult.ok(openapi));
        when(api.datasets()).thenReturn(ApiResult.ok(Map.of("files", List.of(Map.of("file", "olist_orders_dataset.csv", "columns", List.of("order_id", "order_status"))))));
        when(api.health()).thenReturn(ApiResult.failed(DOWN));
        mvc.perform(get("/help")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("<code>/help</code>"), containsString("<code>/api/assistant</code>"),
                containsString("<code>/api/scenarios/sales-impact</code>"), containsString("JSON body"), containsString(">horizon<"),
                containsString("olist_orders_dataset.csv"), containsString(">order_status<"),
                containsString(DOWN))));
    }

    @Test
    void everyPageCarriesTheAssistantWithItsContext() throws Exception {
        when(api.category("sports_leisure")).thenReturn(ok("category"));
        mvc.perform(get("/categories/sports_leisure")).andExpect(status().isOk()).andExpect(content().string(allOf(
                containsString("id=\"assistant\""), containsString("data-context=\"category sports_leisure\""), containsString("/js/assistant.js"))));
    }

    @Test
    void submittedScenarioWithoutTheCheckboxSkipsTheExplanation() throws Exception {
        Map<String, Object> none = fixture("scenario");
        none.put("consequences", null);
        none.put("reason", "no_baseline_activity");
        when(api.salesImpact(6, -50.0)).thenReturn(ApiResult.ok(none));
        mvc.perform(get("/scenario").param("run", "1").param("change", "-50").param("horizon", "6")).andExpect(status().isOk())
                .andExpect(content().string(containsString("there were no sales in the recent months")));
    }
}
