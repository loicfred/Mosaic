package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.obj.ApiResult;
import mu.mosaic.opportunity.service.ai.PanelChat;
import mu.mosaic.opportunity.service.ai.PanelChat.Turn;
import mu.mosaic.opportunity.service.ai.Panels;
import mu.mosaic.opportunity.service.ai.Panels.Panel;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Follow-up questions typed under a suggestion or caveats answer, on the overview and the trend pages. The panel's
 * figures are fetched again here, so the browser can never hand the model figures of its own.
 */
@RestController
public class PanelChatController {
    private final Panels panels;
    private final PanelChat chat;

    public PanelChatController(Panels panels, PanelChat chat) {
        this.panels = panels;
        this.chat = chat;
    }

    /** What the page posts: the new question and the panel's earlier messages, oldest first. */
    public record Question(String question, List<Turn> history) {
        private static final int MAX_QUESTION = 500, MAX_TURNS = 8, MAX_TURN_TEXT = 2000;

        public List<Turn> history() { return history == null ? List.of() : history; }

        /** Why the question cannot be sent to the model, or null when it can. */
        String problem() {
            if (question == null || question.isBlank()) return "Type a question first.";
            if (question.length() > MAX_QUESTION) return "Keep the question under " + MAX_QUESTION + " characters.";
            if (history().size() > MAX_TURNS) return "This conversation is long; reload the page to start a new one.";
            for (Turn t : history())
                if (t == null || t.text() == null || t.text().length() > MAX_TURN_TEXT || !("user".equals(t.role()) || "assistant".equals(t.role())))
                    return "The conversation could not be read; reload the page to start a new one.";
            return null;
        }
    }

    @PostMapping("/api/overview/{panel}/ask")
    public ResponseEntity<?> overview(@PathVariable String panel, @RequestBody Question q) { return answer(panels.find("sales", panel), q); }

    @PostMapping("/api/trend/{measure}/{panel}/ask")
    public ResponseEntity<?> trend(@PathVariable String measure, @PathVariable String panel, @RequestBody Question q) {
        return answer(panels.find(measure, panel), q);
    }

    private ResponseEntity<?> answer(Optional<Panel<?>> panel, Question q) {
        if (panel.isEmpty()) return ResponseEntity.status(404).body(Map.of("error", "There is no such panel."));
        String problem = q == null ? "Type a question first." : q.problem();
        if (problem != null) return ResponseEntity.badRequest().body(Map.of("error", problem));
        ApiResult figures = panel.get().figures();
        if (figures.failed()) return ResponseEntity.status(502).body(Map.of("error", figures.error()));
        PanelChat.Answer answer = chat.ask(panel.get().evidence(figures), q.history(), q.question());
        Map<String, Object> body = answer.narrative().toJson();
        body.put("charts", answer.charts());
        return ResponseEntity.ok(body);
    }
}
