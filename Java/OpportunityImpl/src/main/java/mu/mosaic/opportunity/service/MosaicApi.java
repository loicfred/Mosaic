package mu.mosaic.opportunity.service;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.obj.Measure;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * The Python analytics API in Java/OpportunityApp/config/py/mosaic. It owns every number; this site only asks for them and formats them.
 * Every method answers an {@link ApiResult} rather than throwing, so a page can still render around a failed call.
 */
@Component
public class MosaicApi {
    private static final ParameterizedTypeReference<Map<String, Object>> JSON = new ParameterizedTypeReference<>() {};
    private final RestClient http;
    private final String baseUrl;

    public MosaicApi(@Value("${mosaic.api.base-url}") String baseUrl, @Value("${mosaic.api.timeout-seconds}") int timeoutSeconds) {
        // HTTP/1.1: the JDK client's default h2c upgrade makes uvicorn drop a POST body.
        var client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(3))
                .build();
        var factory = new JdkClientHttpRequestFactory(client);
        factory.setReadTimeout(Duration.ofSeconds(timeoutSeconds));
        this.http = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
        this.baseUrl = baseUrl;
    }

    public ApiResult health() {
        return get("/api/health");
    }

    /** The dataset files the API reads and their columns. */
    public ApiResult datasets() {
        return get("/api/datasets");
    }

    /** FastAPI's own description of every endpoint, so the Help page lists what actually exists. */
    public ApiResult openApi() {
        return get("/openapi.json");
    }

    public ApiResult salesHistory() {
        return get("/api/sales/history");
    }

    public ApiResult salesForecast(int horizon) {
        return call(client -> client.get().uri("/api/sales/forecast?horizon={h}", horizon));
    }

    public ApiResult salesOpportunities(int horizon) {
        return call(client -> client.get().uri("/api/sales/opportunities?horizon={h}", horizon));
    }

    public ApiResult salesCaveats() {
        return get("/api/sales/caveats");
    }

    /** A trend page's monthly figures and its change over the last 3 months. */
    public ApiResult trend(Measure measure) {
        return get("/api/" + measure.path() + "/trend");
    }

    public ApiResult trendOpportunities(Measure measure) {
        return get("/api/" + measure.path() + "/opportunities");
    }

    public ApiResult trendCaveats(Measure measure) {
        return get("/api/" + measure.path() + "/caveats");
    }

    /** Categories, largest recent sales first; flag is null, "underperforming_total" or "latest_month_anomaly". */
    public ApiResult categories(String flag, int limit) {
        return flag == null
                ? call(client -> client.get().uri("/api/sales/categories?limit={l}", limit))
                : call(client -> client.get().uri("/api/sales/categories?limit={l}&flag={f}", limit, flag));
    }

    /** One category's figures and flags; the code is passed as a path variable, so it is encoded, never spliced. */
    public ApiResult category(String code) {
        return call(client -> client.get().uri("/api/sales/categories/{c}", code));
    }

    public ApiResult deliverySummary() {
        return get("/api/risk/delivery/summary");
    }

    public ApiResult reviewSummary() {
        return get("/api/risk/reviews/summary");
    }

    public ApiResult deliverySellers(int minOrders, int limit) {
        return call(client -> client.get().uri("/api/risk/delivery/sellers?min_orders={m}&limit={l}", minOrders, limit));
    }

    public ApiResult openOrders(int limit) {
        return call(client -> client.get().uri("/api/risk/delivery/open-orders?limit={l}", limit));
    }

    public ApiResult unreviewedOrders(int limit) {
        return call(client -> client.get().uri("/api/risk/reviews/unreviewed?limit={l}", limit));
    }

    /** Brazilian events touching a "YYYY-MM" month, or all of them when month is null (external context). */
    public ApiResult events(String month) {
        return month == null ? get("/api/context/events") : call(client -> client.get().uri("/api/context/events?month={m}", month));
    }

    /** Brazil's monthly economic indicators from the Central Bank (external context). */
    public ApiResult economy(String month) {
        return month == null ? get("/api/context/economy") : call(client -> client.get().uri("/api/context/economy?month={m}", month));
    }

    /** How recent sales split; by is "category", "payment_type", "customer_state" or "seller_state". */
    public ApiResult salesMix(String by, int months) {
        return call(client -> client.get().uri("/api/sales/mix?by={b}&months={m}", by, months));
    }

    /** Average order value, freight share, cancellations, instalments and returning customers by month. */
    public ApiResult salesMetrics() {
        return get("/api/sales/metrics");
    }

    /** Orders and sales by "weekday" or "hour". */
    public ApiResult buyingTimes(String by) {
        return call(client -> client.get().uri("/api/breakdowns/buying-times?by={b}", by));
    }

    public ApiResult customerStates() {
        return get("/api/breakdowns/customer-states");
    }

    public ApiResult reviewScores() {
        return get("/api/breakdowns/review-scores");
    }

    public ApiResult salesImpact(int horizon, double salesChangePct) {
        return call(client -> client.post().uri("/api/scenarios/sales-impact")
                .body(Map.of("horizon", horizon, "sales_change_pct", salesChangePct)));
    }

    public ApiResult salesImpact(int horizon, double salesChangePct, String category) {
        if (category == null || category.isBlank()) return salesImpact(horizon, salesChangePct);
        return call(client -> client.post().uri("/api/scenarios/sales-impact")
                .body(Map.of("horizon", horizon, "sales_change_pct", salesChangePct, "category", category)));
    }

    public ApiResult explore(String section) {
        if (!List.of("quality", "payments", "freight", "cohorts", "models", "entities").contains(section))
            return new ApiResult("Unknown analysis page.", 404);
        return get("/api/explore/" + section);
    }

    public ApiResult exploreEntity(String kind, String name) {
        return call(client -> client.get().uri("/api/explore/entities/{kind}/{name}", kind, name));
    }

    public ApiResult findings(Map<String, String> parameters) { return queried("/api/findings", parameters); }

    public ApiResult findingRecords(String id, Map<String, String> parameters) {
        return queried("/api/findings/{id}/records", parameters, id);
    }

    public ApiResult selectedTrend(String measure, Map<String, String> parameters) {
        return queried("/api/findings/trend/{measure}", parameters, measure);
    }

    private ApiResult queried(String path, Map<String, String> parameters, Object... variables) {
        return call(client -> client.get().uri(builder -> {
            builder.path(path);
            parameters.forEach((key, value) -> builder.queryParam(key, "{q_" + key + "}"));
            Map<String, Object> values = new java.util.LinkedHashMap<>();
            parameters.forEach((key, value) -> values.put("q_" + key, value));
            if (variables.length > 0) values.put(path.contains("{id}") ? "id" : "measure", variables[0]);
            return builder.build(values);
        }));
    }

    public org.springframework.http.ResponseEntity<String> findingExport(String id, Map<String, String> parameters) {
        try {
            return http.get().uri(builder -> {
                builder.path("/api/findings/{id}/export");
                Map<String, Object> values = new java.util.LinkedHashMap<>();
                values.put("id", id);
                parameters.forEach((key, value) -> { builder.queryParam(key, "{q_" + key + "}"); values.put("q_" + key, value); });
                return builder.build(values);
            }).retrieve().toEntity(String.class);
        } catch (RestClientResponseException e) {
            return org.springframework.http.ResponseEntity.status(e.getStatusCode()).body(describeApiError(e));
        } catch (ResourceAccessException e) {
            return org.springframework.http.ResponseEntity.status(502).body("The analytics API is unavailable.");
        }
    }

    private ApiResult get(String uri) { return call(h -> h.get().uri(uri)); }

    private ApiResult call(Function<RestClient, RestClient.RequestHeadersSpec<?>> request) {
        try {
            return new ApiResult(request.apply(http).retrieve().body(JSON));
        } catch (RestClientResponseException e) {
            return new ApiResult(describeApiError(e), e.getStatusCode().value());
        } catch (ResourceAccessException e) {
            return new ApiResult("The analytics API is not answering at " + baseUrl + ". It may still be loading the dataset; refresh in a few seconds. If it stays down, start it from Java/OpportunityApp/config/py/mosaic with: python -m app.main", 502);
        }
    }

    private String describeApiError(RestClientResponseException error) {
        Object detail = responseDetail(error);
        String message = detail instanceof String text ? text : null;
        return switch (error.getStatusCode().value()) {
            case 503 -> message != null ? message : "This model has not been trained yet.";
            case 409 -> message != null ? message : "The data changed since this model was trained. Retrain it before using it.";
            case 404 -> message != null ? message : "The analytics API has no such record.";
            case 422 -> {
                String rejected = "The analytics API rejected the request: " + validationMessage(detail);
                yield rejected.endsWith(".") ? rejected : rejected + ".";
            }
            default -> "The analytics API answered HTTP " + error.getStatusCode().value()
                    + (message != null ? ": " + message : ".");
        };
    }

    private Object responseDetail(RestClientResponseException error) {
        try {
            Map<String, Object> body = error.getResponseBodyAs(JSON);
            return body == null ? null : body.get("detail");
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private String validationMessage(Object detail) {
        if (!(detail instanceof List<?> errors)) {
            return detail instanceof String message ? message : "invalid input";
        }
        // FastAPI returns {loc, msg, ...}; only the messages belong in the page notice.
        return errors.stream()
                .map(error -> error instanceof Map<?, ?> fields ? String.valueOf(fields.get("msg")) : String.valueOf(error))
                .collect(Collectors.joining("; "));
    }
}
