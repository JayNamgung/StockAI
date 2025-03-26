"""
TR 저장소 모듈
TR 데이터의 캐싱 및 저장을 담당
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

# 캐시 TTL 정의 (Spring의 CacheConfig.Caches enum에 해당)
CACHE_TTL_MAP = {
    "cache2Sec": 2,
    "cache3Sec": 3,
    "cache10Sec": 10,
    "cache30Sec": 30,
    "cache60Sec": 60,
    "cache10Min": 600,
    "cache30Min": 1800,
    "cache1Hour": 3600,
    "cache8Hour": 28800,
    "cache24HourWithoutEvict": 86400,
}

class TrRepository:
    """
    TR 저장소 클래스
    TR 데이터의 캐싱 및 조회를 담당
    """
    
    def __init__(self):
        """
        TR 저장소 초기화
        캐시 및 필요한 리소스 초기화
        """
        # 메모리 캐시 (TR 코드 + 매개변수로 구성된 키 -> 응답 데이터)
        self.cache = {}
        
        # 캐시 만료 시간 (TR 코드 + 매개변수로 구성된 키 -> 만료 시간)
        self.cache_expiry = {}
        
        # 삭제 제외 TR 코드 목록
        self.not_evict_tr_codes = []
        
        logger.info("TR 저장소 초기화 완료")
    
    def set_not_evict_tr_codes(self, codes: List[str]):
        """
        캐시 삭제 대상에서 제외할 TR 코드 목록을 설정
        
        Args:
            codes: 캐시 삭제 제외 TR 코드 목록
        """
        self.not_evict_tr_codes = codes
        logger.info(f"캐시 삭제 제외 TR 코드 설정: {codes}")
    
    def _generate_cache_key(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> str:
        """
        캐시 키를 생성하는 내부 메서드
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            str: 캐시 키
        """
        # 매개변수를 정렬하여 일관된 키 생성
        sorted_params = dict(sorted(params.items()))
        
        # 매개변수와 연속 조회 키를 포함한 문자열 생성
        key_str = f"{tr_code}_{json.dumps(sorted_params)}"
        if continue_key:
            key_str += f"_{continue_key}"
        
        # SHA-256 해시를 사용하여 일관된 길이의 키 생성
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get_cache_name_by_ttl(self, ttl: int) -> str:
        """
        TTL 값에 해당하는 캐시 이름을 반환
        
        Args:
            ttl: TTL 값 (초 단위)
            
        Returns:
            str: 캐시 이름
        """
        # TTL 값에 가장 가까운 캐시 이름 찾기
        if ttl >= 86400:
            return "cache24HourWithoutEvict"
        elif ttl >= 28800:
            return "cache8Hour"
        elif ttl >= 3600:
            return "cache1Hour"
        elif ttl >= 1800:
            return "cache30Min"
        elif ttl >= 600:
            return "cache10Min"
        elif ttl >= 60:
            return "cache60Sec"
        elif ttl >= 30:
            return "cache30Sec"
        elif ttl >= 10:
            return "cache10Sec"
        elif ttl >= 3:
            return "cache3Sec"
        elif ttl >= 2:
            return "cache2Sec"
        else:
            return "cache30Sec"  # 기본 캐시 (Spring 구현과 일치)
    
    def cached(self, tr_code: str, ttl: int):
        """
        TR 요청 결과를 캐싱하는 데코레이터
        Spring의 @Cacheable 어노테이션에 해당
        
        Args:
            tr_code: TR 코드
            ttl: 캐시 TTL (초 단위)
            
        Returns:
            Callable: 데코레이터 함수
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(self_obj, params: Dict[str, Any], continue_key: Optional[str] = None, *args, **kwargs):
                # 캐시 키 생성
                cache_key = self._generate_cache_key(tr_code, params, continue_key)
                
                # 현재 시간
                current_time = asyncio.get_event_loop().time()
                
                # 캐시에서 결과 확인
                if cache_key in self.cache and (cache_key not in self.cache_expiry or self.cache_expiry[cache_key] > current_time):
                    logger.debug(f"캐시에서 TR 데이터 반환: {tr_code}")
                    return self.cache[cache_key]
                
                # 함수 실행
                result = await func(self_obj, params, continue_key, *args, **kwargs)
                
                # 결과 캐싱
                self.cache[cache_key] = result
                self.cache_expiry[cache_key] = current_time + ttl
                
                logger.debug(f"TR 데이터 캐싱: {tr_code}, TTL: {ttl}초")
                
                return result
            
            return wrapper
            
        return decorator
    
    async def evict_cache(self, cache_name: Optional[str] = None):
        """
        캐시를 초기화하는 메서드
        
        Args:
            cache_name: 초기화할 캐시 이름 (지정하지 않으면 모든 캐시 초기화)
        """
        # 현재 시간
        current_time = asyncio.get_event_loop().time()
        
        # 삭제할 캐시 키 목록
        keys_to_delete = []
        
        # 만료된 캐시 항목 찾기
        for key, expiry_time in self.cache_expiry.items():
            if expiry_time <= current_time:
                keys_to_delete.append(key)
        
        # 만료된 캐시 항목 삭제
        for key in keys_to_delete:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_expiry:
                del self.cache_expiry[key]
        
        logger.info(f"캐시 초기화 완료: {len(keys_to_delete)}개 항목 삭제")
    
    async def evict_all_caches_at_intervals(self):
        """
        주기적으로 모든 캐시를 초기화하는 메서드
        Spring의 @Scheduled(cron = "0 0 8 * * ?") 메서드에 해당
        """
        logger.info("모든 캐시 초기화 시작")
        
        # 삭제 제외 TR 코드를 제외한 모든 캐시 초기화
        keys_to_delete = []
        for key in list(self.cache.keys()):
            # TR 코드가 삭제 제외 목록에 없으면 삭제
            is_excluded = any(not_evict_code in key for not_evict_code in self.not_evict_tr_codes)
            if not is_excluded:
                keys_to_delete.append(key)
        
        # 캐시 항목 삭제
        for key in keys_to_delete:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_expiry:
                del self.cache_expiry[key]
        
        logger.info(f"모든 캐시 초기화 완료: {len(keys_to_delete)}개 항목 삭제")