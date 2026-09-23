package mu.mosaic.opportunity.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class FormatterTest {
    private final Formatter fmt = new Formatter();

    @Test
    void missingValuesShowAsADashNeverAsZero() {
        assertEquals(Formatter.MISSING, fmt.brl(null));
        assertEquals(Formatter.MISSING, fmt.rate(null, 1));
        assertEquals(Formatter.MISSING, fmt.pct(null));
        assertEquals(Formatter.MISSING, fmt.score(null));
        assertEquals(Formatter.MISSING, fmt.date(null));
    }

    @Test
    void rateIsAFractionShownAsPercentage() {
        assertEquals("3.61%", fmt.rate(0.03612320593452669, 2));
        assertEquals("0.0%", fmt.rate(0, 1));
    }

    @Test
    void percentAndPointsAreAlreadyScaledAndSigned() {
        assertEquals("−28.2%", fmt.pct(-28.21126108855308));
        assertEquals("+20.0%", fmt.pct(20));
        assertEquals("+3.5 pp", fmt.pp(3.5368282805630145));
        assertEquals("−10.0 pp", fmt.pp(-10.0));
    }

    @Test
    void valueThatRoundsToZeroCarriesNoSign() {
        assertEquals("0.0%", fmt.pct(-0.04));
        assertEquals("0", fmt.change(0.3));
    }

    @Test
    void signedChangeIsGrouped() {
        assertEquals("+1,253", fmt.change(1253.2666666666673));
        assertEquals("−1,253", fmt.change(-1253.3));
    }

    @Test
    void currencyIsLabelledAndGrouped() {
        assertEquals("BRL 863,390 (≈ USD 253,938)", fmt.brl(863389.9666666667));
        assertEquals("−BRL 2,248 (≈ −USD 661)", fmt.brl(-2247.81));
        assertEquals("BRL 0 (≈ USD 0)", fmt.brl(-0.4));
    }

    @Test
    void scoreIsARankingOutOf100() {
        assertEquals("92", fmt.score(0.924769586445364));
    }

    @Test
    void categoryCodesReadAsWords() {
        assertEquals("Health beauty", fmt.label("health_beauty"));
    }
}
