package com.kbsec.spec.tr.config;
import org.springframework.security.web.authentication.preauth.AbstarctPreAuthenticatedProcessingFilter;

import javax.servlet.http.HttpServletRequest;

public class APIKeyAuthFilter extends AbstractPreAuthenticatedProcessingFIlter {
    private String principalRequestHeader;

    public APIKeyAuthFilter(String principalRequestHeader) {
        this.principalRequestHeader = principalRequestHeader;
    }

    @Override
    protected Object getPreAuthenticatedPrincipal(HttpServletRequest request){
        return request.getHeader(principalRequestHeader)
    }

    @Override
    protected Object getPreAuthenticatedCredentials(HttpServletRequest request){
        return "N/A";
    }
}