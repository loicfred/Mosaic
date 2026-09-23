package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

/** One row of Olist's olist_sellers_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_sellers_dataset")
public class OlistSeller extends DatabaseObject.ID_RECORD_OBJ<Long, OlistSeller> {
    @Column(name = "seller_id")
    private String sellerId;
    @Column(name = "seller_zip_code_prefix")
    private String zipCodePrefix;
    @Column(name = "seller_city")
    private String city;
    @Column(name = "seller_state")
    private String state;

    protected OlistSeller() {}
}
