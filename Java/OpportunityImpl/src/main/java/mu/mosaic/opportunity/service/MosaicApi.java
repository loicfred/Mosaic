package mu.mosaic.opportunity.service;

import mu.mosaic.opportunity.obj.ApiResult;
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
 * The Python analytics API in AI/. It owns every number; this site only asks for them and formats them.
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

    public ApiResult categories(String flag) {
        if (flag == null) return get("/api/sales/categories?limit=100");
        return call(client -> client.get().uri("/api/sales/categories?limit=100&flag={f}", flag));
    }

    public ApiResult category(String name) {
        return call(client -> client.get().uri("/api/sales/categories/{c}", name));
    }

    public ApiResult deliverySummary() {
        return get("/api/risk/delivery/summary");
    }

    public ApiResult openOrders(int limit) {
        return call(client -> client.get().uri("/api/risk/delivery/open-orders?limit={l}", limit));
    }

    public ApiResult sellers(int minOrders, int limit) {
        return call(client -> client.get()
                .uri("/api/risk/delivery/sellers?min_orders={m}&limit={l}", minOrders, limit));
    }

    public ApiResult reviewSummary() {
        return get("/api/risk/reviews/summary");
    }

    public ApiResult unreviewed(int limit) {
        return call(client -> client.get().uri("/api/risk/reviews/unreviewed?limit={l}", limit));
    }

    public ApiResult salesImpact(int horizon, double salesChangePct) {
        return call(client -> client.post().uri("/api/scenarios/sales-impact")
                .body(Map.of("horizon", horizon, "sales_change_pct", salesChangePct)));
    }

    private ApiResult get(String uri) { return call(h -> h.get().uri(uri)); }

    private ApiResult call(Function<RestClient, RestClient.RequestHeadersSpec<?>> request) {
        try {
            return ApiResult.ok(request.apply(http).retrieve().body(JSON));
        } catch (RestClientResponseException e) {
            return ApiResult.failed(describeApiError(e));
        } catch (ResourceAccessException e) {
            return ApiResult.failed("The analytics API is not answering at " + baseUrl + ". It may still be loading the dataset; refresh in a few seconds. If it stays down, start it from AI/ with: python -m app.main");
        }
    }

    private static String describeApiError(RestClientResponseException error) {
        Object detail = responseDetail(error);
        String message = detail instanceof String text ? text : null;
        return switch (error.getStatusCode().value()) {
            case 503 -> message != null ? message : "This model has not been trained yet.";
            case 409 -> message != null ? message : "The data changed since this model was trained. Retrain it before using it.";
            case 404 -> message != null ? message : "The analytics API has no such record.";
            case 422 -> "The analytics API rejected the request: " + validationMessage(detail) + ".";
            default -> "The analytics API answered HTTP " + error.getStatusCode().value()
                    + (message != null ? ": " + message : ".");
        };
    }

    private static Object responseDetail(RestClientResponseException error) {
        try {
            Map<String, Object> body = error.getResponseBodyAs(JSON);
            return body == null ? null : body.get("detail");
        } catch (RuntimeException ignored) {
            return null;
        }
    }

    private static String validationMessage(Object detail) {
        if (!(detail instanceof List<?> errors)) {
            return detail instanceof String message ? message : "invalid input";
        }
        // FastAPI returns {loc, msg, ...}; only the messages belong in the page notice.
        return errors.stream()
                .map(error -> error instanceof Map<?, ?> fields ? String.valueOf(fields.get("msg")) : String.valueOf(error))
                .collect(Collectors.joining("; "));
    }
}
