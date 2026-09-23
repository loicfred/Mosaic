package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** One row of Olist's olist_order_items_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_order_items_dataset")
public class OlistOrderItem extends DatabaseObject.ID_RECORD_OBJ<Long, OlistOrderItem> {
    @Column(name = "order_id")
    private String orderId;
    @Column(name = "order_item_id")
    private Integer orderItemId;
    @Column(name = "product_id")
    private String productId;
    @Column(name = "seller_id")
    private String sellerId;
    @Column(name = "shipping_limit_date")
    private LocalDateTime shippingLimitDate;
    @Column(name = "price")
    private BigDecimal price;
    @Column(name = "freight_value")
    private BigDecimal freightValue;

    protected OlistOrderItem() {}
}
