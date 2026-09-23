package mu.mosaic.opportunity;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

/** The real beans, nothing mocked: catches wiring that the page tests' mocked API would hide. */
@SpringBootTest(properties = "mosaic.python.autostart=false")
class OpportunityAppTest {
    @Test
    void contextLoads() {}
}
