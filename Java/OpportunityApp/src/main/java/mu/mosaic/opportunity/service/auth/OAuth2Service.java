package mu.mosaic.opportunity.service.auth;

import mu.mosaic.opportunity.obj.entity.Account_User;
import org.jspecify.annotations.NullMarked;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.user.DefaultOAuth2User;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * SolarERP's Google sign-in: the first time an email signs in with Google an Account_User is made for it, with a random
 * password nobody knows, so the same person can later set one through a password reset. The principal's name is the
 * email, as with the form login, so the rest of the site sees one kind of user.
 */
@Service
public class OAuth2Service extends DefaultOAuth2UserService {
    private final PasswordEncoder passwordEncoder;

    public OAuth2Service(PasswordEncoder passwordEncoder) {
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    @NullMarked
    public OAuth2User loadUser(OAuth2UserRequest request) throws OAuth2AuthenticationException {
        OAuth2User oauthUser = super.loadUser(request);
        String email = Account_User.normalise(oauthUser.getAttribute("email"));
        if (email == null || !Boolean.TRUE.equals(oauthUser.getAttribute("email_verified")))
            throw new OAuth2AuthenticationException(new OAuth2Error("unverified_email"), "Google did not confirm this email address.");
        if (Account_User.getByEmail(email) == null)
            new Account_User(email, passwordEncoder.encode(UUID.randomUUID().toString()),
                    oauthUser.getAttribute("given_name"), oauthUser.getAttribute("family_name")).Write();
        Map<String, Object> attributes = new java.util.HashMap<>(oauthUser.getAttributes());
        attributes.put("email", email);
        return new DefaultOAuth2User(List.of(), attributes, "email");
    }
}
