package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

/** One row of Olist's olist_products_dataset.csv, columns named as in the file, "lenght" typos included. */
@Entity
@Table(name = "olist_products_dataset")
public class OlistProduct extends DatabaseObject.ID_RECORD_OBJ<Long, OlistProduct> {
    @Column(name = "product_id")
    private String productId;
    @Column(name = "product_category_name")
    private String categoryName;
    @Column(name = "product_name_lenght")
    private Integer nameLength;
    @Column(name = "product_description_lenght")
    private Integer descriptionLength;
    @Column(name = "product_photos_qty")
    private Integer photosQty;
    @Column(name = "product_weight_g")
    private Integer weightG;
    @Column(name = "product_length_cm")
    private Integer lengthCm;
    @Column(name = "product_height_cm")
    private Integer heightCm;
    @Column(name = "product_width_cm")
    private Integer widthCm;

    protected OlistProduct() {}
}
