package mu.mosaic.opportunity.config;

import mu.mosaic.opportunity.obj.entity.Account_PasswordReset;
import mu.mosaic.opportunity.obj.entity.Account_User;
import mu.mosaic.opportunity.obj.entity.PersistentLogins;
import mu.mosaic.opportunity.service.auth.OAuth2Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.solarframework.db.api.IDatabaseManager;
import org.solarframework.db.api.IDatabaseService;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.LoginUrlAuthenticationEntryPoint;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.RememberMeServices;
import org.springframework.security.web.authentication.rememberme.JdbcTokenRepositoryImpl;
import org.springframework.security.web.authentication.rememberme.PersistentTokenBasedRememberMeServices;
import org.springframework.security.web.authentication.rememberme.PersistentTokenRepository;
import org.springframework.security.web.servlet.util.matcher.PathPatternRequestMatcher;

import java.util.List;
import java.util.UUID;

/**
 * SolarERP's sign-in (ERP/.../config/SecurityConfig.java): a form login on Account_User, Google when .env holds its
 * keys, remember-me tokens kept in the database for 14 days, and logout back to the login page.
 */
@Configuration
public class SecurityConfig {
    private static final Logger log = LoggerFactory.getLogger(SecurityConfig.class);
    static final int REMEMBER_SECONDS = 14 * 24 * 3600;
    // only signs tokens inside this process; the tokens themselves live in persistent_logins
    private static final String REMEMBER_KEY = UUID.randomUUID().toString();
    private final IDatabaseService db;

    public SecurityConfig(IDatabaseManager manager) {
        this.db = manager.getDefaultService();
        db.createSchemaIfMissing(List.of(Account_User.class, PersistentLogins.class, Account_PasswordReset.class));
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public UserDetailsService userDetailsService() {
        return email -> {
            Account_User user = Account_User.getByEmail(email);
            if (user == null) throw new UsernameNotFoundException("No account for " + email);
            return User.withUsername(user.getEmail()).password(user.getPasswordHash()).authorities(List.of()).build();
        };
    }

    @Bean
    public PersistentTokenRepository persistentTokenRepository() {
        JdbcTokenRepositoryImpl repo = new JdbcTokenRepositoryImpl();
        repo.setDataSource(db.getDataSource());
        return repo;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http, ObjectProvider<ClientRegistrationRepository> google, OAuth2Service oAuth2Service) {
        http
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/auth/**", "/error", "/css/**", "/js/**", "/img/**", "/webjars/**").permitAll()
                        .anyRequest().authenticated())
                // /api/** is called by the pages' own scripts: a signed-out call gets 401, not the login page's HTML
                .exceptionHandling(ex -> ex.authenticationEntryPoint(entryPoint()))
                // the pages' scripts post JSON to /api/** without a token, as in SolarERP
                .csrf(csrf -> csrf.ignoringRequestMatchers("/api/**"))
                .formLogin(form -> form.loginPage("/auth/v1/login").loginProcessingUrl("/auth/v1/login")
                        .successHandler(onSuccess(null)).failureUrl("/auth/v1/login?error").permitAll())
                .rememberMe(remember -> remember.key(REMEMBER_KEY).tokenRepository(persistentTokenRepository())
                        .tokenValiditySeconds(REMEMBER_SECONDS).userDetailsService(userDetailsService()))
                .logout(logout -> logout.logoutUrl("/logout").logoutSuccessUrl("/auth/v1/login?logout").permitAll());
        // Google only when .env gives it a client id: Spring Boot registers no client otherwise
        if (google.getIfAvailable() != null)
            http.oauth2Login(oauth -> oauth.loginPage("/auth/v1/login").failureUrl("/auth/v1/login?error")
                    .userInfoEndpoint(info -> info.userService(oAuth2Service)).successHandler(onSuccess(rememberMeServices())));
        return http.build();
    }

    private static AuthenticationEntryPoint entryPoint() {
        RequestMatcher api = PathPatternRequestMatcher.withDefaults().matcher("/api/**");
        AuthenticationEntryPoint unauthorized = new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED);
        AuthenticationEntryPoint login = new LoginUrlAuthenticationEntryPoint("/auth/v1/login");
        return (request, response, e) -> (api.matches(request) ? unauthorized : login).commence(request, response, e);
    }

    /** Google sign-ins are always remembered, as in SolarERP; the form remembers only when its box is ticked. */
    @Bean
    public RememberMeServices rememberMeServices() {
        PersistentTokenBasedRememberMeServices services = new PersistentTokenBasedRememberMeServices(REMEMBER_KEY, userDetailsService(), persistentTokenRepository());
        services.setAlwaysRemember(true);
        services.setTokenValiditySeconds(REMEMBER_SECONDS);
        return services;
    }

    private static AuthenticationSuccessHandler onSuccess(RememberMeServices remember) {
        return (request, response, authentication) -> {
            if (remember != null) remember.loginSuccess(request, response, authentication);
            onLogin(authentication);
            response.sendRedirect("/");
        };
    }

    private static void onLogin(Authentication authentication) {
        log.info("{} signed in.", authentication.getName());
        Account_User user = Account_User.getByEmail(authentication.getName());
        if (user != null) user.recordLogin();
    }
}
