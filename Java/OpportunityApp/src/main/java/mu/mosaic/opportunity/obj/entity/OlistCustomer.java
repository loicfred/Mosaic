package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

/** One row of Olist's olist_customers_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_customers_dataset")
public class OlistCustomer extends DatabaseObject.ID_RECORD_OBJ<Long, OlistCustomer> {
    @Column(name = "customer_id")
    private String customerId;
    @Column(name = "customer_unique_id")
    private String customerUniqueId;
    @Column(name = "customer_zip_code_prefix")
    private String zipCodePrefix;
    @Column(name = "customer_city")
    private String city;
    @Column(name = "customer_state")
    private String state;

    protected OlistCustomer() {}
}
