package mu.mosaic.opportunity.service.ai;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NumberCheckTest {

    @Test
    void figuresMayBeRoundedGroupedOrShownAsPercentages() {
        NumberCheck check = new NumberCheck().allow("monthly_sales 863389.9666, late_rate 0.03612320593452669");
        assertTrue(check.unsupported("About BRL 863,390 a month, 3.61% late; 863390 or 3.6%.").isEmpty());
    }

    @Test
    void anInventedFigureIsCaught() {
        assertEquals(List.of("9,999"), new NumberCheck().allow("orders 7519.6").unsupported("Orders could reach 7,520, maybe 9,999."));
    }

    @Test
    void smallWholeNumbersAreProseButSmallDecimalsAreClaims() {
        assertEquals(List.of("2.5"), new NumberCheck().unsupported("Over the next 3 months, the top 5 sellers, up 2.5 points."));
    }

    @Test
    void smallMoneyAndPercentClaimsStillNeedEvidence() {
        NumberCheck nothing = new NumberCheck();
        assertEquals(List.of("4"), nothing.unsupported("a drop of about BRL 4"));
        assertEquals(List.of("4"), nothing.unsupported("down 4%"));
        assertEquals(List.of("4"), nothing.unsupported("a loss of 4 BRL"));
        assertEquals(List.of("4"), nothing.unsupported("up 4 percentage points"));
        assertTrue(nothing.unsupported("over 3 months, the top 5 sellers").isEmpty());
        assertTrue(new NumberCheck().allow("a change of BRL 4").unsupported("about BRL 4").isEmpty());
    }

    @Test
    void aCommaEndingASentenceIsNotPartOfTheNumber() {
        assertTrue(new NumberCheck().allow("7,520 orders").unsupported("About 7,520, which is more.").isEmpty());
    }

    @Test
    void negativeFiguresMayBeRepeatedWithoutTheirSign() {
        assertTrue(new NumberCheck().allow("−28.2% against −12.7%").unsupported("Sales fell 28.2% while the business fell 12.7%.").isEmpty());
    }

    @Test
    void textWithoutNumbersPasses() {
        assertTrue(new NumberCheck().unsupported("Watch late deliveries.").isEmpty());
        assertTrue(new NumberCheck().unsupported(null).isEmpty());
    }

    @Test
    void aFigureInThousandsOrMillionsMustRoundFromTheEvidence() {
        NumberCheck check = new NumberCheck().allow("sales lost 461,022 BRL; sales 2,331,152 BRL");
        assertTrue(check.unsupported("about BRL 461 k less sales").isEmpty());
        assertTrue(check.unsupported("some 461 thousand reais").isEmpty());
        assertTrue(check.unsupported("about 2.3 million").isEmpty());
        assertEquals(List.of("470"), check.unsupported("about BRL 470 k"));  // not a rounding of 461,022
        assertEquals(List.of("461"), check.unsupported("461 categories"));    // no scale word: must be given as such
        assertEquals(List.of("90"), check.unsupported("together over BRL 90 k"));
    }

    @Test
    void thousandsGroupedWithSpecialSpacesAreOneNumber() {
        NumberCheck check = new NumberCheck().allow("credit card BRL 2,032,405");
        assertTrue(check.unsupported("card paid BRL 2 032 405").isEmpty());
        assertTrue(check.unsupported("card paid BRL 2 032 405").isEmpty());
        assertEquals(List.of("2,032,406"), check.unsupported("BRL 2 032 406"));
        assertEquals(List.of("2018", "405"), check.unsupported("in 2018 405 orders")); // a plain space keeps two numbers apart
    }
}
