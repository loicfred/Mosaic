package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

/** A one-use link to choose a new password, as SolarERP's Staff_EmailVerification of type PASSWORD_RESET. */
@Entity
@Table(name = "account_password_reset", comment = "Emailed links to choose a new password.")
public class Account_PasswordReset extends DatabaseObject<Account_PasswordReset> {
    public static final Duration LIFETIME = Duration.ofHours(24);
    @Id
    @Column(name = "Token", length = 64, nullable = false, comment = "Random token carried by the emailed link.")
    private String token;
    @Column(name = "UserID", nullable = false, comment = "Account whose password the link may change.")
    private Long userId;
    @Column(name = "ExpiresAt", nullable = false, comment = "The link stops working after this time.")
    private Instant expiresAt;

    protected Account_PasswordReset() {}
    public Account_PasswordReset(Account_User user) {
        this.token = UUID.randomUUID().toString();
        this.userId = user.getID();
        this.expiresAt = Instant.now().plus(LIFETIME);
    }

    /** The link's row, or null once it is unknown or expired. */
    public static Account_PasswordReset getValid(String token) {
        if (token == null || token.isBlank()) return null;
        Account_PasswordReset reset = retrieveEntityServiceFor(Account_PasswordReset.class).getWhere("Token = ?", token).orElse(null);
        return reset == null || reset.expiresAt.isBefore(Instant.now()) ? null : reset;
    }

    public Account_User getUser() {
        return retrieveEntityServiceFor(Account_User.class).getWhere("ID = ?", userId).orElse(null);
    }
    public String getToken() { return token; }
}
