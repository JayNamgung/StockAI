"""
TR 관리 및 조율 모듈
TR 요청의 실행 및 캐싱을 관리
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.share.core.interface.tr_interface import TrInterface
from agent.share.core.tr.tr_kbsec import KbsecTr
from agent.share.repository.tr_repository import TrRepository

logger = logging.getLogger(__name__)

class TrManager:
    """
    TR 관리 및 조율 클래스
    TR 요청의 실행, 캐싱, 스케줄링을 담당
    """
    
    def __init__(self):
        """
        TR 관리자 초기화
        TR 구현체, 저장소, 스케줄러 초기화
        """
        # TR 구현체 초기화
        self.tr_impl = KbsecTr()
        
        # TR 저장소 초기화
        self.tr_repository = TrRepository()
        
        # 삭제 제외 TR 코드 설정
        self.tr_repository.set_not_evict_tr_codes(self.tr_impl.get_not_evict_tr_codes())
        
        # 스케줄러 초기화
        self.scheduler = AsyncIOScheduler()
        
        # 매일 오전 8시에 캐시 초기화 작업 스케줄링
        self.scheduler.add_job(
            self.tr_repository.evict_all_caches_at_intervals,
            'cron',
            hour=8,
            minute=0,
            second=0,
            id='cache_eviction'
        )
        
        logger.info("TR 관리자 초기화 완료")
    
    def start(self):
        """
        TR 관리자 시작
        스케줄러 시작
        """
        self.scheduler.start()
        logger.info("TR 관리자 스케줄러 시작")
    
    def stop(self):
        """
        TR 관리자 중지
        스케줄러 중지
        """
        self.scheduler.shutdown()
        logger.info("TR 관리자 스케줄러 중지")
    
    async def get_tr_data_by_code(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> Dict[str, Any]:
        """
        TR 코드로 데이터를 요청하는 메서드
        Spring의 ProxyController.getTrDataByCode() 메서드에 해당
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        try:
            return await self._get_tr_data(tr_code, params, continue_key)
        except Exception as e:
            logger.error(f"TR 데이터 요청 중 오류 발생: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"TR 데이터 요청 오류: {str(e)}")
    
    async def get_tr_data_by_alias(self, alias: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> Dict[str, Any]:
        """
        TR 별칭으로 데이터를 요청하는 메서드
        Spring의 ProxyController.getTrDataByAlias() 메서드에 해당
        
        Args:
            alias: TR 별칭
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        # 별칭으로 TR 코드 조회
        tr_code = self.tr_impl.get_tr_code_by_alias(alias)
        if not tr_code:
            logger.error(f"별칭 {alias}에 해당하는 TR 코드를 찾을 수 없습니다.")
            raise HTTPException(status_code=404, detail="TR 코드를 찾을 수 없습니다.")
        
        logger.info(f"별칭: {alias}, TR 코드: {tr_code}")
        
        # TR 데이터 요청
        return await self.get_tr_data_by_code(tr_code, params, continue_key)
    
    async def _get_tr_data(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> Dict[str, Any]:
        """
        TR 데이터를 요청하는 내부 메서드
        캐싱 정책에 따라 적절한 캐싱 처리를 수행
        Spring의 ProxyController.getTrData() 메서드에 해당
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        # TR 코드에 대한 TTL 값 조회
        ttl = self.tr_impl.get_cache_ttl(tr_code)
        logger.info(f"TR 코드: {tr_code}, TTL: {ttl}")
        
        # 캐시 삭제 제외 TR 코드인지 확인
        not_evict_tr_codes = self.tr_impl.get_not_evict_tr_codes()
        
        # 캐싱 정책에 따라 적절한 메서드 호출
        if tr_code in not_evict_tr_codes:
            # 캐싱 데코레이터를 활용한 메서드 호출
            return await self._get_tr_data_cached(tr_code, params, continue_key, 86400)  # 24시간 캐싱
        else:
            if ttl >= 28800:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 28800)  # 8시간 캐싱
            elif ttl >= 3600:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 3600)  # 1시간 캐싱
            elif ttl >= 1800:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 1800)  # 30분 캐싱
            elif ttl >= 600:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 600)   # 10분 캐싱
            elif ttl >= 60:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 60)    # 60초 캐싱
            elif ttl >= 30:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 30)    # 30초 캐싱
            elif ttl >= 10:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 10)    # 10초 캐싱
            elif ttl >= 3:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 3)     # 3초 캐싱
            elif ttl >= 2:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 2)     # 2초 캐싱
            elif ttl == 0:
                logger.info(f"TR 코드: {tr_code}는 캐싱하지 않음")
                return await self.tr_impl.request(tr_code, params, continue_key)
            else:
                return await self._get_tr_data_cached(tr_code, params, continue_key, 30)    # 기본 30초 캐싱
    
    @TrRepository.cached("dynamic", 0)  # TTL은 런타임에 결정됨
    async def _get_tr_data_cached(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None, ttl: int = 30) -> Dict[str, Any]:
        """
        캐싱을 적용한 TR 데이터 요청 메서드
        캐시 데코레이터가 적용되어 결과를 캐싱
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            ttl: 캐시 TTL (초 단위)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        logger.debug(f"{ttl}초 캐싱 적용: {tr_code}")
        return await self.tr_impl.request(tr_code, params, continue_key)