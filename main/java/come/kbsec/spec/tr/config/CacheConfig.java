package com.kbsec.spec.tr.config;

import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.cache.caffeine.CaffeineCache;
import org.springframework.cache.support.SimpleCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.Scheduled;

import java.util.ArrayList;

import java.util.Collection;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

@Slf4j
@Configuration
public class CacheConfig {
    private static final int DEFAULT_MAXSIZE = 10_000;
    private static final int DEFAULT_TTL = 3600;
    
    @Bean
    public CacheManager cacheManager() {
        SimpleCacheManager manager = new SimpleCacheManager();
        ArrayList<CaffeineCache> caches = new ArrayList<>();
        for (Caches c : Caches.values()) {
            caches.add(new CaffeineCache(c.name(),
                Caffeine.newBuilder().recordStats().expireAfterAccess(c.getTtl(), TimeUnit.SECONDS)
                .expireAfterWrite(c.getTtl(), TimeUnit.SECONDS)
                .maximumSize(c.getMaxSize()) // entry 갯수
                .build())
            );
        }
        manager.setCaches(caches);
        return manager;
    }
    
    public enum Caches {
        cache2Sec(2, 1000),
        cache3Sec(3, 1000),
        cache10Sec(10, 1000),
        cache30Sec(30, 2000),
        cache60Sec(60, 3000),
        cache10Min(600, 5000),
        cache30Min(1800, 7000),
        cache1Hour(3600, 10000),
        cache8Hour(28800, 10000),
        cache24HourWithoutEvict(3600*24, 10000);
        
        private int ttl;
        private int maxSize;
        
        Caches(int ttl, int maxSize) {
            this.ttl = ttl;
            this.maxSize = maxSize;
        }
        
        public int getMaxSize() {
            return maxSize;
        }
        
        public int getTtl() {
            return ttl;
        }
    }
    
    public void evictCaches(String name) {
        Objects.requireNonNull(cacheManager().getCache(name)).clear();
    }
    
    @Scheduled(cron = "0 0 8 * * ?")
    public void evictAllCachesAtIntervals() {
        Collection<String> caches = cacheManager().getCacheNames();
        log.info("Clearing All Caches");
        for(String key : caches){
            if(!key.endsWith("WithoutEvict")){
                log.info("Not Evict: " + key);
                Cache cache = cacheManager().getCache(key);
                if(cache!= null){
                    cache.clear();
                }
            }
        }
        log.info("Cleared All Caches");
    }
}