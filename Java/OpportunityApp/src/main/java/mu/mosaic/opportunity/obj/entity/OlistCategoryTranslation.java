package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

/** One row of Olist's product_category_name_translation.csv, columns named as in the file. */
@Entity
@Table(name = "product_category_name_translation")
public class OlistCategoryTranslation extends DatabaseObject.ID_RECORD_OBJ<Long, OlistCategoryTranslation> {
    @Column(name = "product_category_name")
    private String categoryName;
    @Column(name = "product_category_name_english")
    private String categoryNameEnglish;

    protected OlistCategoryTranslation() {}
}
