package mu.mosaic.opportunity.config;

import mu.mosaic.opportunity.obj.entity.Account_User;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ModelAttribute;

import java.security.Principal;

/** Gives every page the signed-in account, for the header's name and sign-out button. */
@ControllerAdvice
public class CurrentUserAdvice {

    @ModelAttribute("currentUser")
    public Account_User currentUser(Principal principal) {
        return Account_User.getByAuthentication(principal);
    }
}
