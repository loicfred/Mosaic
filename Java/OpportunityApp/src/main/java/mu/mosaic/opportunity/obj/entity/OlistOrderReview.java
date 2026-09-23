package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.time.LocalDateTime;

/** One row of Olist's olist_order_reviews_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_order_reviews_dataset")
public class OlistOrderReview extends DatabaseObject.ID_RECORD_OBJ<Long, OlistOrderReview> {
    @Column(name = "review_id")
    private String reviewId;
    @Column(name = "order_id")
    private String orderId;
    @Column(name = "review_score")
    private Integer reviewScore;
    @Column(name = "review_comment_title")
    private String commentTitle;
    @Column(name = "review_comment_message")
    private String commentMessage;
    @Column(name = "review_creation_date")
    private LocalDateTime creationDate;
    @Column(name = "review_answer_timestamp")
    private LocalDateTime answerTimestamp;

    protected OlistOrderReview() {}
}
