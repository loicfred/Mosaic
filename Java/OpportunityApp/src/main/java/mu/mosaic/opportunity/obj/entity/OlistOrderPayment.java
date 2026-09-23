package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.math.BigDecimal;

/** One row of Olist's olist_order_payments_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_order_payments_dataset")
public class OlistOrderPayment extends DatabaseObject.ID_RECORD_OBJ<Long, OlistOrderPayment> {
    @Column(name = "order_id")
    private String orderId;
    @Column(name = "payment_sequential")
    private Integer paymentSequential;
    @Column(name = "payment_type")
    private String paymentType;
    @Column(name = "payment_installments")
    private Integer paymentInstallments;
    @Column(name = "payment_value")
    private BigDecimal paymentValue;

    protected OlistOrderPayment() {}
}
