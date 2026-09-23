package mu.mosaic.opportunity.service.ai;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NumberCheckTest {

    @Test
    void figuresMayBeRoundedGroupedOrShownAsPercentages() {
        Set<String> allowed = NumberCheck.allowedFrom(Map.of("monthly_sales", 863389.9666, "late_rate", 0.03612320593452669));
        assertTrue(NumberCheck.unsupported("About BRL 863,390 a month, 3.61% late; 863390 or 3.6%.", allowed).isEmpty());
    }

    @Test
    void anInventedFigureIsCaught() {
        Set<String> allowed = NumberCheck.allowedFrom(Map.of("orders", 7519.6));
        assertEquals(List.of("9,999"), NumberCheck.unsupported("Orders could reach 7,520, maybe 9,999.", allowed));
    }

    @Test
    void smallWholeNumbersAreProseButSmallDecimalsAreClaims() {
        assertEquals(List.of("2.5"), NumberCheck.unsupported("Over the next 3 months, the top 5 sellers, up 2.5 points.", Set.of()));
    }

    @Test
    void numbersWrittenInsideEvidenceTextCount() {
        Set<String> allowed = NumberCheck.allowedFrom(Map.of("months", List.of("2018-06", "2018-08")));
        assertTrue(NumberCheck.unsupported("From June to August 2018.", allowed).isEmpty());
    }

    @Test
    void aCommaEndingASentenceIsNotPartOfTheNumber() {
        assertTrue(NumberCheck.unsupported("About 7,520, which is more.", NumberCheck.allowedFromText("7,520 orders")).isEmpty());
    }

    @Test
    void negativeFiguresMayBeRepeatedWithoutTheirSign() {
        assertTrue(NumberCheck.unsupported("Sales fell 28.2% while the business fell 12.7%.", NumberCheck.allowedFromText("−28.2% against −12.7%")).isEmpty());
    }

    @Test
    void textWithoutNumbersPasses() {
        assertTrue(NumberCheck.unsupported("Watch late deliveries.", Set.of()).isEmpty());
        assertTrue(NumberCheck.unsupported(null, Set.of()).isEmpty());
    }
}
