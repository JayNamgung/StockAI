"""
KB증권 TR 구현 모듈
KB증권 TR 요청을 처리하기 위한 TrInterface 구현
"""

import os
import json
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import asyncio

from agent.share.core.interface.tr_interface import TrInterface

logger = logging.getLogger(__name__)

class KbsecTr(TrInterface):
    """
    KB증권 TR 구현 클래스
    TrInterface를 구현하여 KB증권 TR 요청 처리
    """
    
    def __init__(self):
        """
        KB증권 TR 클래스 초기화
        설정 파일 로드 및 필요한 초기화 수행
        """
        self.channel_id = "3Aw"  # 채널 ID 설정
        
        # 캐시 설정 로드
        self.tr_rules = self._load_cache_config()
        
        # 별칭 매핑 구성
        self.alias_mapping = {}
        for key, value in self.tr_rules.items():
            alias = value.get("alias")
            if alias:
                self.alias_mapping[alias] = key
        
        # 스키마 캐시 초기화
        self.schema_cache = {}
        
        logger.info(f"KB증권 TR 클래스 초기화 완료: {len(self.tr_rules)} TR 코드, {len(self.alias_mapping)} 별칭")
    
    def _load_cache_config(self) -> Dict[str, Any]:
        """
        캐시 설정 파일을 로드하는 메서드
        
        Returns:
            Dict[str, Any]: 캐시 설정 정보
        """
        try:
            config_path = os.getenv("CACHE_CONFIG_PATH", 
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                            "config", "cache-config.json"))
            
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except FileNotFoundError:
            logger.warning(f"캐시 설정 파일을 찾을 수 없습니다. 기본 설정을 사용합니다: {config_path}")
            # 기본 설정 반환
            return {
                "mock_data": {
                    "ttl": 3600,
                    "description": "가상 데이터",
                    "alias": "mock_data"
                }
            }
        except Exception as e:
            logger.error(f"캐시 설정 로드 중 오류 발생: {str(e)}", exc_info=True)
            return {}
    
    async def request(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> Dict[str, Any]:
        """
        TR 요청을 수행하는 메서드
        Spring Boot의 ProxyService.getTrData() 메서드에 해당
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        logger.info(f"[TR-{tr_code}] 요청")
        
        try:
            # 특수 케이스 처리 (IVCA0060)
            if tr_code == "IVCA0060" and "indTypCd" in params:
                ind_typ_cd = params.get("indTypCd")
                logger.info(f"IVCA0060 호출: indTypCd는 {ind_typ_cd}")
                
                if ind_typ_cd == "001":
                    params["indxId"] = "KG001P"
                elif ind_typ_cd == "301":
                    params["indxId"] = "OG001P"
            
            # 여기서는 실제 KASS 라이브러리 호출 대신 목업 응답을 사용
            # 실제 구현에서는 KASS 라이브러리를 통해 TR 요청 처리
            raw_response = await self._execute_tr_request(tr_code, params, continue_key)
            
            # 응답 가공
            response = self._process_tr_response(raw_response)
            
            # 헤더 구성
            header = {
                "resultCode": "200",
                "resultMessage": "정상",
                "processFlag": "A",
                "category": "API"
            }
            
            if continue_key:
                header["contKey"] = continue_key + "_next"
            
            # 최종 응답 구성
            result = {
                "dataHeader": header,
                "dataBody": response
            }
            
            return result
            
        except Exception as e:
            logger.error(f"TR 요청 처리 중 오류 발생: {str(e)}", exc_info=True)
            raise
    
    async def _execute_tr_request(self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None) -> Dict[str, Any]:
        """
        실제 TR 요청을 실행하는 내부 메서드
        KASS 라이브러리를 통한 실제 TR 요청 처리를 담당
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 원시 응답 데이터
        """
        # TR 요청 처리 시간 시뮬레이션
        await asyncio.sleep(0.1)
        
        # 헤더 정보 구성
        header = {
            "rsp_cd": "0000",
            "rsp_msg": "정상처리되었습니다."
        }
        
        # TR 코드에 따른 목업 응답 생성
        response = {
            "TRX_HEADER": header
        }
        
        # TR 코드별 목업 데이터 생성
        if tr_code == "mock_data":
            response["userData"] = {
                "userId": params.get("userId", "unknown"),
                "name": "홍길동",
                "age": 30,
                "email": "hong@example.com"
            }
        elif tr_code == "IVCA0060":
            response["indxInfo"] = {
                "indxId": params.get("indxId", ""),
                "indxNm": "코스피 지수" if params.get("indxId") == "KG001P" else "해외 지수",
                "indxVal": "2456.78",
                "indxChg": "+12.34",
                "indxChgRt": "+0.5%"
            }
        else:
            # 기본 목업 데이터
            response[f"{tr_code}_data"] = {
                "result": "success",
                "timestamp": "2025-03-26T10:30:00",
                "requestParam": params
            }
            
            # 배열 데이터 예시
            if tr_code.startswith("K"):
                response["items"] = [
                    {"item_id": "1", "item_name": "항목1", "value": "100"},
                    {"item_id": "2", "item_name": "항목2", "value": "200"},
                    {"item_id": "3", "item_name": "항목3", "value": "300"}
                ]
        
        return response
    
    def _process_tr_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        TR 응답을 가공하는 내부 메서드
        Spring의 response 처리 로직에 해당
        
        Args:
            response: TR 원시 응답 데이터
            
        Returns:
            Dict[str, Any]: 가공된 TR 응답 데이터
        """
        result = {}
        
        # 응답 데이터 처리
        for key, value in response.items():
            # 특정 접두사를 가진 키는 제외
            if not key.startswith("_") and not key.startswith("TRX_HEADER") and not key.startswith("filler"):
                if isinstance(value, list):
                    # 배열 처리
                    array = []
                    for item in value:
                        if isinstance(item, dict):
                            child = {}
                            for child_key, child_value in item.items():
                                if not child_key.startswith("_") and not child_key.startswith("TRX_HEADER") and not child_key.startswith("filler"):
                                    child[child_key] = child_value
                            array.append(child)
                    result[key] = array
                else:
                    result[key] = value
        
        return result
    
    async def get_schema(self, tr_code: str) -> Dict[str, Any]:
        """
        TR 스키마 정보를 반환하는 메서드
        
        Args:
            tr_code: TR 코드
            
        Returns:
            Dict[str, Any]: TR 입출력 스키마 정보
        """
        # 스키마 캐시에서 확인
        if tr_code in self.schema_cache:
            return self.schema_cache[tr_code]
        
        # 스키마 파일 경로
        schema_path = os.path.join(os.path.dirname(__file__), "schema", f"{tr_code}.xml")
        
        try:
            # XML 파일 파싱
            tree = ET.parse(schema_path)
            root = tree.getroot()
            
            # 입력 스키마 구성
            inputs = []
            input_elem = root.find("Input")
            if input_elem is not None:
                for field in input_elem.findall("I"):
                    inputs.append({
                        "name": field.get("Name", ""),
                        "align": field.get("Align", "Left"),
                        "desc": field.get("Desc", "")
                    })
            
            # 출력 스키마 구성
            outputs = []
            output_elem = root.find("Output")
            if output_elem is not None:
                for field in output_elem.findall("O"):
                    outputs.append({
                        "name": field.get("Name", ""),
                        "align": field.get("Align", "Left"),
                        "desc": field.get("Desc", "")
                    })
            
            # 스키마 정보 구성
            schema = {
                "inputs": inputs,
                "outputs": outputs
            }
            
            # 스키마 캐시에 저장
            self.schema_cache[tr_code] = schema
            
            return schema
            
        except FileNotFoundError:
            logger.warning(f"스키마 파일을 찾을 수 없습니다: {schema_path}")
            return {"inputs": [], "outputs": []}
            
        except Exception as e:
            logger.error(f"스키마 파싱 중 오류 발생: {str(e)}", exc_info=True)
            return {"inputs": [], "outputs": []}
    
    def get_cache_ttl(self, tr_code: str) -> int:
        """
        TR 코드에 대한 캐시 TTL 값을 반환
        Spring의 getTtlByCode() 메서드에 해당
        
        Args:
            tr_code: TR 코드
            
        Returns:
            int: 캐시 TTL (초 단위)
        """
        tr = self.tr_rules.get(tr_code, {})
        if not tr:
            return 30  # 기본 TTL
        
        return tr.get("ttl", 30)
    
    def get_tr_code_by_alias(self, alias: str) -> Optional[str]:
        """
        별칭에 해당하는 TR 코드를 반환
        Spring의 getTrCodeByAlias() 메서드에 해당
        
        Args:
            alias: TR 별칭
            
        Returns:
            Optional[str]: TR 코드 또는 None
        """
        return self.alias_mapping.get(alias)
    
    def get_not_evict_tr_codes(self) -> List[str]:
        """
        캐시 삭제 대상에서 제외할 TR 코드 목록을 반환
        Spring의 getNotEvictTrCodes() 메서드에 해당
        
        Returns:
            List[str]: 캐시 삭제 제외 TR 코드 목록
        """
        # 하드코딩된 예외 목록 (실제 구현에서는 설정에서 로드 가능)
        return ["KBI50130"]
