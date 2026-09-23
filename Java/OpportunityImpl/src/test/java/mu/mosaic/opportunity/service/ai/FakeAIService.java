package mu.mosaic.opportunity.service.ai;

import org.solarframework.ai.IAIService;
import org.solarframework.ai.dto.AIOptions;
import org.solarframework.ai.dto.TokenUsage;
import org.solarframework.ai.dto.ToolCall;
import org.solarframework.ai.dto.TurnResult;
import org.solarframework.ai.obj.ChatMessage;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.function.Consumer;
import java.util.function.Predicate;

/**
 * A scripted model, as SolarFramework tests its own conversation loop: the loop, tool approval and transcript
 * are provider-neutral, so everything this site adds on top of them can be tested with no model running.
 */
class FakeAIService implements IAIService {
    final Deque<TurnResult> scripted = new ArrayDeque<>();
    final List<List<ChatMessage>> seenHistories = new ArrayList<>();
    final List<ToolCall> approved = new ArrayList<>(), denied = new ArrayList<>();
    boolean available = true;
    RuntimeException failure;
    int turns;

    FakeAIService willAnswer(String text) {
        scripted.add(TurnResult.answer(text, new TokenUsage(1, 1)));
        return this;
    }

    /** The model asks for a tool; if the approver allows it, the call comes back with {@code result}. */
    FakeAIService willCallTool(String name, String result) {
        scripted.add(new TurnResult(null, List.of(new ToolCall("call-" + scripted.size(), name, "{}", result, false)), new TokenUsage(1, 1)));
        return this;
    }

    @Override public TurnResult runTurn(List<ChatMessage> messages, AIOptions options, List<Object> tools, Predicate<ToolCall> approver) {
        turns++;
        seenHistories.add(List.copyOf(messages));
        if (failure != null) throw failure;
        TurnResult next = scripted.isEmpty() ? TurnResult.answer("done", new TokenUsage(1, 1)) : scripted.poll();
        if (next.isAnswer()) return next;
        List<ToolCall> outcomes = new ArrayList<>();
        for (ToolCall c : next.toolCalls()) {
            ToolCall asked = new ToolCall(c.id(), c.name(), c.argumentsJson());
            if (approver == null || approver.test(asked)) { approved.add(asked); outcomes.add(asked.withResult(c.result())); }
            else { denied.add(asked); outcomes.add(asked.asDenied()); }
        }
        return new TurnResult(next.text(), outcomes, next.usage());
    }

    @Override public String streamTurn(List<ChatMessage> messages, AIOptions options, Consumer<String> onChunk) { return null; }
    @Override public <T> T structuredTurn(List<ChatMessage> messages, AIOptions options, Class<T> type) { return null; }
    @Override public String getName() { return DEFAULT; }
    @Override public void setName(String name) {}
    @Override public String getBaseUrl() { return "http://fake"; }
    @Override public void setBaseUrl(String baseUrl) {}
    @Override public String getApiKey() { return "N/A"; }
    @Override public void setApiKey(String apiKey) {}
    @Override public String getModel() { return "fake-model"; }
    @Override public void setModel(String model) {}
    @Override public int getTimeoutSeconds() { return 5; }
    @Override public void setTimeoutSeconds(int timeoutSeconds) {}
    @Override public int getRequestsPerMinute() { return 0; }
    @Override public void setRequestsPerMinute(int requestsPerMinute) {}
    @Override public boolean isAvailable() { return available; }
    @Override public List<String> getAvailableModels() { return List.of("fake-model"); }
    @Override public String getModelState() { return "loaded"; }
    @Override public List<String> getModelCapabilities() { return List.of(TOOL_USE); }
    @Override public int getMaxContextLength() { return 8192; }
    @Override public int getLoadedContextLength() { return 8192; }
    @Override public String getQuantization() { return null; }
    @Override public String getPublisher() { return null; }
    @Override public void refreshModelDetails() {}
    @Override public boolean loadModel(Integer contextLength, Integer ttlSeconds) { return true; }
    @Override public boolean unloadModel() { return true; }
    @Override public boolean ensureModelLoaded() { return true; }
}
