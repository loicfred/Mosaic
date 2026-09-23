package mu.mosaic.opportunity.controller.api;

import mu.mosaic.opportunity.service.ai.Assistant;
import mu.mosaic.opportunity.service.ai.LocalAi;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "mosaic.python.autostart=false")
@AutoConfigureMockMvc
@WithMockUser // every page sits behind the sign-in
class AssistantControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean Assistant assistant;
    @MockitoBean LocalAi ai;

    @Test
    void aQuestionIsAnsweredForThatSession() throws Exception {
        MockHttpSession session = new MockHttpSession();
        when(assistant.ask(eq(session.getId()), eq("Why?"), eq("category sports_leisure"))).thenReturn(new Assistant.Reply("It trails the business.", true, "fake-model", null));
        mvc.perform(post("/api/assistant").session(session).contentType(MediaType.APPLICATION_JSON).content("{\"message\":\"  Why?  \",\"context\":\"category sports_leisure\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.text").value("It trails the business.")).andExpect(jsonPath("$.verified").value(true));
    }

    @Test
    void anEmptyOrOverlongQuestionIsRefused() throws Exception {
        mvc.perform(post("/api/assistant").contentType(MediaType.APPLICATION_JSON).content("{\"message\":\"   \"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/api/assistant").contentType(MediaType.APPLICATION_JSON).content("{\"message\":\"" + "a".repeat(AssistantController.MAX_MESSAGE + 1) + "\"}")).andExpect(status().isBadRequest());
        verify(assistant, never()).ask(any(), any(), any());
    }

    @Test
    void startingOverForgetsThatSession() throws Exception {
        MockHttpSession session = new MockHttpSession();
        mvc.perform(delete("/api/assistant").session(session)).andExpect(status().isNoContent());
        verify(assistant).forget(session.getId());
    }

    @Test
    void statusReportsTheModel() throws Exception {
        when(ai.status()).thenReturn(new LocalAi.Status(true, false, "google/gemma-4-e4b", null));
        mvc.perform(get("/api/assistant/status")).andExpect(jsonPath("$.reachable").value(false)).andExpect(jsonPath("$.model").value("google/gemma-4-e4b"));
    }
}
