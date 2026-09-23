package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.time.LocalDateTime;

/** One row of Olist's olist_orders_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_orders_dataset")
public class OlistOrder extends DatabaseObject.ID_RECORD_OBJ<Long, OlistOrder> {
    @Column(name = "order_id")
    private String orderId;
    @Column(name = "customer_id")
    private String customerId;
    @Column(name = "order_status")
    private String orderStatus;
    @Column(name = "order_purchase_timestamp")
    private LocalDateTime purchaseTimestamp;
    @Column(name = "order_approved_at")
    private LocalDateTime approvedAt;
    @Column(name = "order_delivered_carrier_date")
    private LocalDateTime deliveredCarrierDate;
    @Column(name = "order_delivered_customer_date")
    private LocalDateTime deliveredCustomerDate;
    @Column(name = "order_estimated_delivery_date")
    private LocalDateTime estimatedDeliveryDate;

    protected OlistOrder() {}
}
