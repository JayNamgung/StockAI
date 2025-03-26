package com.kbsec.spec.tr.services;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kbsec.kass.dib.protocol.HeaderWrap;
import com.kbsec.kass.global.exception.RQRPException;
import com.kbsec.kass.secure.DSCheckedException;
import com.kbsec.kass.transaction.TransactionException;
import com.kbsec.kass.transaction.TrxRuleObject;
import com.kbsec.spec.tr.utils.CacheUtil;
import com.kbsec.wts.WTSHandler;
import lombok.extern.slf4j.Slf4j;
import net.sf.json.JSONArray;
import net.sf.json.JSONObject;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;

@Slf4j
@Service
public class ProxyService {
    final HeaderWrap hw;
    
    public ProxyService(CacheUtil cacheUtil) {
        this.hw = new HeaderWrap();
        hw.setChannelID("3Aw");
    }
    
    @Cacheable(value = "cache24HourWithoutEvict" )
    public JSONObject getTrDataCachedWithoutEvict(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug( "24 Hour Caching without evict" + ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);
    }
    
    @Cacheable(value = "cache8Hour" )
    public JSONObject getTrDataCached8Hour(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.info( "8 Hour Caching" + ", trCode:" + trCode);
        log.info(trBody.toString());
        return getTrData(trCode, trBody, continueKey);
    }
    @Cacheable(value = "cache1Hour" )
    public JSONObject getTrDataCached1Hour(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("1 Hour Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);
    }

    @Cacheable(value = "cache30Min" )
    public JSONObject getTrDataCached30Min(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("30 Min Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);

    }
    @Cacheable(value = "cache10Min" )
    public JSONObject getTrDataCached10Min(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("10 Min Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);

    }
    @Cacheable(value = "cache60Sec" )
    public JSONObject getTrDataCached60Sec(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("60 Sec Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);

    }
    @Cacheable(value = "cache30Sec" )
    public JSONObject getTrDataCached30Sec(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("30 Sec Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);
        
    }
    
    @Cacheable(value = "cache10Sec" )
    public JSONObject getTrDataCached10Sec(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("10 Sec Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);
    }
    
    @Cacheable(value = "cache3Sec" )
    public JSONObject getTrDataCached3Sec(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("3 Sec Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);
    }
    
    @Cacheable(value = "cache2Sec" )
    public JSONObject getTrDataCached2Sec(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.debug("2 Sec Caching"+ ", trCode:" + trCode);
        return getTrData(trCode, trBody, continueKey);
    }
    
    public JSONObject getTrData(String trCode, JSONObject trBody, String continueKey) throws RQRPException, TransactionException, DSCheckedException {
        log.info("[TR-"+trCode + "]");
        TrxRuleObject trxRule = new TrxRuleObject("Tkb_"+trCode);
        Map<String, Object> dataBody = getMapFromJsonObject(trBody);
        
        Set<String> keys = dataBody.keySet();
        
        for( String key : keys){
            if(dataBody.get(key) instanceof ArrayList){
                dataBody.put(WTSHandler.INPUT_RECORD_NAME,key);
            }
        }
        
        if("IVCA0060".equals(trCode)){
            log.info("IVCA0060 Invoked: indTypCd is: " + dataBody.get("indTypCd"));
        }
        
        if("IVCA0060".equals(trCode) && keys.contains("indTypCd")){
            if("001".equals(dataBody.get("indTypCd")))
                dataBody.put("indxId","KG001P");
            else if("301".equals(dataBody.get("indTypCd")))
                dataBody.put("indxId","OG001P");
        }
        
        if(continueKey != null){
            log.info("ContinueKey: " + continueKey);
            HeaderWrap header = new HeaderWrap();
            header.setCont_flag("Y");
            header.setContkey_new(continueKey);
            int x = trxRule.rq(dataBody, null, header);
        } else {
            int x = trxRule.rq(dataBody, null, hw);
        }
        
        log.debug(trCode + ": " + trBody);
        JSONObject responseObj = trxRule.getResult().getOutput();
        JSONObject resultObj = new JSONObject();
        JSONObject tempObj = new JSONObject();
        for (Iterator it = responseObj.keys(); it.hasNext(); ) {
            String key = (String)it.next();
            if(!key.startsWith("_") && !key.startsWith("TRX_HEADER") && !key.startsWith("filler")){
                Object test = responseObj.get(key);
                
                if(test instanceof JSONArray){
                    JSONArray array = new JSONArray();
                    for(Object item : (JSONArray)test){
                        JSONObject child = new JSONObject();
                        for (Iterator child_it = ((JSONObject)item).keys(); child_it.hasNext(); ) {
                            String child_key = (String)child_it.next();
                            if(!child_key.startsWith("_") && !child_key.startsWith("TRX_HEADER") && !child_key.startsWith("filler")) {
                                child.put(child_key, ((JSONObject)item).get(child_key));
                            }
                        }
                        array.add(child);
                    }
                    tempObj.put(key,array);
                } else {
                    tempObj.put(key, responseObj.get(key));
                }
            }
        }
        
        JSONObject header = new JSONObject();
        header.put("resultCode", "200");
        header.put("resultMessage", "정상");
        header.put("processFlag", "A");
        header.put("category", "API");
        
        resultObj.put("dataHeader", header);
        resultObj.put("dataBody", tempObj);
        return resultObj;
    }
    
    private Map getMapFromJsonObject(JSONObject jsonObj) throws JsonProcessingException {
        return new ObjectMapper().readValue(jsonObj.toString(), Map.class);
    }
}