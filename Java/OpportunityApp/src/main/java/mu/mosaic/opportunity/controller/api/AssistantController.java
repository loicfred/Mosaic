package mu.mosaic.opportunity.controller.api;

import jakarta.servlet.http.HttpSession;
import mu.mosaic.opportunity.service.ai.Assistant;
import mu.mosaic.opportunity.service.ai.LocalAi;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** The chat box's endpoint: one conversation per browser session. */
@RestController
@RequestMapping("/api/assistant")
public class AssistantController {
    static final int MAX_MESSAGE = 1000;
    private final Assistant assistant;
    private final LocalAi ai;

    public AssistantController(Assistant assistant, LocalAi ai) {
        this.assistant = assistant;
        this.ai = ai;
    }

    /** @param context where the person is, e.g. "category sports_leisure", so "why is this flagged?" has a subject */
    public record Question(String message, String context) {}

    @PostMapping
    public ResponseEntity<?> ask(@RequestBody Question q, HttpSession session) {
        String message = q.message() == null ? "" : q.message().strip();
        if (message.isEmpty() || message.length() > MAX_MESSAGE) return ResponseEntity.badRequest().body(Map.of("error", "Write a question of up to " + MAX_MESSAGE + " characters."));
        return ResponseEntity.ok(assistant.ask(session.getId(), message, q.context()));
    }

    @DeleteMapping
    public ResponseEntity<Void> forget(HttpSession session) {
        assistant.forget(session.getId());
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/status")
    public LocalAi.Status status() { return ai.status(); }
}
