package com.kbsec.spec.tr.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpClientErrorException;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

@Slf4j
@ControllerAdvice
@RestController
public class GlobalExceptionHandler extends RuntimeException {

    private static final long serialVersionUID = 1L;
    
    @ExceptionHandler(HttpClientErrorException.class)
    protected ResponseEntity<Map<String, String>> RestApi404Exception(HttpClientErrorException e) {
        log.error("Not Found", e);
        Map<String, String> errMap = new HashMap<>();
        errMap.put("message", e.getMessage());
        return new ResponseEntity<>(errMap, HttpStatus.NOT_FOUND);
    }
}