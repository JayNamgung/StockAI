package com.kbsec.spec.tr.controllers;

import com.kbsec.spec.tr.services.ProxyService;
import com.kbsec.spec.tr.utils.CacheUtil;
import lombok.extern.slf4j.Slf4j;
import net.sf.json.JSONObject;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpClientErrorException;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/proxy")
public class ProxyController {
    
    final ProxyService proxyService;
    
    final CacheUtil cacheUtil;
    
    final List<String> notEvictTrCodes;
    

    public ProxyController(ProxyService proxyService, CacheUtil cacheUtil) {
        this.proxyService = proxyService;
        this.cacheUtil = cacheUtil;
        this.notEvictTrCodes = cacheUtil.getNotEvictTrCodes();
    }
    
    @GetMapping("/health")
    public ResponseEntity<String> healthCheck(){
        return ResponseEntity.ok("ok");
    }

    
    @PostMapping("/api/kb/{trCode}")
    public ResponseEntity<JSONObject> getTrDataByCode(
            @PathVariable String trCode,
            @RequestBody JSONObject trBody
    ) throws Exception {
        log.debug(trCode);
        return ResponseEntity.ok(getTrData(trCode, trBody));
    }
    
    @PostMapping("/v1.0/ksv/spec/{alias}")
    public ResponseEntity<JSONObject> getTrDataByAlias(
            @PathVariable String alias,
            @RequestBody JSONObject trBody
    ) throws Exception {

        log.debug("Alias: " + alias);
        String trCode = cacheUtil.getTrCodeByAlias(alias);
        if(trCode == null) {
            throw new HttpClientErrorException(HttpStatus.NOT_FOUND);
        }
        log.info("Alias: " + alias + ", TrCode: " + trCode);
        return ResponseEntity.ok(getTrData(trCode, trBody));
    }
    
    @PostMapping("/v2.0/NISV01/{alias}")
    public ResponseEntity<JSONObject> getTrDataByAliasV2(
            @PathVariable String alias,
            @RequestBody JSONObject trBody
    ) throws Exception {
        
        String trCode = cacheUtil.getTrCodeByAlias(alias);
        if(trCode == null) {
            throw new HttpClientErrorException(HttpStatus.NOT_FOUND);
        }
        log.info("TrCode: " + trCode);
        return ResponseEntity.ok(getTrData(trCode, trBody));
    }
    
    private JSONObject getTrData(String trCode, JSONObject trBody) throws Exception{
        JSONObject result;
        
        JSONObject dataBody;
        
        JSONObject dataHeader;
        
        String continueKey = null ;
        
        if(trBody.has("dataHeader")){
            dataHeader = trBody.getJSONObject("dataHeader");
            if(dataHeader.has("contKey")){
                continueKey = dataHeader.getString("contKey");
            }
        }
        
        if(trBody.has("dataBody")){
            dataBody = trBody.getJSONObject("dataBody");
        } else {
            log.debug("No dataBody use trBody");
            dataBody = trBody;
        }
        
        long ttl = cacheUtil.getTtlByCode(trCode);
        log.info("TrCode: " + trCode + ", ttl: " + ttl);
        
        if(notEvictTrCodes.contains(trCode)){
            result = proxyService.getTrDataCachedWithoutEvict(trCode, dataBody, continueKey);
        } else {
            if(ttl >= 28800) {
                result = proxyService.getTrDataCached8Hour(trCode, dataBody, continueKey);
            } else if( ttl >= 3600) {
                result = proxyService.getTrDataCached1Hour(trCode, dataBody, continueKey);
            } else if ( ttl >= 1800) {
                result = proxyService.getTrDataCached30Min(trCode, dataBody, continueKey);
            } else if ( ttl >= 600) {
                result = proxyService.getTrDataCached10Min(trCode, dataBody, continueKey);
            } else if ( ttl >= 60) {
                result = proxyService.getTrDataCached60Sec(trCode, dataBody, continueKey);
            } else if ( ttl > 30) {
                result = proxyService.getTrDataCached10Sec(trCode, dataBody, continueKey);
            } else if ( ttl > 10) {
                result = proxyService.getTrDataCached3Sec(trCode, dataBody, continueKey);
            } else if ( ttl > 3){
                result = proxyService.getTrDataCached2Sec(trCode, dataBody, continueKey);
            } else if (ttl == 0){
                log.info("TrCode: " + trCode + " is Not cached");
                result = proxyService.getTrData(trCode, dataBody, continueKey);
            } else {
                result = proxyService.getTrDataCached30Sec(trCode, dataBody, continueKey);
            }
        }
        
        return result;
    }
}