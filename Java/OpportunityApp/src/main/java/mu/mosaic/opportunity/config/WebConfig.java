package mu.mosaic.opportunity.config;

import org.solarframework.web.spring.RequestLoggerInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addInterceptors(InterceptorRegistry registry) { // static assets skip the request log
        registry.addInterceptor(new RequestLoggerInterceptor()).excludePathPatterns("/css/**", "/js/**", "/img/**", "/webjars/**");
    }
}
