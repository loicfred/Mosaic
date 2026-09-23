package mu.mosaic.opportunity;

import org.solarframework.ai.spring.AIConfig;
import org.solarframework.db.spring.DatabaseConfig;
import org.solarframework.mail.spring.MailConfig;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.hibernate.autoconfigure.HibernateJpaAutoConfiguration;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.context.annotation.Import;

import java.util.TimeZone;

// SolarFramework's DatabaseConfig builds the only DataSource; Boot's own would be a second one.
@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class, HibernateJpaAutoConfiguration.class})
@Import({AIConfig.class, DatabaseConfig.class, MailConfig.class}) // the AI manager (LocalAi fills it from config/ai/agents.json), the business database, and the mailbox for password resets
public class OpportunityApp {

    static void main(String[] args) {
        // SQLite keeps a timestamp as epoch millis in the JVM's zone; UTC has no daylight-saving gaps to shift one.
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
        ModuleHome.pin();
        SpringApplication.run(OpportunityApp.class, args);
    }
}
