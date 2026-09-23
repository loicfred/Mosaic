package mu.mosaic.opportunity.service;

import mu.mosaic.opportunity.obj.ApiResult;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/** Against a real local HTTP server, so status codes, bodies and refused connections are the genuine article. */
class MosaicApiTest {
    private HttpServer server;
    private final AtomicReference<String> lastRequest = new AtomicReference<>(), upgrade = new AtomicReference<>();

    private MosaicApi apiAnswering(int status, String body) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", ex -> {
            String sent = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            lastRequest.set(ex.getRequestMethod() + " " + ex.getRequestURI() + (sent.isEmpty() ? "" : " " + sent));
            upgrade.set(ex.getRequestHeaders().getFirst("Upgrade"));
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().add("Content-Type", "application/json");
            ex.sendResponseHeaders(status, bytes.length);
            ex.getResponseBody().write(bytes);
            ex.close();
        });
        server.start();
        return new MosaicApi("http://127.0.0.1:" + server.getAddress().getPort(), 5);
    }

    @AfterEach
    void stop() { if (server != null) server.stop(0); }

    @Test
    void successReturnsTheJsonBody() throws IOException {
        ApiResult r = apiAnswering(200, "{\"unit\": \"BRL\", \"months\": [{\"month\": \"2018-08\", \"sales\": 848860.1}]}").salesHistory();
        assertNull(r.error());
        assertEquals("BRL", r.data().get("unit"));
        assertEquals("GET /api/sales/history", lastRequest.get());
    }

    @Test
    void untrainedModelShowsTheApiInstruction() throws IOException {
        ApiResult r = apiAnswering(503, "{\"detail\": \"No trained 'late_delivery' model found. Run: python -m app.models.train_risk\"}").openOrders(25);
        assertNull(r.data());
        assertEquals("No trained 'late_delivery' model found. Run: python -m app.models.train_risk", r.error());
    }

    @Test
    void staleModelWithoutDetailStillExplainsWhatToDo() throws IOException {
        assertTrue(apiAnswering(409, "{}").unreviewed(10).error().contains("Retrain"));
    }

    @Test
    void validationErrorSaysTheRequestWasRejected() throws IOException {
        ApiResult r = apiAnswering(422, "{\"detail\": [{\"msg\": \"Input should be less than or equal to 100\"}]}").salesImpact(3, 500);
        assertEquals("The analytics API rejected the request: Input should be less than or equal to 100.", r.error());
    }

    @Test
    void categoryNameIsEncodedIntoThePath() throws IOException {
        apiAnswering(404, "{\"detail\": \"Unknown category\"}").category("a b/c");
        assertEquals("GET /api/sales/categories/a%20b%2Fc", lastRequest.get());
    }

    @Test
    void scenarioPostsItsSettings() throws IOException {
        apiAnswering(200, "{}").salesImpact(3, 20);
        String req = lastRequest.get();
        assertTrue(req.startsWith("POST /api/scenarios/sales-impact "));
        assertTrue(req.contains("\"horizon\":3") && req.contains("\"sales_change_pct\":20.0") && !req.contains("explain"), req);
        assertNull(upgrade.get(), "an h2c upgrade makes uvicorn drop the body");
    }

    @Test
    void apiThatIsNotRunningGivesAStartInstruction() throws IOException {
        int port;
        try (ServerSocket s = new ServerSocket(0)) { port = s.getLocalPort(); }
        ApiResult r = new MosaicApi("http://127.0.0.1:" + port, 5).health();
        assertNull(r.data());
        assertTrue(r.error().contains("python -m app.main"), r.error());
    }
}
