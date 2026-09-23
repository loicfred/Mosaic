package mu.mosaic.opportunity.obj.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import org.solarframework.db.spring.DatabaseObject;

import java.security.Principal;
import java.time.Instant;

/**
 * A person who can sign in, as SolarERP's Staff_Account keeps them, trimmed to what a local demo needs: no email
 * verification (there is no mail server), so an account can sign in as soon as it is created.
 */
@Entity
@Table(name = "account_user", comment = "People who can sign in to Mosaic.")
public class Account_User extends DatabaseObject.ID_RECORD_OBJ<Long, Account_User> {
    @Column(name = "Email", length = 128, nullable = false, unique = true, comment = "Sign-in name, stored lower case.")
    private String email;
    @Column(name = "PasswordHash", length = 512, nullable = false, comment = "BCrypt hash; never the password itself.")
    private String passwordHash;
    @Column(name = "FirstName", length = 64, comment = "Given name shown in the header.")
    private String firstName;
    @Column(name = "LastName", length = 64, comment = "Family name.")
    private String lastName;
    @Column(name = "LastLoginAt", comment = "Time of the last successful sign-in.")
    private Instant lastLoginAt;
    @Column(name = "LoginCount", comment = "Successful sign-ins so far.")
    private Integer loginCount = 0;

    protected Account_User() {}
    public Account_User(String email, String passwordHash, String firstName, String lastName) {
        this.ID = Instant.now().toEpochMilli();
        this.email = normalise(email);
        this.passwordHash = passwordHash;
        this.firstName = firstName;
        this.lastName = lastName;
    }

    public static Account_User getByEmail(String email) {
        if (email == null) return null;
        return retrieveEntityServiceFor(Account_User.class).getWhere("Email = ?", normalise(email)).orElse(null);
    }
    public static Account_User getByAuthentication(Principal principal) {
        return principal == null ? null : getByEmail(principal.getName());
    }

    /** Emails are compared case-insensitively, so they are stored in one case. */
    public static String normalise(String email) { return email == null ? null : email.trim().toLowerCase(); }

    public void recordLogin() {
        loginCount = (loginCount == null ? 0 : loginCount) + 1;
        lastLoginAt = Instant.now();
        UpdateOnly("LoginCount", "LastLoginAt");
    }

    public String getEmail() { return email; }
    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public Instant getLastLoginAt() { return lastLoginAt; }
    public Integer getLoginCount() { return loginCount; }
    public String getDisplayName() { return firstName == null || firstName.isBlank() ? email : firstName; }
}
