package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

/** One row of Olist's olist_geolocation_dataset.csv, columns named as in the file. */
@Entity
@Table(name = "olist_geolocation_dataset")
public class OlistGeolocation extends DatabaseObject.ID_RECORD_OBJ<Long, OlistGeolocation> {
    @Column(name = "geolocation_zip_code_prefix")
    private String zipCodePrefix;
    @Column(name = "geolocation_lat")
    private Double lat;
    @Column(name = "geolocation_lng")
    private Double lng;
    @Column(name = "geolocation_city")
    private String city;
    @Column(name = "geolocation_state")
    private String state;

    protected OlistGeolocation() {}
}
