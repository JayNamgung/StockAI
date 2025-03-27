from typing import AsyncGenerator, Dict, Any, Optional
import logging
from fastapi import Depends, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.share.core.interface.tr_interface import TrInterface
from agent.share.core.tr.tr_kbsec import KbsecTr
from agent.share.repository.tr_repository import TrRepository

logger = logging.getLogger(__name__)

class TrManager:
    """
    TR 관리자
    TR 요청 및 캐싱을 조율
    """
    
    def __init__(self, tr_repo: TrRepository):
        """
        TR 관리자 초기화
        
        Args:
            tr_repo: TR 저장소
        """
        self.tr_repo = tr_repo
        
        # 스케줄러 초기화
        self.scheduler = AsyncIOScheduler()
        
        # 매일 오전 8시에 캐시 초기화 작업 스케줄링
        self.scheduler.add_job(
            self.tr_repo.evict_all_caches_at_intervals,
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
    
    async def get_tr_data_by_code(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        TR 코드로 데이터를 요청
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        return await self.tr_repo.request_tr(tr_code, params, continue_key)
    
    async def get_tr_data_by_alias(
        self, alias: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        TR 별칭으로 데이터를 요청
        
        Args:
            alias: TR 별칭
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        # 별칭으로 TR 코드 조회
        tr_code = self.tr_repo.tr.get_tr_code_by_alias(alias)
        if not tr_code:
            return {
                "dataHeader": {
                    "resultCode": "404",
                    "resultMessage": f"별칭 {alias}에 해당하는 TR 코드를 찾을 수 없습니다.",
                    "processFlag": "E",
                    "category": "API"
                },
                "dataBody": {}
            }
        
        logger.info(f"별칭: {alias}, TR 코드: {tr_code}")
        
        # TR 데이터 요청
        return await self.get_tr_data_by_code(tr_code, params, continue_key)