package mu.mosaic.opportunity.service.auth;

import jakarta.servlet.http.HttpServletRequest;
import mu.mosaic.opportunity.obj.entity.Account_PasswordReset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.mail.spring.MailRegistry;
import org.springframework.stereotype.Service;

/** SolarERP's reset letter, sent through SolarFramework's default mailbox (seeded from .env's spring.mail keys). */
@Service
public class AuthEmailService {
    private static final Logger log = LoggerFactory.getLogger(AuthEmailService.class);

    public boolean isAvailable() {
        return MailRegistry.DefaultMailService != null && MailRegistry.DefaultMailService.getUsername() != null
                && !MailRegistry.DefaultMailService.getUsername().isBlank();
    }

    /** False when the letter could not be sent; the reason goes to the log, not to the page. */
    public boolean sendResetPasswordEmail(HttpServletRequest req, String to, String token) {
        String link = req.getRequestURL().toString().replaceFirst(req.getRequestURI() + "$", "") + "/auth/v1/newpassword?token=" + token;
        String body = "We received a request to reset the password for your Mosaic account.\n\n"
                + "Choose a new password here:\n" + link + "\n\n"
                + "This link can be used once and stops working after " + Account_PasswordReset.LIFETIME.toHours() + " hours.\n\n"
                + "If you did not request this, you can safely ignore this message. Your current password still works."
                + "\n\nKind regards,\nThe Mosaic team\n\nThis message was sent automatically. Please do not reply to it.";
        try {
            MailRegistry.DefaultMailService.send(to, "Reset your Mosaic password", body);
            return true;
        } catch (RuntimeException e) {
            log.warn("Password-reset email to {} not sent: {}", to, e.getMessage());
            return false;
        }
    }
}
