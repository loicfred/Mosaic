package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.time.LocalDateTime;

/** Spring Security's remember-me table, declared here so SolarFramework creates it, as SolarERP does. */
@Entity
@Table(name = "persistent_logins", comment = "Remembered browser sign-ins.")
public class PersistentLogins extends DatabaseObject<PersistentLogins> {
    @Id
    @Column(name = "series", nullable = false, length = 64, comment = "Identifier of the remembered sign-in series.")
    private String series;
    @Column(name = "username", nullable = false, length = 64, comment = "Email of the account remembered.")
    private String username;
    @Column(name = "token", nullable = false, length = 64, comment = "Current token of the series.")
    private String token;
    @Column(name = "last_used", nullable = false, comment = "Time the token was last used.")
    private LocalDateTime lastUsed;

    protected PersistentLogins() {}
}
