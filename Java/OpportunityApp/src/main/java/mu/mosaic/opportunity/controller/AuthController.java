package mu.mosaic.opportunity.controller;

import jakarta.servlet.http.HttpServletRequest;
import mu.mosaic.opportunity.obj.entity.Account_PasswordReset;
import mu.mosaic.opportunity.obj.entity.Account_User;
import mu.mosaic.opportunity.service.auth.AuthEmailService;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.security.Principal;
import java.util.regex.Pattern;

/** SolarERP's /auth/v1 pages: log in (the form posts to Spring Security), sign up, and reset a password by email. */
@Controller
@RequestMapping("/auth/v1")
public class AuthController {
    private static final int MIN_PASSWORD = 8;
    private static final int MAX_PASSWORD = 72; // BCrypt reads 72 bytes at most
    private static final Pattern EMAIL = Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");
    private final PasswordEncoder passwordEncoder;
    private final AuthEmailService emails;
    private final ObjectProvider<ClientRegistrationRepository> google;

    public AuthController(PasswordEncoder passwordEncoder, AuthEmailService emails, ObjectProvider<ClientRegistrationRepository> google) {
        this.passwordEncoder = passwordEncoder;
        this.emails = emails;
        this.google = google;
    }

    @GetMapping("/login")
    public String login(Principal loggedUser, Model model) {
        if (loggedUser != null) return "redirect:/";
        model.addAttribute("googleEnabled", google.getIfAvailable() != null);
        model.addAttribute("mailEnabled", emails.isAvailable());
        return "auth/v1/login";
    }

    @GetMapping("/signup")
    public String signupForm(Principal loggedUser) {
        return loggedUser != null ? "redirect:/" : "auth/v1/signup";
    }

    @PostMapping("/signup")
    public String signup(@RequestParam String email, @RequestParam String password, @RequestParam String confirm,
                         @RequestParam(defaultValue = "") String firstName, @RequestParam(defaultValue = "") String lastName) {
        email = Account_User.normalise(email);
        if (!EMAIL.matcher(email).matches() || email.length() > 128) return "redirect:/auth/v1/signup?bademail";
        String problem = passwordProblem(password, confirm);
        if (problem != null) return "redirect:/auth/v1/signup?" + problem;
        if (Account_User.getByEmail(email) != null) return "redirect:/auth/v1/signup?taken";
        new Account_User(email, passwordEncoder.encode(password), trim(firstName), trim(lastName)).Write();
        return "redirect:/auth/v1/login?created";
    }

    @GetMapping("/resetpassword")
    public String resetPasswordForm(Model model) {
        model.addAttribute("mailEnabled", emails.isAvailable());
        return "auth/v1/resetpassword";
    }

    /** Answers the same whether or not the email has an account, so the form cannot be used to find out who has one. */
    @PostMapping("/resetpassword")
    public String resetPassword(HttpServletRequest request, @RequestParam String email) {
        if (!emails.isAvailable()) return "redirect:/auth/v1/resetpassword";
        Account_User user = Account_User.getByEmail(email);
        if (user != null) {
            Account_PasswordReset reset = new Account_PasswordReset(user);
            reset.Write();
            if (!emails.sendResetPasswordEmail(request, user.getEmail(), reset.getToken())) return "redirect:/auth/v1/resetpassword?failed";
        }
        return "redirect:/auth/v1/resetpassword?sent";
    }

    @GetMapping("/newpassword")
    public String newPasswordForm(@RequestParam(defaultValue = "") String token, Model model) {
        if (Account_PasswordReset.getValid(token) == null) return "redirect:/auth/v1/resetpassword?expired";
        model.addAttribute("token", token);
        return "auth/v1/newpassword";
    }

    @PostMapping("/newpassword")
    public String newPassword(@RequestParam String token, @RequestParam String password, @RequestParam String confirm) {
        Account_PasswordReset reset = Account_PasswordReset.getValid(token);
        Account_User user = reset == null ? null : reset.getUser();
        if (user == null) return "redirect:/auth/v1/resetpassword?expired";
        String problem = passwordProblem(password, confirm);
        if (problem != null) return "redirect:/auth/v1/newpassword?token=" + token + "&" + problem;
        user.setPasswordHash(passwordEncoder.encode(password));
        user.UpdateOnly("PasswordHash");
        reset.Delete();
        return "redirect:/auth/v1/login?newpassword";
    }

    /** The query flag naming what is wrong with the password, or null when it will do. */
    private static String passwordProblem(String password, String confirm) {
        if (password.length() < MIN_PASSWORD || password.length() > MAX_PASSWORD) return "badpassword";
        return password.equals(confirm) ? null : "mismatch";
    }

    private static String trim(String s) {
        s = s.strip();
        return s.length() > 64 ? s.substring(0, 64) : s;
    }
}
