package com.kbsec.spec.tr.utils;

import lombok.extern.slf4j.Slf4j;

import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Component;

import java.io.FileReader;
import java.io.IOException;
import java.io.Reader;
import java.net.URL;
import java.util.*;

@Slf4j
@Component
public class CacheUtil {

   final ResourceLoader loader;
   
   final JSONObject trRules;
   
   final Map<String, String> aliasMapping;
   
   public CacheUtil(ResourceLoader loader) throws IOException, ParseException {
       this.loader = loader;
       
       Reader reader = new FileReader("config/cache-config.json");
       JSONParser parser = new JSONParser();
       
       this.trRules = (JSONObject) parser.parse(reader);
       
       this.aliasMapping = new HashMap<>();
       Set<String> keys = (Set<String>) this.trRules.keySet();
       for(String key : keys){
           JSONObject jsonObject = (JSONObject) trRules.get(key);
           String alias = String.valueOf(jsonObject.get("alias"));
           if(alias != null){
               aliasMapping.put(alias, key);
           }
       }
   }
   
   public long getTtlByCode(String code){
       JSONObject tr = (JSONObject) trRules.get(code);
       if(tr == null || tr.isEmpty()){
           return 30;
       } else {
           return (long)tr.get("ttl");
       }
   }
   
   public String getTrCodeByAlias(String alias) {
       return aliasMapping.get(alias);
   }
   
   public String getArrayName(String trCode){
       JSONObject tr = (JSONObject) trRules.get(trCode);
       if(tr.isEmpty()){
           return "";
       }
       return (String) tr.get("arrayName");
   }
   
   public List<String> getNotEvictTrCodes(){
       List<String> codes = new ArrayList<>();
       codes.add("KBI50130");
       return codes;
   }
}