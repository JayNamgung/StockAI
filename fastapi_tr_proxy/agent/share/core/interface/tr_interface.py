"""
TR 인터페이스 정의 모듈
여러 증권사 TR 구현을 위한 공통 인터페이스 제공
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class TrInterface(ABC):
    """
    TR(Transaction) 인터페이스 추상 클래스
    모든 증권사별 TR 구현체가 따라야 하는 인터페이스 정의
    """
    
    @abstractmethod
    async def request(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> Dict[str, Any]:
        """
        TR 요청을 수행하는 메서드
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        pass
    
    @abstractmethod
    async def get_schema(self, tr_code: str) -> Dict[str, Any]:
        """
        TR 스키마 정보를 반환하는 메서드
        
        Args:
            tr_code: TR 코드
            
        Returns:
            Dict[str, Any]: TR 입출력 스키마 정보
        """
        pass
    
    @abstractmethod
    def get_cache_ttl(self, tr_code: str) -> int:
        """
        TR 코드에 대한 캐시 TTL(Time-To-Live) 값을 반환
        
        Args:
            tr_code: TR 코드
            
        Returns:
            int: 캐시 TTL (초 단위)
        """
        pass
    
    @abstractmethod
    def get_tr_code_by_alias(self, alias: str) -> Optional[str]:
        """
        별칭에 해당하는 TR 코드를 반환
        
        Args:
            alias: TR 별칭
            
        Returns:
            Optional[str]: TR 코드 또는 None
        """
        pass
    
    @abstractmethod
    def get_not_evict_tr_codes(self) -> List[str]:
        """
        캐시 삭제 대상에서 제외할 TR 코드 목록을 반환
        
        Returns:
            List[str]: 캐시 삭제 제외 TR 코드 목록
        """
        pass