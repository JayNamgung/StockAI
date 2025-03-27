from typing import AsyncGenerator, Dict, Any, Optional, List
import logging
import json
import time
import asyncio
from fastapi import Request, Depends

from agent.share.core.interface.tr_interface import TrInterface

logger = logging.getLogger(__name__)

class TrRepository:
    """
    TR 데이터 저장소
    TR 요청 및 캐싱을 관리
    """
    
    def __init__(self, tr: TrInterface):
        """
        TR 저장소 초기화
        
        Args:
            tr: TR 인터페이스 구현체
        """
        self.tr = tr
        
        # 캐시 저장소
        self.cache = {}
        self.cache_expiry = {}
        
        # 캐시 삭제 제외 TR 코드 목록
        self.not_evict_tr_codes = tr.get_not_evict_tr_codes()
        
        logger.info("TR 저장소 초기화 완료")
    
    async def request_tr(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        TR 요청을 실행하고 결과를 반환
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        # 캐시 키 생성
        cache_key = self._generate_cache_key(tr_code, params, continue_key)
        
        # 캐시 TTL 결정
        ttl = self.tr.get_cache_ttl(tr_code)
        
        # 연속 조회는 캐싱하지 않음
        if continue_key:
            return await self.tr.request_tr(tr_code, params, continue_key)
        
        # 캐시 확인
        current_time = time.time()
        if cache_key in self.cache and current_time < self.cache_expiry.get(cache_key, 0):
            logger.debug(f"캐시에서 TR 데이터 반환: {tr_code}")
            return self.cache[cache_key]
        
        # TR 요청 실행
        result = await self.tr.request_tr(tr_code, params, continue_key)
        
        # 캐싱 (캐시 삭제 제외 TR 코드 또는 TTL > 0인 경우)
        if tr_code in self.not_evict_tr_codes or ttl > 0:
            self.cache[cache_key] = result
            self.cache_expiry[cache_key] = current_time + ttl
            logger.debug(f"TR 데이터 캐싱: {tr_code}, TTL: {ttl}초")
        
        return result
    
    def _generate_cache_key(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> str:
        """
        캐시 키를 생성
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            str: 캐시 키
        """
        # 매개변수를 정렬하여 일관된 키 생성
        sorted_params = dict(sorted(params.items()))
        
        # TR 코드와 매개변수를 포함한 키 생성
        key_str = f"{tr_code}_{json.dumps(sorted_params)}"
        
        # 연속 조회 키가 있으면 포함
        if continue_key:
            key_str += f"_{continue_key}"
        
        return key_str
    
    async def evict_cache(self, tr_code: Optional[str] = None):
        """
        캐시를 초기화
        
        Args:
            tr_code: 초기화할 TR 코드 (None이면 모든 캐시 초기화)
        """
        if tr_code:
            # 특정 TR 코드 캐시만 초기화
            keys_to_delete = []
            for key in self.cache.keys():
                if key.startswith(f"{tr_code}_"):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if key in self.cache:
                    del self.cache[key]
                if key in self.cache_expiry:
                    del self.cache_expiry[key]
            
            logger.info(f"TR {tr_code} 캐시 초기화 완료: {len(keys_to_delete)}개 항목")
        else:
            # 캐시 삭제 제외 TR 코드를 제외한 모든 캐시 초기화
            keys_to_delete = []
            for key in list(self.cache.keys()):
                is_excluded = any(key.startswith(f"{code}_") for code in self.not_evict_tr_codes)
                if not is_excluded:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if key in self.cache:
                    del self.cache[key]
                if key in self.cache_expiry:
                    del self.cache_expiry[key]
            
            logger.info(f"모든 캐시 초기화 완료: {len(keys_to_delete)}개 항목")
    
    async def evict_all_caches_at_intervals(self):
        """
        주기적으로 모든 캐시를 초기화
        """
        logger.info("주기적 캐시 초기화 시작")
        await self.evict_cache()
        logger.info("주기적 캐시 초기화 완료")