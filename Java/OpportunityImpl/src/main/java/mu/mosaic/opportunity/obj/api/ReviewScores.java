package mu.mosaic.opportunity.obj.api;

import java.util.List;

/** How many orders got each star rating, by their latest review. */
public record ReviewScores(List<Score> scores) {

    public record Score(String score, Double orders, Double share) {}
}
