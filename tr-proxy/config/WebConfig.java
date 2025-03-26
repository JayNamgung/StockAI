package com.kbsec.spec.tr.config;

import com.kbsec.wts.listener.KASSHttpSessionListener;
import com.kbsec.wts.listener.KASSServletContextListener;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.servlet.ServletContextInitializer;
import org.springframework.boot.web.servlet.ServletListenerRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;

import javax.servlet.ServletContext;
import javax.servlet.ServletException;
import java.net.SocketException;

@Slf4j
@Configuration
public class WebConfig {
    private final Environment env;
    
    @Value("${sysConf}")
    private String sysConfig;
    
    @Value("${vtsSysConf")
    private String vtsSysConfig;
    

    public WebConfig(Environment env) {
        this.env = env;
    }
    
    @Bean
    public ServletListenerRegistrationBean<KASSServletContextListener> servletContextListener() throws SocketException {
        ServletListenerRegistrationBean<KASSServletContextListener> listenerRegBean = new ServletListenerRegistrationBean<>();
        listenerRegBean.setListener(new KASSServletContextListener());
        return listenerRegBean;
    }
    
    @Bean
    public ServletListenerRegistrationBean<KASSHttpSessionListener> httpSessionListener() throws SocketException {
        ServletListenerRegistrationBean<KASSHttpSessionListener> listenerRegBean = new ServletListenerRegistrationBean<>();
        listenerRegBean.setListener(new KASSHttpSessionListener());
        return listenerRegBean;
    }
    
    @Bean
    public ServletContextInitializer initializer(){
        
        return new ServletContextInitializer() {
            @Override
            public void onStartup(ServletContext servletContext) throws ServletException {
                servletContext.setInitParameter("version", "version");
                servletContext.setInitParameter("serviceType", "WTS");
                servletContext.setInitParameter("initParam", "1");
                servletContext.setInitParameter("sysconf", sysConfig);
                servletContext.setInitParameter("vts_sysconf", vtsSysConfig);
            }
        };
    }
}